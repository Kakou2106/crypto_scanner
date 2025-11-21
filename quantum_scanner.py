#!/usr/bin/env python3
# quantum_scanner_ultime.py
# Ultra base monolithique version

import os, re, json, sqlite3, asyncio, logging, sys, random
from datetime import datetime
import aiohttp

# ---------------- Logging ----------------
def setup_logging(verbose=False):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    logger.handlers = [h]

def log_exception(ctx, exc):
    logging.error(f"Exception in {ctx}: {exc}", exc_info=True)

# ---------------- Storage ----------------
DB_PATH = os.getenv("DB_PATH", "quantum.db")

def get_conn(): return sqlite3.connect(DB_PATH)

def init_db():
    c = get_conn(); cur = c.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS projects(
        id INTEGER PRIMARY KEY, name TEXT, source TEXT, link TEXT UNIQUE,
        announced_at TEXT, raw_json TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS scan_history(
        id INTEGER PRIMARY KEY, link TEXT, scanned_at TEXT,
        verdict TEXT, score REAL, report_json TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS blacklists(
        id INTEGER PRIMARY KEY, kind TEXT, value TEXT UNIQUE)""")
    c.commit(); c.close()

def save_project_candidate(p):
    c=get_conn();cur=c.cursor()
    cur.execute("INSERT OR IGNORE INTO projects(name,source,link,announced_at,raw_json) VALUES(?,?,?,?,?)",
                (p.get("name"),p.get("source"),p.get("link"),p.get("announced_at"),json.dumps(p)))
    c.commit();c.close()

def save_scan_result(p,v):
    c=get_conn();cur=c.cursor()
    cur.execute("INSERT INTO scan_history(link,scanned_at,verdict,score,report_json) VALUES(?,?,?,?,?)",
                (p.get("link"),datetime.utcnow().isoformat(),v.get("verdict"),v.get("score"),json.dumps(v.get("report"))))
    c.commit();c.close()
    os.makedirs("results",exist_ok=True)
    with open(f"results/{p.get('name','unknown')}.json","w") as f: json.dump({"project":p,"verdict":v},f,indent=2)

def is_blacklisted_domain(d):
    if not d: return False
    c=get_conn();cur=c.cursor();cur.execute("SELECT 1 FROM blacklists WHERE kind='domain' AND value=?",(d,))
    r=cur.fetchone();c.close();return bool(r)

def is_blacklisted_contract(a):
    if not a: return False
    c=get_conn();cur=c.cursor();cur.execute("SELECT 1 FROM blacklists WHERE kind='contract' AND value=?",(a.lower(),))
    r=cur.fetchone();c.close();return bool(r)

# ---------------- Performance ----------------
def with_backoff(fn, retries=3):
    async def wrapper():
        delay=0.5
        for _ in range(retries):
            try: return await fn()
            except Exception as e: await asyncio.sleep(delay+random.random()*0.5); delay=min(5.0,delay*2)
        return []
    return wrapper

# ---------------- Metrics ----------------
class Metrics:
    def __init__(self): self.verdicts={}; self.started=datetime.utcnow()
    def record(self,v): self.verdicts[v]=self.verdicts.get(v,0)+1
    def summary(self): return {"started":self.started.isoformat(),"verdicts":self.verdicts}

# ---------------- Ratios ----------------
def clamp01(x): return max(0.0,min(1.0,float(x)))
DEFAULT_WEIGHTS={"mc_fdmc":0.1,"circ_vs_total":0.1,"volume_mc":0.1,"liquidity_ratio":0.1,"whale_concentration":0.1}

def calculer_21_ratios(p):
    mc=float(p.get("mc_eur") or 1); fdmc=float(p.get("fdmc_eur") or mc)
    circ=float(p.get("circulating_supply") or 1); total=float(p.get("total_supply") or circ)
    vol=float(p.get("volume_24h_eur") or 0); liq=float(p.get("dex_liquidity_eur") or 0); top10=float(p.get("top10_holders_share") or 0)
    return {"mc_fdmc":mc/fdmc if fdmc>0 else 0,"circ_vs_total":circ/total if total>0 else 0,
            "volume_mc":vol/mc if mc>0 else 0,"liquidity_ratio":liq/mc if mc>0 else 0,"whale_concentration":clamp01(top10)}

def score_from_ratios(r):
    s=0
    for k,w in DEFAULT_WEIGHTS.items():
        val=r.get(k,0); 
        if k=="whale_concentration": val=1-val
        s+=clamp01(val)*w
    return round(s*100,2)

# ---------------- Verifier ----------------
async def quick_site_content_check(txt): return bool(txt and len(txt.strip())>=200)

async def verify_project(p,go_score=70,max_mc=210000):
    report={"red_flags":[]}
    if not await quick_site_content_check(p.get("website_content","")): report["red_flags"].append("poor_site")
    if is_blacklisted_domain(p.get("website_domain")): report["red_flags"].append("scam_domain")
    if p.get("contract_address") and is_blacklisted_contract(p.get("contract_address")): report["red_flags"].append("scam_contract")
    ratios=calculer_21_ratios(p); score=score_from_ratios(ratios); report["ratios"]=ratios
    if report["red_flags"]: verdict="REJECT"; reason="Critical fail"
    elif not p.get("coingecko_listed",False): verdict="REVIEW"; reason="Missing CG listing"
    elif score>=go_score and (p.get("mc_eur") or 0)<=max_mc: verdict="ACCEPT"; reason="All good"
    else: verdict="REVIEW"; reason="Score/MC out of bounds"
    return {"verdict":verdict,"score":score,"reason":reason,"report":report}

# ---------------- Alerts ----------------
async def send_alert(p,v):
    if os.getenv("TELEGRAM_ENABLED","false").lower()!="true": return
    token=os.getenv("TELEGRAM_BOT_TOKEN"); chat=os.getenv("TELEGRAM_CHAT_ID") if v["verdict"]=="ACCEPT" else os.getenv("TELEGRAM_CHAT_REVIEW")
    if not token or not chat: return
    text=f"🌌 {p.get('name')} | SCORE {v['score']} | {v['verdict']}\nRed flags: {','.join(v['report']['red_flags'])}"
    async with aiohttp.ClientSession() as s:
        await s.post(f"https://api.telegram.org/bot{token}/sendMessage",json={"chat_id":chat,"text":text})

# ---------------- Sources stubs ----------------
async def fetch_binance():
    await asyncio.sleep(0)
    return [{"name":"BinanceSample","link":"https://binance.com/x","source":"binance","announced_at":datetime.utcnow().isoformat()}]

async def fetch_polkastarter():
    await asyncio.sleep(0)
    return [{"name":"PolkaSample","link":"https://polkastarter.com/x","source":"polkastarter","announced_at":datetime.utcnow().isoformat()}]

async def enrich_market_data(p):
    p=dict(p); p.update({"website_domain":"example.com","website_content":"ok "*100,"mc_eur":150000,"fdmc_eur":300000,
                         "circulating_supply":1e6,"total_supply":5e6,"volume_24h_eur":10000,"dex_liquidity_eur":20000,
                         "top10_holders_share":0.3,"coingecko_listed":False})
    return p

# ---------------- Core ----------------
async def gather_candidates():
    res=await asyncio.gather(with_backoff(fetch_binance)(),with_backoff(fetch_polkastarter)())
    cands=[]; [cands.extend(r) for r in res if isinstance(r,list)]; return cands

async def process_candidate(p,dry,metrics):
    save_project_candidate(p); enriched=await enrich_market_data(p); v=await verify_project(enriched)
    save_scan_result(enriched,v); metrics.record(v["verdict"]); 
    if not dry and v["verdict"] in ("REVIEW","ACCEPT"): await send_alert(enriched,v)
    return v

async def run_once(dry=False,test=None):
    metrics=Metrics()
    if test: await process_candidate({"name":"Test","link":test,"source":"manual","announced_at":datetime.utcnow().isoformat()},dry,metrics)
    else:
        for p in (await gather_candidates())[:5]: await process_candidate(p,dry,metrics)
    print(metrics.summary())

# ---------------- CLI ----------------
import argparse
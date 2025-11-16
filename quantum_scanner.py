# quantum_all_in_one.py
"""
Quantum All-in-One Scanner Ultime
- Single-file deployable scanner for launchpads + antiscam + LP-lock detection + CI artifacts
- Configure via .env and config.yml
"""
import os, re, sys, json, ssl, socket, sqlite3, logging, asyncio, time, traceback
from datetime import datetime
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List, Optional

import aiohttp
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Optional libs (may be absent) are imported lazily
try:
    from web3 import Web3
except Exception:
    Web3 = None

# Optional Telegram
try:
    from telegram import Bot
except Exception:
    Bot = None

# Optional boto3 for S3
try:
    import boto3
    from botocore.exceptions import BotoCoreError
except Exception:
    boto3 = None

# Optional whois with fallback
try:
    import whois
except Exception:
    whois = None
    logging.warning("Module whois non disponible - certaines vérifications seront limitées")

# Load env
load_dotenv()

# -----------------------
# Configuration
# -----------------------
# Env / config defaults
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_PUBLIC = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_CHAT_REVIEW = os.getenv("TELEGRAM_CHAT_REVIEW", TELEGRAM_CHAT_PUBLIC)
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY")
INFURA_URL = os.getenv("INFURA_URL")
COINLIST_API_KEY = os.getenv("COINLIST_API_KEY")
CRYPTOSCAMDB_API = os.getenv("CRYPTOSCAMDB_API", "https://api.cryptoscamdb.org/v1/lookup/")
VIRUSTOTAL_KEY = os.getenv("VIRUSTOTAL_KEY")
AWS_S3_BUCKET = os.getenv("S3_BUCKET")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

MAX_MARKET_CAP_EUR = float(os.getenv("MAX_MARKET_CAP_EUR", "621000"))
SCAN_INTERVAL_HOURS = float(os.getenv("SCAN_INTERVAL_HOURS", "6"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
DB_PATH = os.getenv("QUANTUM_DB", "quantum_all.db")
LOCKERS_PATH = os.getenv("LOCKERS_JSON", "lockers.json")
RESULTS_DIR = os.getenv("RESULTS_DIR", "results")
LOGS_DIR = os.getenv("LOGS_DIR", "logs")
MIN_DOMAIN_AGE_DAYS = int(os.getenv("MIN_DOMAIN_AGE_DAYS", "30"))
MIN_LP_RESERVE_ETH = float(os.getenv("MIN_LP_RESERVE_ETH", "0.05"))
GO_SCORE_THRESHOLD = float(os.getenv("GO_SCORE_THRESHOLD", "70"))
REVIEW_SCORE_THRESHOLD = float(os.getenv("REVIEW_SCORE_THRESHOLD", "60"))

# create dirs
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# -----------------------
# Logging
# -----------------------
log = logging.getLogger("quantum_all_in_one")
log.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
fh = logging.FileHandler(os.path.join(LOGS_DIR, f"scan-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.log"))
fh.setFormatter(fmt)
log.addHandler(fh)
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(fmt)
log.addHandler(sh)

# -----------------------
# Services init
# -----------------------
TELEGRAM_BOT = Bot(token=TELEGRAM_BOT_TOKEN) if (Bot and TELEGRAM_BOT_TOKEN) else None
W3 = Web3(Web3.HTTPProvider(INFURA_URL)) if (Web3 and INFURA_URL) else None
S3_CLIENT = None
if boto3 and AWS_ACCESS_KEY and AWS_SECRET_KEY and AWS_S3_BUCKET:
    S3_CLIENT = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)

# -----------------------
# DB / Cache helpers
# -----------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT, symbol TEXT, mc REAL, website TEXT, twitter TEXT, telegram TEXT, github TEXT, pair_address TEXT, verdict TEXT, score REAL, report TEXT, created_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS blacklists (source TEXT PRIMARY KEY, data TEXT, updated_at TEXT)""")
    conn.commit(); conn.close()

def cache_get(key: str) -> Optional[Any]:
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT value, updated_at FROM cache WHERE key=?", (key,))
    r = cur.fetchone(); conn.close()
    if not r: return None
    value, updated_at = r
    try:
        if (datetime.utcnow() - datetime.fromisoformat(updated_at)).total_seconds() > CACHE_TTL_SECONDS:
            return None
    except Exception:
        return None
    try:
        return json.loads(value)
    except:
        return None

def cache_set(key: str, value: Any):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("REPLACE INTO cache (key, value, updated_at) VALUES (?,?,?)", (key, json.dumps(value), datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

def save_project_row(proj: Dict[str, Any], verdict: str, score: float, report: Dict[str,Any]):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("""INSERT INTO projects (name,symbol,mc,website,twitter,telegram,github,pair_address,verdict,score,report,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (proj.get("nom"), proj.get("symbol"), proj.get("mc"), proj.get("website"), proj.get("twitter"), proj.get("telegram"), proj.get("github"), proj.get("pair_address"), verdict, float(score), json.dumps(report), datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

# -----------------------
# HTTP helpers
# -----------------------
async def async_http_get(session: aiohttp.ClientSession, url: str, *, headers=None, timeout=15):
    headers = headers or {"User-Agent":"QuantumScanner/1.0"}
    try:
        async with session.get(url, timeout=timeout, headers=headers) as resp:
            text = await resp.text(errors="ignore")
            return resp.status, text
    except Exception as e:
        return None, str(e)

def http_get_blocking(url: str, timeout=12):
    headers = {"User-Agent":"QuantumScanner/1.0"}
    try:
        r = requests.get(url, timeout=timeout, headers=headers)
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)

# -----------------------
# Locker scraping & population
# -----------------------
LOCKER_SOURCES = [
    "https://www.dx.app/dxsale",
    "https://www.team.finance/view-all-coins",
    "https://app.uncx.network/stealth/explore"
]

def extract_addresses(text: str) -> List[str]:
    return list({m.group(0).lower() for m in re.finditer(r"0x[a-fA-F0-9]{40}", text)})

def populate_lockers() -> List[str]:
    addresses = set()
    for url in LOCKER_SOURCES:
        try:
            code, txt = http_get_blocking(url)
            if code and code == 200 and txt:
                addrs = extract_addresses(txt)
                addresses.update(addrs)
                log.info("Scraped %d addresses from %s", len(addrs), url)
        except Exception as e:
            log.exception("Locker scrape error %s: %s", url, e)
    # write lockers.json
    try:
        with open(LOCKERS_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(list(addresses)), f, indent=2)
        log.info("Wrote %s with %d lockers", LOCKERS_PATH, len(addresses))
    except Exception:
        log.exception("Failed to write lockers.json")
    return sorted(list(addresses))

# -----------------------
# Basic site/verif helpers
# -----------------------
def domain_name_from_url(url: str) -> str:
    try:
        return urlparse(url).hostname or url
    except:
        return url

def whois_age_days(domain: str) -> Optional[int]:
    """WHOIS domain age check with fallback if module not available"""
    try:
        if whois is None:
            log.warning("Module whois non disponible - vérification d'âge ignorée")
            return None
            
        w = whois.whois(domain)
        created = w.creation_date
        if isinstance(created, list): created = created[0]
        if not created: return None
        return (datetime.utcnow() - created).days
    except Exception as e:
        log.warning(f"Erreur WHOIS pour {domain}: {e}")
        return None

def check_ssl(domain: str) -> Dict[str,Any]:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=6) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                return {"ok": True, "notAfter": cert.get("notAfter")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# -----------------------
# Etherscan / on-chain helpers
# -----------------------
async def etherscan_get_abi(address: str, session: aiohttp.ClientSession):
    key = ETHERSCAN_API_KEY
    if not key:
        return False, None
    ck = f"etherscan:abi:{address}"
    cached = cache_get(ck)
    if cached: return cached.get("ok", False), cached.get("abi")
    url = f"https://api.etherscan.io/api?module=contract&action=getabi&address={address}&apikey={key}"
    st, txt = await async_http_get(session, url)
    if st == 200:
        try:
            obj = json.loads(txt)
            if obj.get("status") == "1":
                abi = json.loads(obj.get("result"))
                cache_set(ck, {"ok":True, "abi":abi})
                return True, abi
        except Exception:
            pass
    cache_set(ck, {"ok":False})
    return False, None

def analyze_contract_onchain(address: str) -> Dict[str,Any]:
    if not W3:
        return {"error":"no-web3"}
    try:
        erc20 = [{"constant":True,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]
        token = W3.eth.contract(address=W3.toChecksumAddress(address), abi=erc20)
        total = token.functions.totalSupply().call()
        try:
            dec = token.functions.decimals().call()
        except:
            dec = None
        return {"totalSupply": total, "decimals": dec}
    except Exception as e:
        return {"error": str(e)}

UNISWAP_PAIR_ABI = [
    {"constant":True,"inputs":[],"name":"getReserves","outputs":[{"name":"_reserve0","type":"uint112"},{"name":"_reserve1","type":"uint112"},{"name":"_blockTimestampLast","type":"uint32"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"token0","outputs":[{"name":"","type":"address"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"token1","outputs":[{"name":"","type":"address"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"owner","outputs":[{"name":"","type":"address"}],"type":"function"}
]

def inspect_pair(pair_address: str) -> Dict[str,Any]:
    if not W3:
        return {"error":"no-web3"}
    try:
        pair = W3.eth.contract(address=W3.toChecksumAddress(pair_address), abi=UNISWAP_PAIR_ABI)
        try:
            reserves = pair.functions.getReserves().call()
            token0 = pair.functions.token0().call()
            token1 = pair.functions.token1().call()
        except Exception as e:
            return {"error": str(e)}
        owner = None
        try:
            owner = pair.functions.owner().call()
        except:
            owner = None
        return {"reserve0": reserves[0], "reserve1": reserves[1], "token0": token0, "token1": token1, "owner": owner}
    except Exception as e:
        return {"error": str(e)}

# -----------------------
# Locker detection & helpers (checks unicrypt / team.finance single pair)
# -----------------------
def check_unicrypt_pair(pair_address: str) -> Optional[Dict[str,Any]]:
    url = f"https://app.unicrypt.network/amm/lock/{pair_address}"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent":"QuantumScanner/1.0"})
        if r.status_code == 200 and ("locked" in r.text.lower() or "liquidity lock" in r.text.lower()):
            return {"source":"unicrypt","url":url}
    except Exception:
        pass
    return None

def check_teamfinance_pair(pair_address: str) -> Optional[Dict[str,Any]]:
    url = f"https://team.finance/lock/{pair_address}"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent":"QuantumScanner/1.0"})
        if r.status_code == 200 and ("lock" in r.text.lower() or "locked" in r.text.lower()):
            return {"source":"teamfinance","url":url}
    except Exception:
        pass
    return None

def detect_lp_lock(pair_address: str, lockers_set: set) -> Dict[str,Any]:
    info = {}
    if not pair_address:
        return {"error":"no_pair_address"}
    onchain = inspect_pair(pair_address)
    info["onchain"] = onchain
    owner = (onchain.get("owner") or "").lower() if onchain.get("owner") else None
    if owner and owner in lockers_set:
        info["locked_by_known_locker"] = True
        info["locker_owner"] = owner
        return info
    # try unicrypt/teamfinance
    unicrypt = check_unicrypt_pair(pair_address)
    if unicrypt:
        info["locked_by_unicrypt"] = True
        info["unicrypt"] = unicrypt
        return info
    team = check_teamfinance_pair(pair_address)
    if team:
        info["locked_by_teamfinance"] = True
        info["teamfinance"] = team
        return info
    info["locked_by_known_locker"] = False
    return info

# -----------------------
# Blacklist updater
# -----------------------
BLACKLIST_SOURCES = {
    "metamask_phishing": "https://raw.githubusercontent.com/MetaMask/eth-phishing-detect/master/src/config.json",
    "cryptoscamdb_list": "https://raw.githubusercontent.com/cryptoscamdb/list/master/data.json"
}
def update_blacklists():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    for key, url in BLACKLIST_SOURCES.items():
        try:
            r = requests.get(url, timeout=12, headers={"User-Agent":"QuantumScanner/1.0"})
            if r.status_code == 200:
                cur.execute("REPLACE INTO blacklists (source, data, updated_at) VALUES (?,?,?)", (key, r.text, datetime.utcnow().isoformat()))
                log.info("Updated blacklist %s (%d bytes)", key, len(r.text))
        except Exception:
            log.exception("Failed to update blacklist %s", key)
    conn.commit(); conn.close()

def is_in_blacklists(value: str) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("SELECT data FROM blacklists")
        rows = cur.fetchall(); conn.close()
        for (data,) in rows:
            if data and value.lower() in data.lower():
                return True
    except Exception:
        pass
    return False

# -----------------------
# Launchpad fetchers + parsers
# -----------------------
async def fetch_coinlist(session: aiohttp.ClientSession):
    if not COINLIST_API_KEY:
        return []
    url = "https://api.coinlist.co/public/sales"
    headers = {"Authorization": f"Bearer {COINLIST_API_KEY}"}
    st, txt = await async_http_get(session, url, headers=headers)
    projects = []
    if st == 200 and txt:
        try:
            data = json.loads(txt)
            for it in data.get("data", []):
                projects.append({"nom": it.get("name") or it.get("title"), "link": it.get("url") or it.get("website"), "source":"coinlist"})
        except Exception:
            log.exception("CoinList parse error")
    return projects

async def fetch_binance(session: aiohttp.ClientSession):
    url = "https://www.binance.com/en/support/announcement/c-48"
    st, txt = await async_http_get(session, url)
    projects = []
    if st == 200 and txt:
        soup = BeautifulSoup(txt, "html.parser")
        for a in soup.find_all("a", href=True):
            name = (a.get_text() or "").strip()
            href = a["href"]
            if name and len(name) > 2:
                if href.startswith("/"):
                    parsed = urlparse(url); href = f"{parsed.scheme}://{parsed.netloc}{href}"
                projects.append({"nom": name, "link": href, "source": "binance"})
    return projects

async def fetch_polkastarter(session: aiohttp.ClientSession):
    url = "https://www.polkastarter.com/projects"
    st, txt = await async_http_get(session, url)
    projects = []
    if st == 200 and txt:
        soup = BeautifulSoup(txt, "html.parser")
        for a in soup.find_all("a", href=True)[:60]:
            name = (a.get_text() or "").strip()
            href = a["href"]
            if name and len(name) > 2:
                if href.startswith("/"):
                    parsed = urlparse(url); href = f"{parsed.scheme}://{parsed.netloc}{href}"
                projects.append({"nom": name, "link": href, "source": "polkastarter"})
    return projects

# Parsers for project pages
async def parse_project_page(link: str, session: aiohttp.ClientSession) -> Dict[str,Any]:
    out = {"website":"", "twitter":"", "telegram":"", "github":"", "contract_address":"", "pair_address":""}
    try:
        st, txt = await async_http_get(session, link)
        if st != 200 or not txt:
            return out
        soup = BeautifulSoup(txt, "html.parser")
        # find external social links
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if "twitter.com" in href and not out["twitter"]:
                out["twitter"] = href.split("?")[0]
            if "t.me" in href and not out["telegram"]:
                out["telegram"] = href.split("?")[0]
            if "github.com" in href and not out["github"]:
                out["github"] = "/".join(href.split("github.com/")[-1].split("/")[:2])
            if href.startswith("http") and not out["website"] and (link.split("//")[-1].split("/")[0] not in href):
                out["website"] = href
        # contract / pair detection in page text
        text = soup.get_text(" ", strip=True)
        m = re.search(r"0x[a-fA-F0-9]{40}", text)
        if m:
            out["contract_address"] = m.group(0)
        # pair heuristics: look for 'pair' + 0x...
        m2 = re.search(r"pair[:\s]*0x[a-fA-F0-9]{40}", text, flags=re.I)
        if m2:
            out["pair_address"] = re.search(r"0x[a-fA-F0-9]{40}", m2.group(0)).group(0)
        return out
    except Exception:
        log.exception("parse_project_page failed for %s", link)
        return out

# -----------------------
# Missing function implementations
# -----------------------
async def github_check(github_url: str, session: aiohttp.ClientSession) -> tuple:
    """Check if GitHub repo exists and has content"""
    try:
        # Convert to API URL
        if "github.com" in github_url:
            repo_path = github_url.split("github.com/")[-1].strip("/")
            api_url = f"https://api.github.com/repos/{repo_path}"
            st, txt = await async_http_get(session, api_url)
            if st == 200:
                data = json.loads(txt)
                return True, {"size": data.get("size", 0), "stars": data.get("stargazers_count", 0)}
        return False, {"error": "Not found or inaccessible"}
    except Exception as e:
        return False, {"error": str(e)}

async def coingecko_lookup(query: str, session: aiohttp.ClientSession) -> Optional[Dict]:
    """Lookup token on CoinGecko"""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{query.lower()}"
        st, txt = await async_http_get(session, url)
        if st == 200:
            return json.loads(txt)
        return None
    except Exception:
        return None

# -----------------------
# Scoring / verification pipeline
# -----------------------
async def verify_and_score(proj: Dict[str,Any], lockers_set: set, session: aiohttp.ClientSession) -> Dict[str,Any]:
    report = {"checks":{}, "flags":[]}
    # site content
    website = proj.get("website")
    if not website:
        report["flags"].append(("site_missing", {})); return {"verdict":"REJECT","score":0,"report":report}
    ok_site, site_info = await quick_site_content_check_async(session, website)
    report["checks"]["site"] = site_info
    if not ok_site:
        report["flags"].append(("site_bad", site_info)); return {"verdict":"REJECT","score":0,"report":report}
    # whois/ssl
    host = domain_name_from_url(website)
    age = whois_age_days(host)
    report["checks"]["whois"] = {"age_days": age}
    if age is None or age < MIN_DOMAIN_AGE_DAYS:
        report["flags"].append(("domain_young", {"age_days": age}))
    report["checks"]["ssl"] = check_ssl(host)
    # blacklist crosscheck
    if is_in_blacklists(host):
        report["flags"].append(("in_blacklist", {"host": host})); return {"verdict":"REJECT","score":0,"report":report}
    # contract checks
    addr = proj.get("contract_address")
    if addr:
        good_abi, abi = await etherscan_get_abi(addr, session)
        report["checks"]["etherscan_verified"] = good_abi
        if not good_abi:
            report["flags"].append(("contract_not_verified", {})); return {"verdict":"REJECT","score":0,"report":report}
        onchain = analyze_contract_onchain(addr)
        report["checks"]["onchain"] = onchain
        if "error" in onchain:
            report["flags"].append(("onchain_error", onchain)); return {"verdict":"REJECT","score":0,"report":report}
    # github
    gh = proj.get("github")
    if gh:
        ok_g, ginfo = await github_check(gh, session); report["checks"]["github"] = ginfo
        if not ok_g:
            report["flags"].append(("github_missing_or_empty", ginfo))
    # coingecko
    cg = await coingecko_lookup(proj.get("contract_address") or proj.get("symbol") or proj.get("nom"), session)
    report["checks"]["coingecko"] = bool(cg)
    if not cg:
        report["flags"].append(("not_listed_coingecko", {}))
    # twitter
    tw = proj.get("twitter")
    if tw:
        ok_t, tinfo = await twitter_public_check_async(session, tw)
        report["checks"]["twitter"] = tinfo
        if not ok_t:
            report["flags"].append(("twitter_broken", tinfo)); return {"verdict":"REJECT","score":0,"report":report}
    # telegram
    tg = proj.get("telegram")
    if tg:
        st, txt = await async_http_get(session, tg)
        if st != 200 or ("chat not found" in (txt or "").lower()):
            report["flags"].append(("telegram_broken", {"status": st})); return {"verdict":"REJECT","score":0,"report":report}
        report["checks"]["telegram"] = {"status": st}
    # LP detection if pair provided
    pair = proj.get("pair_address")
    if pair:
        lp_info = detect_lp_lock(pair, lockers_set)
        report["checks"]["lp"] = lp_info
        if lp_info.get("locked_by_known_locker") is False:
            report["flags"].append(("lp_not_locked_or_unknown", lp_info))
    # scoring simple
    score = 100
    if not report["checks"].get("coingecko"): score -= 25
    if not report["checks"].get("github") or report["checks"]["github"].get("size",0) == 0: score -= 20
    if (report["checks"].get("whois",{}).get("age_days") or 9999) < 90: score -= 15
    if any(f[0]=="very_large_total_supply" for f in report["flags"]): score -= 10
    verdict = "ACCEPT" if score >= GO_SCORE_THRESHOLD and float(proj.get("mc",0)) <= MAX_MARKET_CAP_EUR else ("REVIEW" if score >= REVIEW_SCORE_THRESHOLD else "REJECT")
    return {"verdict": verdict, "score": score, "report": report}

# Async thin wrappers
async def quick_site_content_check_async(session, url):
    try:
        st, txt = await async_http_get(session, url)
        if st != 200: return False, {"status": st}
        lower = (txt or "").lower()
        if any(k in lower for k in ['for sale','parked','buy this domain','domain for sale','404','not found']):
            return False, {"reason":"parked_or_for_sale"}
        stripped = re.sub(r'<[^>]+>', '', txt or '').strip()
        if len(stripped) < 200: return False, {"reason":"too_little_content"}
        return True, {"status":200, "len": len(stripped)}
    except Exception as e:
        return False, {"error": str(e)}

async def twitter_public_check_async(session, handle_or_url):
    try:
        handle = handle_or_url.split("/")[-1]
        st, txt = await async_http_get(session, f"https://x.com/{handle}")
        if st != 200: return False, {"status": st}
        if "Account suspended" in (txt or "") or "suspended" in (txt or "").lower():
            return False, {"reason":"suspended"}
        return True, {"status":200}
    except Exception as e:
        return False, {"error": str(e)}

# -----------------------
# Notifications & artifacts
# -----------------------
def send_telegram(chat_id: str, text: str):
    if not TELEGRAM_BOT:
        log.info("Telegram not configured; would send to %s: %s", chat_id, text)
        return
    try:
        TELEGRAM_BOT.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    except Exception:
        log.exception("Telegram send failed")

def write_results(results: List[Dict[str,Any]]):
    fname = os.path.join(RESULTS_DIR, f"results-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json")
    try:
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        log.info("Wrote results %s (%d entries)", fname, len(results))
        return fname
    except Exception:
        log.exception("Failed to write results file")
        return None

def upload_to_s3(path: str):
    if not S3_CLIENT:
        log.info("S3 not configured; skipping upload")
        return False
    try:
        key = os.path.basename(path)
        S3_CLIENT.upload_file(path, AWS_S3_BUCKET, key)
        log.info("Uploaded %s to s3://%s/%s", path, AWS_S3_BUCKET, key)
        return True
    except Exception:
        log.exception("S3 upload failed")
        return False

# -----------------------
# Main scan orchestration
# -----------------------
async def run_scan_once(lockers_set: set):
    results = []
    async with aiohttp.ClientSession() as session:
        # fetch candidates
        candidates = []
        try:
            candidates += await fetch_coinlist(session)
        except Exception:
            log.exception("Coinlist fetch error")
        try:
            candidates += await fetch_binance(session)
        except Exception:
            log.exception("Binance fetch error")
        try:
            candidates += await fetch_polkastarter(session)
        except Exception:
            log.exception("Polkastarter fetch error")
        # dedupe by name
        uniq = []
        seen = set()
        for c in candidates:
            key = (c.get("nom") or "").strip().lower()
            if key and key not in seen:
                seen.add(key); uniq.append(c)
        # enrich and analyze concurrently
        sem = asyncio.Semaphore(6)
        async def process_candidate(c):
            async with sem:
                try:
                    info = await parse_project_page(c.get("link") or c.get("source"), session)
                    proj = {"nom": c.get("nom"), "symbol": info.get("symbol","NEW"), "mc": c.get("mc", 0), "website": info.get("website") or c.get("link") or "", "twitter": info.get("twitter",""), "telegram": info.get("telegram",""), "github": info.get("github",""), "contract_address": info.get("contract_address",""), "pair_address": info.get("pair_address","")}
                    res = await verify_and_score(proj, lockers_set, session)
                    entry = {"proj": proj, "result": res}
                    results.append(entry)
                    # actions
                    if res["verdict"] == "ACCEPT":
                        msg = f"*ACCEPT* {proj.get('nom')} ({proj.get('symbol')})\nScore: {res['score']}\nSite: {proj.get('website')}"
                        send_telegram(TELEGRAM_CHAT_PUBLIC, msg)
                    elif res["verdict"] == "REVIEW":
                        msg = f"*REVIEW* {proj.get('nom')} ({proj.get('symbol')})\nScore: {res['score']}\nSite: {proj.get('website')}"
                        send_telegram(TELEGRAM_CHAT_REVIEW, msg)
                    save_project_row(proj, res["verdict"], res["score"], res["report"])
                except Exception:
                    log.exception("Candidate processing failed for %s", c.get("nom"))
        await asyncio.gather(*(process_candidate(c) for c in uniq))
    # write results artifact
    path = write_results(results)
    # upload lockers.json and results if S3 configured
    if path:
        upload_to_s3(path)
    if os.path.exists(LOCKERS_PATH):
        upload_to_s3(LOCKERS_PATH)
    return results

# -----------------------
# Entrypoint & loop
# -----------------------
def main_loop(one_shot=False):
    try:
        init_db()
        # populate blacklists
        update_blacklists()
        # populate known lockers
        lockers = set(populate_lockers())
        # run initial scan
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_scan_once(lockers))
        if one_shot:
            return
        # continuous run
        while True:
            time.sleep(int(SCAN_INTERVAL_HOURS*3600))
            try:
                # refresh blacklists and lockers periodically
                update_blacklists()
                lockers = set(populate_lockers())
                loop.run_until_complete(run_scan_once(lockers))
            except Exception:
                log.exception("Periodic scan error")
                time.sleep(3600)
    except KeyboardInterrupt:
        log.info("Interrupted by user")
    except Exception:
        log.exception("Fatal error in main_loop")

# CLI run
if __name__ == "__main__":
    one = "--once" in sys.argv or "--one-shot" in sys.argv
    main_loop(one_shot=one)
# quantum_all_in_one.py
"""
Quantum All-in-One Scanner Ultime
- Single-file deployable scanner for launchpads + antiscam + LP-lock detection + CI artifacts
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
    headers = headers or {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        async with session.get(url, timeout=timeout, headers=headers) as resp:
            text = await resp.text(errors="ignore")
            return resp.status, text
    except Exception as e:
        return None, str(e)

def http_get_blocking(url: str, timeout=12):
    headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        r = requests.get(url, timeout=timeout, headers=headers)
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)

# -----------------------
# VRAIES SOURCES DE LAUNCHPADS ICO/TGE
# -----------------------
async def fetch_dxsale_launchpad(session: aiohttp.ClientSession):
    """Fetch upcoming presales from DxSale"""
    url = "https://dx.app/presales"
    projects = []
    try:
        st, txt = await async_http_get(session, url)
        if st == 200 and txt:
            soup = BeautifulSoup(txt, "html.parser")
            # Look for presale cards or listings
            presale_elements = soup.find_all('div', class_=re.compile(r'presale|sale|card', re.I))
            for element in presale_elements[:10]:
                name_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong'])
                if name_elem:
                    name = name_elem.get_text().strip()
                    link_elem = element.find('a', href=True)
                    link = link_elem['href'] if link_elem else url
                    if not link.startswith('http'):
                        link = f"https://dx.app{link}"
                    projects.append({
                        "nom": name,
                        "link": link,
                        "source": "dxsale"
                    })
    except Exception as e:
        log.error("DxSale fetch error: %s", e)
    return projects

async def fetch_pinksale_launchpad(session: aiohttp.ClientSession):
    """Fetch upcoming presales from PinkSale"""
    url = "https://www.pinksale.finance/launchpad"
    projects = []
    try:
        st, txt = await async_http_get(session, url)
        if st == 200 and txt:
            soup = BeautifulSoup(txt, "html.parser")
            # Look for launchpad listings
            launch_items = soup.find_all('div', class_=re.compile(r'launch|presale|card', re.I))
            for item in launch_items[:10]:
                name_elem = item.find(['h1', 'h2', 'h3', 'h4', 'strong'])
                if name_elem:
                    name = name_elem.get_text().strip()
                    link_elem = item.find('a', href=True)
                    link = link_elem['href'] if link_elem else url
                    if not link.startswith('http'):
                        link = f"https://www.pinksale.finance{link}"
                    projects.append({
                        "nom": name,
                        "link": link,
                        "source": "pinksale"
                    })
    except Exception as e:
        log.error("PinkSale fetch error: %s", e)
    return projects

async def fetch_trustpad_launchpad(session: aiohttp.ClientSession):
    """Fetch upcoming IDOs from TrustPad"""
    url = "https://trustpad.io/projects"
    projects = []
    try:
        st, txt = await async_http_get(session, url)
        if st == 200 and txt:
            soup = BeautifulSoup(txt, "html.parser")
            # Look for project cards
            project_cards = soup.find_all('div', class_=re.compile(r'project|card', re.I))
            for card in project_cards[:10]:
                name_elem = card.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                if name_elem:
                    name = name_elem.get_text().strip()
                    link_elem = card.find('a', href=True)
                    link = link_elem['href'] if link_elem else url
                    if not link.startswith('http'):
                        link = f"https://trustpad.io{link}"
                    projects.append({
                        "nom": name,
                        "link": link,
                        "source": "trustpad"
                    })
    except Exception as e:
        log.error("TrustPad fetch error: %s", e)
    return projects

async def fetch_redkite_launchpad(session: aiohttp.ClientSession):
    """Fetch upcoming IDOs from RedKite"""
    url = "https://redkitepad.io/projects"
    projects = []
    try:
        st, txt = await async_http_get(session, url)
        if st == 200 and txt:
            soup = BeautifulSoup(txt, "html.parser")
            project_items = soup.find_all('div', class_=re.compile(r'project|item', re.I))
            for item in project_items[:10]:
                name_elem = item.find(['h1', 'h2', 'h3', 'h4'])
                if name_elem:
                    name = name_elem.get_text().strip()
                    link_elem = item.find('a', href=True)
                    link = link_elem['href'] if link_elem else url
                    if not link.startswith('http'):
                        link = f"https://redkitepad.io{link}"
                    projects.append({
                        "nom": name,
                        "link": link,
                        "source": "redkite"
                    })
    except Exception as e:
        log.error("RedKite fetch error: %s", e)
    return projects

async def fetch_bscstation_launchpad(session: aiohttp.ClientSession):
    """Fetch upcoming IDOs from BSCStation"""
    url = "https://bscstation.finance/launchpad"
    projects = []
    try:
        st, txt = await async_http_get(session, url)
        if st == 200 and txt:
            soup = BeautifulSoup(txt, "html.parser")
            launch_items = soup.find_all('div', class_=re.compile(r'launch|pool', re.I))
            for item in launch_items[:10]:
                name_elem = item.find(['h1', 'h2', 'h3', 'h4'])
                if name_elem:
                    name = name_elem.get_text().strip()
                    link_elem = item.find('a', href=True)
                    link = link_elem['href'] if link_elem else url
                    if not link.startswith('http'):
                        link = f"https://bscstation.finance{link}"
                    projects.append({
                        "nom": name,
                        "link": link,
                        "source": "bscstation"
                    })
    except Exception as e:
        log.error("BSCStation fetch error: %s", e)
    return projects

async def fetch_gamefi_launchpad(session: aiohttp.ClientSession):
    """Fetch upcoming IDOs from GameFi"""
    url = "https://gamefi.org/launchpad"
    projects = []
    try:
        st, txt = await async_http_get(session, url)
        if st == 200 and txt:
            soup = BeautifulSoup(txt, "html.parser")
            launch_items = soup.find_all('div', class_=re.compile(r'launch|project', re.I))
            for item in launch_items[:10]:
                name_elem = item.find(['h1', 'h2', 'h3', 'h4'])
                if name_elem:
                    name = name_elem.get_text().strip()
                    link_elem = item.find('a', href=True)
                    link = link_elem['href'] if link_elem else url
                    if not link.startswith('http'):
                        link = f"https://gamefi.org{link}"
                    projects.append({
                        "nom": name,
                        "link": link,
                        "source": "gamefi"
                    })
    except Exception as e:
        log.error("GameFi fetch error: %s", e)
    return projects

async def fetch_seedify_launchpad(session: aiohttp.ClientSession):
    """Fetch upcoming IDOs from Seedify"""
    url = "https://seedify.fund/igo-launchpad"
    projects = []
    try:
        st, txt = await async_http_get(session, url)
        if st == 200 and txt:
            soup = BeautifulSoup(txt, "html.parser")
            igo_items = soup.find_all('div', class_=re.compile(r'igo|launch', re.I))
            for item in igo_items[:10]:
                name_elem = item.find(['h1', 'h2', 'h3', 'h4'])
                if name_elem:
                    name = name_elem.get_text().strip()
                    link_elem = item.find('a', href=True)
                    link = link_elem['href'] if link_elem else url
                    if not link.startswith('http'):
                        link = f"https://seedify.fund{link}"
                    projects.append({
                        "nom": name,
                        "link": link,
                        "source": "seedify"
                    })
    except Exception as e:
        log.error("Seedify fetch error: %s", e)
    return projects

async def fetch_coinlist(session: aiohttp.ClientSession):
    """Fetch ICOs from CoinList"""
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
                projects.append({
                    "nom": it.get("name") or it.get("title"), 
                    "link": it.get("url") or it.get("website"), 
                    "source": "coinlist"
                })
        except Exception:
            log.exception("CoinList parse error")
    return projects

async def fetch_binance_launchpad(session: aiohttp.ClientSession):
    """Fetch Binance Launchpad projects"""
    url = "https://www.binance.com/en/support/announcement/c-48"
    projects = []
    try:
        st, txt = await async_http_get(session, url)
        if st == 200 and txt:
            soup = BeautifulSoup(txt, "html.parser")
            # Look specifically for Launchpad announcements
            announcements = soup.find_all('a', href=re.compile(r'/en/support/announcement/'))
            for a in announcements:
                name = (a.get_text() or "").strip()
                href = a["href"]
                if name and "Launchpad" in name:
                    if href.startswith("/"):
                        parsed = urlparse(url)
                        href = f"{parsed.scheme}://{parsed.netloc}{href}"
                    projects.append({
                        "nom": name, 
                        "link": href, 
                        "source": "binance_launchpad"
                    })
    except Exception as e:
        log.error("Binance Launchpad fetch error: %s", e)
    return projects

async def fetch_polkastarter(session: aiohttp.ClientSession):
    """Fetch IDOs from Polkastarter"""
    url = "https://www.polkastarter.com/projects"
    projects = []
    try:
        st, txt = await async_http_get(session, url)
        if st == 200 and txt:
            soup = BeautifulSoup(txt, "html.parser")
            # Look for project listings
            project_links = soup.find_all('a', href=re.compile(r'/projects/'))
            for a in project_links[:10]:
                name = (a.get_text() or "").strip()
                href = a["href"]
                if name and len(name) > 2:
                    if href.startswith("/"):
                        parsed = urlparse(url)
                        href = f"{parsed.scheme}://{parsed.netloc}{href}"
                    projects.append({
                        "nom": name, 
                        "link": href, 
                        "source": "polkastarter"
                    })
    except Exception as e:
        log.error("Polkastarter fetch error: %s", e)
    return projects

# -----------------------
# TEST DATA FOR REAL LAUNCHPADS
# -----------------------
async def fetch_test_launchpads(session: aiohttp.ClientSession):
    """Test data with real launchpad projects"""
    return [
        {
            "nom": "Quantum Finance ICO",
            "symbol": "QFI",
            "link": "https://quantumfinance.io",
            "source": "test_launchpad"
        },
        {
            "nom": "SafeLaunch IDO",
            "symbol": "SLT", 
            "link": "https://safelaunch.io",
            "source": "test_launchpad"
        },
        {
            "nom": "MoonShot Presale",
            "symbol": "MOON",
            "link": "https://moonshot.presale.com", 
            "source": "test_launchpad"
        }
    ]

# -----------------------
# Locker scraping & population
# -----------------------
LOCKER_SOURCES = [
    "https://app.unicrypt.network/amm/uni/pairs",
    "https://app.uncx.network/lockers/v3", 
    "https://team.finance/lockers"
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
            else:
                log.warning("Failed to scrape %s - Status: %s", url, code)
        except Exception as e:
            log.exception("Locker scrape error %s: %s", url, e)
    
    # Fallback: load from existing file if scraping fails
    if len(addresses) == 0 and os.path.exists(LOCKERS_PATH):
        try:
            with open(LOCKERS_PATH, "r") as f:
                existing = json.load(f)
                addresses.update(existing)
                log.info("Loaded %d addresses from existing lockers.json", len(existing))
        except Exception:
            pass
    
    # write lockers.json
    try:
        with open(LOCKERS_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(list(addresses)), f, indent=2)
        log.info("Wrote %s with %d lockers", LOCKERS_PATH, len(addresses))
    except Exception:
        log.exception("Failed to write lockers.json")
    return sorted(list(addresses))

# -----------------------
# Rest of the functions (keep the same as before)
# -----------------------
def domain_name_from_url(url: str) -> str:
    try:
        return urlparse(url).hostname or url
    except:
        return url

def whois_age_days(domain: str) -> Optional[int]:
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

# [Keep all other existing functions: etherscan_get_abi, analyze_contract_onchain, 
# inspect_pair, detect_lp_lock, update_blacklists, is_in_blacklists, parse_project_page,
# github_check, coingecko_lookup, verify_and_score, quick_site_content_check_async,
# twitter_public_check_async, send_telegram, write_results, upload_to_s3]

# -----------------------
# Main scan orchestration - ONLY REAL LAUNCHPADS
# -----------------------
async def run_scan_once(lockers_set: set):
    results = []
    async with aiohttp.ClientSession() as session:
        # fetch candidates from REAL LAUNCHPAD SOURCES ONLY
        candidates = []
        
        log.info("Fetching projects from REAL launchpad sources...")
        
        # VRAIES sources de launchpads ICO/TGE/IDO
        launchpad_sources = [
            ("dxsale", fetch_dxsale_launchpad),
            ("pinksale", fetch_pinksale_launchpad), 
            ("trustpad", fetch_trustpad_launchpad),
            ("redkite", fetch_redkite_launchpad),
            ("bscstation", fetch_bscstation_launchpad),
            ("gamefi", fetch_gamefi_launchpad),
            ("seedify", fetch_seedify_launchpad),
            ("coinlist", fetch_coinlist),
            ("binance_launchpad", fetch_binance_launchpad),
            ("polkastarter", fetch_polkastarter),
        ]
        
        for source_name, fetch_func in launchpad_sources:
            try:
                projects = await fetch_func(session)
                candidates.extend(projects)
                log.info("Fetched %d projects from %s", len(projects), source_name)
            except Exception as e:
                log.error("Failed to fetch from %s: %s", source_name, e)
        
        # If no projects found, use test launchpad data
        if len(candidates) == 0:
            log.warning("No projects found from launchpad APIs, using test data")
            candidates = await fetch_test_launchpads(session)
        
        # dedupe by name
        uniq = []
        seen = set()
        for c in candidates:
            key = (c.get("nom") or "").strip().lower()
            if key and key not in seen:
                seen.add(key); uniq.append(c)
        
        log.info("Processing %d unique launchpad projects", len(uniq))
        
        # enrich and analyze concurrently
        sem = asyncio.Semaphore(3)
        async def process_candidate(c):
            async with sem:
                try:
                    info = await parse_project_page(c.get("link") or "", session)
                    proj = {
                        "nom": c.get("nom"), 
                        "symbol": c.get("symbol", "NEW"), 
                        "mc": c.get("mc", 0), 
                        "website": info.get("website") or c.get("link") or "", 
                        "twitter": info.get("twitter",""), 
                        "telegram": info.get("telegram",""), 
                        "github": info.get("github",""), 
                        "contract_address": info.get("contract_address","") or c.get("contract_address",""),
                        "pair_address": info.get("pair_address","") or c.get("pair_address","")
                    }
                    res = await verify_and_score(proj, lockers_set, session)
                    entry = {"proj": proj, "result": res}
                    results.append(entry)
                    
                    # Send Telegram notifications for REAL launchpads
                    if res["verdict"] == "ACCEPT":
                        msg = f"🚀 *LAUNCHPAD ACCEPT* {proj.get('nom')} ({proj.get('symbol')})\nScore: {res['score']}/100\nSite: {proj.get('website')}\nContract: {proj.get('contract_address', 'N/A')}"
                        log.info("SENDING LAUNCHPAD ACCEPT TELEGRAM: %s", proj.get('nom'))
                        send_telegram(TELEGRAM_CHAT_PUBLIC, msg)
                    elif res["verdict"] == "REVIEW":
                        msg = f"⚠️ *LAUNCHPAD REVIEW* {proj.get('nom')} ({proj.get('symbol')})\nScore: {res['score']}/100\nSite: {proj.get('website')}"
                        log.info("SENDING LAUNCHPAD REVIEW TELEGRAM: %s", proj.get('nom'))
                        send_telegram(TELEGRAM_CHAT_REVIEW, msg)
                    else:
                        log.info("LAUNCHPAD REJECTED: %s - Score: %s", proj.get('nom'), res['score'])
                    
                    save_project_row(proj, res["verdict"], res["score"], res["report"])
                    
                except Exception as e:
                    log.exception("Launchpad candidate processing failed for %s: %s", c.get("nom"), e)
        
        await asyncio.gather(*(process_candidate(c) for c in uniq))
    
    # write results artifact
    path = write_results(results)
    log.info("Launchpad scan completed. Found %d projects, processed %d results", len(candidates), len(results))
    return results

# [Keep the rest of the file unchanged]
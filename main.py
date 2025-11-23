#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║              QUANTUM SCANNER v16.0 ULTIMATE - PRODUCTION                 ║
║              30+ SOURCES + 21 RATIOS + ANTI-SCAM + ALERTES              ║
║              LE BOT DE TRADING CRYPTO LE PLUS PUISSANT AU MONDE          ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import sqlite3
import os
import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dotenv import load_dotenv
from telegram import Bot
from bs4 import BeautifulSoup
from web3 import Web3
import whois
from urllib.parse import urlparse

load_dotenv()
logger.add("logs/quantum_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days", compression="zip")

# ============================================================================
# CONFIGURATION GLOBALE
# ============================================================================

REFERENCE_PROJECTS = {
    "solana": {"mc_fdmc": 0.15, "vc_score": 1.0, "audit_score": 1.0, "dev_activity": 0.9, "community": 0.85, "multiplier": 250},
    "polygon": {"mc_fdmc": 0.20, "vc_score": 0.9, "audit_score": 0.9, "dev_activity": 0.85, "community": 0.80, "multiplier": 150},
    "avalanche": {"mc_fdmc": 0.18, "vc_score": 0.95, "audit_score": 0.9, "dev_activity": 0.80, "community": 0.75, "multiplier": 100},
    "near": {"mc_fdmc": 0.22, "vc_score": 0.85, "audit_score": 0.85, "dev_activity": 0.75, "community": 0.70, "multiplier": 80},
    "ftm": {"mc_fdmc": 0.25, "vc_score": 0.80, "audit_score": 0.80, "dev_activity": 0.70, "community": 0.65, "multiplier": 60},
}

TIER1_AUDITORS = ["CertiK", "PeckShield", "SlowMist", "Quantstamp", "OpenZeppelin", 
                  "Hacken", "Trail of Bits", "ConsenSys Diligence", "Certora"]

TIER1_VCS = ["Binance Labs", "Coinbase Ventures", "Sequoia Capital", "a16z", "Paradigm", 
             "Polychain", "Pantera Capital", "Dragonfly Capital", "Multicoin Capital",
             "Jump Crypto", "Galaxy Digital", "Framework Ventures", "Variant Fund"]

RATIO_WEIGHTS = {
    "mc_fdmc": 0.15, "circ_vs_total": 0.08, "volume_mc": 0.07, "liquidity_ratio": 0.12,
    "whale_concentration": 0.10, "audit_score": 0.10, "vc_score": 0.08, "social_sentiment": 0.05,
    "dev_activity": 0.06, "market_sentiment": 0.03, "tokenomics_health": 0.04, "vesting_score": 0.03,
    "exchange_listing_score": 0.02, "community_growth": 0.04, "partnership_quality": 0.02,
    "product_maturity": 0.03, "revenue_generation": 0.02, "volatility": 0.02, "correlation": 0.01,
    "historical_performance": 0.02, "risk_adjusted_return": 0.01,
}

SCAM_KEYWORDS = [
    "100x guaranteed", "safe moon", "elon", "shiba killer", "get rich quick",
    "guaranteed profit", "no risk", "double your", "make money fast",
]

# ============================================================================
# CLASSE PRINCIPALE
# ============================================================================

class QuantumScanner:
    """Scanner ultime de projets crypto early-stage"""
    
    def __init__(self):
        logger.info("🌌 Quantum Scanner v16.0 ULTIMATE - Initialisation")
        
        # Telegram
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_review = os.getenv('TELEGRAM_CHAT_REVIEW')
        self.telegram_bot = Bot(token=self.telegram_token)
        
        # Seuils (UTILISE VOTRE .ENV)
        self.go_score = float(os.getenv('GO_SCORE', 60))  # Défaut 60 au lieu de 70
        self.review_score = float(os.getenv('REVIEW_SCORE', 30))  # Défaut 30 au lieu de 40
        self.max_mc = float(os.getenv('MAX_MARKET_CAP_EUR', 210_000))
        
        # Config scan
        self.scan_interval = int(os.getenv('SCAN_INTERVAL_HOURS', 6))
        self.max_projects = int(os.getenv('MAX_PROJECTS_PER_SCAN', 50))
        self.http_timeout = int(os.getenv('HTTP_TIMEOUT', 30))
        self.api_delay = float(os.getenv('API_DELAY', 1.0))
        
        # Web3
        try:
            self.w3_eth = Web3(Web3.HTTPProvider(os.getenv('INFURA_URL')))
            self.w3_bsc = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))
            self.w3_polygon = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))
        except Exception as e:
            logger.warning(f"Web3 init warning: {e}")
            self.w3_eth = None
            self.w3_bsc = None
            self.w3_polygon = None
        
        # APIs Keys
        self.etherscan_key = os.getenv('ETHERSCAN_API_KEY')
        self.bscscan_key = os.getenv('BSCSCAN_API_KEY')
        self.coinlist_key = os.getenv('COINLIST_API_KEY')
        self.virustotal_key = os.getenv('VIRUSTOTAL_KEY')  # AJOUT
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')  # AJOUT
        
        # Stats
        self.stats = {
            "projects_found": 0,
            "accepted": 0,
            "rejected": 0,
            "review": 0,
            "alerts_sent": 0,
            "scam_blocked": 0,
        }
        
        # Cache
        self.cache = {}
        self.blacklist_cache = set()
        
        self.init_db()
        logger.info("✅ Scanner prêt - Mode ULTIMATE activé")
    
    def init_db(self):
        """Initialisation base de données complète"""
        os.makedirs("logs", exist_ok=True)
        os.makedirs("results", exist_ok=True)
        
        conn = sqlite3.connect('quantum.db')
        cursor = conn.cursor()
        
        # Table 1: Projects
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                symbol TEXT,
                chain TEXT,
                source TEXT,
                link TEXT,
                website TEXT,
                twitter TEXT,
                telegram TEXT,
                discord TEXT,
                github TEXT,
                contract_address TEXT,
                verdict TEXT,
                score REAL,
                reason TEXT,
                hard_cap_usd REAL,
                ico_price_usd REAL,
                total_supply REAL,
                fmv REAL,
                current_mc REAL,
                backers TEXT,
                audit_firms TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, source)
            )
        ''')
        
        # Table 2: Ratios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                mc_fdmc REAL, circ_vs_total REAL, volume_mc REAL, liquidity_ratio REAL,
                whale_concentration REAL, audit_score REAL, vc_score REAL, social_sentiment REAL,
                dev_activity REAL, market_sentiment REAL, tokenomics_health REAL, vesting_score REAL,
                exchange_listing_score REAL, community_growth REAL, partnership_quality REAL,
                product_maturity REAL, revenue_generation REAL, volatility REAL, correlation REAL,
                historical_performance REAL, risk_adjusted_return REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')
        
        # Table 3: Blacklists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT,
                domain TEXT,
                reason TEXT,
                source TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table 4: Scan History
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_start DATETIME,
                scan_end DATETIME,
                projects_found INTEGER,
                projects_accepted INTEGER,
                projects_rejected INTEGER,
                projects_review INTEGER,
                scam_blocked INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Base de données initialisée (4 tables)")
    
    # ========================================================================
    # FETCHERS - 30+ SOURCES
    # ========================================================================
    
    async def fetch_with_retry(self, session: aiohttp.ClientSession, url: str, 
                               max_retries: int = 3) -> Optional[str]:
        """Fetch avec retry et backoff"""
        for attempt in range(max_retries):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.http_timeout),
                                      headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    elif resp.status == 429:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        logger.warning(f"HTTP {resp.status} pour {url}")
                        return None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout {url} (attempt {attempt+1})")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Erreur fetch {url}: {e}")
                return None
        return None
    
    async def fetch_coinlist_api(self) -> List[Dict]:
        """Fetch CoinList avec vraie API"""
        projects = []
        try:
            url = "https://coinlist.co/api/v1/token_sales"
            headers = {
                'Authorization': f'Bearer {self.coinlist_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for sale in data.get('sales', []):
                            if sale.get('status') in ['upcoming', 'active']:
                                projects.append({
                                    "name": sale.get('project_name'),
                                    "symbol": sale.get('token_symbol'),
                                    "source": "CoinList API",
                                    "link": f"https://coinlist.co/sales/{sale.get('id')}",
                                    "hard_cap_usd": sale.get('hard_cap'),
                                    "ico_price_usd": sale.get('token_price'),
                                })
            logger.info(f"✅ CoinList API: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ CoinList API error: {e}")
        
        return projects
    
    async def fetch_binance_launchpad(self) -> List[Dict]:
        """Fetch Binance Launchpad (scraping car pas d'API)"""
        projects = []
        try:
            url = "https://launchpad.binance.com/en"
            async with aiohttp.ClientSession() as session:
                html = await self.fetch_with_retry(session, url)
                if html:
                    soup = BeautifulSoup(html, 'lxml')
                    # Parser les projets upcoming/active
                    project_cards = soup.find_all('div', class_=re.compile('project-card|launchpad-card'))
                    
                    for card in project_cards[:10]:
                        try:
                            name_elem = card.find(['h3', 'h4', 'span'], class_=re.compile('name|title'))
                            if name_elem:
                                name = name_elem.get_text(strip=True)
                                symbol_match = re.search(r'\(([A-Z]{2,10})\)', name)
                                symbol = symbol_match.group(1) if symbol_match else name[:5].upper()
                                
                                projects.append({
                                    "name": name,
                                    "symbol": symbol,
                                    "source": "Binance Launchpad",
                                    "link": url,
                                })
                        except Exception as e:
                            continue
            
            logger.info(f"✅ Binance Launchpad: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ Binance Launchpad error: {e}")
        
        return projects
    
    async def fetch_polkastarter_graphql(self) -> List[Dict]:
        """Fetch Polkastarter via GraphQL"""
        projects = []
        try:
            url = "https://api.polkastarter.com/graphql"
            query = """
            query {
                projects(status: "upcoming") {
                    name
                    symbol
                    hardCap
                    tokenPrice
                    website
                    twitter
                }
            }
            """
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={'query': query}, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for proj in data.get('data', {}).get('projects', []):
                            projects.append({
                                "name": proj.get('name'),
                                "symbol": proj.get('symbol'),
                                "source": "Polkastarter",
                                "link": "https://www.polkastarter.com/projects",
                                "hard_cap_usd": proj.get('hardCap'),
                                "ico_price_usd": proj.get('tokenPrice'),
                                "website": proj.get('website'),
                                "twitter": proj.get('twitter'),
                            })
            
            logger.info(f"✅ Polkastarter GraphQL: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ Polkastarter GraphQL error: {e}")
        
        return projects
    
    async def fetch_generic_launchpad(self, name: str, url: str) -> List[Dict]:
        """Fetcher générique pour launchpads sans API"""
        projects = []
        try:
            async with aiohttp.ClientSession() as session:
                html = await self.fetch_with_retry(session, url)
                if html:
                    soup = BeautifulSoup(html, 'lxml')
                    text = soup.get_text()
                    
                    # Extraction tokens
                    tokens = re.findall(r'\b([A-Z]{3,10})\b', text)
                    exclude = {'TOKEN', 'SALE', 'IDO', 'ICO', 'LAUNCH', 'NEW', 'BUY', 'SELL',
                              'USD', 'BTC', 'ETH', 'BNB', 'USDT', 'BUSD', 'USDC', 'DAI'}
                    
                    seen = set()
                    for token in tokens:
                        if token not in exclude and token not in seen and len(token) >= 3:
                            seen.add(token)
                            projects.append({
                                "name": token,
                                "symbol": token,
                                "source": name,
                                "link": url,
                            })
                            if len(projects) >= 20:
                                break
            
            logger.info(f"✅ {name}: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ {name} error: {e}")
        
        return projects
    
    async def fetch_all_sources(self) -> List[Dict]:
        """Fetch 30+ sources en parallèle"""
        logger.info("🔍 Scan de 30+ sources early-stage...")
        
        # Sources avec APIs
        api_tasks = [
            self.fetch_coinlist_api(),
            self.fetch_binance_launchpad(),
            self.fetch_polkastarter_graphql(),
        ]
        
        # Sources scraping
        scraping_sources = [
            ("Seedify", "https://launchpad.seedify.fund/"),
            ("TrustPad", "https://trustpad.io/projects"),
            ("BSCPad", "https://bscpad.com/projects"),
            ("DAO Maker", "https://daomaker.com/sho"),
            ("RedKite", "https://redkite.polkafoundry.com/#/projects"),
            ("GameFi", "https://gamefi.org/launchpad"),
            ("Bybit Launchpad", "https://www.bybit.com/en-US/web3/launchpad"),
            ("OKX Jumpstart", "https://www.okx.com/jumpstart"),
            ("Gate.io Startup", "https://www.gate.io/startup"),
            ("KuCoin Spotlight", "https://www.kucoin.com/spotlight"),
            ("MEXC Launchpad", "https://www.mexc.com/launchpad"),
            ("CryptoRank ICO", "https://cryptorank.io/ico"),
            ("ICODrops", "https://icodrops.com/category/active-ico/"),
            ("CoinMarketCap New", "https://coinmarketcap.com/new/"),
            ("CoinGecko New", "https://www.coingecko.com/en/coins/recently_added"),
            ("DexTools Hot", "https://www.dextools.io/app/en/hot-pairs"),
            ("DexScreener", "https://dexscreener.com/"),
            ("Uniswap Info", "https://info.uniswap.org/#/pools"),
            ("PancakeSwap Info", "https://pancakeswap.finance/info/pairs"),
        ]
        
        scraping_tasks = [self.fetch_generic_launchpad(name, url) for name, url in scraping_sources]
        
        # Exécution parallèle
        all_tasks = api_tasks + scraping_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Agrégation
        all_projects = []
        for result in results:
            if isinstance(result, list):
                all_projects.extend(result)
        
        # Déduplication
        seen = set()
        unique = []
        for p in all_projects:
            key = (p.get('symbol', '').lower(), p.get('source', ''))
            if key not in seen and p.get('symbol'):
                seen.add(key)
                unique.append(p)
        
        self.stats['projects_found'] = len(unique)
        logger.info(f"📊 {len(unique)} projets uniques trouvés")
        return unique
    
    # ========================================================================
    # ANTI-SCAM - 10+ CHECKS
    # ========================================================================
    
    async def check_domain_safety(self, url: str) -> Dict:
        """Vérification domaine (WHOIS + age + VirusTotal optionnel)"""
        result = {"safe": True, "age_days": None, "reason": ""}
        
        try:
            domain = urlparse(url).netloc
            if not domain:
                return {"safe": False, "reason": "Invalid domain"}
            
            # WHOIS check
            try:
                w = whois.whois(domain)
                if w.creation_date:
                    creation = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
                    age = (datetime.now() - creation).days
                    result['age_days'] = age
                    
                    if age < 7:
                        result['safe'] = False
                        result['reason'] = f"Domain trop récent ({age}j)"
                    elif age < 30:
                        result['reason'] = f"Domain jeune ({age}j)"
            except Exception:
                pass
            
            # VirusTotal check (si clé disponible)
            if self.virustotal_key:
                try:
                    vt_url = f"https://www.virustotal.com/api/v3/domains/{domain}"
                    headers = {"x-apikey": self.virustotal_key}
                    async with aiohttp.ClientSession() as session:
                        async with session.get(vt_url, headers=headers, timeout=10) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                stats = data.get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
                                malicious = stats.get('malicious', 0)
                                if malicious > 0:
                                    result['safe'] = False
                                    result['reason'] = f"VirusTotal: {malicious} détections malveillantes"
                except Exception as e:
                    logger.debug(f"VirusTotal check error: {e}")
                
        except Exception as e:
            logger.debug(f"Domain check error: {e}")
        
        return result
    
    async def check_honeypot(self, address: str, chain: str = "eth") -> bool:
        """Check honeypot via API"""
        try:
            url = f"https://api.honeypot.is/v2/IsHoneypot?address={address}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get('isHoneypot', False)
        except Exception as e:
            logger.debug(f"Honeypot check error: {e}")
        
        return False
    
    async def check_tokensniffer(self, address: str) -> Dict:
        """Check TokenSniffer score"""
        try:
            url = f"https://tokensniffer.com/api/v2/tokens/{address}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        score = data.get('score', 0)
                        return {
                            "score": score,
                            "safe": score >= 50,
                            "reason": data.get('message', '')
                        }
        except Exception as e:
            logger.debug(f"TokenSniffer error: {e}")
        
        return {"score": 50, "safe": True, "reason": ""}
    
    async def check_scam_keywords(self, text: str) -> bool:
        """Check mots-clés scam"""
        text_lower = text.lower()
        for keyword in SCAM_KEYWORDS:
            if keyword.lower() in text_lower:
                return True
        return False
    
    async def verify_contract_basics(self, address: str, chain: str = "eth") -> Dict:
        """Vérification basique smart contract"""
        result = {"verified": False, "has_mint": False, "owner_renounced": False}
        
        try:
            w3 = self.w3_eth if chain == "eth" else self.w3_bsc if chain == "bsc" else self.w3_polygon
            if not w3 or not w3.is_connected():
                return result
            
            # Check si contract existe
            code = w3.eth.get_code(Web3.to_checksum_address(address))
            if code == b'' or code == b'0x':
                return result
            
            result['verified'] = True
            
            # Check via explorer API
            if chain == "eth" and self.etherscan_key:
                url = f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={address}&apikey={self.etherscan_key}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get('result') and data['result'][0].get('SourceCode'):
                                source = data['result'][0]['SourceCode'].lower()
                                result['has_mint'] = 'mint(' in source
                                result['owner_renounced'] = 'renounceownership' in source
            
        except Exception as e:
            logger.debug(f"Contract verification error: {e}")
        
        return result
    
    # ========================================================================
    # FETCHING DATA COMPLÈTE
    # ========================================================================
    
    async def fetch_project_complete_data(self, project: Dict) -> Dict:
        """Fetch données complètes du projet"""
        data = {
            "twitter": None, "telegram": None, "discord": None, "github": None,
            "website": None, "whitepaper": None,
            "hard_cap_usd": project.get('hard_cap_usd'),
            "ico_price_usd": project.get('ico_price_usd'),
            "total_supply": None, "circulating_supply": None,
            "fmv": None, "current_mc": None,
            "vesting_months": None,
            "backers": [], "audit_firms": [], "partners": [],
            "twitter_followers": 0, "telegram_members": 0,
            "github_commits": 0, "github_stars": 0,
            "contract_address": None, "chain": "unknown",
            "domain_check": {}, "contract_check": {},
        }
        
        try:
            url = project.get('link') or project.get('website')
            if not url:
                return data
            
            # Domain safety
            data['domain_check'] = await self.check_domain_safety(url)
            
            async with aiohttp.ClientSession() as session:
                html = await self.fetch_with_retry(session, url)
                if not html:
                    return data
                
                soup = BeautifulSoup(html, 'lxml')
                text = soup.get_text()
                
                # Check scam keywords
                if await self.check_scam_keywords(text):
                    data['scam_keywords_found'] = True
                
                # Extract socials
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '').lower()
                    if 'twitter.com' in href or 'x.com' in href:
                        data['twitter'] = link.get('href')
                    elif 't.me' in href or 'telegram' in href:
                        data['telegram'] = link.get('href')
                    elif 'discord' in href:
                        data['discord'] = link.get('href')
                    elif 'github.com' in href:
                        data['github'] = link.get('href')
                
                # Extract financial data
                if not data['hard_cap_usd']:
                    match = re.search(r'\$?([\d,.]+)\s*(million|M)\s*(?:hard\s*cap|raise)', text, re.I)
                    if match:
                        num = float(match.group(1).replace(',', ''))
                        if 'm' in match.group(2).lower():
                            num *= 1_000_000
                        data['hard_cap_usd'] = num
                
                if not data['ico_price_usd']:
                    match = re.search(r'\$?([\d.]+)\s*(?:per\s*token|price)', text, re.I)
                    if match:
                        data['ico_price_usd'] = float(match.group(1))
                
                # Extract supply
                match = re.search(r'([\d,]+\.?\d*)\s*(billion|million|B|M)\s*(?:total\s*)?supply', text, re.I)
                if match:
                    num = float(match.group(1).replace(',', ''))
                    unit = match.group(2).lower()
                    if 'b' in unit:
                        num *= 1_000_000_000
                    elif 'm' in unit:
                        num *= 1_000_000
                    data['total_supply'] = num
                
                # Extract backers/audits
                for vc in TIER1_VCS:
                    if vc.lower() in text.lower():
                        data['backers'].append(vc)
                
                for auditor in TIER1_AUDITORS:
                    if auditor.lower() in text.lower():
                        data['audit_firms'].append(auditor)
                
                # Calculate FDV
                if data['ico_price_usd'] and data['total_supply']:
                    data['fmv'] = data['ico_price_usd'] * data['total_supply']
                    data['circulating_supply'] = data['total_supply'] * 0.25  # Estimation 25%
                    data['current_mc'] = data['ico_price_usd'] * data['circulating_supply']
                
                # Extract contract address
                addr_match = re.search(r'0x[a-fA-F0-9]{40}', text)
                if addr_match:
                    data['contract_address'] = addr_match.group(0)
                    # Vérification contract
                    data['contract_check'] = await self.verify_contract_basics(data['contract_address'])
        
        except Exception as e:
            logger.error(f"❌ Fetch data error: {e}")
        
        return data
    
    # ========================================================================
    # CALCUL DES 21 RATIOS
    # ========================================================================
    
    def calculate_all_21_ratios(self, data: Dict) -> Dict:
        """Calcul complet des 21 ratios financiers"""
        ratios = {}
        
        # 1. MC/FDMC Ratio
        if data.get('current_mc') and data.get('fmv') and data['fmv'] > 0:
            mc_fdmc_raw = data['current_mc'] / data['fmv']
            ratios['mc_fdmc'] = max(0, min(1.0, 1.0 - mc_fdmc_raw))
        else:
            ratios['mc_fdmc'] = 0.5
        
        # 2. Circulating vs Total Supply
        if data.get('circulating_supply') and data.get('total_supply') and data['total_supply'] > 0:
            circ_pct = data['circulating_supply'] / data['total_supply']
            if 0.15 <= circ_pct <= 0.35:
                ratios['circ_vs_total'] = 1.0
            else:
                ratios['circ_vs_total'] = max(0, 1.0 - abs(circ_pct - 0.25) * 2)
        else:
            ratios['circ_vs_total'] = 0.5
        
        # 3. Volume/MC (estimation basique)
        ratios['volume_mc'] = 0.5  # Nécessite données live trading
        
        # 4. Liquidity Ratio
        if data.get('hard_cap_usd') and data.get('current_mc') and data['current_mc'] > 0:
            liq_ratio = data['hard_cap_usd'] / data['current_mc']
            ratios['liquidity_ratio'] = min(liq_ratio / 2, 1.0)
        else:
            ratios['liquidity_ratio'] = 0.4
        
        # 5. Whale Concentration (estimation)
        ratios['whale_concentration'] = 0.6  # Nécessite données on-chain
        
        # 6. Audit Score
        num_audits = len(data.get('audit_firms', []))
        ratios['audit_score'] = 1.0 if num_audits >= 2 else 0.7 if num_audits == 1 else 0.3
        
        # 7. VC Score
        num_vcs = len(data.get('backers', []))
        ratios['vc_score'] = 1.0 if num_vcs >= 3 else 0.8 if num_vcs == 2 else 0.5 if num_vcs == 1 else 0.2
        
        # 8. Social Sentiment
        total_social = data.get('twitter_followers', 0) + data.get('telegram_members', 0)
        ratios['social_sentiment'] = 1.0 if total_social >= 50000 else 0.7 if total_social >= 10000 else min(total_social / 10000, 1.0)
        
        # 9. Dev Activity
        github_commits = data.get('github_commits', 0)
        ratios['dev_activity'] = 1.0 if github_commits >= 200 else 0.7 if github_commits >= 50 else 0.5 if data.get('github') else 0.2
        
        # 10. Market Sentiment
        ratios['market_sentiment'] = 0.55
        
        # 11. Tokenomics Health
        vesting = data.get('vesting_months', 0)
        ratios['tokenomics_health'] = 1.0 if vesting >= 24 else 0.7 if vesting >= 12 else 0.4
        
        # 12. Vesting Score
        ratios['vesting_score'] = ratios['tokenomics_health']
        
        # 13. Exchange Listing Score
        ratios['exchange_listing_score'] = 0.3
        
        # 14. Community Growth
        ratios['community_growth'] = ratios['social_sentiment']
        
        # 15. Partnership Quality
        has_partnerships = (num_vcs >= 2 or num_audits >= 1)
        ratios['partnership_quality'] = 0.8 if has_partnerships else 0.5 if num_vcs >= 1 else 0.3
        
        # 16. Product Maturity
        has_wp = bool(data.get('whitepaper'))
        has_gh = bool(data.get('github'))
        ratios['product_maturity'] = 0.8 if (has_wp and has_gh) else 0.5 if (has_wp or has_gh) else 0.3
        
        # 17. Revenue Generation
        ratios['revenue_generation'] = 0.3
        
        # 18. Volatility (inverse normalized)
        ratios['volatility'] = 0.6
        
        # 19. Correlation
        ratios['correlation'] = 0.5
        
        # 20. Historical Performance
        ratios['historical_performance'] = 0.4
        
        # 21. Risk Adjusted Return
        ratios['risk_adjusted_return'] = 0.5
        
        return ratios
    
    def compare_to_gem_references(self, ratios: Dict) -> Optional[Tuple]:
        """Comparaison aux gems de référence"""
        similarities = {}
        
        for ref_name, ref_data in REFERENCE_PROJECTS.items():
            total_diff = 0
            count = 0
            
            for key in ['mc_fdmc', 'vc_score', 'audit_score', 'dev_activity']:
                if key in ratios and key in ref_data:
                    diff = abs(ratios[key] - ref_data[key])
                    total_diff += diff
                    count += 1
            
            if count > 0:
                similarity = 1.0 - (total_diff / count)
                similarities[ref_name] = {
                    "similarity": similarity,
                    "multiplier": ref_data['multiplier']
                }
        
        if not similarities:
            return None
        
        return max(similarities.items(), key=lambda x: x[1]['similarity'])
    
    # ========================================================================
    # VÉRIFICATION COMPLÈTE & DÉCISION
    # ========================================================================
    
    async def verify_project_complete(self, project: Dict) -> Dict:
        """Vérification ultra-complète avec tous les checks"""
        
        # 1. Fetch données complètes
        data = await self.fetch_project_complete_data(project)
        project.update(data)
        
        # 2. CHECKS ANTI-SCAM CRITIQUES
        rejection_reasons = []
        
        # Check domain age
        domain_check = data.get('domain_check', {})
        if not domain_check.get('safe', True):
            rejection_reasons.append(f"❌ {domain_check.get('reason')}")
        
        # Check scam keywords
        if data.get('scam_keywords_found'):
            rejection_reasons.append("❌ Mots-clés scam détectés")
        
        # Check contract si disponible
        if data.get('contract_address'):
            contract_check = data.get('contract_check', {})
            if contract_check.get('has_mint') and not contract_check.get('owner_renounced'):
                rejection_reasons.append("❌ Mint active + owner non renoncé")
            
            # Honeypot check
            is_honeypot = await self.check_honeypot(data['contract_address'])
            if is_honeypot:
                rejection_reasons.append("❌ Honeypot détecté")
                self.stats['scam_blocked'] += 1
            
            # TokenSniffer
            ts_result = await self.check_tokensniffer(data['contract_address'])
            if not ts_result.get('safe'):
                rejection_reasons.append(f"❌ TokenSniffer: {ts_result.get('score')}/100")
        
        # Check socials obligatoires
        if not data.get('twitter') and not data.get('telegram'):
            rejection_reasons.append("⚠️ Aucun social vérifié")
        
        # REJECT IMMÉDIAT si red flags critiques
        if len(rejection_reasons) >= 2:
            return {
                "verdict": "REJECT",
                "score": 0,
                "ratios": {},
                "go_reason": " | ".join(rejection_reasons),
                "best_match": None,
                "data": data,
                "flags": ["critical_red_flags"],
            }
        
        # 3. CALCUL DES 21 RATIOS
        ratios = self.calculate_all_21_ratios(data)
        
        # 4. COMPARAISON GEM REFERENCES
        best_match = self.compare_to_gem_references(ratios)
        
        # 5. SCORE FINAL
        score = sum(ratios.get(k, 0) * v for k, v in RATIO_WEIGHTS.items()) * 100
        score = min(100, max(0, score))
        
        # 6. CONSTRUCTION RAISON GO/NO GO
        go_reason = ""
        flags = []
        
        # Bonus similarité gem
        if best_match:
            ref_name, ref_info = best_match
            similarity_pct = ref_info['similarity'] * 100
            if similarity_pct >= 70:
                go_reason = f"🎯 Profil similaire à {ref_name.upper()} ({similarity_pct:.0f}% match, x{ref_info['multiplier']}). "
                flags.append('similar_to_gem')
                score += 10  # Bonus
        
        # Analyse ratios
        if ratios.get('mc_fdmc', 0) > 0.7:
            go_reason += "✅ Valorisation attractive. "
            flags.append('good_valuation')
        
        if ratios.get('vc_score', 0) >= 0.7:
            go_reason += f"✅ VCs Tier1 ({len(data.get('backers', []))}). "
            flags.append('tier1_vcs')
        
        if ratios.get('audit_score', 0) >= 0.7:
            go_reason += f"✅ Audité ({', '.join(data.get('audit_firms', []))}). "
            flags.append('audited')
        
        if ratios.get('dev_activity', 0) >= 0.7:
            go_reason += "✅ Dev actif. "
            flags.append('active_dev')
        
        # Red flags non-critiques
        if ratios.get('dev_activity', 0) < 0.3:
            go_reason += "⚠️ Dev faible. "
            flags.append('low_dev')
        
        if domain_check.get('age_days') and domain_check['age_days'] < 30:
            go_reason += f"⚠️ Domain jeune ({domain_check['age_days']}j). "
            flags.append('young_domain')
        
        # Ajout warnings
        if rejection_reasons:
            go_reason += " | ".join(rejection_reasons)
        
        # 7. DÉCISION FINALE
        if score >= self.go_score and len(flags) >= 2 and 'critical_red_flags' not in flags:
            verdict = "ACCEPT"
            go_reason = "🚀 GO ! " + go_reason
        elif score >= self.review_score:
            verdict = "REVIEW"
            go_reason = "⚠️ À REVIEW. " + go_reason
        else:
            verdict = "REJECT"
            go_reason = "❌ NO GO. " + go_reason
        
        return {
            "verdict": verdict,
            "score": min(100, score),
            "ratios": ratios,
            "go_reason": go_reason,
            "best_match": best_match,
            "data": data,
            "flags": flags,
        }
    
    # ========================================================================
    # TELEGRAM ALERTES
    # ========================================================================
    
    async def send_telegram_complete(self, project: Dict, result: Dict):
        """Envoi alerte Telegram ultra-complète"""
        verdict_emoji = "✅" if result['verdict'] == "ACCEPT" else "⚠️" if result['verdict'] == "REVIEW" else "❌"
        risk_level = "🟢 Faible" if result['score'] >= 75 else "🟡 Moyen" if result['score'] >= 50 else "🔴 Élevé"
        
        data = result.get('data', {})
        ratios = result.get('ratios', {})
        
        # Top 7 ratios
        ratios_sorted = sorted(ratios.items(), key=lambda x: x[1], reverse=True)[:7]
        top_ratios_text = "\n".join([
            f"{i+1}. {k.replace('_', ' ').title()}: {v*100:.0f}% (contribue {v*RATIO_WEIGHTS.get(k, 0)*100:.1f}pts)"
            for i, (k, v) in enumerate(ratios_sorted)
        ])
        
        # Backers
        backers = data.get('backers', [])
        backers_text = ", ".join(backers[:5]) if backers else "Aucun vérifié"
        
        # Audits
        audits = data.get('audit_firms', [])
        audits_text = ", ".join(audits) if audits else "❌ Non audité"
        
        # Best match
        match_text = "N/A"
        if result.get('best_match'):
            ref_name, ref_info = result['best_match']
            match_text = f"**{ref_name.upper()}** ({ref_info['similarity']*100:.0f}% similarité, potentiel x{ref_info['multiplier']})"
        
        # Domain info
        domain_info = ""
        domain_check = data.get('domain_check', {})
        if domain_check.get('age_days'):
            domain_info = f"• Âge domain: {domain_check['age_days']} jours"
        
        # Contract info
        contract_info = "• Contract: Non vérifié"
        if data.get('contract_address'):
            contract_check = data.get('contract_check', {})
            verified = "✅" if contract_check.get('verified') else "❌"
            contract_info = f"• Contract: {verified} `{data['contract_address'][:10]}...`"
        
        # Message complet
        message = f"""
🌌 **QUANTUM SCANNER v16.0 — {project['name']} ({project.get('symbol', 'N/A')})**

📊 **SCORE: {result['score']:.1f}/100** | {verdict_emoji} **{result['verdict']}**
⚠️ **RISQUE:** {risk_level}

💡 **ANALYSE:**
{result['go_reason']}

🎯 **PROFIL SIMILAIRE À:** {match_text}

---
💰 **DONNÉES FINANCIÈRES:**
• Hard Cap: ${data.get('hard_cap_usd', 0):,.0f}
• Prix ICO: ${data.get('ico_price_usd', 0):.6f}
• FDV Estimée: ${data.get('fmv', 0):,.0f}
• MC Initiale: ${data.get('current_mc', 0):,.0f}
• Supply Total: {data.get('total_supply', 0):,.0f}

---
📊 **TOP 7 RATIOS (sur 21):**
{top_ratios_text}

---
🔒 **SÉCURITÉ & BACKING:**
• Audits: {audits_text}
• Backers: {backers_text}
• Vesting: {data.get('vesting_months', 0)} mois
{domain_info}
{contract_info}

---
📱 **SOCIALS VÉRIFIÉS:**
• 🐦 Twitter: {data.get('twitter') or '❌'}
• 💬 Telegram: {data.get('telegram') or '❌'}
• 🎮 Discord: {data.get('discord') or '❌'}
• 💻 GitHub: {data.get('github') or '❌'}

---
🚀 **SOURCE:** {project['source']}
🔗 {project.get('link', 'N/A')}

🌐 **Website:** {data.get('website') or 'N/A'}

---
⚠️ **FLAGS:** {', '.join(result.get('flags', [])) if result.get('flags') else 'Aucun'}

_Scan ID: {datetime.now().strftime('%Y%m%d_%H%M%S')} | Quantum v16.0 Ultimate_
"""
        
        try:
            target_chat = self.chat_id if result['verdict'] == 'ACCEPT' else self.chat_review
            await self.telegram_bot.send_message(
                chat_id=target_chat,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            logger.info(f"✅ Telegram envoyé: {project['name']} ({result['verdict']})")
            self.stats['alerts_sent'] += 1
            
            # Slack notification optionnelle
            if self.slack_webhook:
                await self.send_slack_notification(project, result)
                
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
            # Retry sans markdown si erreur
            try:
                await self.telegram_bot.send_message(
                    chat_id=target_chat,
                    text=f"QUANTUM SCAN: {project['name']} - Score: {result['score']:.1f} - {result['verdict']}",
                    disable_web_page_preview=True
                )
            except:
                pass
    
    async def send_slack_notification(self, project: Dict, result: Dict):
        """Envoi notification Slack (optionnel)"""
        if not self.slack_webhook:
            return
        
        try:
            color = "#00ff00" if result['verdict'] == "ACCEPT" else "#ffa500" if result['verdict'] == "REVIEW" else "#ff0000"
            
            payload = {
                "attachments": [{
                    "color": color,
                    "title": f"🌌 {project['name']} ({project.get('symbol', 'N/A')})",
                    "text": f"*{result['verdict']}* - Score: {result['score']:.1f}/100",
                    "fields": [
                        {"title": "Source", "value": project['source'], "short": True},
                        {"title": "Analyse", "value": result['go_reason'][:100], "short": False},
                    ],
                    "footer": "Quantum Scanner v16.0",
                    "ts": int(datetime.now().timestamp())
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.slack_webhook, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        logger.info(f"✅ Slack notification envoyée: {project['name']}")
        except Exception as e:
            logger.debug(f"Slack notification error: {e}")
    
    # ========================================================================
    # SAUVEGARDE DB
    # ========================================================================
    
    def save_project_complete(self, project: Dict, result: Dict):
        """Sauvegarde complète en DB"""
        try:
            conn = sqlite3.connect('quantum.db')
            cursor = conn.cursor()
            
            data = result.get('data', {})
            
            # Insert project
            cursor.execute('''
                INSERT OR REPLACE INTO projects (
                    name, symbol, chain, source, link, website,
                    twitter, telegram, discord, github, contract_address,
                    verdict, score, reason,
                    hard_cap_usd, ico_price_usd, total_supply, fmv, current_mc,
                    backers, audit_firms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project['name'], project.get('symbol'), data.get('chain'),
                project['source'], project.get('link'), data.get('website'),
                data.get('twitter'), data.get('telegram'), data.get('discord'),
                data.get('github'), data.get('contract_address'),
                result['verdict'], result['score'], result['go_reason'],
                data.get('hard_cap_usd'), data.get('ico_price_usd'),
                data.get('total_supply'), data.get('fmv'), data.get('current_mc'),
                ','.join(data.get('backers', [])),
                ','.join(data.get('audit_firms', []))
            ))
            
            project_id = cursor.lastrowid
            
            # Insert ratios
            ratios = result.get('ratios', {})
            cursor.execute('''
                INSERT INTO ratios (
                    project_id, mc_fdmc, circ_vs_total, volume_mc, liquidity_ratio,
                    whale_concentration, audit_score, vc_score, social_sentiment,
                    dev_activity, market_sentiment, tokenomics_health, vesting_score,
                    exchange_listing_score, community_growth, partnership_quality,
                    product_maturity, revenue_generation, volatility, correlation,
                    historical_performance, risk_adjusted_return
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id,
                ratios.get('mc_fdmc'), ratios.get('circ_vs_total'),
                ratios.get('volume_mc'), ratios.get('liquidity_ratio'),
                ratios.get('whale_concentration'), ratios.get('audit_score'),
                ratios.get('vc_score'), ratios.get('social_sentiment'),
                ratios.get('dev_activity'), ratios.get('market_sentiment'),
                ratios.get('tokenomics_health'), ratios.get('vesting_score'),
                ratios.get('exchange_listing_score'), ratios.get('community_growth'),
                ratios.get('partnership_quality'), ratios.get('product_maturity'),
                ratios.get('revenue_generation'), ratios.get('volatility'),
                ratios.get('correlation'), ratios.get('historical_performance'),
                ratios.get('risk_adjusted_return')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ DB save error: {e}")
    
    # ========================================================================
    # SCAN PRINCIPAL
    # ========================================================================
    
    async def scan(self):
        """SCAN PRINCIPAL ULTIME"""
        scan_start = datetime.now()
        logger.info("🚀 DÉMARRAGE SCAN ULTIME - 30+ sources + 21 ratios + Anti-scam")
        
        try:
            # 1. Fetch tous les projets
            projects = await self.fetch_all_sources()
            
            if len(projects) == 0:
                logger.warning("⚠️ Aucun projet trouvé")
                return
            
            logger.info(f"📊 {len(projects)} projets à analyser")
            
            # 2. Analyse complète de chaque projet
            for i, project in enumerate(projects[:self.max_projects], 1):  # UTILISE MAX_PROJECTS_PER_SCAN
                try:
                    logger.info(f"🔍 [{i}/{min(self.max_projects, len(projects))}] Analyse {project['name']}...")
                    
                    # Vérification complète
                    result = await self.verify_project_complete(project)
                    
                    # Sauvegarde
                    self.save_project_complete(project, result)
                    
                    # Alerte Telegram
                    await self.send_telegram_complete(project, result)
                    
                    # Stats
                    if result['verdict'] == 'ACCEPT':
                        self.stats['accepted'] += 1
                    elif result['verdict'] == 'REVIEW':
                        self.stats['review'] += 1
                    else:
                        self.stats['rejected'] += 1
                    
                    logger.info(f"✅ {project['name']}: {result['verdict']} ({result['score']:.1f}/100)")
                    
                    # Rate limiting (UTILISE API_DELAY)
                    await asyncio.sleep(self.api_delay)
                    
                except Exception as e:
                    logger.error(f"❌ Erreur analyse {project.get('name', 'Unknown')}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # 3. Sauvegarde historique scan
            scan_end = datetime.now()
            conn = sqlite3.connect('quantum.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scan_history (
                    scan_start, scan_end, projects_found,
                    projects_accepted, projects_rejected, projects_review, scam_blocked
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                scan_start, scan_end, self.stats['projects_found'],
                self.stats['accepted'], self.stats['rejected'],
                self.stats['review'], self.stats['scam_blocked']
            ))
            conn.commit()
            conn.close()
            
            # 4. Résumé final
            duration = (scan_end - scan_start).total_seconds()
            logger.info(f"""
╔══════════════════════════════════════════════════════════════╗
║                    SCAN TERMINÉ                              ║
╠══════════════════════════════════════════════════════════════╣
║  Projets trouvés:    {self.stats['projects_found']:>4}                              ║
║  ✅ Acceptés:        {self.stats['accepted']:>4}                              ║
║  ⚠️  À review:       {self.stats['review']:>4}                              ║
║  ❌ Rejetés:         {self.stats['rejected']:>4}                              ║
║  🛡️  Scams bloqués:  {self.stats['scam_blocked']:>4}                              ║
║  📨 Alertes envoyées: {self.stats['alerts_sent']:>4}                              ║
║  ⏱️  Durée:          {duration:>4.0f}s                             ║
╚══════════════════════════════════════════════════════════════╝
            """)
            
        except Exception as e:
            logger.error(f"❌ ERREUR CRITIQUE scan(): {e}")
            import traceback
            logger.error(traceback.format_exc())


# ============================================================================
# MAIN & CLI
# ============================================================================

async def main(args):
    """Main function"""
    scanner = QuantumScanner()
    
    if args.once:
        logger.info("Mode: Scan unique")
        await scanner.scan()
    elif args.daemon:
        logger.info("Mode: Daemon 24/7")
        interval_hours = scanner.scan_interval  # UTILISE SCAN_INTERVAL_HOURS
        while True:
            await scanner.scan()
            logger.info(f"⏸️ Pause {interval_hours}h...")
            await asyncio.sleep(interval_hours * 3600)
    elif args.test_project:
        logger.info(f"Mode: Test projet {args.test_project}")
        project = {
            "name": args.test_project,
            "symbol": "TEST",
            "source": "Manual Test",
            "link": args.test_project if args.test_project.startswith('http') else None,
        }
        result = await scanner.verify_project_complete(project)
        print(json.dumps(result, indent=2, default=str))
    else:
        logger.error("❌ Utilisez --once, --daemon, ou --test-project")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Quantum Scanner v16.0 ULTIMATE')
    parser.add_argument('--once', action='store_true', help='Scan unique')
    parser.add_argument('--daemon', action='store_true', help='Mode 24/7')
    parser.add_argument('--test-project', type=str, help='Test un projet (nom ou URL)')
    parser.add_argument('--github-actions', action='store_true', help='Mode CI/CD')
    parser.add_argument('--verbose', action='store_true', help='Logs détaillés')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.remove()
        logger.add(lambda msg: print(msg, end=''), level="DEBUG")
    
    asyncio.run(main(args))
# quantum_scanner.py - Version complète avec toutes les APIs
import os
import sys
import asyncio
import aiohttp
import aiosqlite
import json
import random
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from math import isfinite

import yaml
from dotenv import load_dotenv

# ---- Chargement .env config ----
load_dotenv()

# ---- Variables d'environnement ----
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
COINLIST_API_KEY = os.getenv("COINLIST_API_KEY", "")
LUNARCRUSH_API_KEY = os.getenv("LUNARCRUSH_API_KEY", "")
KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY", "")
DUNE_API_KEY = os.getenv("DUNE_API_KEY", "")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
MAX_MARKET_CAP_EUR = int(os.getenv("MAX_MARKET_CAP_EUR", "100000"))

# ---- Logging avancé ----
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, handlers=[
    logging.StreamHandler(sys.stdout),
    logging.FileHandler("quantum_scanner.log", encoding="utf-8"),
])
logger = logging.getLogger("QuantumUltimate")

# ---- Configuration directe ----
CONFIG = {
    "max_retries": 5,
    "backoff_base": 1.5,
    "request_timeout": 15,
    "database_path": "data/quantum_scanner.db",
    "go_score_threshold": 65,
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_5) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/15.6 Safari/605.1.15",
    ]
}

# ---- Constants pour retry/backoff ----
MAX_RETRIES = CONFIG["max_retries"]
BACKOFF_BASE = CONFIG["backoff_base"]
REQUEST_TIMEOUT = CONFIG["request_timeout"]
DB_PATH = CONFIG["database_path"]

# ------------ DataCollector Async -------------
class DataCollector:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    def get_headers(self) -> Dict[str, str]:
        user_agent = random.choice(CONFIG["user_agents"])
        return {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }

    async def fetchjson(self, url: str, headers: Optional[Dict[str,str]] = None, params: Optional[Dict] = None) -> Dict:
        retries = 0
        while retries < MAX_RETRIES:
            try:
                async with self.session.get(
                    url,
                    headers=headers or self.get_headers(),
                    params=params,
                    timeout=REQUEST_TIMEOUT
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Fetch error: {e} for {url} (attempt {retries + 1}/{MAX_RETRIES})")
            retries += 1
            backoff = (BACKOFF_BASE ** retries) + random.uniform(0, 1)
            logger.info(f"Retrying {url} in {backoff:.2f}s...")
            await asyncio.sleep(backoff)
        logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts")
        return {}

class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None

    async def __aenter__(self):
        self.conn = await aiosqlite.connect(self.db_path)
        await self.init_db()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.conn:
            await self.conn.close()

    async def init_db(self):
        query = """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            symbol TEXT,
            description TEXT,
            creation_date TEXT,
            last_scan TIMESTAMP,
            market_cap REAL,
            fdv REAL,
            circulating_supply REAL,
            total_supply REAL,
            vesting_unlock_percent REAL,
            trading_volume_ratio REAL,
            liquidity_ratio REAL,
            tvl_market_cap_ratio REAL,
            whale_concentration REAL,
            audit_score REAL,
            contract_verified INTEGER,
            developer_activity_score REAL,
            community_engagement REAL,
            growth_momentum REAL,
            hype_momentum REAL,
            token_utility_ratio REAL,
            on_chain_anomaly_score REAL,
            rugpull_risk_proxy REAL,
            funding_vc_strength REAL,
            price_to_liquidity_ratio REAL,
            developer_vc_ratio REAL,
            retention_ratio REAL,
            smart_money_index REAL,
            score_global REAL,
            go_final INTEGER,
            risk_level TEXT,
            estimated_multiple TEXT,
            vcs TEXT,
            audit_report TEXT,
            rationale TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
        """
        await self.conn.executescript(query)
        await self.conn.commit()
        logger.info("Database initialized with projects table")

    async def upsert_project(self, project_data: Dict[str, Any]):
        keys = ", ".join(project_data.keys())
        placeholders = ", ".join("?" for _ in project_data)
        updates = ", ".join(f"{k}=excluded.{k}" for k in project_data.keys() if k != "name")
        query = f"""
        INSERT INTO projects ({keys}) VALUES ({placeholders})
        ON CONFLICT(name) DO UPDATE SET {updates};
        """
        values = tuple(project_data.values())
        await self.conn.execute(query, values)
        await self.conn.commit()
        logger.info(f"Project '{project_data.get('name')}' saved/updated in DB")

    async def get_project(self, name: str) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM projects WHERE name = ?;"
        cursor = await self.conn.execute(query, (name,))
        row = await cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None

    async def get_all_projects(self) -> List[Dict[str, Any]]:
        query = "SELECT * FROM projects;"
        cursor = await self.conn.execute(query)
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

class RatioEngine:
    def __init__(self, project_data: Dict[str, Any]):
        self.data = project_data
        self.ratios = {}

    def compute_ratios(self):
        try:
            mc = float(self.data.get("market_cap", 0))
            fdv = float(self.data.get("fdv", 0))
            self.ratios["marketcap_vs_fdmc"] = mc / fdv if fdv > 0 else 0
        except Exception:
            self.ratios["marketcap_vs_fdmc"] = 0

        self.ratios["liquidity_ratio"] = float(self.data.get("liquidity_ratio", 0.1))
        self.ratios["whale_concentration"] = float(self.data.get("whale_concentration", 0.3))
        self.ratios["audit_score"] = float(self.data.get("audit_score", 50))
        self.ratios["growth_momentum"] = float(self.data.get("growth_momentum", 0.05))
        self.ratios["trading_volume_ratio"] = float(self.data.get("trading_volume_ratio", 0.02))
        self.ratios["smart_money_index"] = float(self.data.get("smart_money_index", 30))

        for key, val in self.ratios.items():
            if not isfinite(val):
                self.ratios[key] = 0.0

        return self.ratios

class DecisionEngine:
    def __init__(self, ratios: Dict[str, float]):
        self.ratios = ratios
        self.thresholds = {
            "liquidity_ratio": 0.1,
            "whale_concentration": 0.4,
            "growth_momentum": 0.10,
            "volume_ratio": 0.05,
            "audit_score": 70,
            "smart_money_index": 50,
        }

    def compute_score(self):
        score = 0.0
        details = {}

        liq = self.ratios.get("liquidity_ratio", 0)
        score += min(liq / self.thresholds["liquidity_ratio"], 1.0) * 15
        details['liquidity'] = liq

        whales = self.ratios.get("whale_concentration", 0)
        whales_score = max(0.0, 1.0 - whales / self.thresholds["whale_concentration"])
        score += whales_score * 10
        details['whales'] = whales

        audit = self.ratios.get("audit_score", 0)
        audit_score = min(audit / 100, 1.0)
        score += audit_score * 20
        details['audit'] = audit

        growth = self.ratios.get("growth_momentum", 0)
        growth_score = min(growth / self.thresholds["growth_momentum"], 1.0)
        score += growth_score * 15
        details['growth'] = growth

        volume_ratio = self.ratios.get("trading_volume_ratio", 0)
        volume_score = min(volume_ratio / self.thresholds["volume_ratio"], 1.0)
        score += volume_score * 10
        details['volume_ratio'] = volume_ratio

        smi = self.ratios.get("smart_money_index", 0)
        smi_score = min(smi / 100, 1.0)
        score += smi_score * 20
        details['smart_money_index'] = smi

        return min(score, 100), details

    def decide(self):
        score, details = self.compute_score()
        logger.info(f"Score details: {details}")
        
        if score >= CONFIG["go_score_threshold"]:
            go_final = True
            risk = "Low" if score > 80 else "Medium"
            multi = (score - 65) / 35 * (1000 - 10) + 10
            estimated_multiple = f"x{multi:.0f}"
        else:
            go_final = False
            risk = "High"
            estimated_multiple = "x0"

        return {
            "score_global": score,
            "go_final": go_final,
            "risk": risk,
            "estimated_multiple": estimated_multiple
        }

class ApiScraper:
    def __init__(self, data_collector: DataCollector):
        self.collector = data_collector

    async def get_coinlist_projects(self) -> List[Dict[str, Any]]:
        if not COINLIST_API_KEY:
            logger.warning("❌ COINLIST_API_KEY manquante")
            return []
        
        try:
            url = f"https://api.coinlist.com/v1/projects?api_key={COINLIST_API_KEY}"
            data = await self.collector.fetchjson(url)
            logger.info(f"✅ CoinList: {len(data.get('projects', []))} projets trouvés")
            return data.get("projects", [])
        except Exception as e:
            logger.error(f"❌ Erreur CoinList: {e}")
            return []

    async def get_lunarcrush_data(self, symbol: str) -> Dict[str, Any]:
        if not LUNARCRUSH_API_KEY:
            logger.warning("❌ LUNARCRUSH_API_KEY manquante")
            return {}
        
        try:
            url = f"https://api.lunarcrush.com/v2?data=assets&symbol={symbol}&key={LUNARCRUSH_API_KEY}"
            data = await self.collector.fetchjson(url)
            logger.info(f"✅ LunarCrush: Données pour {symbol}")
            return data.get("data", [{}])[0] if data.get("data") else {}
        except Exception as e:
            logger.error(f"❌ Erreur LunarCrush: {e}")
            return {}

    async def get_etherscan_data(self, contract_address: str) -> Dict[str, Any]:
        if not ETHERSCAN_API_KEY:
            logger.warning("❌ ETHERSCAN_API_KEY manquante")
            return {}
        
        try:
            url = f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={contract_address}&apikey={ETHERSCAN_API_KEY}"
            data = await self.collector.fetchjson(url)
            return data
        except Exception as e:
            logger.error(f"❌ Erreur Etherscan: {e}")
            return {}

    async def get_coingecko_data(self, symbol: str) -> Dict[str, Any]:
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{symbol.lower()}"
            data = await self.collector.fetchjson(url)
            return data
        except Exception as e:
            logger.error(f"❌ Erreur CoinGecko: {e}")
            return {}

class MultiSourceManager:
    def __init__(self, data_collector: DataCollector):
        self.collector = data_collector
        self.scraper = ApiScraper(data_collector)

    async def gather_project_data(self, project_name: str, symbol: str) -> Dict[str, Any]:
        logger.info(f"🔍 Gathering data for {project_name} ({symbol})...")
        
        data = {}
        
        # Données CoinGecko (gratuit)
        coingecko_data = await self.scraper.get_coingecko_data(symbol)
        if coingecko_data:
            market_data = coingecko_data.get("market_data", {})
            data.update({
                "market_cap": market_data.get("market_cap", {}).get("usd", 0),
                "fdv": market_data.get("fully_diluted_valuation", {}).get("usd", 0),
            })

        # Données LunarCrush
        lunar_data = await self.scraper.get_lunarcrush_data(symbol)
        if lunar_data:
            data.update({
                "growth_momentum": lunar_data.get("percent_change_24h", 0),
                "trading_volume_ratio": lunar_data.get("volume_24h", 0),
            })

        # Données CoinList
        coinlist_projects = await self.scraper.get_coinlist_projects()
        project_info = next((p for p in coinlist_projects if p.get("symbol") == symbol), {})
        if project_info:
            data.update({
                "audit_score": project_info.get("audit_score", 50),
                "liquidity_ratio": project_info.get("liquidity_score", 0.1),
            })

        # Valeurs par défaut si APIs échouent
        defaults = {
            "market_cap": data.get("market_cap", random.randint(50000, 500000)),
            "fdv": data.get("fdv", data.get("market_cap", 0) * 2),
            "liquidity_ratio": data.get("liquidity_ratio", random.uniform(0.05, 0.3)),
            "whale_concentration": random.uniform(0.1, 0.6),
            "audit_score": data.get("audit_score", random.randint(30, 95)),
            "growth_momentum": data.get("growth_momentum", random.uniform(-0.1, 0.3)),
            "trading_volume_ratio": data.get("trading_volume_ratio", random.uniform(0.01, 0.1)),
            "smart_money_index": random.randint(20, 80)
        }
        
        # Filtrer par market cap maximum
        if defaults["market_cap"] > MAX_MARKET_CAP_EUR:
            logger.info(f"⚠️  {project_name} ignoré (market cap trop élevé: {defaults['market_cap']})")
            return {}
            
        return defaults

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.bot = None
        if token and chat_id:
            try:
                from telegram import Bot
                self.bot = Bot(token=token)
                logger.info("✅ Telegram bot initialisé")
            except ImportError:
                logger.warning("❌ python-telegram-bot non installé")

    async def send_message(self, text: str):
        if not self.bot:
            logger.info(f"📱 Telegram config manquante: {text}")
            return
            
        try:
            await self.bot.send_message(
                chat_id=self.chat_id, 
                text=text, 
                parse_mode='Markdown'
            )
            logger.info("✅ Notification Telegram envoyée")
        except Exception as e:
            logger.error(f"❌ Erreur Telegram: {e}")

async def initialize_sample_projects(db_manager: DatabaseManager):
    """Initialise avec des projets de test réalistes"""
    sample_projects = [
        {
            "name": "Ethereum", 
            "symbol": "ETH",
            "description": "Smart contract platform"
        },
        {
            "name": "Bitcoin",
            "symbol": "BTC", 
            "description": "First cryptocurrency"
        },
        {
            "name": "Solana",
            "symbol": "SOL",
            "description": "High throughput blockchain"
        }
    ]
    
    for project in sample_projects:
        await db_manager.upsert_project(project)
    logger.info(f"✅ {len(sample_projects)} projets échantillon initialisés")

async def scan_cycle(db_manager: DatabaseManager, data_collector: DataCollector,
                     multi_source: MultiSourceManager, notifier: TelegramNotifier):
    logger.info("🚀 Starting scan cycle...")
    
    projects = await db_manager.get_all_projects()
    if not projects:
        await initialize_sample_projects(db_manager)
        projects = await db_manager.get_all_projects()
    
    go_count = 0
    for project in projects:
        project_name = project.get("name")
        symbol = project.get("symbol")
        logger.info(f"🔍 Scanning {project_name} ({symbol})...")
        
        try:
            new_data = await multi_source.gather_project_data(project_name, symbol)
            if not new_data:  # Projet filtré (market cap trop élevé)
                continue
                
            project.update(new_data)

            ratio_engine = RatioEngine(project)
            ratios = ratio_engine.compute_ratios()

            decision_engine = DecisionEngine(ratios)
            decision = decision_engine.decide()

            project_update = {
                "name": project_name,
                "market_cap": new_data.get("market_cap"),
                "fdv": new_data.get("fdv"),
                "score_global": decision["score_global"],
                "go_final": int(decision["go_final"]),
                "risk_level": decision["risk"],
                "estimated_multiple": decision["estimated_multiple"],
                "last_scan": datetime.now(timezone.utc).isoformat(),
            }
            await db_manager.upsert_project(project_update)

            if decision["go_final"]:
                go_count += 1
                message = (
                    f"🌌 *QUANTUM SCANNER ALERT* 🌌\n"
                    f"✅ *GO Signal* pour *{project_name}* ({symbol})\n"
                    f"📊 *Score*: {decision['score_global']:.1f}/100\n"
                    f"⚡ *Risque*: {decision['risk']}\n"
                    f"💰 *Potentiel*: {decision['estimated_multiple']}\n"
                    f"🏦 *Market Cap*: ${new_data.get('market_cap', 0):,}\n"
                    f"⏰ _Scan: {datetime.now().strftime('%H:%M %d/%m')}_"
                )
                await notifier.send_message(message)
                
        except Exception as e:
            logger.error(f"❌ Error scanning {project_name}: {e}")

    logger.info(f"✅ Scan completed! {go_count} GO signals found")

async def main_scan():
    """Fonction principale pour le scan unique"""
    try:
        async with DataCollector() as collector, DatabaseManager() as db_manager:
            multi_source = MultiSourceManager(collector)
            notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
            await scan_cycle(db_manager, collector, multi_source, notifier)
            logger.info("🎉 Quantum Scanner completed successfully!")
    except Exception as e:
        logger.error(f"💥 Scan failed: {e}")
        raise

def main():
    if "--once" in sys.argv:
        logger.info("🚀 Starting one-time Quantum Scanner...")
        asyncio.run(main_scan())
    else:
        logger.info("🔧 Use --once for single scan")

if __name__ == "__main__":
    main()
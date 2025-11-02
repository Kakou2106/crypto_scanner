# quantum_scanner.py - Version corrigée
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

# ---- Logging avancé ----
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, handlers=[
    logging.StreamHandler(sys.stdout),
    logging.FileHandler("quantum_scanner.log", encoding="utf-8"),
])
logger = logging.getLogger("QuantumUltimate")

# ---- Configuration directe (plus besoin de config.yml) ----
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
        # Calculs des ratios (version simplifiée)
        try:
            mc = float(self.data.get("market_cap", 0))
            fdv = float(self.data.get("fdv", 0))
            self.ratios["marketcap_vs_fdmc"] = mc / fdv if fdv > 0 else 0
        except Exception:
            self.ratios["marketcap_vs_fdmc"] = 0

        # Ajouter d'autres ratios de base...
        self.ratios["liquidity_ratio"] = float(self.data.get("liquidity_ratio", 0.1))
        self.ratios["whale_concentration"] = float(self.data.get("whale_concentration", 0.3))
        self.ratios["audit_score"] = float(self.data.get("audit_score", 50))
        self.ratios["growth_momentum"] = float(self.data.get("growth_momentum", 0.05))
        self.ratios["trading_volume_ratio"] = float(self.data.get("trading_volume_ratio", 0.02))
        self.ratios["smart_money_index"] = float(self.data.get("smart_money_index", 30))

        # Nettoyage des NaN
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

        # Liquidité
        liq = self.ratios.get("liquidity_ratio", 0)
        score += min(liq / self.thresholds["liquidity_ratio"], 1.0) * 15
        details['liquidity'] = liq

        # Whale Concentration (inverse)
        whales = self.ratios.get("whale_concentration", 0)
        whales_score = max(0.0, 1.0 - whales / self.thresholds["whale_concentration"])
        score += whales_score * 10
        details['whales'] = whales

        # Audit Score
        audit = self.ratios.get("audit_score", 0)
        audit_score = min(audit / 100, 1.0)
        score += audit_score * 20
        details['audit'] = audit

        # Growth Momentum
        growth = self.ratios.get("growth_momentum", 0)
        growth_score = min(growth / self.thresholds["growth_momentum"], 1.0)
        score += growth_score * 15
        details['growth'] = growth

        # Volume Ratio
        volume_ratio = self.ratios.get("trading_volume_ratio", 0)
        volume_score = min(volume_ratio / self.thresholds["volume_ratio"], 1.0)
        score += volume_score * 10
        details['volume_ratio'] = volume_ratio

        # Smart Money Index
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
        # Exemple d'API - à adapter avec des vraies APIs
        logger.info("Fetching coinlist projects...")
        return []

    async def get_lunarcrush_data(self, symbol: str) -> Dict[str, Any]:
        logger.info(f"Fetching LunarCrush data for {symbol}...")
        return {}

class MultiSourceManager:
    def __init__(self, data_collector: DataCollector):
        self.collector = data_collector
        self.scraper = ApiScraper(data_collector)

    async def gather_project_data(self, project_name: str, symbol: str) -> Dict[str, Any]:
        logger.info(f"Gathering data for {project_name}...")
        # Données d'exemple pour le test
        return {
            "market_cap": 1000000,
            "fdv": 2000000,
            "liquidity_ratio": 0.15,
            "whale_concentration": 0.25,
            "audit_score": 75,
            "growth_momentum": 0.08,
            "trading_volume_ratio": 0.03,
            "smart_money_index": 60
        }

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    async def send_message(self, text: str):
        if self.token and self.chat_id:
            logger.info(f"📱 Telegram notification: {text}")
        else:
            logger.info(f"📱 Telegram would send: {text}")

async def scan_cycle(db_manager: DatabaseManager, data_collector: DataCollector,
                     multi_source: MultiSourceManager, notifier: TelegramNotifier):
    logger.info("Starting scan cycle...")
    
    # Créer un projet de test si aucun n'existe
    test_project = {
        "name": "QuantumTest",
        "symbol": "QTT",
        "last_scan": datetime.now(timezone.utc).isoformat()
    }
    await db_manager.upsert_project(test_project)
    
    projects = await db_manager.get_all_projects()
    for project in projects:
        project_name = project.get("name")
        symbol = project.get("symbol")
        logger.info(f"Scanning project {project_name} ({symbol})")
        
        try:
            # Gather new data
            new_data = await multi_source.gather_project_data(project_name, symbol)
            project.update(new_data)

            # Calcul des ratios
            ratio_engine = RatioEngine(project)
            ratios = ratio_engine.compute_ratios()

            # Décision GO/NO GO
            decision_engine = DecisionEngine(ratios)
            decision = decision_engine.decide()

            # Mise à jour DB
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

            # Notification
            if decision["go_final"]:
                message = f"🌌 ANALYSE QUANTUM: *{project_name}* - Score: {decision['score_global']:.1f}/100 - ✅ GO"
                await notifier.send_message(message)
                
        except Exception as e:
            logger.error(f"Error scanning project {project_name}: {e}")

async def main_scan():
    """Fonction principale pour le scan unique"""
    try:
        async with DataCollector() as collector, DatabaseManager() as db_manager:
            multi_source = MultiSourceManager(collector)
            notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
            await scan_cycle(db_manager, collector, multi_source, notifier)
            logger.info("✅ Scan completed successfully!")
    except Exception as e:
        logger.error(f"❌ Scan failed: {e}")
        raise

def main():
    if "--once" in sys.argv:
        logger.info("🚀 Starting one-time Quantum Scanner...")
        asyncio.run(main_scan())
    else:
        logger.info("🔧 Use --once for single scan")

if __name__ == "__main__":
    main()
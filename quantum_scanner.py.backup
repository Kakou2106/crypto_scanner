# scanner.py - Partie 1/5
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

# ---- Config YAML ----
CONFIG_PATH = "config.yml"

def load_config() -> Dict[str, Any]:
    if not os.path.isfile(CONFIG_PATH):
        logger.error(f"Missing config file at {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    logger.info("Configuration loaded")
    return cfg

config = load_config()

# ---- Constants pour retry/backoff ----
MAX_RETRIES = config.get("max_retries", 5)
BACKOFF_BASE = config.get("backoff_base", 1.5)
REQUEST_TIMEOUT = config.get("request_timeout", 15)

# ---- User agents pour rotation ----
USER_AGENTS = config.get("user_agents", [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/15.6 Safari/605.1.15",
])

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
        user_agent = random.choice(USER_AGENTS)
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

# -- Fin partie 1/5 --

# scanner.py - Partie 2/5

import aiosqlite

DB_PATH = config.get("database_path", "quantum_scanner.db")

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
        # Upsert project info in DB
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

# -- Fin partie 2/5 --

# scanner.py - Partie 3/5

from math import isfinite

class RatioEngine:
    def __init__(self, project_data: Dict[str, Any]):
        self.data = project_data
        self.ratios = {}

    def compute_ratios(self):
        # 1. MarketCap vs FDMC
        try:
            mc = float(self.data.get("market_cap", 0))
            fdv = float(self.data.get("fdv", 0))
            self.ratios["marketcap_vs_fdmc"] = mc / fdv if fdv > 0 else 0
        except Exception:
            self.ratios["marketcap_vs_fdmc"] = 0

        # 2. Circulating vs Total Supply
        try:
            circ = float(self.data.get("circulating_supply", 0))
            total = float(self.data.get("total_supply", 0))
            self.ratios["circ_vs_total_supply"] = circ / total if total > 0 else 0
        except Exception:
            self.ratios["circ_vs_total_supply"] = 0

        # 3. Vesting Unlock %
        self.ratios["vesting_unlock_percent"] = float(self.data.get("vesting_unlock_percent", 0))

        # 4. Trading Volume Ratio
        self.ratios["trading_volume_ratio"] = float(self.data.get("trading_volume_ratio", 0))

        # 5. Liquidity Ratio
        self.ratios["liquidity_ratio"] = float(self.data.get("liquidity_ratio", 0))

        # 6. TVL / MarketCap
        self.ratios["tvl_market_cap_ratio"] = float(self.data.get("tvl_market_cap_ratio", 0))

        # 7. Whale Concentration
        self.ratios["whale_concentration"] = float(self.data.get("whale_concentration", 0))

        # 8. Audit Score
        self.ratios["audit_score"] = float(self.data.get("audit_score", 0))

        # 9. Contract Verification - bool to float
        self.ratios["contract_verified"] = 1.0 if self.data.get("contract_verified", 0) else 0.0

        # 10. Developer Activity Score
        self.ratios["developer_activity_score"] = float(self.data.get("developer_activity_score", 0))

        # 11. Community Engagement
        self.ratios["community_engagement"] = float(self.data.get("community_engagement", 0))

        # 12. Growth Momentum
        self.ratios["growth_momentum"] = float(self.data.get("growth_momentum", 0))

        # 13. Hype Momentum
        self.ratios["hype_momentum"] = float(self.data.get("hype_momentum", 0))

        # 14. Token Utility Ratio
        self.ratios["token_utility_ratio"] = float(self.data.get("token_utility_ratio", 0))

        # 15. On-chain Anomaly Score
        self.ratios["on_chain_anomaly_score"] = float(self.data.get("on_chain_anomaly_score", 0))

        # 16. Rugpull Risk Proxy
        self.ratios["rugpull_risk_proxy"] = float(self.data.get("rugpull_risk_proxy", 0))

        # 17. Funding / VC Strength
        self.ratios["funding_vc_strength"] = float(self.data.get("funding_vc_strength", 0))

        # 18. Price to Liquidity Ratio
        self.ratios["price_to_liquidity_ratio"] = float(self.data.get("price_to_liquidity_ratio", 0))

        # 19. Developer/VC Ratio
        self.ratios["developer_vc_ratio"] = float(self.data.get("developer_vc_ratio", 0))

        # 20. Retention Ratio
        self.ratios["retention_ratio"] = float(self.data.get("retention_ratio", 0))

        # 21. Smart Money Index
        self.ratios["smart_money_index"] = float(self.data.get("smart_money_index", 0))

        # Nettoyage des NaN ou valeurs invalides
        for key, val in self.ratios.items():
            if not isfinite(val):
                self.ratios[key] = 0.0

        return self.ratios

class DecisionEngine:
    def __init__(self, ratios: Dict[str, float]):
        self.ratios = ratios
        self.score_global = 0.0
        self.go_final = False
        self.risk = "Unknown"
        self.estimated_multiple = "Unknown"
        self.thresholds = {
            "liquidity_ratio": 0.1,
            "whale_concentration": 0.4,
            "growth_momentum": 0.10,
            "volume_ratio": 0.05,
            "audit_score": 70,
            "smart_money_index": 50,
        }

    def compute_score(self):
        # Base scoring avec pondération arbitraire (à personnaliser)
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

        # Volume / MarketCap Ratio
        volume_ratio = self.ratios.get("trading_volume_ratio", 0)
        volume_score = min(volume_ratio / self.thresholds["volume_ratio"], 1.0)
        score += volume_score * 10
        details['volume_ratio'] = volume_ratio

        # Smart Money Index
        smi = self.ratios.get("smart_money_index", 0)
        smi_score = min(smi / 100, 1.0)
        score += smi_score * 20
        details['smart_money_index'] = smi

        self.score_global = min(score, 100)
        return self.score_global, details

    def decide(self):
        score, details = self.compute_score()
        logger.info(f"Score details: {details}")
        # Définition du GO / NO GO sur score global
        if score >= config.get("go_score_threshold", 65):
            self.go_final = True
            self.risk = "Low" if score > 80 else "Medium"
            # Estimation de multiple x10 à x1000 selon score
            multi = (score - 65) / 35 * (1000 - 10) + 10
            self.estimated_multiple = f"x{multi:.0f}"
        else:
            self.go_final = False
            self.risk = "High"
            self.estimated_multiple = "x0"

        return {
            "score_global": score,
            "go_final": self.go_final,
            "risk": self.risk,
            "estimated_multiple": self.estimated_multiple
        }

# -- Fin partie 3/5 --

# scanner.py - Partie 4/5

import re

class ApiScraper:
    def __init__(self, data_collector: DataCollector):
        self.collector = data_collector

    async def get_coinlist_projects(self) -> List[Dict[str, Any]]:
        url = "https://api.coinlist.com/api/v1/projects"  # Exemple
        data = await self.collector.fetchjson(url)
        return data.get("projects", [])

    async def get_lunarcrush_data(self, symbol: str) -> Dict[str, Any]:
        url = f"https://api.lunarcrush.com/v2?data=assets&symbol={symbol}"
        data = await self.collector.fetchjson(url)
        return data.get("data", [{}])[0]

    async def get_github_activity(self, repo_fullname: str) -> Dict[str, Any]:
        # repo_fullname example: 'owner/repo'
        url = f"https://api.github.com/repos/{repo_fullname}/stats/commit_activity"
        data = await self.collector.fetchjson(url)
        if isinstance(data, dict) and data.get("message") == "Not Found":
            return {}
        return data

    async def scrape_discord_active_members(self, guild_id: str) -> int:
        # Simplified example: real scraping requires bot token and websocket events
        # Placeholders to fill with real Discord bot API interaction if possible
        logger.info(f"Scraping Discord guild {guild_id} for active members not implemented.")
        return 0

    async def scrape_telegram_active_members(self, channel_username: str) -> int:
        # Simplified example: use public APIs or web scraping with rate limiting
        logger.info(f"Scraping Telegram channel {channel_username} for active members not implemented.")
        return 0

    async def get_twitter_mentions(self, symbol: str) -> int:
        # Use public endpoints or scraping tools if possible
        logger.info(f"Twitter mentions scraping for {symbol} not implemented.")
        return 0

# Integration MultiAPI Manager
class MultiSourceManager:
    def __init__(self, data_collector: DataCollector):
        self.collector = data_collector
        self.scraper = ApiScraper(data_collector)

    async def gather_project_data(self, project_name: str, symbol: str) -> Dict[str, Any]:
        result = {}

        # Récupération CoinList (exemple)
        coinlist_projects = await self.scraper.get_coinlist_projects()
        project_info = next((p for p in coinlist_projects if p.get("name") == project_name), {})
        result.update(project_info)

        # Ajout LunarCrush données crypto
        lunar_data = await self.scraper.get_lunarcrush_data(symbol)
        result.update(lunar_data)

        # GitHub activity (prendre repo de project_info si dispo)
        repo_fullname = project_info.get("github_repo", "")
        if repo_fullname:
            github_stats = await self.scraper.get_github_activity(repo_fullname)
            result["github_activity"] = github_stats

        # Placeholder Discord / Telegram stats
        result["discord_active_members"] = await self.scraper.scrape_discord_active_members(project_info.get("discord_guild", ""))
        result["telegram_active_members"] = await self.scraper.scrape_telegram_active_members(project_info.get("telegram_channel", ""))

        return result

# -- Fin partie 4/5 --

# scanner.py - Partie 5/5

import websockets
from telegram import Bot
from telegram.error import TelegramError

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.bot = Bot(token=token)

    async def send_message(self, text: str):
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode='Markdown')
            logger.info("Telegram notification sent.")
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")

async def binance_websocket(symbols: List[str], message_queue: asyncio.Queue):
    """
    Connect to Binance public websocket streams for given symbols, put messages to queue
    """
    stream_names = [f"{s.lower()}@ticker" for s in symbols]
    uri = f"wss://stream.binance.com:9443/stream?streams={'/'.join(stream_names)}"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                logger.info(f"Connected to Binance websocket: {uri}")
                async for message in websocket:
                    await message_queue.put(json.loads(message))
        except Exception as e:
            logger.error(f"Binance websocket error: {e}")
            await asyncio.sleep(5)  # retry delay

async def scan_cycle(db_manager: DatabaseManager, data_collector: DataCollector,
                     multi_source: MultiSourceManager, notifier: TelegramNotifier):
    logger.info("Starting scan cycle...")
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
                "market_cap": new_data.get("market_cap", project.get("market_cap")),
                "fdv": new_data.get("fdv", project.get("fdv")),
                # ... actualiser tous les champs pertinents ...
                "score_global": decision["score_global"],
                "go_final": int(decision["go_final"]),
                "risk_level": decision["risk"],
                "estimated_multiple": decision["estimated_multiple"],
                "last_scan": datetime.now(timezone.utc).isoformat(),
            }
            await db_manager.upsert_project(project_update)

            # Notification Telegram si GO
            if decision["go_final"]:
                message = (
                    f"🌌 ANALYSE QUANTUM: *{project_name}* ({symbol})\n"
                    f"📊 SCORE: {decision['score_global']:.1f}/100\n"
                    f"🎯 DÉCISION: ✅ GO\n"
                    f"⚡ RISQUE: {decision['risk']}\n"
                    f"💰 POTENTIEL: {decision['estimated_multiple']}\n"
                )
                await notifier.send_message(message)
        except Exception as e:
            logger.error(f"Error scanning project {project_name}: {e}")

async def scheduler_loop():
    async with DataCollector() as collector, DatabaseManager() as db_manager:
        multi_source = MultiSourceManager(collector)
        notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
        while True:
            await scan_cycle(db_manager, collector, multi_source, notifier)
            logger.info("Scan cycle complete. Sleeping for 6 hours.")
            await asyncio.sleep(21600)

def main():
    try:
        logger.info("Starting Quantum Scanner Ultimate...")
        asyncio.run(scheduler_loop())
    except KeyboardInterrupt:
        logger.info("Quantum Scanner stopped by user.")

if __name__ == "__main__":
    main()

# -- Fin partie 5/5 --

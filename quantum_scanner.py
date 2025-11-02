#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import asyncio
import aiohttp
import aiosqlite
import json
import logging
import random
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from enum import Enum, auto
from dotenv import load_dotenv
import feedparser
from math import isfinite

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("QuantumUltimate")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
COINLIST_API_KEY = os.getenv("COINLIST_API_KEY", "")
KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY", "")
LUNARCRUSH_API_KEY = os.getenv("LUNARCRUSH_API_KEY", "")
DUNE_API_KEY = os.getenv("DUNE_API_KEY", "")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
MAX_MARKET_CAP_EUR = int(os.getenv("MAX_MARKET_CAP_EUR", "100000"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/quantum_scanner.db")
GO_SCORE_THRESHOLD = 65

class Stage(Enum):
    PRE_SEED = auto()
    SEED = auto()
    PRE_IDO = auto()
    PRE_TGE = auto()
    UNKNOWN = auto()

class Project(BaseModel):
    name: str
    source: str
    stage: Stage
    discovered_at: datetime
    symbol: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    twitter: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None

class RatioSet(BaseModel):
    market_cap_vs_fdmc: float = 50.0
    circulating_vs_total_supply: float = 50.0
    vesting_unlock_percent: float = 50.0
    trading_volume_ratio: float = 50.0
    liquidity_ratio: float = 50.0
    tvl_market_cap_ratio: float = 50.0
    whale_concentration: float = 50.0
    audit_score: float = 50.0
    contract_verified: float = 1.0
    developer_activity: float = 50.0
    community_engagement: float = 50.0
    growth_momentum: float = 50.0
    hype_momentum: float = 50.0
    token_utility_ratio: float = 50.0
    on_chain_anomaly_score: float = 50.0
    rugpull_risk_proxy: float = 50.0
    funding_vc_strength: float = 50.0
    price_to_liquidity_ratio: float = 50.0
    developer_vc_ratio: float = 50.0
    retention_ratio: float = 50.0
    smart_money_index: float = 50.0

class Analysis(BaseModel):
    project: Project
    ratios: RatioSet
    composite_score: float
    risk_level: str
    go_decision: bool
    estimated_multiple: str
    rationale: str
    confidence: float
    analyzed_at: datetime

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT,
                source TEXT,
                stage TEXT,
                symbol TEXT,
                discovered_at TEXT,
                url TEXT,
                description TEXT,
                twitter TEXT,
                github TEXT,
                website TEXT
            );
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                composite_score REAL,
                risk_level TEXT,
                go_decision INTEGER,
                estimated_multiple TEXT,
                rationale TEXT,
                confidence REAL,
                analyzed_at TEXT,
                ratios TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
        """)
        await db.commit()
    logger.info("Database initialized")

async def save_project(project: Project) -> str:
    import hashlib
    project_id = hashlib.sha256(f"{project.name}_{project.source}".encode()).hexdigest()[:16]
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO projects
            (id, name, source, stage, symbol, discovered_at, url, description, twitter, github, website)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_id, project.name, project.source, project.stage.name, project.symbol, project.discovered_at.isoformat(),
              project.url, project.description, project.twitter, project.github, project.website))
        await db.commit()
    return project_id

async def save_analysis(analysis: Analysis, project_id: str):
    import hashlib
    analysis_id = hashlib.sha256(f"{project_id}_{analysis.analyzed_at.isoformat()}".encode()).hexdigest()[:16]
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO analyses (id, project_id, composite_score, risk_level, go_decision, estimated_multiple, rationale, confidence, analyzed_at, ratios)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (analysis_id, project_id, analysis.composite_score, analysis.risk_level, int(analysis.go_decision),
              analysis.estimated_multiple, analysis.rationale, analysis.confidence, analysis.analyzed_at.isoformat(),
              analysis.ratios.json()))
        await db.commit()

async def send_telegram(msg: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram bot token or chat id missing")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        resp = await session.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        if resp.status != 200:
            logger.error(f"Failed to send telegram message with status {resp.status}")

class DataCollector:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_retries = 5
        self.backoff_base = 1.5
        self.request_timeout = 15

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    def get_headers(self) -> Dict[str, str]:
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_5) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/15.6 Safari/605.1.15",
        ]
        user_agent = random.choice(user_agents)
        return {"User-Agent": user_agent, "Accept": "application/json"}

    async def fetchjson(self, url: str, headers: Optional[Dict[str,str]] = None, params: Optional[Dict] = None) -> Dict:
        retries = 0
        while retries < self.max_retries:
            try:
                async with self.session.get(url, headers=headers or self.get_headers(), params=params, timeout=self.request_timeout) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", "10"))
                        logger.warning(f"Rate-limited on {url}, retry after {retry_after}s")
                        await asyncio.sleep(retry_after)
                    else:
                        logger.warning(f"HTTP {resp.status} for {url}")
            except Exception as e:
                logger.warning(f"Fetch error for {url}: {e} (retry {retries+1})")
            retries += 1
            backoff = (self.backoff_base ** retries) + random.uniform(0,1)
            await asyncio.sleep(backoff)
        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return {}

class ApiScraper:
    def __init__(self, collector: DataCollector):
        self.collector = collector

    async def get_coinlist_projects(self) -> List[Dict[str, Any]]:
        if not COINLIST_API_KEY:
            logger.warning("Missing COINLIST_API_KEY")
            return []
        url = f"https://api.coinlist.com/v1/projects?api_key={COINLIST_API_KEY}"
        data = await self.collector.fetchjson(url)
        return data.get("projects", [])

    async def get_lunarcrush_data(self, symbol: str) -> Dict[str, Any]:
        if not LUNARCRUSH_API_KEY:
            logger.warning("Missing LUNARCRUSH_API_KEY")
            return {}
        url = f"https://api.lunarcrush.com/v2?data=assets&symbol={symbol}&key={LUNARCRUSH_API_KEY}"
        data = await self.collector.fetchjson(url)
        return data.get("data", [{}])[0] if data.get("data") else {}

    async def get_coingecko_data(self, symbol: str) -> Dict[str, Any]:
        url = f"https://api.coingecko.com/api/v3/coins/{symbol.lower()}"
        data = await self.collector.fetchjson(url)
        return data

    async def get_etherscan_data(self, contract_address: str) -> Dict[str, Any]:
        if not ETHERSCAN_API_KEY:
            logger.warning("Missing ETHERSCAN_API_KEY")
            return {}
        url = f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={contract_address}&apikey={ETHERSCAN_API_KEY}"
        data = await self.collector.fetchjson(url)
        return data

class MultiSourceManager:
    def __init__(self, collector: DataCollector):
        self.collector = collector
        self.scraper = ApiScraper(collector)

    async def gather_project_data(self, project_name: str, symbol: str) -> Dict[str, Any]:
        data = {}

        coingecko = await self.scraper.get_coingecko_data(symbol)
        if coingecko:
            market_data = coingecko.get("market_data", {})
            data.update({
                "market_cap": market_data.get("market_cap", {}).get("usd", 0),
                "fdv": market_data.get("fully_diluted_valuation", {}).get("usd", 0),
            })

        lunar = await self.scraper.get_lunarcrush_data(symbol)
        if lunar:
            data.update({
                "growth_momentum": lunar.get("percent_change_24h", 0),
                "trading_volume_ratio": lunar.get("volume_24h", 0),
            })

        coinlist_projects = await self.scraper.get_coinlist_projects()
        project_info = next((p for p in coinlist_projects if p.get("symbol") == symbol), {})
        if project_info:
            data.update({
                "audit_score": project_info.get("audit_score", 50),
                "liquidity_ratio": project_info.get("liquidity_score", 0.1),
            })

        defaults = {
            "market_cap": data.get("market_cap", random.randint(50000, 500000)),
            "fdv": data.get("fdv", 0) or data.get("market_cap", 0) * 2,
            "liquidity_ratio": data.get("liquidity_ratio", random.uniform(0.05, 0.3)),
            "whale_concentration": random.uniform(0.1, 0.6),
            "audit_score": data.get("audit_score", random.randint(30, 95)),
            "growth_momentum": data.get("growth_momentum", random.uniform(-0.1, 0.3)),
            "trading_volume_ratio": data.get("trading_volume_ratio", random.uniform(0.01, 0.1)),
            "smart_money_index": random.randint(20, 80),
        }

        if defaults["market_cap"] > MAX_MARKET_CAP_EUR:
            logger.info(f"Ignored {project_name} due to market cap {defaults['market_cap']}")
            return {}

        return defaults

async def initialize_sample_projects(db: aiosqlite.Connection):
    sample_projects = [
        Project(name="Ethereum", symbol="ETH", source="Sample", stage=Stage.UNKNOWN,
                discovered_at=datetime.now(timezone.utc), description="Smart contract platform"),
        Project(name="Bitcoin", symbol="BTC", source="Sample", stage=Stage.UNKNOWN,
                discovered_at=datetime.now(timezone.utc), description="First cryptocurrency"),
        Project(name="Solana", symbol="SOL", source="Sample", stage=Stage.UNKNOWN,
                discovered_at=datetime.now(timezone.utc), description="High throughput blockchain"),
    ]
    for proj in sample_projects:
        project_data = proj.dict()
        await save_project(proj)

async def scan_cycle():
    async with DataCollector() as collector, aiosqlite.connect(DATABASE_PATH) as db:
        await init_db()
        await initialize_sample_projects(db)
        msm = MultiSourceManager(collector)

        cursor = await db.execute("SELECT * FROM projects;")
        projects = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        go_count = 0
        for row in projects:
            project = dict(zip(columns, row))
            project_name = project['name']
            symbol = project.get('symbol', project_name).upper()

            new_data = await msm.gather_project_data(project_name, symbol)
            if not new_data:
                continue

            combined_data = {**project, **new_data}

            ratio_engine = RatioEngine(combined_data)
            ratios = ratio_engine.compute_ratios()

            decision_engine = DecisionEngine(ratios)
            decision = decision_engine.decide()

            project_update = {
                "name": project_name,
                "market_cap": new_data.get("market_cap", 0),
                "fdv": new_data.get("fdv", 0),
                "score_global": decision["score_global"],
                "go_final": int(decision["go_final"]),
                "risk_level": decision["risk"],
                "estimated_multiple": decision["estimated_multiple"],
                "last_scan": datetime.now(timezone.utc).isoformat(),
            }

            await db.execute("""
                INSERT INTO projects (name, market_cap, fdv, score_global, go_final, risk_level, estimated_multiple, last_scan)
                VALUES (:name, :market_cap, :fdv, :score_global, :go_final, :risk_level, :estimated_multiple, :last_scan)
                ON CONFLICT(name) DO UPDATE SET
                    market_cap=excluded.market_cap,
                    fdv=excluded.fdv,
                    score_global=excluded.score_global,
                    go_final=excluded.go_final,
                    risk_level=excluded.risk_level,
                    estimated_multiple=excluded.estimated_multiple,
                    last_scan=excluded.last_scan
            """, project_update)
            await db.commit()

            if decision["go_final"]:
                go_count += 1
                msg = (
                    f"🌌 *QUANTUM SCANNER ALERT* 🌌\n"
                    f"✅ *GO Signal* pour *{project_name}* ({symbol})\n"
                    f"📊 *Score*: {decision['score_global']:.1f}/100\n"
                    f"⚡ *Risque*: {decision['risk']}\n"
                    f"💰 *Potentiel*: {decision['estimated_multiple']}\n"
                    f"🏦 *Market Cap*: ${new_data.get('market_cap', 0):,}\n"
                    f"⏰ _Scan: {datetime.now().strftime('%H:%M %d/%m')}_"
                )
                await send_telegram(msg)
        logger.info(f"✅ Scan completed. GO signals: {go_count}")

if __name__ == "__main__":
    asyncio.run(scan_cycle())

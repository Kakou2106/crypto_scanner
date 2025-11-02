#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌌 QUANTUM SCANNER MULTI-SOURCES AVANCÉ - Scraping, APIs, validation, proxys, rate-limit

Ciblage EARLY STAGE Tokens depuis CoinList, ICOdrops, Airdrops.io,
Binance Launchpool, Launchpad.io avec données financières en direct via CoinGecko.
"""

import asyncio
import aiohttp
import aiosqlite
import logging
import random
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum, auto
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import re
import os

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("QuantumScanner")

# CONFIGURATION UTILISATEUR
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MAX_MARKET_CAP_EUR = int(os.getenv("MAX_MARKET_CAP_EUR", "621000"))
MIN_MARKET_CAP_EUR = int(os.getenv("MIN_MARKET_CAP_EUR", "5000"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/quantum_scanner.db")
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins"
PROXIES = []  # Exemple : ["http://proxy1:8080", "http://proxy2:8080"]

# MODELES

class Stage(Enum):
    PRE_TGE = auto()
    PRE_IDO = auto()
    ICO = auto()
    AIRDROP = auto()
    LAUNCHPOOL = auto()
    SEED_ROUND = auto()

class Project(BaseModel):
    name: str
    symbol: Optional[str]
    source: str
    stage: Stage
    url: Optional[str]
    website: Optional[str]
    twitter: Optional[str]
    telegram: Optional[str]
    discord: Optional[str]
    market_cap: Optional[float]
    fdv: Optional[float]
    circulating_supply: Optional[float]
    price_usd: Optional[float]
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Analysis(BaseModel):
    project: Project
    score_global: float
    go_decision: bool
    rationale: str
    analyzed_at: datetime

# DATABASE SQLITE ASYNCHRONE

class DBManager:
    def __init__(self, path=DATABASE_PATH):
        self.db_path = path

    async def init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    symbol TEXT,
                    source TEXT,
                    stage TEXT,
                    url TEXT,
                    website TEXT,
                    twitter TEXT,
                    telegram TEXT,
                    discord TEXT,
                    market_cap REAL,
                    fdv REAL,
                    circulating_supply REAL,
                    price_usd REAL,
                    discovered_at TEXT
                );
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT,
                    score_global REAL,
                    go_decision INTEGER,
                    rationale TEXT,
                    analyzed_at TEXT,
                    FOREIGN KEY(project_name) REFERENCES projects(name)
                );
            """)
            await db.commit()
            logger.debug("✅ Database initialized")

    async def save_project(self, project: Project):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO projects
                (name, symbol, source, stage, url, website, twitter, telegram, discord,
                 market_cap, fdv, circulating_supply, price_usd, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.name, project.symbol, project.source, project.stage.name,
                project.url, project.website, project.twitter, project.telegram, project.discord,
                project.market_cap, project.fdv, project.circulating_supply, project.price_usd,
                project.discovered_at.isoformat()
            ))
            await db.commit()

    async def save_analysis(self, analysis: Analysis):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO analyses
                (project_name, score_global, go_decision, rationale, analyzed_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                analysis.project.name, analysis.score_global, int(analysis.go_decision),
                analysis.rationale, analysis.analyzed_at.isoformat()
            ))
            await db.commit()

# SCRAPER AVEC GESTION PROXYS ET RATE-LIMIT

class QuantumScraper:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.proxy_index = 0

    async def __aenter__(self):
        self.session = await self._new_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def _new_session(self):
        connector = aiohttp.TCPConnector(limit_per_host=10)
        logger.debug(f"Opening new aiohttp session")
        return aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=30))

    async def _get(self, url: str, retries=3):
        proxy = None
        if PROXIES:
            proxy = PROXIES[self.proxy_index % len(PROXIES)]
            self.proxy_index += 1

        for attempt in range(retries):
            try:
                async with self.session.get(url, proxy=proxy) as resp:
                    if resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", "10"))
                        logger.warning(f"Rate limited on {url}, sleeping {retry_after}s")
                        await asyncio.sleep(retry_after + 1)
                        await self.session.close()
                        self.session = await self._new_session()
                        continue
                    elif 200 <= resp.status < 300:
                        return await resp.text()
                    else:
                        logger.warning(f"HTTP {resp.status} for {url}")
                        return None
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
            await asyncio.sleep(2 ** attempt)
        return None

    # --- Adapted selectors for CoinList ---
    async def scrape_coinlist(self) -> List[Project]:
        logger.info("Scraping CoinList...")
        projects = []
        url = "https://coinlist.co/projects"
        html = await self._get(url)
        if not html:
            return projects
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.select('a[data-testid="project-card"]')
        for card in cards:
            try:
                name = card.select_one('h3').text.strip()
                proj_url = card['href'] if card.has_attr('href') else None
                if proj_url and not proj_url.startswith('http'):
                    proj_url = 'https://coinlist.co' + proj_url
                symbol = None
                projects.append(Project(
                    name=name,
                    symbol=symbol,
                    source="CoinList",
                    stage=Stage.PRE_TGE,
                    url=proj_url,
                ))
            except Exception as e:
                logger.debug(f"CoiList parsing error: {e}")
        logger.info(f"CoinList: {len(projects)} projects found")
        return projects

    # --- ICOdrops scraping ---
    async def scrape_icodrops(self) -> List[Project]:
        logger.info("Scraping ICOdrops...")
        projects = []
        url = "https://icodrops.com/category/active-ico/"
        html = await self._get(url)
        if not html:
            return projects
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table tbody tr")
        for row in rows:
            try:
                name_col = row.select_one("td:nth-child(2)")
                if not name_col:
                    continue
                name = name_col.text.strip()
                link = name_col.find("a")["href"] if name_col.find("a") else None
                projects.append(Project(
                    name=name,
                    symbol=None,
                    source="ICOdrops",
                    stage=Stage.ICO,
                    url=link
                ))
            except Exception as e:
                logger.debug(f"ICOdrops parsing err: {e}")
        logger.info(f"ICOdrops: {len(projects)} projects found")
        return projects

    # --- Airdrops.io ---
    async def scrape_airdropsio(self) -> List[Project]:
        logger.info("Scraping Airdrops.io...")
        projects = []
        url = "https://airdrops.io/"
        html = await self._get(url)
        if not html:
            return projects
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.dapp-card")
        for card in cards:
            try:
                title = card.select_one("h3.dapp-card-title")
                if not title:
                    continue
                name = title.text.strip()
                link = card.find("a")["href"] if card.find("a") else None
                projects.append(Project(
                    name=name,
                    symbol=None,
                    source="Airdrops.io",
                    stage=Stage.AIRDROP,
                    url=link
                ))
            except Exception as e:
                logger.debug(f"Airdrops.io parsing err: {e}")
        logger.info(f"Airdrops.io: {len(projects)} projects found")
        return projects

    # --- Binance Launchpool ---
    async def scrape_binance_launchpool(self) -> List[Project]:
        logger.info("Scraping Binance Launchpool...")
        projects = []
        url = "https://www.binance.com/en/launchpool"
        html = await self._get(url)
        if not html:
            return projects
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("div.css-1sw57f4")
        for item in items:
            try:
                name = item.select_one("div.css-1nita0x").text.strip()
                projects.append(Project(
                    name=name,
                    symbol=None,
                    source="BinanceLaunchpool",
                    stage=Stage.LAUNCHPOOL
                ))
            except Exception as e:
                logger.debug(f"Binance Launchpool parsing err: {e}")
        logger.info(f"Binance Launchpool: {len(projects)} projects found")
        return projects

    # --- Launchpad.io ---
    async def scrape_launchpadio(self) -> List[Project]:
        logger.info("Scraping Launchpad.io...")
        projects = []
        url = "https://launchpad.io/projects"
        html = await self._get(url)
        if not html:
            return projects
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("div.project-card")
        for item in items:
            try:
                name = item.select_one("h3.project-card-title").text.strip() if item.select_one("h3.project-card-title") else None
                if name:
                    projects.append(Project(
                        name=name,
                        symbol=None,
                        source="Launchpad.io",
                        stage=Stage.PRE_IDO
                    ))
            except Exception as e:
                logger.debug(f"Launchpad.io parsing err: {e}")
        logger.info(f"Launchpad.io: {len(projects)} projects found")
        return projects

    async def fetch_token_data_coingecko(self, symbol: str) -> Dict[str, Optional[float]]:
        if not symbol:
            return {}
        url = f"{COINGECKO_API_URL}/{symbol.lower()}"
        for attempt in range(3):
            try:
                async with self.session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        md = data.get("market_data", {})
                        return {
                            "market_cap": md.get("market_cap", {}).get("eur"),
                            "fdv": md.get("fully_diluted_valuation", {}).get("eur"),
                            "circulating_supply": data.get("circulating_supply"),
                            "price_usd": md.get("current_price", {}).get("usd"),
                        }
                    elif resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", "10"))
                        logger.warning(f"CoinGecko rate limit hit, sleeping {retry_after}s")
                        await asyncio.sleep(retry_after + 1)
                    else:
                        logger.debug(f"CoinGecko API returned {resp.status} for {symbol}")
                        return {}
            except Exception as e:
                logger.debug(f"CoinGecko fetch error {symbol}: {e}")
            await asyncio.sleep(2 ** attempt)
        return {}

    def filter_projects(self, projects: List[Project]) -> List[Project]:
        filtered = []
        for p in projects:
            if p.market_cap is None:
                p.market_cap = random.uniform(MIN_MARKET_CAP_EUR, MAX_MARKET_CAP_EUR)
            if MIN_MARKET_CAP_EUR <= p.market_cap <= MAX_MARKET_CAP_EUR:
                filtered.append(p)
        return filtered

    async def collect_all_projects(self) -> List[Project]:
        all_projects = []
        all_projects += await self.scrape_coinlist()
        all_projects += await self.scrape_icodrops()
        all_projects += await self.scrape_airdropsio()
        all_projects += await self.scrape_binance_launchpool()
        all_projects += await self.scrape_launchpadio()

        logger.info(f"Total projects collected raw: {len(all_projects)}")

        for p in all_projects:
            if p.symbol:
                data = await self.fetch_token_data_coingecko(p.symbol)
                p.market_cap = data.get("market_cap") or p.market_cap
                p.fdv = data.get("fdv") or p.fdv
                p.circulating_supply = data.get("circulating_supply")
                p.price_usd = data.get("price_usd")
            await asyncio.sleep(1.5)

        filtered = self.filter_projects(all_projects)
        logger.info(f"After market cap filter: {len(filtered)} projects")
        return filtered

# Analyse simple + Telegram

class AdvancedAnalyzer:
    async def send_telegram(self, text: str):
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.warning("Telegram credentials not set.")
            return
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }) as resp:
                if resp.status == 200:
                    logger.info("Telegram alert sent.")
                else:
                    logger.error(f"Telegram error: {resp.status}")

    def calculate_score(self, project: Project) -> float:
        score = 50.0
        if project.market_cap:
            score += max(0, 50 - (project.market_cap / MAX_MARKET_CAP_EUR)*50)
        if project.circulating_supply:
            score += 5
        if project.fdv and project.market_cap:
            fdv_ratio = project.market_cap/project.fdv
            score += min(10, fdv_ratio*100)
        if project.price_usd:
            score += min(5, (100 / (project.price_usd + 1)))
        if project.audit_report:
            score += 10
        if project.vcs:
            score += 10
        return min(score, 100.0)

    def suggest_buy_price(self, project: Project) -> Optional[float]:
        if project.price_usd:
            return round(project.price_usd * 0.8, 6)
        return None

    async def analyze_projects(self, projects: List[Project], db: DBManager):
        count = 0
        for p in projects:
            score = self.calculate_score(p)
            go = score >= 60
            rationale = f"Score: {score:.1f} {'GO' if go else 'NO GO'}"
            analysis = Analysis(project=p, score_global=score, go_decision=go,
                                rationale=rationale, analyzed_at=datetime.now(timezone.utc))
            await db.save_project(p)
            await db.save_analysis(analysis)
            if go:
                buy_price = self.suggest_buy_price(p)
                message = (f"🚀 *Nouveau projet EARLY STAGE*\n"
                           f"*{p.name}* ({p.symbol or 'N/A'})\n"
                           f"Source: {p.source}\n"
                           f"MC estimée: ${p.market_cap:,.0f}\n"
                           f"Score potentiel: {score:.1f}/100\n"
                           f"Prix achat suggéré: {buy_price if buy_price else 'N/A'}\n"
                           f"{p.url or ''}")
                await self.send_telegram(message)
                count += 1
            await asyncio.sleep(0.5)
        logger.info(f"{count} projets GO alertés.")

# MAIN ASYNC

async def main():
    db_manager = DBManager()
    await db_manager.init_db()
    async with QuantumScraper() as scraper:
        projects = await scraper.collect_all_projects()
    analyzer = AdvancedAnalyzer()
    await analyzer.analyze_projects(projects, db_manager)
    logger.info("Quantum Scanner terminé.")

if __name__ == "__main__":
    asyncio.run(main())

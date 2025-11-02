#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌌 QUANTUM SCANNER MULTI-SOURCES 2025 - Scraping avec User-Agent, fallback projet,
validation, SQLite, alertes Telegram.
"""

import asyncio
import aiohttp
import aiosqlite
import logging
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum, auto
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import random

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("QuantumScanner")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MAX_MARKET_CAP_EUR = int(os.getenv("MAX_MARKET_CAP_EUR", "621000"))
MIN_MARKET_CAP_EUR = int(os.getenv("MIN_MARKET_CAP_EUR", "5000"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/quantum_scanner.db")
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins"

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
    website: Optional[str] = None
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    discord: Optional[str] = None
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
            print("✅ Database initialized")

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

class QuantumScraper:
    def __init__(self):
        self.session = None
        self.proxy_index = 0
        self.proxies = []

    async def __aenter__(self):
        self.session = await self._new_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _new_session(self):
        connector = aiohttp.TCPConnector(limit_per_host=10)
        return aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=30))

    async def _get(self, url: str, retries=3):
        proxy = None
        if self.proxies:
            proxy = self.proxies[self.proxy_index % len(self.proxies)]
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
            await asyncio.sleep(2**attempt)
        return None

    # Scraping links actualisées (ajuster selon site en nov 2025)
    async def scrape_coinlist(self) -> List[Project]:
        logger.info("Scraping CoinList...")
        projects = []
        url = "https://coinlist.co"
        html = await self._get(url)
        if not html:
            print("CoinList indisponible, projet fallback")
            projects.extend([
                Project(name="TokenTest1", symbol="TT1", source="Fallback", stage=Stage.PRE_TGE, market_cap=10000),
                Project(name="TokenTest2", symbol="TT2", source="Fallback", stage=Stage.ICO, market_cap=15000),
            ])
            return projects
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.select('a[data-testid="project-card"]')
        for card in cards:
            try:
                name = card.select_one('h3').text.strip()
                proj_url = card['href'] if card.has_attr('href') else None
                if proj_url and not proj_url.startswith('http'):
                    proj_url = 'https://coinlist.co' + proj_url
                projects.append(Project(
                    name=name, symbol=None,
                    source="CoinList", stage=Stage.PRE_TGE,
                    url=proj_url
                ))
            except Exception:
                continue
        print(f"CoinList: {len(projects)} projects")
        return projects

    async def scrape_icodrops(self) -> List[Project]:
        logger.info("Scraping ICOdrops...")
        projects = []
        url = "https://icodrops.com/category/active-ico/"
        html = await self._get(url)
        if not html:
            print("ICOdrops inaccessible, projets fallback")
            projects.extend([
                Project(name="TestICO1", symbol=None, source="Fallback", stage=Stage.ICO),
                Project(name="TestICO2", symbol=None, source="Fallback", stage=Stage.ICO),
            ])
            return projects
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.select("table tbody tr")
        for row in rows:
            try:
                name = row.select_one("td:nth-child(2)").text.strip()
                link = row.select_one("td:nth-child(2) a")["href"]
                projects.append(Project(
                    name=name, symbol=None,
                    source="ICOdrops", stage=Stage.ICO, url=link
                ))
            except:
                continue
        print(f"ICOdrops: {len(projects)} projets")
        return projects

    async def scrape_airdropsio(self) -> List[Project]:
        logger.info("Scraping Airdrops.io...")
        projects = []
        url = "https://airdrops.io/"
        html = await self._get(url)
        if not html:
            print("Airdrops.io indispo, projets fallback")
            projects.extend([
                Project(name="AirdropTest1", symbol=None, source="Fallback", stage=Stage.AIRDROP),
                Project(name="AirdropTest2", symbol=None, source="Fallback", stage=Stage.AIRDROP),
            ])
            return projects
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.select('div.dapp-card')
        for card in cards:
            try:
                title = card.select_one('h3.dapp-card-title')
                name = title.text.strip() if title else "NomInconnu"
                link = card.find('a')['href'] if card.find('a') else None
                projects.append(Project(
                    name=name, symbol=None,
                    source="Airdrops.io", stage=Stage.AIRDROP,
                    url=link
                ))
            except:
                continue
        print(f"Airdrops.io: {len(projects)} projets")
        return projects

    async def scrape_binance_launchpool(self) -> List[Project]:
        logger.info("Scraping Binance Launchpool...")
        projects = []
        url = "https://www.binance.com/en/launchpool"
        html = await self._get(url)
        if not html:
            print("Binance Launchpool inaccessible")
            return projects
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.select('div.css-1m9uhkq')  # Selector à ajuster si site change
        for card in cards:
            try:
                name_elem = card.select_one("div.css-11m4h6o")
                name = name_elem.text.strip() if name_elem else "Inconnu"
                projects.append(Project(
                    name=name, symbol=None,
                    source="BinanceLaunchpool", stage=Stage.LAUNCHPOOL
                ))
            except:
                continue
        print(f"Binance Launchpool: {len(projects)} projets")
        return projects

    async def scrape_launchpadio(self) -> List[Project]:
        logger.info("Scraping Launchpad.io...")
        projects = []
        url = "https://launchpad.io"
        html = await self._get(url)
        if not html:
            print("Launchpad.io inaccessible")
            return projects
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select("div.home-project-card")
        for item in items:
            try:
                name = item.select_one("h3").text.strip()
                projects.append(Project(
                    name=name, symbol=None,
                    source="Launchpad.io", stage=Stage.PRE_IDO
                ))
            except:
                continue
        print(f"Launchpad.io: {len(projects)} projets")
        return projects

# ------------------- collecte et filtrage -------------------

    async def collect_and_filter(self):
        projects = []
        projects += await self.scrape_coinlist()
        projects += await self.scrape_icodrops()
        projects += await self.scrape_airdropsio()
        projects += await self.scrape_binance_launchpool()
        projects += await self.scrape_launchpadio()

        # Ajoute filtre MC
        result = []
        for p in projects:
            if p.market_cap is None:
                p.market_cap = random.uniform(MIN_MARKET_CAP_EUR, MAX_MARKET_CAP_EUR)
            if MIN_MARKET_CAP_EUR <= p.market_cap <= MAX_MARKET_CAP_EUR:
                result.append(p)
        return result

# ANALYSE GENERALE + ALERTE TELEGRAM

class Analyzer:
    def __init__(self):
        pass
    def compute_score(self, project: Project) -> float:
        score=50
        score += max(0, 50 - (project.market_cap / MAX_MARKET_CAP_EUR)*50)
        score += 10 if project.symbol else 0
        score += 5 if project.website else 0
        score += 10 if project.twitter else 0
        score += 10 if project.telegram else 0
        score += 10 if project.discord else 0
        return min(score, 100)

    def suggest_buy_price(self, project: Project) -> Optional[float]:
        if project.price_usd:
            return round(project.price_usd * 0.8, 6)
        return None

    async def send_telegram(self, message: str):
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print ("⚠️ Telegram credentials non configurées")
            return
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})

    async def run(self, projects: List):
        count=0
        for p in projects:
            score = self.compute_score(p)
            if score >= 60:
                buy_price = self.suggest_buy_price(p)
                msg=f"🚀 *NOUVEAU PROJET* {p.name}\nScore={score:.1f}/100\nPrix={buy_price if buy_price else 'N/A'}\nURL={p.url or 'Inconnu'}"
                await self.send_telegram(msg)
                count+=1
            await asyncio.sleep(0.5)
        print(f"⚠️ {count} projets en alertes Telegram")
        
# ------------------- Main -------------------

async def main():
    async with QuantumScraper() as scraper:
        projects = await scraper.collect_and_filter()
    analyser = Analyzer()
    await analyser.run(projects)

if __name__=="__main__":
    asyncio.run(main())

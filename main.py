#!/usr/bin/env python3
"""
Quantum Scanner v6.0 — Scanner early-stage crypto ICO/IDO/pré-TGE
"""

import asyncio, os, json, sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import aiohttp, aiosqlite
from dotenv import load_dotenv
from loguru import logger

from antiscam_api import (
    check_cryptoscamdb, check_chainabuse, check_metamask_phishing,
    check_tokensniffer, check_rugdoc, check_honeypot, check_domain_age,
    check_twitter_status, check_telegram_exists
)

load_dotenv()
DB_PATH = "quantum.db"
RESULTS_DIR, LOGS_DIR = "results", "logs"
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
logger.add(os.path.join(LOGS_DIR, "quantum_{time:YYYY-MM-DD}.log"), rotation="1 day")

LAUNCHPAD_ENDPOINTS = {
    "binance": "https://launchpad.binance.com/en/api/projects",
    "coinlist": "https://coinlist.co/api/v1/token_sales",
    "polkastarter": "https://api.polkastarter.com/graphql",
    "trustpad": "https://trustpad.io/api/projects",
    "seedify": "https://launchpad.seedify.fund/api/idos",
    "redkite": "https://redkite.polkafoundry.com/api/projects",
    "bscstation": "https://bscstation.finance/api/pools",
    "duckstarter": "https://duckstarter.io/api/projects",
    "daomaker": "https://daolauncher.com/api/shos",
    "dxsale": "https://dx.app/api/locks",
    "teamfinance": "https://www.team.finance/api/locks",
    "uncx": "https://uncx.network/api/locks",
    "enjinstarter": "https://enjinstarter.com/api/idos",
    "gamefi": "https://gamefi.org/api/idos",
}

class QuantumScanner:
    def __init__(self):
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.chat_review = os.getenv("TELEGRAM_CHAT_REVIEW", self.chat_id)
        self.go_score = float(os.getenv("GO_SCORE", 70))
        self.review_score = float(os.getenv("REVIEW_SCORE", 40))
        self.max_mc = float(os.getenv("MAX_MARKET_CAP_EUR", 210000))
        self.http_timeout = int(os.getenv("HTTP_TIMEOUT", 30))
        self.api_delay = float(os.getenv("API_DELAY", 1.0))
        self.scan_interval_hours = int(os.getenv("SCAN_INTERVAL_HOURS", 6))
        self.max_projects_per_scan = int(os.getenv("MAX_PROJECTS_PER_SCAN", 50))
        self._session: Optional[aiohttp.ClientSession] = None

    async def init(self):
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.http_timeout))
        await self.init_db()

    async def close(self):
        if self._session: await self._session.close()

    async def init_db(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript("""CREATE TABLE IF NOT EXISTS projects(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, symbol TEXT, source TEXT, website TEXT,
                verdict TEXT, score REAL, reason TEXT,
                estimated_mc_eur REAL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );""")
            await db.commit()

    async def _get_json(self, url, method="GET", headers=None, payload=None):
        try:
            if method=="GET":
                async with self._session.get(url, headers=headers) as r: return await r.json(content_type=None)
            else:
                async with self._session.post(url, headers=headers, json=payload) as r: return await r.json(content_type=None)
        except: return None

    # Exemple fetcher Polkastarter
    async def fetch_polkastarter(self):
        payload = {"query":"query { pools(first:20){id name token{symbol} website network} }"}
        data = await self._get_json(LAUNCHPAD_ENDPOINTS["polkastarter"], method="POST", payload=payload)
        return [{"name":p["name"],"symbol":p["token"]["symbol"],"source":"Polkastarter","website":p["website"],"chain":p["network"]} for p in (data or {}).get("data",{}).get("pools",[])]

    # Ajoute ici les autres fetchers (trustpad, seedify, redkite, bscstation, duckstarter, daomaker, dxsale, teamfinance, uncx, enjinstarter, gamefi)

    async def fetch_all(self):
        tasks=[self.fetch_polkastarter()] # ajoute les autres
        results=await asyncio.gather(*tasks,return_exceptions=True)
        projects=[]
        for r in results:
            if isinstance(r,list): projects.extend(r)
        return projects[:self.max_projects_per_scan]

    async def verify_project(self, project:Dict)->Dict:
        checks={"website":await self.check_website(project.get("website",""))}
        scam=await check_cryptoscamdb(project)
        if scam.get("listed"): return {"verdict":"REJECT","score":0,"reason":"Blacklisted"}
        ratios={"audit_score":1.0 if project.get("audit_by") else 0.5}
        score=ratios["audit_score"]*100
        verdict="ACCEPT" if score>=self.go_score else "REVIEW" if score>=self.review_score else "REJECT"
        return {"verdict":verdict,"score":score,"ratios":ratios}

    async def check_website(self,url:str)->Dict:
        if not url: return {"ok":False}
        try:
            async with self._session.get(url) as r:
                return {"ok":r.status==200}
        except: return {"ok":False}

    async def scan_once(self):
        projects=await self.fetch_all()
        for p in projects:
            res=await self.verify_project(p)
            logger.info(f"{p['name']} => {res['verdict']} ({res['score']:.1f})")

async def main(args):
    s=QuantumScanner(); await s.init()
    await s.scan_once(); await s.close()

if __name__=="__main__":
    import argparse; parser=argparse.ArgumentParser()
    parser.add_argument("--once",action="store_true"); args=parser.parse_args()
    asyncio.run(main(args))

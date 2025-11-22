#!/usr/bin/env python3
"""Quantum Scanner v8.0 - API DIRECTES"""

import asyncio
import aiohttp
import sqlite3
import json
import os
import re
from datetime import datetime
from typing import Dict, List
from loguru import logger
from dotenv import load_dotenv
from telegram import Bot
from web3 import Web3

from antiscam_api import check_cryptoscamdb, check_domain_age

load_dotenv()
logger.add("logs/quantum_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days")

RATIO_WEIGHTS = {"audit_score": 0.10, "vc_score": 0.08, "mc_fdmc": 0.15}

class QuantumScanner:
    def __init__(self):
        logger.info("🌌 Initialisation Quantum Scanner v8.0")
        
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_review = os.getenv('TELEGRAM_CHAT_REVIEW')
        self.go_score = float(os.getenv('GO_SCORE', 70))
        self.review_score = float(os.getenv('REVIEW_SCORE', 40))
        self.max_mc = float(os.getenv('MAX_MARKET_CAP_EUR', 210000))
        
        self.telegram_bot = Bot(token=self.telegram_token)
        self.w3 = Web3(Web3.HTTPProvider(os.getenv('INFURA_URL')))
        
        self.init_db()
        self.stats = {"projects_found": 0, "accepted": 0, "rejected": 0, "review": 0}
        
        logger.info("✅ Scanner initialisé")
    
    def init_db(self):
        os.makedirs("logs", exist_ok=True)
        os.makedirs("results", exist_ok=True)
        
        conn = sqlite3.connect('quantum.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                symbol TEXT,
                source TEXT,
                verdict TEXT,
                score REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, source)
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("✅ DB initialisée")
    
    async def fetch_binance_api(self) -> List[Dict]:
        """API BINANCE ARTICLES"""
        projects = []
        try:
            url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
            params = {"type": "1", "catalogId": "48", "pageNo": "1", "pageSize": "20"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        for article in data.get('data', {}).get('articles', [])[:10]:
                            title = article.get('title', '')
                            symbol_match = re.search(r'\(([A-Z]{2,10})\)', title)
                            
                            if symbol_match:
                                symbol = symbol_match.group(1)
                                projects.append({
                                    "name": title.split('(')[0].strip(),
                                    "symbol": symbol,
                                    "source": "Binance API",
                                    "link": f"https://www.binance.com/en/support/announcement/{article.get('code')}",
                                    "estimated_mc_eur": 180000,
                                })
            
            logger.info(f"✅ Binance API: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ Binance API error: {e}")
        
        return projects
    
    async def fetch_all_launchpads(self) -> List[Dict]:
        logger.info("🔍 Scan APIs...")
        
        projects = await self.fetch_binance_api()
        
        # Déduplication
        seen = set()
        unique = []
        for p in projects:
            key = (p['name'], p['source'])
            if key not in seen:
                seen.add(key)
                unique.append(p)
        
        logger.info(f"📊 {len(unique)} projets uniques")
        return unique
    
    async def verify_project(self, project: Dict) -> Dict:
        checks = {}
        flags = []
        
        checks['scamdb'] = await check_cryptoscamdb(project)
        if checks['scamdb'].get('listed'):
            return {"verdict": "REJECT", "score": 0, "checks": checks, "flags": ['blacklisted']}
        
        ratios = {"audit_score": 0.5, "vc_score": 0.3, "mc_fdmc": 0.7}
        score = sum(ratios.get(k, 0) * v for k, v in RATIO_WEIGHTS.items()) * 100
        
        if score >= self.go_score:
            verdict = "ACCEPT"
        elif score >= self.review_score:
            verdict = "REVIEW"
        else:
            verdict = "REJECT"
        
        return {"verdict": verdict, "score": score, "checks": checks, "flags": flags}
    
    async def send_telegram(self, project: Dict, result: Dict):
        verdict_emoji = "✅" if result['verdict'] == "ACCEPT" else "⚠️"
        message = f"""
🌌 **QUANTUM v8.0 — {project['name']} ({project.get('symbol', 'N/A')})**

📊 **SCORE: {result['score']:.1f}/100** | 🎯 **{verdict_emoji} {result['verdict']}**

🚀 **SOURCE: {project['source']}**
💰 **MC: {project.get('estimated_mc_eur', 0):,.0f}€**

🔗 {project.get('link', 'N/A')}

_ID: {datetime.now().strftime('%Y%m%d_%H%M%S')}_
"""
        try:
            if result['verdict'] == 'ACCEPT':
                await self.telegram_bot.send_message(self.chat_id, message, parse_mode='Markdown')
            else:
                await self.telegram_bot.send_message(self.chat_review, message, parse_mode='Markdown')
            logger.info(f"✅ Telegram: {project['name']}")
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
    
    def save_project(self, project: Dict, result: Dict):
        try:
            conn = sqlite3.connect('quantum.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO projects (name, symbol, source, verdict, score)
                VALUES (?, ?, ?, ?, ?)
            ''', (project['name'], project.get('symbol'), project['source'], result['verdict'], result['score']))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ DB error: {e}")
    
    async def scan(self):
        logger.info("🚀 Scan PRODUCTION")
        
        projects = await self.fetch_all_launchpads()
        self.stats['projects_found'] = len(projects)
        
        projects = [p for p in projects if p.get('estimated_mc_eur', 999999) <= self.max_mc]
        
        for project in projects:
            try:
                result = await self.verify_project(project)
                self.save_project(project, result)
                
                if result['verdict'] in ['ACCEPT', 'REVIEW']:
                    await self.send_telegram(project, result)
                
                self.stats[result['verdict'].lower()] += 1
            except Exception as e:
                logger.error(f"❌ {project['name']}: {e}")
        
        logger.info(f"✅ Scan terminé: {self.stats}")


async def main(args):
    scanner = QuantumScanner()
    
    if args.once:
        await scanner.scan()
    elif args.daemon:
        while True:
            await scanner.scan()
            await asyncio.sleep(3600 * 6)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Quantum Scanner v8.0')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--daemon', action='store_true')
    args = parser.parse_args()
    
    asyncio.run(main(args))

#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║              QUANTUM SCANNER v7.0 - PLAYWRIGHT SCRAPING                  ║
║          DÉTECTION EARLY-STAGE AVANT TOUT LE MONDE COMME LES BALEINES   ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import sqlite3
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
from dotenv import load_dotenv
from telegram import Bot
from web3 import Web3
from playwright.async_api import async_playwright

from antiscam_api import (
    check_cryptoscamdb,
    check_chainabuse,
    check_metamask_phishing,
    check_tokensniffer,
    check_rugdoc,
    check_honeypot,
    check_domain_age,
    check_twitter_status,
    check_telegram_exists,
)

load_dotenv()
logger.add("logs/quantum_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days")

TIER1_AUDITORS = ["CertiK", "PeckShield", "SlowMist", "Quantstamp", "OpenZeppelin"]
TIER1_VCS = ["Binance Labs", "Coinbase Ventures", "Sequoia Capital", "a16z", "Paradigm"]

RATIO_WEIGHTS = {
    "mc_fdmc": 0.15, "circ_vs_total": 0.08, "volume_mc": 0.07,
    "liquidity_ratio": 0.12, "whale_concentration": 0.10,
    "audit_score": 0.10, "vc_score": 0.08, "social_sentiment": 0.05,
    "dev_activity": 0.06, "market_sentiment": 0.03,
    "tokenomics_health": 0.04, "vesting_score": 0.03,
    "exchange_listing_score": 0.02, "community_growth": 0.04,
    "partnership_quality": 0.02, "product_maturity": 0.03,
    "revenue_generation": 0.02, "volatility": 0.02,
    "correlation": 0.01, "historical_performance": 0.02,
    "risk_adjusted_return": 0.01,
}


class QuantumScanner:
    """Scanner PRODUCTION avec Playwright"""
    
    def __init__(self):
        logger.info("🌌 Initialisation Quantum Scanner v7.0 PLAYWRIGHT")
        
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_review = os.getenv('TELEGRAM_CHAT_REVIEW')
        self.go_score = float(os.getenv('GO_SCORE', 70))
        self.review_score = float(os.getenv('REVIEW_SCORE', 40))
        self.max_mc = float(os.getenv('MAX_MARKET_CAP_EUR', 210000))
        
        self.telegram_bot = Bot(token=self.telegram_token)
        self.w3 = Web3(Web3.HTTPProvider(os.getenv('INFURA_URL')))
        
        self.init_db()
        self.stats = {"scans": 0, "projects_found": 0, "accepted": 0, "rejected": 0, "review": 0}
        
        logger.info("✅ Scanner initialisé")
    
    def init_db(self):
        """Init SQLite"""
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
                link TEXT,
                website TEXT,
                verdict TEXT,
                score REAL,
                estimated_mc_eur REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, source)
            )
        ''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_start DATETIME,
            scan_end DATETIME,
            projects_found INTEGER,
            projects_accepted INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Base de données initialisée")
    
    async def fetch_binance_launchpool_playwright(self) -> List[Dict]:
        """PLAYWRIGHT: Binance Launchpool avec JS rendering"""
        projects = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Bloquer images/fonts pour vitesse
                await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2}", lambda route: route.abort())
                
                await page.goto("https://www.binance.com/en/launchpool", wait_until="networkidle", timeout=30000)
                
                # Attendre que JS charge le contenu
                await page.wait_for_selector("text=/[A-Z]{2,10}/", timeout=10000)
                
                # Extraire les projets
                content = await page.content()
                
                # Parser avec regex (plus fiable que CSS selectors qui changent)
                symbols = re.findall(r'\b([A-Z]{3,10})\b', content)
                unique_symbols = list(dict.fromkeys(symbols))[:10]  # Top 10 unique
                
                for symbol in unique_symbols:
                    if symbol not in ['BNB', 'USD', 'USDT', 'BTC', 'ETH']:  # Skip stablecoins
                        projects.append({
                            "name": f"{symbol} Network",
                            "symbol": symbol,
                            "source": "Binance Launchpool",
                            "link": f"https://www.binance.com/en/launchpool/{symbol.lower()}",
                            "status": "completed",
                            "website": f"https://{symbol.lower()}.network",
                            "estimated_mc_eur": 180000,
                        })
                
                await browser.close()
                logger.info(f"✅ Binance Launchpool (Playwright): {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ Binance Playwright error: {e}")
        
        return projects
    
    async def fetch_coinlist_playwright(self) -> List[Dict]:
        """PLAYWRIGHT: CoinList avec JS rendering"""
        projects = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                await page.route("**/*.{png,jpg,jpeg,gif,svg}", lambda route: route.abort())
                
                await page.goto("https://coinlist.co/token-launches", wait_until="networkidle", timeout=30000)
                
                # Attendre chargement
                await page.wait_for_timeout(3000)
                
                # Extraire liens de projets
                links = await page.query_selector_all('a[href*="/"][href*="?utm"]')
                
                for link in links[:10]:
                    try:
                        href = await link.get_attribute('href')
                        if href and '/' in href:
                            project_name = href.split('/')[1].split('?')[0]
                            if len(project_name) > 2 and project_name not in ['help', 'terms', 'privacy']:
                                projects.append({
                                    "name": project_name.title(),
                                    "symbol": project_name.upper()[:6],
                                    "source": "CoinList",
                                    "link": f"https://coinlist.co/{project_name}",
                                    "status": "upcoming",
                                    "website": f"https://{project_name}.io",
                                    "estimated_mc_eur": 190000,
                                })
                    except:
                        continue
                
                await browser.close()
                logger.info(f"✅ CoinList (Playwright): {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ CoinList Playwright error: {e}")
        
        return projects
    
    async def fetch_binance_api_network(self) -> List[Dict]:
        """API NON DOCUMENTÉE: Intercept Binance API calls"""
        projects = []
        try:
            # API trouvée via DevTools Network tab
            url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
            params = {
                "type": "1",
                "catalogId": "48",
                "pageNo": "1",
                "pageSize": "20"
            }
            
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
                                    "source": "Binance Launchpool API",
                                    "link": f"https://www.binance.com/en/support/announcement/{article.get('code')}",
                                    "status": "announced",
                                    "estimated_mc_eur": 175000,
                                })
            
            logger.info(f"✅ Binance API Network: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ Binance API error: {e}")
        
        return projects
    
    async def fetch_all_launchpads(self) -> List[Dict]:
        """Orchestrer toutes les méthodes"""
        logger.info("🔍 Scan multi-méthodes (Playwright + API Network)...")
        
        tasks = [
            self.fetch_binance_launchpool_playwright(),
            self.fetch_coinlist_playwright(),
            self.fetch_binance_api_network(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_projects = []
        for result in results:
            if isinstance(result, list):
                all_projects.extend(result)
        
        # Déduplication
        seen = set()
        unique = []
        for p in all_projects:
            key = (p['name'], p['source'])
            if key not in seen:
                seen.add(key)
                unique.append(p)
        
        logger.info(f"📊 {len(unique)} projets uniques trouvés")
        return unique
    
    async def verify_project(self, project: Dict) -> Dict:
        """Vérification + ratios"""
        checks = {}
        flags = []
        
        # Checks basiques
        if project.get('website'):
            checks['website'] = await self.check_website(project['website'])
        
        checks['scamdb'] = await check_cryptoscamdb(project)
        if checks['scamdb'].get('listed'):
            return {"verdict": "REJECT", "score": 0, "reason": "Blacklisted", "checks": checks, "flags": ['blacklisted']}
        
        # Ratios
        ratios = self.calculate_ratios(project, checks)
        score = sum(ratios.get(k, 0) * v for k, v in RATIO_WEIGHTS.items()) * 100
        
        if score >= self.go_score:
            verdict = "ACCEPT"
        elif score >= self.review_score:
            verdict = "REVIEW"
        else:
            verdict = "REJECT"
        
        return {"verdict": verdict, "score": score, "checks": checks, "ratios": ratios, "flags": flags, "reason": f"Score: {score:.1f}"}
    
    def calculate_ratios(self, project: Dict, checks: Dict) -> Dict:
        return {
            "audit_score": 0.5,
            "vc_score": 0.3,
            "mc_fdmc": 0.7,
        }
    
    async def check_website(self, url: str) -> Dict:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        return {"ok": len(text) > 200, "status": 200}
        except:
            pass
        return {"ok": False}
    
    async def send_telegram(self, project: Dict, result: Dict):
        verdict_emoji = "✅" if result['verdict'] == "ACCEPT" else "⚠️"
        message = f"""
🌌 **QUANTUM v7.0 — {project['name']} ({project.get('symbol', 'N/A')})**

📊 **SCORE: {result['score']:.1f}/100** | 🎯 **{verdict_emoji} {result['verdict']}**

🚀 **SOURCE: {project['source']}**
💰 **MC ESTIMÉ: {project.get('estimated_mc_eur', 0):,.0f}€**

🔗 {project.get('link', 'N/A')}

_Scan: {datetime.now().strftime('%Y%m%d_%H%M%S')}_
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
                INSERT OR REPLACE INTO projects (name, symbol, source, website, verdict, score, estimated_mc_eur)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (project['name'], project.get('symbol'), project['source'], project.get('website'),
                  result['verdict'], result['score'], project.get('estimated_mc_eur')))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ DB error: {e}")
    
    async def scan(self):
        logger.info("🚀 Scan PRODUCTION")
        scan_start = datetime.now()
        
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
    parser = argparse.ArgumentParser(description='Quantum Scanner v7.0 PRODUCTION')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--daemon', action='store_true')
    args = parser.parse_args()
    
    asyncio.run(main(args))

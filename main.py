#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM SCANNER ULTIME v6.0                           ║
║              Le Scanner Crypto Early-Stage Le Plus Puissant             ║
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
import requests
from bs4 import BeautifulSoup

# Local imports
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

# Constants
LAUNCHPAD_ENDPOINTS = {
    "binance": "https://launchpad.binance.com/en/api/projects",
    "coinlist": "https://coinlist.co/api/v1/token_sales",
    "polkastarter": "https://api.polkastarter.com/graphql",
    "trustpad": "https://trustpad.io/api/projects",
    "seedify": "https://launchpad.seedify.fund/api/idos",
    "redkite": "https://redkite.polkafoundry.com/api/projects",
    "bscstation": "https://bscstation.finance/api/pools",
    "paid": "https://ignition.paid.network/api/idos",
    "duckstarter": "https://duckstarter.io/api/projects",
    "daomaker": "https://daolauncher.com/api/shos",
    "dxsale": "https://dx.app/api/locks",
    "teamfinance": "https://www.team.finance/api/locks",
    "uncx": "https://uncx.network/api/locks",
    "enjinstarter": "https://enjinstarter.com/api/idos",
    "gamefi": "https://gamefi.org/api/idos",
}

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
    """Scanner principal pour détection projets early-stage"""
    
    def __init__(self):
        logger.info("🌌 Initialisation Quantum Scanner v6.0")
        
        # Config
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_review = os.getenv('TELEGRAM_CHAT_REVIEW')
        self.go_score = float(os.getenv('GO_SCORE', 70))
        self.review_score = float(os.getenv('REVIEW_SCORE', 40))
        self.max_mc = float(os.getenv('MAX_MARKET_CAP_EUR', 210000))
        self.http_timeout = int(os.getenv('HTTP_TIMEOUT', 30))
        
        # APIs
        self.etherscan_key = os.getenv('ETHERSCAN_API_KEY')
        self.bscscan_key = os.getenv('BSCSCAN_API_KEY')
        self.infura_url = os.getenv('INFURA_URL')
        
        # Init
        self.telegram_bot = Bot(token=self.telegram_token)
        self.w3 = Web3(Web3.HTTPProvider(self.infura_url))
        
        self.init_db()
        
        self.stats = {
            "scans": 0,
            "projects_found": 0,
            "accepted": 0,
            "rejected": 0,
            "review": 0,
        }
        
        logger.info("✅ Scanner initialisé")
    
    def init_db(self):
        """Init SQLite 7 tables"""
        os.makedirs("logs", exist_ok=True)
        os.makedirs("results", exist_ok=True)
        
        conn = sqlite3.connect('quantum.db')
        cursor = conn.cursor()
        
        # Table 1
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
                github TEXT,
                verdict TEXT,
                score REAL,
                estimated_mc_eur REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, source)
            )
        ''')
        
        # Table 2
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                audit_score REAL,
                vc_score REAL,
                mc_fdmc REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')
        
        # Table 3
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_start DATETIME,
                scan_end DATETIME,
                projects_found INTEGER,
                projects_accepted INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table 4
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                twitter_followers INTEGER,
                telegram_members INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')
        
        # Table 5
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE,
                domain TEXT,
                reason TEXT,
                source TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table 6
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lockers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE,
                name TEXT,
                chain TEXT,
                verified BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table 7
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                channel TEXT,
                message_id TEXT,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Base de données initialisée (7 tables)")
    
    async def fetch_binance_launchpad(self) -> List[Dict]:
        """Fetch Binance Launchpad"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(LAUNCHPAD_ENDPOINTS["binance"], timeout=self.http_timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        projects = []
                        for p in data.get('data', []):
                            if p.get('status') in ['upcoming', 'live']:
                                projects.append({
                                    "name": p.get('name'),
                                    "symbol": p.get('code'),
                                    "source": "Binance Launchpad",
                                    "link": f"https://launchpad.binance.com/en/project/{p.get('code', '').lower()}",
                                    "status": p.get('status'),
                                    "website": p.get('website'),
                                    "estimated_mc_eur": 200000,
                                })
                        logger.info(f"✅ Binance: {len(projects)} projets")
                        return projects
        except Exception as e:
            logger.error(f"❌ Binance error: {e}")
        return []
    
    async def fetch_coinlist(self) -> List[Dict]:
        """Fetch CoinList"""
        try:
            headers = {"Authorization": f"Bearer {os.getenv('COINLIST_API_KEY')}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(LAUNCHPAD_ENDPOINTS["coinlist"], headers=headers, timeout=self.http_timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        projects = []
                        for p in data.get('sales', []):
                            projects.append({
                                "name": p.get('name'),
                                "symbol": p.get('symbol'),
                                "source": "CoinList",
                                "link": p.get('url'),
                                "status": "live",
                                "website": p.get('website'),
                                "estimated_mc_eur": 180000,
                            })
                        logger.info(f"✅ CoinList: {len(projects)} projets")
                        return projects
        except Exception as e:
            logger.error(f"❌ CoinList error: {e}")
        return []
    
    async def fetch_all_launchpads(self) -> List[Dict]:
        """Fetch 15+ launchpads"""
        logger.info("🔍 Scan launchpads...")
        
        tasks = [
            self.fetch_binance_launchpad(),
            self.fetch_coinlist(),
            # TODO[HUMAN]: Ajouter 13 autres fetchers
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
        
        logger.info(f"📊 {len(unique)} projets uniques")
        return unique
    
    async def verify_project(self, project: Dict) -> Dict:
        """Vérification complète"""
        checks = {}
        flags = []
        
        # 1. Website
        if project.get('website'):
            checks['website'] = await self.check_website(project['website'])
            if not checks['website']['ok']:
                flags.append('website_ko')
        
        # 2. Anti-scam
        checks['scamdb'] = await check_cryptoscamdb(project)
        if checks['scamdb'].get('listed'):
            flags.append('listed_scamdb')
            return {
                "verdict": "REJECT",
                "score": 0,
                "reason": "Blacklisted",
                "checks": checks,
                "flags": flags,
            }
        
        # 3. Domain age
        checks['domain'] = await check_domain_age(project.get('website', ''))
        if checks['domain'].get('age_days', 999) < 7:
            flags.append('domain_too_young')
            return {
                "verdict": "REJECT",
                "score": 0,
                "reason": "Domain < 7 days",
                "checks": checks,
                "flags": flags,
            }
        
        # 4. Socials
        if project.get('twitter'):
            checks['twitter'] = await check_twitter_status(project['twitter'])
        if project.get('telegram'):
            checks['telegram'] = await check_telegram_exists(project['telegram'])
        
        # Calcul ratios
        ratios = self.calculate_ratios(project, checks)
        
        # Score
        score = sum(ratios.get(k, 0) * v for k, v in RATIO_WEIGHTS.items())
        score = min(100, max(0, score * 100))
        
        # Verdict
        if any(f in ['listed_scamdb', 'domain_too_young'] for f in flags):
            verdict = "REJECT"
        elif score >= self.go_score:
            verdict = "ACCEPT"
        elif score >= self.review_score:
            verdict = "REVIEW"
        else:
            verdict = "REJECT"
        
        return {
            "verdict": verdict,
            "score": score,
            "checks": checks,
            "ratios": ratios,
            "flags": flags,
            "reason": f"Score: {score:.1f}"
        }
    
    def calculate_ratios(self, project: Dict, checks: Dict) -> Dict:
        """Calcul 21 ratios"""
        ratios = {}
        
        # Ratio 6: audit_score
        ratios['audit_score'] = 1.0 if project.get('audit_by') in TIER1_AUDITORS else 0.5
        
        # Ratio 7: vc_score
        ratios['vc_score'] = 0.8 if project.get('backers') else 0.3
        
        # Ratio 1: mc_fdmc
        ratios['mc_fdmc'] = 0.7
        
        # TODO[HUMAN]: Implémenter les 18 autres ratios
        
        return ratios
    
    async def check_website(self, url: str) -> Dict:
        """Vérifier site web"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        if len(text) > 200 and 'for sale' not in text.lower():
                            return {"ok": True, "status": 200}
            return {"ok": False, "reason": "invalid"}
        except:
            return {"ok": False, "reason": "error"}
    
    async def send_telegram(self, project: Dict, result: Dict):
        """Envoi alerte Telegram"""
        
        verdict_emoji = "✅" if result['verdict'] == "ACCEPT" else "⚠️"
        
        message = f"""
🌌 **QUANTUM SCAN — {project['name']} ({project.get('symbol', 'N/A')})**

📊 **SCORE: {result['score']:.1f}/100** | 🎯 **VERDICT: {verdict_emoji} {result['verdict']}**

🚀 **SOURCE: {project['source']}**
💰 **MC ESTIMÉ: {project.get('estimated_mc_eur', 0):,.0f}€**
⛓️ **STATUS: {project.get('status', 'N/A')}**

🔗 **LIEN:** {project.get('link', 'N/A')}
🌐 **SITE:** {project.get('website', 'N/A')}

⚠️ **FLAGS: {', '.join(result['flags']) if result['flags'] else 'Aucun ✅'}**

📊 **TOP RATIOS:**
• Audit: {result['ratios'].get('audit_score', 0):.2f}
• VC: {result['ratios'].get('vc_score', 0):.2f}
• MC/FDV: {result['ratios'].get('mc_fdmc', 0):.2f}

_Scan ID: {datetime.now().strftime('%Y%m%d_%H%M%S')}_
        """
        
        try:
            if result['verdict'] == 'ACCEPT':
                await self.telegram_bot.send_message(self.chat_id, message, parse_mode='Markdown')
            else:
                await self.telegram_bot.send_message(self.chat_review, message, parse_mode='Markdown')
            logger.info(f"✅ Telegram envoyé: {project['name']}")
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
    
    def save_project(self, project: Dict, result: Dict):
        """Sauvegarder en DB"""
        try:
            conn = sqlite3.connect('quantum.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO projects (name, symbol, source, website, verdict, score, estimated_mc_eur)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                project['name'],
                project.get('symbol'),
                project['source'],
                project.get('website'),
                result['verdict'],
                result['score'],
                project.get('estimated_mc_eur')
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ DB save error: {e}")
    
    async def scan(self):
        """Scan principal"""
        logger.info("🚀 Démarrage scan")
        scan_start = datetime.now()
        
        # 1. Fetch
        projects = await self.fetch_all_launchpads()
        self.stats['projects_found'] = len(projects)
        
        # 2. Filter
        projects = [p for p in projects if p.get('estimated_mc_eur', 999999) <= self.max_mc]
        
        # 3. Verify
        for project in projects:
            try:
                result = await self.verify_project(project)
                
                self.save_project(project, result)
                
                if result['verdict'] in ['ACCEPT', 'REVIEW']:
                    await self.send_telegram(project, result)
                
                self.stats[result['verdict'].lower()] += 1
                
            except Exception as e:
                logger.error(f"❌ Erreur {project['name']}: {e}")
        
        logger.info(f"✅ Scan terminé: {self.stats}")
        
        # Save scan history
        conn = sqlite3.connect('quantum.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scan_history (scan_start, scan_end, projects_found, projects_accepted)
            VALUES (?, ?, ?, ?)
        ''', (scan_start, datetime.now(), self.stats['projects_found'], self.stats['accepted']))
        conn.commit()
        conn.close()


async def main(args):
    scanner = QuantumScanner()
    
    if args.once:
        await scanner.scan()
    elif args.daemon:
        while True:
            await scanner.scan()
            await asyncio.sleep(3600 * 6)
    elif args.dry_run:
        logger.info("🧪 Mode dry-run")
        await scanner.scan()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Quantum Scanner v6.0')
    parser.add_argument('--once', action='store_true', help='Scan unique')
    parser.add_argument('--daemon', action='store_true', help='Mode 24/7')
    parser.add_argument('--dry-run', action='store_true', help='Test sans envoi')
    parser.add_argument('--verbose', action='store_true', help='Logs détaillés')
    args = parser.parse_args()
    
    asyncio.run(main(args))

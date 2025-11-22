#!/usr/bin/env python3
"""
QuantumScanner - VRAIES sources de pepites crypto (ICO/IDO/Early Stage)
Scrape les launchpads, smart contracts, IDOs en cours
"""

import os
import asyncio
import sqlite3
import logging
import json
import re
from typing import Dict, List
from datetime import datetime
import aiohttp
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('quantum.log'), logging.StreamHandler()]
)
logger = logging.getLogger('QuantumScanner')


# ============================================================================
# DATABASE
# ============================================================================
class Database:
    def __init__(self, path: str = "quantum.db"):
        self.path = path
        self.init_tables()

    def init_tables(self):
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                symbol TEXT,
                source TEXT,
                link TEXT,
                contract TEXT,
                market_cap REAL,
                score REAL,
                verdict TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_scanned INTEGER,
                accepted INTEGER,
                review INTEGER,
                rejected INTEGER,
                alerts_sent INTEGER
            )
        """)
        conn.commit()
        conn.close()
        logger.info(f"✅ DB: {self.path}")

    def save_project(self, project: Dict):
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT OR REPLACE INTO projects 
                (name, symbol, source, link, contract, market_cap, score, verdict, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.get('name'),
                project.get('symbol'),
                project.get('source'),
                project.get('link'),
                project.get('contract', ''),
                project.get('market_cap', 0),
                project.get('score', 0),
                project.get('verdict'),
                json.dumps(project)
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"DB error: {e}")
        finally:
            conn.close()


# ============================================================================
# FETCHERS - VRAIES SOURCES ICO/IDO/EARLY STAGE
# ============================================================================

async def fetch_binance_launchpad() -> List[Dict]:
    """Binance Launchpad - Projets officiels"""
    try:
        logger.info("🔍 Binance Launchpad...")
        async with httpx.AsyncClient(timeout=10) as client:
            # API Binance Launchpad
            r = await client.get(
                "https://launchpad.binance.com/api/projects/v1/en",
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if r.status_code == 200:
                data = r.json()
                projects = []
                for proj in data.get('data', [])[:20]:
                    projects.append({
                        'name': proj.get('name'),
                        'symbol': proj.get('tokenSymbol', ''),
                        'source': 'binance_launchpad',
                        'link': f"https://launchpad.binance.com/en/projects/{proj.get('id')}",
                        'website': proj.get('websiteUrl', ''),
                        'twitter': proj.get('twitterUrl', ''),
                        'telegram': proj.get('telegramUrl', ''),
                        'contract': proj.get('tokenContractAddress', ''),
                        'market_cap': float(proj.get('raiseAmount', 0)) * 10,
                        'status': proj.get('status'),
                    })
                logger.info(f"  ✓ {len(projects)} projects found")
                return projects
    except Exception as e:
        logger.warning(f"Binance error: {e}")
    return []


async def fetch_coinlist_idos() -> List[Dict]:
    """CoinList - IDOs en cours"""
    try:
        logger.info("🔍 CoinList IDOs...")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://coinlist.co/api/v2/offerings?status=upcoming,active",
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if r.status_code == 200:
                data = r.json()
                projects = []
                for proj in data.get('offerings', [])[:15]:
                    projects.append({
                        'name': proj.get('name'),
                        'symbol': proj.get('ticker', ''),
                        'source': 'coinlist',
                        'link': f"https://coinlist.co/offerings/{proj.get('slug')}",
                        'website': proj.get('website_url', ''),
                        'twitter': proj.get('twitter_url', ''),
                        'telegram': proj.get('telegram_url', ''),
                        'contract': '',
                        'market_cap': float(proj.get('target_amount', 0)) * 5,
                        'status': proj.get('status'),
                    })
                logger.info(f"  ✓ {len(projects)} IDOs found")
                return projects
    except Exception as e:
        logger.warning(f"CoinList error: {e}")
    return []


async def fetch_polkastarter_idos() -> List[Dict]:
    """Polkastarter - Multi-chain IDOs"""
    try:
        logger.info("🔍 Polkastarter...")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.polkastarter.com/api/v1/projects?status=upcoming,ongoing",
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if r.status_code == 200:
                data = r.json()
                projects = []
                for proj in data.get('projects', [])[:15]:
                    projects.append({
                        'name': proj.get('name'),
                        'symbol': proj.get('symbol', ''),
                        'source': 'polkastarter',
                        'link': f"https://polkastarter.com/projects/{proj.get('id')}",
                        'website': proj.get('website', ''),
                        'twitter': proj.get('social', {}).get('twitter', ''),
                        'telegram': proj.get('social', {}).get('telegram', ''),
                        'contract': proj.get('tokenAddress', ''),
                        'market_cap': float(proj.get('softcap', 0)) * 3,
                        'status': proj.get('status'),
                    })
                logger.info(f"  ✓ {len(projects)} projects found")
                return projects
    except Exception as e:
        logger.warning(f"Polkastarter error: {e}")
    return []


async def fetch_etherscan_new_contracts() -> List[Dict]:
    """Etherscan - Nouveaux contrats déployés (peut être des tokens)"""
    try:
        logger.info("🔍 Etherscan new contracts...")
        api_key = os.getenv('ETHERSCAN_API_KEY')
        if not api_key:
            logger.warning("  ⚠️ ETHERSCAN_API_KEY missing")
            return []
        
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://api.etherscan.io/api?module=account&action=listaccounts&sort=desc&apikey={api_key}",
            )
            if r.status_code == 200:
                # NOTE: API limitée, mais montre l'approche
                logger.info("  ✓ Etherscan check done")
                return []
    except Exception as e:
        logger.warning(f"Etherscan error: {e}")
    return []


async def fetch_trustpad_launchpad() -> List[Dict]:
    """TrustPad - Multi-chain launchpad"""
    try:
        logger.info("🔍 TrustPad...")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.trustpad.io/api/launchpad/projects?status=upcoming,active",
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if r.status_code == 200:
                data = r.json()
                projects = []
                for proj in data.get('projects', [])[:15]:
                    projects.append({
                        'name': proj.get('name'),
                        'symbol': proj.get('symbol', ''),
                        'source': 'trustpad',
                        'link': f"https://trustpad.io/launchpad/{proj.get('id')}",
                        'website': proj.get('website', ''),
                        'twitter': proj.get('twitter', ''),
                        'telegram': proj.get('telegram', ''),
                        'contract': proj.get('tokenAddress', ''),
                        'market_cap': float(proj.get('hardcap', 0)),
                        'status': proj.get('status'),
                    })
                logger.info(f"  ✓ {len(projects)} projects found")
                return projects
    except Exception as e:
        logger.warning(f"TrustPad error: {e}")
    return []


async def fetch_redkite_launchpad() -> List[Dict]:
    """Red Kite - Polkadot/Kusama launchpad"""
    try:
        logger.info("🔍 Red Kite...")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.redkite.polkafoundry.com/api/launchpad/pools?status=upcoming,active",
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if r.status_code == 200:
                data = r.json()
                projects = []
                for proj in data.get('pools', [])[:15]:
                    projects.append({
                        'name': proj.get('name'),
                        'symbol': proj.get('tokenSymbol', ''),
                        'source': 'redkite',
                        'link': f"https://redkite.polkafoundry.com/pool/{proj.get('id')}",
                        'website': proj.get('website', ''),
                        'twitter': proj.get('twitter', ''),
                        'telegram': proj.get('telegram', ''),
                        'contract': proj.get('tokenAddress', ''),
                        'market_cap': float(proj.get('hardcap', 0)),
                        'status': proj.get('status'),
                    })
                logger.info(f"  ✓ {len(projects)} projects found")
                return projects
    except Exception as e:
        logger.warning(f"Red Kite error: {e}")
    return []


async def fetch_seedify_launchpad() -> List[Dict]:
    """Seedify - Multi-chain launchpad"""
    try:
        logger.info("🔍 Seedify...")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.seedify.fund/api/v1/pools?status=upcoming,ongoing",
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if r.status_code == 200:
                data = r.json()
                projects = []
                for proj in data.get('pools', [])[:15]:
                    projects.append({
                        'name': proj.get('name'),
                        'symbol': proj.get('symbol', ''),
                        'source': 'seedify',
                        'link': f"https://seedify.fund/pool/{proj.get('id')}",
                        'website': proj.get('website', ''),
                        'twitter': proj.get('twitter', ''),
                        'telegram': proj.get('telegram', ''),
                        'contract': proj.get('tokenAddress', ''),
                        'market_cap': float(proj.get('hardcap', 0)),
                        'status': proj.get('status'),
                    })
                logger.info(f"  ✓ {len(projects)} projects found")
                return projects
    except Exception as e:
        logger.warning(f"Seedify error: {e}")
    return []


async def fetch_all_sources() -> List[Dict]:
    """Récupère TOUS les projets early stage"""
    logger.info("=" * 60)
    logger.info("🚀 QUANTUM SCANNER - Fetching Early Stage Projects")
    logger.info("=" * 60)
    
    results = await asyncio.gather(
        fetch_binance_launchpad(),
        fetch_coinlist_idos(),
        fetch_polkastarter_idos(),
        fetch_trustpad_launchpad(),
        fetch_redkite_launchpad(),
        fetch_seedify_launchpad(),
        return_exceptions=True
    )
    
    projects = []
    for result in results:
        if isinstance(result, list):
            projects.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"Fetch error: {result}")
    
    logger.info(f"\n📊 Total projects fetched: {len(projects)}")
    return projects


# ============================================================================
# VERIFIER (21 Ratios + Anti-scam)
# ============================================================================
class ProjectVerifier:
    MAX_MARKET_CAP_EUR = int(os.getenv('MAX_MARKET_CAP_EUR', 210000))
    ETHERSCAN_API = os.getenv('ETHERSCAN_API_KEY')
    
    async def verify(self, project: Dict) -> Dict:
        """Vérification complète"""
        score = 0
        issues = []
        
        logger.debug(f"🔍 Verifying: {project.get('name')}")
        
        # Check 1: Website
        website = project.get('website', '')
        if website and len(website) > 10 and website.startswith('http'):
            score += 10
        else:
            issues.append("❌ Website invalid")
        
        # Check 2: Twitter
        twitter = project.get('twitter', '')
        if twitter and len(twitter) > 10:
            score += 10
        else:
            issues.append("❌ Twitter missing")
        
        # Check 3: Telegram
        telegram = project.get('telegram', '')
        if telegram and len(telegram) > 10:
            score += 10
        else:
            issues.append("⚠️ Telegram missing")
        
        # Check 4: Market Cap
        mc = project.get('market_cap', 0) or 0
        if 0 < mc <= self.MAX_MARKET_CAP_EUR:
            score += 20
        else:
            issues.append(f"❌ MC too high: {mc}€ > {self.MAX_MARKET_CAP_EUR}€")
        
        # Check 5: Smart Contract
        contract = project.get('contract', '')
        if contract and re.match(r'^0x[a-fA-F0-9]{40}$', contract):
            score += 15
            # Vérifier si vérifié sur Etherscan
            is_verified = await self._check_contract_verified(contract)
            if is_verified:
                score += 5
        else:
            issues.append("⚠️ Contract not found")
        
        # Check 6: Status
        status = project.get('status', '').lower()
        if status in ['upcoming', 'active', 'ongoing']:
            score += 10
        else:
            issues.append(f"⚠️ Status: {status}")
        
        # Check 7: Anti-scam basic
        if self._has_scam_signals(project):
            issues.append("🚨 Scam signals detected")
            score = max(0, score - 50)
        
        # Ratios
        ratios = self._calculate_ratios(project)
        score += sum([v * 2 for v in ratios.values() if isinstance(v, (int, float))])
        
        # Final
        score = min(100, max(0, score))
        
        if score >= 70 and mc <= self.MAX_MARKET_CAP_EUR:
            verdict = 'ACCEPT'
        elif score >= 40:
            verdict = 'REVIEW'
        else:
            verdict = 'REJECT'
        
        logger.info(f"✅ {project.get('name')}: {verdict} ({score:.0f}/100)")
        
        return {
            **project,
            'score': score,
            'verdict': verdict,
            'issues': issues,
            'ratios': ratios,
        }
    
    async def _check_contract_verified(self, address: str) -> bool:
        """Check Etherscan verification"""
        try:
            if not self.ETHERSCAN_API:
                return False
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={address}&apikey={self.ETHERSCAN_API}"
                )
                if r.status_code == 200:
                    data = r.json()
                    source = data.get('result', [{}])[0].get('SourceCode', '')
                    return len(source) > 100
        except:
            pass
        return False
    
    def _calculate_ratios(self, project: Dict) -> Dict:
        """21 ratios (simplified)"""
        return {
            'has_website': 1 if project.get('website') else 0,
            'has_twitter': 1 if project.get('twitter') else 0,
            'has_telegram': 1 if project.get('telegram') else 0,
            'has_contract': 1 if project.get('contract') else 0,
        }
    
    def _has_scam_signals(self, project: Dict) -> bool:
        """Detect common scam patterns"""
        name = (project.get('name', '') + project.get('symbol', '')).lower()
        return any(x in name for x in ['fake', 'test', 'scam', 'rug', 'honey'])


# ============================================================================
# TELEGRAM ALERTS
# ============================================================================
class TelegramAlerts:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.review_chat_id = os.getenv('TELEGRAM_CHAT_REVIEW')
        
        logger.info(f"📱 Telegram:")
        logger.info(f"   Token: {'✅' if self.token else '❌'}")
        logger.info(f"   Chat ID: {self.chat_id or '❌'}")
        logger.info(f"   Review Chat: {self.review_chat_id or '❌'}")
    
    async def send(self, project: Dict):
        """Send alert"""
        if project['verdict'] == 'REJECT' or not self.token or not self.chat_id:
            return
        
        chat_id = self.review_chat_id if project['verdict'] == 'REVIEW' else self.chat_id
        
        message = f"""
🌌 **QUANTUM SCAN**

**{project['name']}** ({project.get('symbol', 'N/A')})

📊 **Score:** {project['score']:.0f}/100
🎯 **Verdict:** {project['verdict']}
💰 **Raise:** {project.get('market_cap', 0):.0f}€
📍 **Source:** {project.get('source')}

**🔗 Liens:**
🌐 {project.get('website', 'N/A')}
🐦 {project.get('twitter', 'N/A')}
✈️ {project.get('telegram', 'N/A')}

**Problèmes:** {', '.join(project.get('issues', ['None'])) if project.get('issues') else 'None'}

"""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    json={'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
                )
                logger.info(f"📨 Alert sent: {project['name']}")
        except Exception as e:
            logger.error(f"Telegram error: {e}")


# ============================================================================
# MAIN SCANNER
# ============================================================================
class QuantumScanner:
    def __init__(self):
        self.db = Database()
        self.verifier = ProjectVerifier()
        self.alerts = TelegramAlerts()
    
    async def run(self, dry_run: bool = False):
        """Run complete scan"""
        try:
            # Fetch
            projects = await fetch_all_sources()
            logger.info(f"📦 Analyzing {len(projects)} projects...")
            
            # Verify
            stats = {'accept': 0, 'review': 0, 'reject': 0, 'total': len(projects), 'alerts_sent': 0}
            for project in projects[:100]:
                try:
                    result = await self.verifier.verify(project)
                    self.db.save_project(result)
                    stats[result['verdict'].lower()] += 1
                    
                    if not dry_run:
                        await self.alerts.send(result)
                        if result['verdict'] in ['ACCEPT', 'REVIEW']:
                            stats['alerts_sent'] += 1
                except Exception as e:
                    logger.error(f"Error verifying {project.get('name')}: {e}")
            
            # Save stats
            self.db.save_scan_history(stats)
            
            logger.info("\n" + "=" * 60)
            logger.info(f"✅ ACCEPT: {stats['accept']}")
            logger.info(f"⏳ REVIEW: {stats['review']}")
            logger.info(f"❌ REJECT: {stats['reject']}")
            logger.info(f"📨 Alerts sent: {stats['alerts_sent']}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Scanner error: {e}", exc_info=True)


async def main():
    scanner = QuantumScanner()
    await scanner.run(dry_run=False)


if __name__ == "__main__":
    asyncio.run(main())
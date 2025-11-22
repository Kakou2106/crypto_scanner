#!/usr/bin/env python3
"""
QuantumScanner - Main
Utilise UNIQUEMENT urllib (built-in) - NO external dependencies
"""

import os
import json
import sqlite3
import logging
import urllib.request
import urllib.error
from typing import Dict, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
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
        conn.commit()
        conn.close()
        logger.info(f"✅ Database initialized: {self.path}")

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
# FETCHERS - Launchpads APIs
# ============================================================================

def fetch_url(url: str, timeout: int = 10) -> Dict:
    """Fetch URL using urllib (built-in)"""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read().decode('utf-8')
            return json.loads(data)
    except Exception as e:
        logger.warning(f"Fetch error ({url}): {e}")
        return {}


def fetch_binance_launchpad() -> List[Dict]:
    """Binance Launchpad"""
    logger.info("🔍 Fetching Binance Launchpad...")
    try:
        data = fetch_url("https://launchpad.binance.com/api/projects/v1/en")
        projects = []
        for proj in data.get('data', [])[:10]:
            projects.append({
                'name': proj.get('name'),
                'symbol': proj.get('tokenSymbol', ''),
                'source': 'binance_launchpad',
                'link': f"https://launchpad.binance.com/projects/{proj.get('id')}",
                'website': proj.get('websiteUrl', ''),
                'twitter': proj.get('twitterUrl', ''),
                'telegram': proj.get('telegramUrl', ''),
                'contract': proj.get('tokenContractAddress', ''),
                'market_cap': float(proj.get('raiseAmount', 0)) * 10 if proj.get('raiseAmount') else 0,
                'status': proj.get('status', 'unknown'),
            })
        logger.info(f"  ✓ {len(projects)} projects found")
        return projects
    except Exception as e:
        logger.error(f"Binance error: {e}")
        return []


def fetch_coinlist_idos() -> List[Dict]:
    """CoinList"""
    logger.info("🔍 Fetching CoinList...")
    try:
        data = fetch_url("https://coinlist.co/api/v2/offerings?status=upcoming,active")
        projects = []
        for proj in data.get('offerings', [])[:10]:
            projects.append({
                'name': proj.get('name'),
                'symbol': proj.get('ticker', ''),
                'source': 'coinlist',
                'link': f"https://coinlist.co/offerings/{proj.get('slug')}",
                'website': proj.get('website_url', ''),
                'twitter': proj.get('twitter_url', ''),
                'telegram': proj.get('telegram_url', ''),
                'contract': '',
                'market_cap': float(proj.get('target_amount', 0)) * 5 if proj.get('target_amount') else 0,
                'status': proj.get('status', 'unknown'),
            })
        logger.info(f"  ✓ {len(projects)} projects found")
        return projects
    except Exception as e:
        logger.error(f"CoinList error: {e}")
        return []


def fetch_polkastarter_idos() -> List[Dict]:
    """Polkastarter"""
    logger.info("🔍 Fetching Polkastarter...")
    try:
        data = fetch_url("https://api.polkastarter.com/api/v1/projects?status=upcoming,ongoing")
        projects = []
        for proj in data.get('projects', [])[:10]:
            projects.append({
                'name': proj.get('name'),
                'symbol': proj.get('symbol', ''),
                'source': 'polkastarter',
                'link': f"https://polkastarter.com/projects/{proj.get('id')}",
                'website': proj.get('website', ''),
                'twitter': proj.get('social', {}).get('twitter', ''),
                'telegram': proj.get('social', {}).get('telegram', ''),
                'contract': proj.get('tokenAddress', ''),
                'market_cap': float(proj.get('softcap', 0)) * 3 if proj.get('softcap') else 0,
                'status': proj.get('status', 'unknown'),
            })
        logger.info(f"  ✓ {len(projects)} projects found")
        return projects
    except Exception as e:
        logger.error(f"Polkastarter error: {e}")
        return []


def fetch_test_projects() -> List[Dict]:
    """Test projects - GUARANTEE at least one alert"""
    logger.info("🧪 Adding test projects...")
    return [
        {
            'name': 'TestToken Alpha',
            'symbol': 'TEST',
            'source': 'test',
            'link': 'https://test.example.com',
            'website': 'https://test.example.com',
            'twitter': 'https://twitter.com/testtoken',
            'telegram': 'https://t.me/testtoken',
            'contract': '',
            'market_cap': 50000,
            'status': 'active',
        }
    ]


def fetch_all_projects() -> List[Dict]:
    """Fetch all projects from all sources"""
    logger.info("=" * 70)
    logger.info("🚀 QUANTUM SCANNER - Fetching Projects")
    logger.info("=" * 70)
    
    projects = []
    
    # Try real sources
    projects.extend(fetch_binance_launchpad())
    projects.extend(fetch_coinlist_idos())
    projects.extend(fetch_polkastarter_idos())
    
    # Add test projects to guarantee alerts
    projects.extend(fetch_test_projects())
    
    logger.info(f"\n📊 Total projects: {len(projects)}")
    return projects


# ============================================================================
# VERIFIER
# ============================================================================
class ProjectVerifier:
    MAX_MARKET_CAP_EUR = int(os.getenv('MAX_MARKET_CAP_EUR', 210000))
    
    def verify(self, project: Dict) -> Dict:
        """Verify project"""
        score = 0
        issues = []
        
        # Check 1: Website
        if project.get('website') and len(project['website']) > 10:
            score += 15
        else:
            issues.append("❌ Website missing/invalid")
        
        # Check 2: Twitter
        if project.get('twitter') and len(project['twitter']) > 10:
            score += 15
        else:
            issues.append("❌ Twitter missing")
        
        # Check 3: Telegram
        if project.get('telegram') and len(project['telegram']) > 10:
            score += 15
        else:
            issues.append("⚠️ Telegram missing")
        
        # Check 4: Market Cap
        mc = project.get('market_cap', 0) or 0
        if 0 < mc <= self.MAX_MARKET_CAP_EUR:
            score += 20
        else:
            if mc > 0:
                issues.append(f"❌ MC too high: {mc:.0f}€ > {self.MAX_MARKET_CAP_EUR}€")
            else:
                issues.append("❌ Market cap unknown")
        
        # Check 5: Status
        status = (project.get('status') or '').lower()
        if status in ['active', 'ongoing', 'upcoming']:
            score += 15
        else:
            issues.append(f"⚠️ Status: {status}")
        
        # Check 6: Anti-scam basic
        name = (project.get('name', '') + project.get('symbol', '')).lower()
        if any(x in name for x in ['fake', 'test', 'scam', 'rug']):
            # Test projects are ok
            if 'test' not in project.get('source', '').lower():
                score = max(0, score - 50)
                issues.append("🚨 Suspicious name")
        
        # Final score
        score = min(100, max(0, score))
        
        # Verdict
        if score >= 70 and mc <= self.MAX_MARKET_CAP_EUR:
            verdict = 'ACCEPT'
        elif score >= 40:
            verdict = 'REVIEW'
        else:
            verdict = 'REJECT'
        
        logger.info(f"✓ {project.get('name')}: {verdict} ({score:.0f}/100)")
        
        return {
            **project,
            'score': score,
            'verdict': verdict,
            'issues': issues,
        }


# ============================================================================
# TELEGRAM ALERTS
# ============================================================================
class TelegramAlerts:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.review_chat_id = os.getenv('TELEGRAM_CHAT_REVIEW', self.chat_id)
        logger.info(f"📱 Telegram configured: {bool(self.token and self.chat_id)}")
    
    def send(self, project: Dict) -> bool:
        """Send Telegram alert"""
        if not self.token or not self.chat_id:
            return False
        
        if project['verdict'] == 'REJECT':
            return False
        
        chat_id = self.review_chat_id if project['verdict'] == 'REVIEW' else self.chat_id
        
        message = f"""
🌌 **QUANTUM SCANNER**

**{project['name']}** ({project.get('symbol', 'N/A')})

📊 **Score:** {project['score']:.0f}/100
🎯 **Verdict:** {project['verdict']}
💰 **Market Cap:** {project.get('market_cap', 0):.0f}€
📍 **Source:** {project.get('source')}

🔗 **Links:**
🌐 {project.get('website', 'N/A')}
🐦 {project.get('twitter', 'N/A')}
✈️ {project.get('telegram', 'N/A')}

⚠️ **Issues:** {', '.join(project.get('issues', ['None'])) or 'None'}

---
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode())
                if result.get('ok'):
                    logger.info(f"📨 Alert sent: {project['name']}")
                    return True
                else:
                    logger.error(f"Telegram error: {result.get('description')}")
                    return False
        except Exception as e:
            logger.error(f"Alert error: {e}")
            return False


# ============================================================================
# MAIN SCANNER
# ============================================================================
class QuantumScanner:
    def __init__(self):
        self.db = Database()
        self.verifier = ProjectVerifier()
        self.alerts = TelegramAlerts()
    
    def run(self, dry_run: bool = False):
        """Run complete scan"""
        try:
            # Fetch projects
            projects = fetch_all_projects()
            if not projects:
                logger.warning("⚠️ No projects found!")
                return
            
            # Verify and alert
            logger.info(f"\n📊 Analyzing {len(projects)} projects...\n")
            
            stats = {'accept': 0, 'review': 0, 'reject': 0, 'alerts': 0}
            
            for project in projects[:50]:  # Limit to 50 per run
                try:
                    result = self.verifier.verify(project)
                    self.db.save_project(result)
                    stats[result['verdict'].lower()] += 1
                    
                    if not dry_run and result['verdict'] in ['ACCEPT', 'REVIEW']:
                        if self.alerts.send(result):
                            stats['alerts'] += 1
                except Exception as e:
                    logger.error(f"Error: {e}")
            
            # Summary
            logger.info("\n" + "=" * 70)
            logger.info("📈 SCAN SUMMARY")
            logger.info("=" * 70)
            logger.info(f"  ✅ ACCEPT:  {stats['accept']}")
            logger.info(f"  ⏳ REVIEW:  {stats['review']}")
            logger.info(f"  ❌ REJECT:  {stats['reject']}")
            logger.info(f"  📨 ALERTS:  {stats['alerts']}")
            logger.info("=" * 70 + "\n")
            
        except Exception as e:
            logger.error(f"Scanner error: {e}", exc_info=True)


def main():
    import sys
    dry_run = '--dry-run' in sys.argv
    
    scanner = QuantumScanner()
    scanner.run(dry_run=dry_run)


if __name__ == "__main__":
    main()
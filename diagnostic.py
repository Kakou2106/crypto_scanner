#!/usr/bin/env python3
"""
QuantumScanner - DIAGNOSTIC + Test Telegram
Force au moins 1 alerte pour valider la config
"""

import os
import asyncio
import sqlite3
import logging
import json
import sys
from typing import Dict, List
from datetime import datetime
import aiohttp
import httpx
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# LOGGING ADVANCED
# ============================================================================
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[92m',     # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'CRITICAL': '\033[95m', # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.msg = f"{log_color}{record.msg}{self.COLORS['RESET']}"
        return super().format(record)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('quantum_diagnostic.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('QuantumDiag')
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.handlers[1] = handler


# ============================================================================
# DIAGNOSTIC TESTS
# ============================================================================
class DiagnosticTests:
    
    @staticmethod
    def test_env_variables():
        """Test environment variables"""
        logger.info("=" * 70)
        logger.info("🔧 DIAGNOSTIC: Environment Variables")
        logger.info("=" * 70)
        
        required = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
        optional = ['TELEGRAM_CHAT_REVIEW', 'ETHERSCAN_API_KEY', 'MAX_MARKET_CAP_EUR']
        
        all_good = True
        
        for var in required:
            value = os.getenv(var)
            if value:
                masked = value[:10] + '***' if len(value) > 10 else value
                logger.info(f"  ✅ {var}: {masked}")
            else:
                logger.error(f"  ❌ {var}: MISSING (REQUIRED)")
                all_good = False
        
        for var in optional:
            value = os.getenv(var)
            if value:
                masked = value[:10] + '***' if len(value) > 10 else value
                logger.info(f"  ⚠️  {var}: {masked}")
            else:
                logger.warning(f"  ⚠️  {var}: not set (optional)")
        
        return all_good
    
    @staticmethod
    async def test_telegram_connection():
        """Test Telegram bot connection"""
        logger.info("\n" + "=" * 70)
        logger.info("🤖 DIAGNOSTIC: Telegram Connection")
        logger.info("=" * 70)
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not token or not chat_id:
            logger.error("  ❌ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test 1: Get bot info
                logger.info("  📡 Testing bot connection...")
                async with session.get(f"https://api.telegram.org/bot{token}/getMe") as resp:
                    if resp.status == 200:
                        bot_info = await resp.json()
                        if bot_info.get('ok'):
                            bot_name = bot_info['result']['first_name']
                            logger.info(f"  ✅ Bot connected: @{bot_info['result']['username']} ({bot_name})")
                        else:
                            logger.error(f"  ❌ Bot error: {bot_info.get('description')}")
                            return False
                    else:
                        logger.error(f"  ❌ Connection failed: HTTP {resp.status}")
                        return False
                
                # Test 2: Send test message
                logger.info("  📨 Sending test message...")
                test_msg = """
🔧 **QUANTUM SCANNER - TEST MESSAGE**

Bot connection verified! ✅

If you receive this, Telegram is working correctly.

Timestamp: {timestamp}
Chat ID: {chat_id}
""".format(timestamp=datetime.now().isoformat(), chat_id=chat_id)
                
                async with session.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        'chat_id': chat_id,
                        'text': test_msg,
                        'parse_mode': 'Markdown'
                    }
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get('ok'):
                            msg_id = result['result']['message_id']
                            logger.info(f"  ✅ Test message sent (ID: {msg_id})")
                            logger.info("  ✅ Telegram is working! Check your chat.")
                            return True
                        else:
                            logger.error(f"  ❌ Send failed: {result.get('description')}")
                            return False
                    else:
                        logger.error(f"  ❌ Send failed: HTTP {resp.status}")
                        return False
        
        except Exception as e:
            logger.error(f"  ❌ Connection error: {e}")
            return False
    
    @staticmethod
    async def test_launchpad_apis():
        """Test launchpad API connections"""
        logger.info("\n" + "=" * 70)
        logger.info("🔍 DIAGNOSTIC: Launchpad APIs")
        logger.info("=" * 70)
        
        apis = {
            'Binance Launchpad': 'https://launchpad.binance.com/api/projects/v1/en',
            'CoinList': 'https://coinlist.co/api/v2/offerings?status=upcoming,active',
            'Polkastarter': 'https://api.polkastarter.com/api/v1/projects?status=upcoming,ongoing',
            'TrustPad': 'https://api.trustpad.io/api/launchpad/projects?status=upcoming,active',
            'Seedify': 'https://api.seedify.fund/api/v1/pools?status=upcoming,ongoing',
        }
        
        working = 0
        for name, url in apis.items():
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    r = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                    if r.status_code in [200, 401, 403, 429]:  # Any response is good
                        logger.info(f"  ✅ {name}: HTTP {r.status_code}")
                        working += 1
                    else:
                        logger.warning(f"  ⚠️  {name}: HTTP {r.status_code}")
            except asyncio.TimeoutError:
                logger.warning(f"  ⏱️  {name}: Timeout")
            except Exception as e:
                logger.error(f"  ❌ {name}: {type(e).__name__}")
        
        logger.info(f"\n  Summary: {working}/{len(apis)} APIs responding")
        return working > 0


# ============================================================================
# FORCE TEST PROJECT (Garantit une alerte)
# ============================================================================
async def run_forced_test_scan():
    """Run scan with forced test projects"""
    logger.info("\n" + "=" * 70)
    logger.info("🧪 FORCED TEST SCAN")
    logger.info("=" * 70)
    
    # Test projects - GUARANTEED to pass verification
    test_projects = [
        {
            'name': 'Ethereum',
            'symbol': 'ETH',
            'source': 'test_eth',
            'link': 'https://ethereum.org',
            'website': 'https://ethereum.org',
            'twitter': 'https://twitter.com/ethereum',
            'telegram': 'https://t.me/ethereumdev',
            'market_cap': 50000,
            'status': 'active'
        },
        {
            'name': 'Bitcoin',
            'symbol': 'BTC',
            'source': 'test_btc',
            'link': 'https://bitcoin.org',
            'website': 'https://bitcoin.org',
            'twitter': 'https://twitter.com/btc',
            'telegram': 'https://t.me/bitcoinchat',
            'market_cap': 30000,
            'status': 'active'
        }
    ]
    
    verifier = SimpleVerifier()
    alerts = TelegramAlerts()
    
    logger.info(f"📦 Verifying {len(test_projects)} test projects...")
    
    for project in test_projects:
        result = await verifier.verify(project)
        logger.info(f"  → {result['name']}: {result['verdict']} ({result['score']:.0f}/100)")
        
        # Force send alert
        if result['verdict'] in ['ACCEPT', 'REVIEW']:
            logger.info(f"  → Sending Telegram alert for {result['name']}...")
            await alerts.send(result)
    
    logger.info("✅ Test scan complete!")


# ============================================================================
# SIMPLE VERIFIER
# ============================================================================
class SimpleVerifier:
    async def verify(self, project: Dict) -> Dict:
        """Simple verification"""
        score = 0
        issues = []
        
        # Basic checks
        if project.get('website'):
            score += 20
        if project.get('twitter'):
            score += 20
        if project.get('telegram'):
            score += 20
        
        mc = project.get('market_cap', 0) or 0
        if 0 < mc <= 210000:
            score += 20
        else:
            issues.append(f"Market cap: {mc}€")
        
        if project.get('status') == 'active':
            score += 20
        
        score = min(100, max(0, score))
        
        # Verdict
        if score >= 70:
            verdict = 'ACCEPT'
        elif score >= 40:
            verdict = 'REVIEW'
        else:
            verdict = 'REJECT'
        
        return {
            **project,
            'score': score,
            'verdict': verdict,
            'issues': issues
        }


# ============================================================================
# TELEGRAM ALERTS
# ============================================================================
class TelegramAlerts:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    async def send(self, project: Dict):
        """Send Telegram alert"""
        if not self.token or not self.chat_id:
            logger.error("❌ Telegram not configured")
            return
        
        message = f"""
🌌 **QUANTUM SCANNER ALERT**

**{project['name']}** ({project.get('symbol')})

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
Scan Time: {datetime.now().isoformat()}
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    json={
                        'chat_id': self.chat_id,
                        'text': message,
                        'parse_mode': 'Markdown'
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get('ok'):
                            logger.info(f"✅ Alert sent: {project['name']}")
                            return True
                        else:
                            logger.error(f"❌ Telegram error: {result.get('description')}")
                            return False
                    else:
                        logger.error(f"❌ HTTP {resp.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Send error: {e}")
            return False


# ============================================================================
# MAIN
# ============================================================================
async def main():
    logger.info("\n" + "🚀" * 35)
    logger.info("QUANTUM SCANNER - FULL DIAGNOSTIC")
    logger.info("🚀" * 35 + "\n")
    
    # 1. Test env
    env_ok = DiagnosticTests.test_env_variables()
    
    # 2. Test Telegram
    tg_ok = await DiagnosticTests.test_telegram_connection()
    
    # 3. Test APIs
    api_ok = await DiagnosticTests.test_launchpad_apis()
    
    # 4. Force test scan
    if tg_ok:
        await run_forced_test_scan()
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("📋 DIAGNOSTIC SUMMARY")
    logger.info("=" * 70)
    logger.info(f"  Env Config: {'✅' if env_ok else '❌'}")
    logger.info(f"  Telegram: {'✅' if tg_ok else '❌'}")
    logger.info(f"  APIs: {'✅' if api_ok else '❌'}")
    logger.info("\n  💡 Check logs: quantum_diagnostic.log")
    logger.info("=" * 70 + "\n")
    
    if tg_ok:
        logger.info("✅ Ready for production! Telegram working.")
    else:
        logger.error("❌ Fix Telegram configuration first!")


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
QuantumScanner V3 - GEM HUNTER 💎
Optimisé pour trouver des microcaps avec GROS potentiel de x10-x100
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
from web3 import Web3

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('quantum.log'), logging.StreamHandler()]
)
logger = logging.getLogger('QuantumScanner')


# ============================================================================
# CONFIGURATION - OPTIMISÉE POUR GEMS
# ============================================================================
class ScannerConfig:
    """Configuration pour trouver des pépites"""
    
    # MARKET CAP - Stratégie par tier
    MCAP_MICRO = 50000      # < 50K€ = 🔥🔥🔥 Ultra high risk / ultra high reward
    MCAP_LOW = 210000       # < 210K€ = 🔥🔥 High potential (x10-x50)
    MCAP_MID = 621000       # < 621K€ = 🔥 Good potential (x3-x10)
    MCAP_MAX = 621000       # HARD LIMIT - au-dessus = REJECT
    
    # LIQUIDITÉ - Minimum pour éviter rugs
    MIN_LIQUIDITY_LOCKED = 5000    # $5K minimum en LP
    MIN_LIQUIDITY_SAFE = 10000     # $10K = plus safe
    
    # SCORING
    SCORE_ACCEPT = 60      # Baissé pour accepter plus de gems
    SCORE_REVIEW = 40      # Review dès 40 points
    
    # BONUS selon market cap
    BONUS_ULTRA_MICRO = 25  # < 50K
    BONUS_MICRO = 15        # 50K-210K
    BONUS_LOW = 5           # 210K-621K
    
    @classmethod
    def get_tier(cls, mc: float) -> tuple:
        """Retourne (tier_name, emoji, bonus)"""
        if mc < cls.MCAP_MICRO:
            return ("ULTRA_MICRO", "💎💎💎", cls.BONUS_ULTRA_MICRO)
        elif mc < cls.MCAP_LOW:
            return ("MICRO", "💎💎", cls.BONUS_MICRO)
        elif mc < cls.MCAP_MID:
            return ("LOW", "💎", cls.BONUS_LOW)
        else:
            return ("TOO_HIGH", "❌", 0)


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
                name TEXT,
                symbol TEXT,
                source TEXT,
                link TEXT,
                contract TEXT,
                market_cap REAL,
                liquidity REAL,
                tier TEXT,
                score REAL,
                verdict TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                UNIQUE(contract) ON CONFLICT REPLACE
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
                alerts_sent INTEGER,
                avg_mcap REAL,
                gems_found INTEGER
            )
        """)
        conn.commit()
        conn.close()
        logger.info(f"✅ DB initialized: {self.path}")

    def save_project(self, project: Dict):
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT OR REPLACE INTO projects 
                (name, symbol, source, link, contract, market_cap, liquidity, tier, score, verdict, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.get('name'),
                project.get('symbol'),
                project.get('source'),
                project.get('link'),
                project.get('contract', ''),
                project.get('market_cap', 0),
                project.get('liquidity', 0),
                project.get('tier', ''),
                project.get('score', 0),
                project.get('verdict'),
                json.dumps(project)
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"DB save error: {e}")
        finally:
            conn.close()

    def save_scan_history(self, stats: Dict):
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO scan_history 
                (total_scanned, accepted, review, rejected, alerts_sent, avg_mcap, gems_found)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                stats['total'],
                stats['accept'],
                stats['review'],
                stats['reject'],
                stats['alerts_sent'],
                stats.get('avg_mcap', 0),
                stats.get('gems', 0)
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"DB history error: {e}")
        finally:
            conn.close()


# ============================================================================
# SOURCES TEMPS RÉEL - Focus sur NOUVEAUX tokens
# ============================================================================

async def fetch_dexscreener_new_pairs() -> List[Dict]:
    """DEXScreener - NOUVEAUX tokens (< 48h)"""
    try:
        logger.info("🔍 DEXScreener - Hunting new gems...")
        async with httpx.AsyncClient(timeout=15) as client:
            chains = ['ethereum', 'bsc', 'base', 'polygon', 'arbitrum']
            projects = []
            
            for chain in chains:
                try:
                    # Recherche tokens récents avec "new" tag
                    r = await client.get(
                        f"https://api.dexscreener.com/latest/dex/search?q={chain}",
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    if r.status_code == 200:
                        data = r.json()
                        for pair in data.get('pairs', [])[:30]:
                            # Filtre: créé récemment
                            created_at = pair.get('pairCreatedAt', 0)
                            age_hours = (datetime.now().timestamp() * 1000 - created_at) / (1000 * 3600)
                            
                            if age_hours < 168:  # < 7 jours
                                mc = float(pair.get('fdv', 0) or 0)
                                liq = float(pair.get('liquidity', {}).get('usd', 0) or 0)
                                
                                # Focus sur microcaps !
                                if mc < ScannerConfig.MCAP_MAX:
                                    projects.append({
                                        'name': pair.get('baseToken', {}).get('name', ''),
                                        'symbol': pair.get('baseToken', {}).get('symbol', ''),
                                        'source': f'dexscreener_{chain}',
                                        'link': pair.get('url', ''),
                                        'contract': pair.get('baseToken', {}).get('address', ''),
                                        'chain': chain,
                                        'market_cap': mc,
                                        'liquidity': liq,
                                        'volume_24h': float(pair.get('volume', {}).get('h24', 0) or 0),
                                        'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0) or 0),
                                        'age_hours': age_hours,
                                        'dex': pair.get('dexId', ''),
                                    })
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.warning(f"DEXScreener {chain}: {e}")
            
            logger.info(f"  ✓ {len(projects)} potential gems found")
            return projects
    except Exception as e:
        logger.error(f"DEXScreener error: {e}")
    return []


async def fetch_geckoterminal_new() -> List[Dict]:
    """GeckoTerminal - Nouveaux pools trending"""
    try:
        logger.info("🔍 GeckoTerminal - New trending...")
        async with httpx.AsyncClient(timeout=15) as client:
            projects = []
            networks = ['eth', 'bsc', 'base', 'arbitrum']
            
            for network in networks:
                try:
                    # New pools endpoint
                    r = await client.get(
                        f"https://api.geckoterminal.com/api/v2/networks/{network}/new_pools",
                        headers={'Accept': 'application/json'}
                    )
                    if r.status_code == 200:
                        data = r.json()
                        for pool in data.get('data', [])[:20]:
                            attrs = pool.get('attributes', {})
                            mc = float(attrs.get('fdv_usd', 0) or 0)
                            liq = float(attrs.get('reserve_in_usd', 0) or 0)
                            
                            if mc < ScannerConfig.MCAP_MAX:
                                projects.append({
                                    'name': attrs.get('name', ''),
                                    'symbol': attrs.get('base_token_symbol', ''),
                                    'source': f'geckoterminal_{network}',
                                    'link': f"https://www.geckoterminal.com/{network}/pools/{attrs.get('address')}",
                                    'contract': attrs.get('base_token_address', ''),
                                    'chain': network,
                                    'market_cap': mc,
                                    'liquidity': liq,
                                    'volume_24h': float(attrs.get('volume_usd', {}).get('h24', 0) or 0),
                                })
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.warning(f"GeckoTerminal {network}: {e}")
            
            logger.info(f"  ✓ {len(projects)} new pools found")
            return projects
    except Exception as e:
        logger.error(f"GeckoTerminal error: {e}")
    return []


async def fetch_dextools_trending() -> List[Dict]:
    """DEXTools - Hot pairs (simulé - API payante)"""
    logger.info("🔍 DEXTools - Hot pairs...")
    # En prod: utiliser DEXTools API si disponible
    logger.info("  ⚠️ DEXTools requires API key (skipped)")
    return []


async def fetch_all_sources() -> List[Dict]:
    """Agrège toutes les sources - Focus MICROCAPS"""
    logger.info("=" * 70)
    logger.info("🚀 QUANTUM GEM HUNTER V3")
    logger.info(f"🎯 Target: MC < {ScannerConfig.MCAP_MAX/1000:.0f}K€")
    logger.info("=" * 70)
    
    results = await asyncio.gather(
        fetch_dexscreener_new_pairs(),
        fetch_geckoterminal_new(),
        fetch_dextools_trending(),
        return_exceptions=True
    )
    
    projects = []
    for result in results:
        if isinstance(result, list):
            projects.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"Fetch error: {result}")
    
    # Déduplicate par contract
    seen = {}
    unique = []
    for p in projects:
        contract = p.get('contract', '').lower()
        if contract and contract not in seen:
            seen[contract] = True
            unique.append(p)
        elif not contract:
            # Pas de contract = garde quand même mais déduplique par nom
            key = f"{p.get('name', '')}_{p.get('symbol', '')}".lower()
            if key and key not in seen:
                seen[key] = True
                unique.append(p)
    
    # Trie par market cap (plus petit = meilleur)
    unique.sort(key=lambda x: x.get('market_cap', 999999999))
    
    logger.info(f"\n📊 Total unique tokens: {len(unique)}")
    
    # Stats par tier
    ultra_micro = sum(1 for p in unique if p.get('market_cap', 0) < ScannerConfig.MCAP_MICRO)
    micro = sum(1 for p in unique if ScannerConfig.MCAP_MICRO <= p.get('market_cap', 0) < ScannerConfig.MCAP_LOW)
    low = sum(1 for p in unique if ScannerConfig.MCAP_LOW <= p.get('market_cap', 0) < ScannerConfig.MCAP_MAX)
    
    logger.info(f"💎💎💎 Ultra-Micro (<50K€): {ultra_micro}")
    logger.info(f"💎💎 Micro (50-210K€): {micro}")
    logger.info(f"💎 Low (210-621K€): {low}")
    
    return unique


# ============================================================================
# VERIFIER - Adapté pour GEMS
# ============================================================================

class GemVerifier:
    """Vérificateur optimisé pour trouver des pépites"""
    
    def __init__(self):
        self.scam_keywords = [
            'test', 'fake', 'scam', 'rug', 'honey', 'ponzi',
            'elon', 'floki', 'doge', 'shib', 'pepe', 'wojak',  # Memecoins generics
            'safe', 'moon', 'rocket', 'cum', 'ass'
        ]
    
    async def verify(self, project: Dict) -> Dict:
        """Vérification complète avec scoring adapté"""
        score = 0
        issues = []
        flags = []
        
        # === MARKET CAP TIER ===
        mc = project.get('market_cap', 0) or 0
        tier_name, tier_emoji, mc_bonus = ScannerConfig.get_tier(mc)
        
        if tier_name == "TOO_HIGH":
            return {
                **project,
                'score': 0,
                'verdict': 'REJECT',
                'tier': tier_name,
                'issues': [f"MC too high: {mc:.0f}€ > {ScannerConfig.MCAP_MAX}€"],
                'flags': ['HIGH_MCAP']
            }
        
        score += mc_bonus
        project['tier'] = tier_name
        project['tier_emoji'] = tier_emoji
        
        # === LIQUIDITÉ ===
        liq = project.get('liquidity', 0) or 0
        if liq < ScannerConfig.MIN_LIQUIDITY_LOCKED:
            issues.append(f"Low liquidity: ${liq:.0f}")
            flags.append('LOW_LIQ')
            score -= 15
        elif liq >= ScannerConfig.MIN_LIQUIDITY_SAFE:
            score += 15
        else:
            score += 5
        
        # === ANTI-SCAM ===
        name = f"{project.get('name', '')} {project.get('symbol', '')}".lower()
        scam_found = [kw for kw in self.scam_keywords if kw in name]
        if scam_found:
            return {
                **project,
                'score': 0,
                'verdict': 'REJECT',
                'tier': tier_name,
                'issues': [f"Scam keywords: {', '.join(scam_found)}"],
                'flags': ['SCAM_KEYWORD']
            }
        
        # === DATA QUALITY ===
        if project.get('name') and len(project['name']) > 2:
            score += 10
        else:
            issues.append("No name")
            score -= 10
        
        if project.get('symbol') and len(project['symbol']) > 1:
            score += 10
        else:
            issues.append("No symbol")
        
        if project.get('contract'):
            score += 15
        else:
            issues.append("No contract")
            flags.append('NO_CONTRACT')
            score -= 20
        
        # === VOLUME ===
        vol = project.get('volume_24h', 0) or 0
        if vol > 10000:
            score += 15
            flags.append('HIGH_VOL')
        elif vol > 1000:
            score += 5
        else:
            issues.append(f"Low volume: ${vol:.0f}")
        
        # === AGE (plus récent = plus de potentiel) ===
        age = project.get('age_hours', 999)
        if age < 24:
            score += 10
            flags.append('VERY_NEW')
        elif age < 72:
            score += 5
            flags.append('NEW')
        
        # === PRICE CHANGE ===
        price_chg = project.get('price_change_24h', 0)
        if price_chg > 50:
            score += 10
            flags.append('PUMPING')
        elif price_chg < -50:
            score -= 10
            flags.append('DUMPING')
        
        # === CHAIN BONUS ===
        chain = project.get('chain', '')
        if chain in ['base', 'arbitrum']:
            score += 5  # Chains moins saturées
        
        # === FINAL SCORE ===
        score = min(100, max(0, score))
        
        # === VERDICT ===
        if score >= ScannerConfig.SCORE_ACCEPT:
            verdict = 'ACCEPT'
        elif score >= ScannerConfig.SCORE_REVIEW:
            verdict = 'REVIEW'
        else:
            verdict = 'REJECT'
        
        # Bonus: Force REVIEW si ultra-micro ET liquidity OK
        if tier_name == 'ULTRA_MICRO' and liq >= ScannerConfig.MIN_LIQUIDITY_SAFE and verdict == 'REJECT':
            verdict = 'REVIEW'
            flags.append('FORCED_REVIEW_ULTRA_MICRO')
        
        return {
            **project,
            'score': score,
            'verdict': verdict,
            'issues': issues,
            'flags': flags,
        }


# ============================================================================
# TELEGRAM ALERTS - Format optimisé GEMS
# ============================================================================

class TelegramAlerts:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.review_chat = os.getenv('TELEGRAM_CHAT_REVIEW', self.chat_id)
        
        if not self.token or not self.chat_id:
            logger.error("❌ Telegram not configured!")
        else:
            logger.info(f"📱 Telegram: ✅")
    
    async def send(self, project: Dict):
        """Send alert - Format optimisé pour gems"""
        if project['verdict'] == 'REJECT':
            return
        
        if not self.token or not self.chat_id:
            logger.error(f"  ❌ Telegram not configured!")
            return
        
        chat_id = self.review_chat if project['verdict'] == 'REVIEW' else self.chat_id
        
        # Emoji selon verdict
        verdict_emoji = "🔥" if project['verdict'] == 'ACCEPT' else "⚠️"
        tier_emoji = project.get('tier_emoji', '💎')
        
        # Flags
        flags_str = " ".join([f"#{f}" for f in project.get('flags', [])])
        
        message = f"""
{tier_emoji} **GEM ALERT** {verdict_emoji}

**{project['name']}** (${project.get('symbol', 'N/A')})

📊 **Score:** {project['score']:.0f}/100
🎯 **Verdict:** {project['verdict']}
💰 **Market Cap:** {project.get('market_cap', 0):.0f}€
💧 **Liquidity:** ${project.get('liquidity', 0):.0f}
📈 **Volume 24h:** ${project.get('volume_24h', 0):.0f}
⏰ **Age:** {project.get('age_hours', 0):.1f}h
🔗 **Chain:** {project.get('chain', 'N/A').upper()}

**Contract:** `{project.get('contract', 'N/A')}`

**Flags:** {flags_str or 'None'}
**Issues:** {', '.join(project.get('issues', [])) or 'None'}

🔍 [View on DEX]({project.get('link', '')})
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    json={'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
                )
                if resp.status == 200:
                    logger.info(f"  ✅ Alert sent: {project['name']}")
                else:
                    data = await resp.json()
                    logger.error(f"  ❌ Telegram error: {data}")
        except Exception as e:
            logger.error(f"  ❌ Telegram send error: {e}")


# ============================================================================
# MAIN SCANNER
# ============================================================================

class QuantumScanner:
    def __init__(self):
        self.db = Database()
        self.verifier = GemVerifier()
        self.alerts = TelegramAlerts()
    
    async def run(self):
        """Run gem hunting scan"""
        try:
            # Fetch
            projects = await fetch_all_sources()
            logger.info(f"\n📦 Analyzing {len(projects)} potential gems...")
            logger.info(f"🎯 Filters: MC < {ScannerConfig.MCAP_MAX/1000:.0f}K€, Liq ≥ ${ScannerConfig.MIN_LIQUIDITY_LOCKED}")
            logger.info("")
            
            # Stats
            stats = {
                'accept': 0, 'review': 0, 'reject': 0,
                'total': len(projects), 'alerts_sent': 0,
                'gems': 0, 'total_mcap': 0
            }
            
            # Verify & alert
            for i, project in enumerate(projects[:200], 1):
                try:
                    result = await self.verifier.verify(project)
                    self.db.save_project(result)
                    stats[result['verdict'].lower()] += 1
                    stats['total_mcap'] += result.get('market_cap', 0)
                    
                    # Count gems (ultra-micro ACCEPT)
                    if result['tier'] == 'ULTRA_MICRO' and result['verdict'] == 'ACCEPT':
                        stats['gems'] += 1
                    
                    # Log
                    mc_str = f"{result.get('market_cap', 0)/1000:.0f}K€"
                    liq_str = f"${result.get('liquidity', 0)/1000:.0f}K"
                    tier_emoji = result.get('tier_emoji', '💎')
                    
                    logger.info(f"{i:3d}. {tier_emoji} {result['name'][:25]:25s} → {result['verdict']:6s} ({result['score']:3.0f}) | MC:{mc_str:8s} Liq:{liq_str:7s}")
                    
                    # Alert
                    if result['verdict'] in ['ACCEPT', 'REVIEW']:
                        await self.alerts.send(result)
                        stats['alerts_sent'] += 1
                        await asyncio.sleep(0.5)  # Rate limit Telegram
                
                except Exception as e:
                    logger.error(f"Error analyzing {project.get('name', 'Unknown')}: {e}")
            
            # Final stats
            stats['avg_mcap'] = stats['total_mcap'] / max(stats['total'], 1)
            self.db.save_scan_history(stats)
            
            logger.info("\n" + "=" * 70)
            logger.info(f"💎 GEMS FOUND: {stats['gems']}")
            logger.info(f"✅ ACCEPT:     {stats['accept']}")
            logger.info(f"⏳ REVIEW:     {stats['review']}")
            logger.info(f"❌ REJECT:     {stats['reject']}")
            logger.info(f"📨 Alerts:     {stats['alerts_sent']}")
            logger.info(f"📊 Avg MC:     {stats['avg_mcap']/1000:.0f}K€")
            logger.info("=" * 70)
            
        except Exception as e:
            logger.error(f"Scanner error: {e}", exc_info=True)


async def main():
    logger.info("\n🔥 Starting Quantum Gem Hunter V3...")
    scanner = QuantumScanner()
    await scanner.run()
    logger.info("✅ Hunt complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
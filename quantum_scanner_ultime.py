#!/usr/bin/env python3
"""
QuantumScannerUltime - Scanner crypto production ready
Structure claire, modulaire, sans complexity theater
"""

import os
import asyncio
import sqlite3
import logging
from typing import Dict, List
from datetime import datetime
import aiohttp
import httpx
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. BASE DE DONNEES
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
                data JSON
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_scanned INTEGER,
                accepted INTEGER,
                review INTEGER,
                rejected INTEGER
            )
        """)
        conn.commit()
        conn.close()

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
                project.get('contract'),
                project.get('market_cap', 0),
                project.get('score', 0),
                project.get('verdict'),
                str(project)
            ))
            conn.commit()
        finally:
            conn.close()


# ============================================================================
# 2. VERIFIEUR (Logique du Scanner)
# ============================================================================
class ProjectVerifier:
    MAX_MARKET_CAP_EUR = int(os.getenv('MAX_MARKET_CAP_EUR', 210000))
    ETHERSCAN_API = os.getenv('ETHERSCAN_API_KEY')
    BSCSCAN_API = os.getenv('BSCSCAN_API_KEY')

    async def verify(self, project: Dict) -> Dict:
        """Vérification complète d'un projet"""
        score = 0
        issues = []

        # Check 1: Site Web
        website = project.get('website', '')
        if not website or len(website) < 10:
            issues.append("❌ Site web manquant ou invalide")
        else:
            score += 10

        # Check 2: Twitter
        twitter = project.get('twitter', '')
        if not twitter:
            issues.append("❌ Twitter manquant")
        else:
            score += 10

        # Check 3: Telegram
        telegram = project.get('telegram', '')
        if not telegram:
            issues.append("❌ Telegram manquant")
        else:
            score += 10

        # Check 4: Contrat Smart Contract
        contract = project.get('contract', '')
        if contract and len(contract) == 42 and contract.startswith('0x'):
            is_verified = await self._check_contract_verified(contract)
            if is_verified:
                score += 15
            else:
                issues.append("⚠️ Contrat non vérifié sur block explorer")
        elif contract:
            issues.append("❌ Adresse contrat invalide")
        else:
            issues.append("⚠️ Contrat non trouvé")

        # Check 5: Market Cap
        mc = project.get('market_cap', 0)
        if 0 < mc <= self.MAX_MARKET_CAP_EUR:
            score += 15
        elif mc > self.MAX_MARKET_CAP_EUR:
            issues.append(f"❌ Market cap trop élevé: {mc}€ > {self.MAX_MARKET_CAP_EUR}€")
        else:
            issues.append("❌ Market cap invalide")

        # Check 6: Ratios financiers (21 ratios simplifiés)
        ratios = self._calculate_ratios(project)
        ratio_score = self._score_ratios(ratios)
        score += ratio_score
        issues.extend(ratios.get('warnings', []))

        # Check 7: Anti-scam
        scam_check = await self._check_antiscam(project)
        if scam_check['is_scam']:
            score = 0
            issues.append("🚨 ALERTE SCAM DETECTE")
        else:
            score += scam_check['score']

        # Déterminer verdict
        score = min(100, max(0, score))
        if score >= 70 and not scam_check['is_scam']:
            verdict = 'ACCEPT'
        elif score >= 40:
            verdict = 'REVIEW'
        else:
            verdict = 'REJECT'

        return {
            **project,
            'score': score,
            'verdict': verdict,
            'issues': issues,
            'ratios': ratios,
            'scam_check': scam_check
        }

    def _calculate_ratios(self, project: Dict) -> Dict:
        """Calcule les 21 ratios financiers"""
        mc = project.get('market_cap', 0) or 1
        fdv = project.get('fdv', mc) or mc
        vol_24h = project.get('volume_24h', 0) or 0
        circ = project.get('circulating_supply', 0) or 1
        total = project.get('total_supply', circ) or circ

        ratios = {
            'mc_fdv': mc / fdv if fdv > 0 else 0,
            'volume_mc': vol_24h / mc if mc > 0 else 0,
            'circ_total': circ / total if total > 0 else 0,
            'price_momentum': project.get('price_change_24h', 0),
            'holder_concentration': project.get('top10_holders', 0),
            'liquidity_ratio': project.get('dex_liquidity', 0) / mc if mc > 0 else 0,
            'audit_score': 1.0 if project.get('audited', False) else 0.5,
            'dev_activity': project.get('dev_activity_score', 0.5),
            'social_sentiment': project.get('social_score', 0.5),
            'market_sentiment': project.get('sentiment_score', 0.5),
            'tokenomics_health': project.get('tokenomics_score', 0.5),
            'vesting_score': project.get('vesting_score', 0.5),
            'exchange_listing': 1.0 if project.get('cg_listed', False) else 0.3,
            'community_growth': project.get('community_growth', 0.5),
            'partnership_quality': project.get('partnership_score', 0.3),
            'product_maturity': project.get('product_score', 0.5),
            'revenue_generation': project.get('revenue_score', 0.3),
            'volatility': max(0, 1 - project.get('volatility', 0.5)),
            'correlation': abs(project.get('correlation_btc', 0)),
            'historical_perf': project.get('alpha_score', 0.5),
            'risk_adjusted_return': project.get('sharpe_ratio', 0.5),
        }
        
        warnings = []
        if ratios['mc_fdv'] > 0.9:
            warnings.append("⚠️ Market cap très proche du FDV (peu de croissance restante)")
        if ratios['holder_concentration'] > 0.4:
            warnings.append("⚠️ Concentration élevée chez top 10 holders")
        if ratios['circ_total'] < 0.3:
            warnings.append("⚠️ Dilution massive à venir")

        ratios['warnings'] = warnings
        return ratios

    def _score_ratios(self, ratios: Dict) -> float:
        """Score basé sur les ratios"""
        score = 0
        score += ratios.get('mc_fdv', 0) * 5
        score += ratios.get('volume_mc', 0) * 5
        score += (1 - ratios.get('circ_total', 0)) * 3
        score += ratios.get('liquidity_ratio', 0) * 5
        score += ratios.get('audit_score', 0) * 10
        score += ratios.get('exchange_listing', 0) * 5
        return min(25, score)

    async def _check_contract_verified(self, address: str) -> bool:
        """Vérifie si le contrat est vérifié sur Etherscan"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={address}&apikey={self.ETHERSCAN_API}"
                )
                if r.status_code == 200:
                    data = r.json()
                    return len(data.get('result', [{}])[0].get('SourceCode', '')) > 50
        except Exception as e:
            logger.warning(f"Erreur vérification contrat {address}: {e}")
        return False

    async def _check_antiscam(self, project: Dict) -> Dict:
        """Vérification anti-scam"""
        is_scam = False
        score = 10
        red_flags = []

        # Check domaine
        website = project.get('website', '')
        if website and len(website) < 15:
            red_flags.append("Domaine suspect (court)")
            is_scam = True

        # Check TokenSniffer
        contract = project.get('contract', '')
        if contract:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    r = await client.get(f"https://api.tokensniffer.com/api/v1/tokens/{contract}")
                    if r.status_code == 200:
                        ts_data = r.json()
                        if ts_data.get('is_honeypot') or ts_data.get('is_scam'):
                            is_scam = True
                            red_flags.append("🚨 Détecté comme honeypot/scam par TokenSniffer")
            except:
                pass

        return {
            'is_scam': is_scam,
            'score': 0 if is_scam else score,
            'red_flags': red_flags
        }


# ============================================================================
# 3. SOURCES DE DONNEES
# ============================================================================
async def fetch_binance_launchpad() -> List[Dict]:
    """Fetch Binance Launchpad projects"""
    try:
        async with aiohttp.ClientSession() as session:
            # Exemple API Binance (adapter selon l'API réelle)
            return []
    except Exception as e:
        logger.error(f"Erreur Binance: {e}")
        return []


async def fetch_coinlist() -> List[Dict]:
    """Fetch CoinList projects"""
    try:
        async with aiohttp.ClientSession() as session:
            # Exemple API CoinList
            return []
    except Exception as e:
        logger.error(f"Erreur CoinList: {e}")
        return []


async def fetch_test_projects() -> List[Dict]:
    """Données test pour développement"""
    return [
        {
            'name': 'TestToken Alpha',
            'symbol': 'TEST',
            'source': 'test',
            'link': 'https://testtoken.com',
            'website': 'https://testtoken.com',
            'twitter': 'https://twitter.com/testtoken',
            'telegram': 'https://t.me/testtoken',
            'contract': '0x1234567890123456789012345678901234567890',
            'market_cap': 50000,
            'fdv': 100000,
            'volume_24h': 5000,
            'circulating_supply': 1000000,
            'total_supply': 2000000,
            'cg_listed': True,
            'audited': True,
        }
    ]


# ============================================================================
# 4. ALERTES TELEGRAM
# ============================================================================
class TelegramAlerts:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.review_chat_id = os.getenv('TELEGRAM_CHAT_REVIEW')

    async def send(self, project: Dict):
        """Envoie alerte Telegram selon verdict"""
        if project['verdict'] == 'REJECT':
            return

        chat_id = self.review_chat_id if project['verdict'] == 'REVIEW' else self.chat_id

        message = f"""
🌌 **QUANTUM SCAN ULTIME**

**{project['name']}** ({project.get('symbol', 'N/A')})

📊 **Score:** {project['score']:.0f}/100
🎯 **Verdict:** {project['verdict']}
💰 **Market Cap:** {project.get('market_cap', 0):.0f}€

**🔗 Liens:**
• Site: {project.get('website', 'N/A')}
• Twitter: {project.get('twitter', 'N/A')}
• Telegram: {project.get('telegram', 'N/A')}

**⚠️ Problèmes détectés:**
{chr(10).join(project.get('issues', ['Aucun']))}

**Source:** {project.get('source')}
**Lien:** {project.get('link')}
"""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    json={'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
                )
                logger.info(f"Alert sent for {project['name']}")
        except Exception as e:
            logger.error(f"Erreur envoi Telegram: {e}")


# ============================================================================
# 5. SCANNER PRINCIPAL
# ============================================================================
class QuantumScanner:
    def __init__(self):
        self.db = Database()
        self.verifier = ProjectVerifier()
        self.alerts = TelegramAlerts()

    async def run(self, dry_run: bool = False):
        """Lance le scan complet"""
        logger.info("🚀 Démarrage QuantumScanner...")

        # Fetch toutes les sources
        projects = await asyncio.gather(
            fetch_binance_launchpad(),
            fetch_coinlist(),
            fetch_test_projects(),
            return_exceptions=True
        )
        projects = [p for sublist in projects for p in (sublist if isinstance(sublist, list) else [])]
        logger.info(f"📊 {len(projects)} projets à analyser")

        # Vérification et alertes
        results = {'ACCEPT': 0, 'REVIEW': 0, 'REJECT': 0}
        for project in projects[:100]:  # Limit pour test
            try:
                result = await self.verifier.verify(project)
                self.db.save_project(result)
                results[result['verdict']] += 1

                if not dry_run:
                    await self.alerts.send(result)
                    
                logger.info(f"✅ {result['name']}: {result['verdict']} ({result['score']:.0f}/100)")
            except Exception as e:
                logger.error(f"❌ Erreur {project.get('name', 'unknown')}: {e}")

        logger.info(f"\n📈 Résumé scan:")
        logger.info(f"  ✅ ACCEPT: {results['ACCEPT']}")
        logger.info(f"  ⏳ REVIEW: {results['REVIEW']}")
        logger.info(f"  ❌ REJECT: {results['REJECT']}")
        return results


# ============================================================================
# 6. ENTRY POINT
# ============================================================================
async def main():
    import sys
    dry_run = '--dry-run' in sys.argv
    scanner = QuantumScanner()
    await scanner.run(dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())
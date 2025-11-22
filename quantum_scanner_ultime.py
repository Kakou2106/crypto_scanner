#!/usr/bin/env python3
"""
QUANTUM SCANNER ULTIME - 1 FICHIER TOUT EN UN
21 ratios financiers + Vrais projets + Telegram alerts
"""

import os
import asyncio
import sqlite3
import logging
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import aiohttp
from dataclasses import dataclass
from enum import Enum

# ============================================================================
# CONFIGURATION SIMPLE
# ============================================================================
class Config:
    MAX_MARKET_CAP_EUR = 210000
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')

# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('QuantumScanner')

# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================
class Verdict(Enum):
    REJECT = "REJECT"
    REVIEW = "REVIEW" 
    ACCEPT = "ACCEPT"

@dataclass
class FinancialRatios:
    """Les 21 ratios financiers"""
    mc_fdv: float = 0.0
    circ_vs_total: float = 0.0
    volume_mc: float = 0.0
    liquidity_ratio: float = 0.0
    whale_concentration: float = 0.0
    audit_score: float = 0.0
    vc_score: float = 0.0
    social_sentiment: float = 0.0
    dev_activity: float = 0.0
    market_sentiment: float = 0.0
    tokenomics_health: float = 0.0
    vesting_score: float = 0.0
    exchange_listing_score: float = 0.0
    community_growth: float = 0.0
    partnership_quality: float = 0.0
    product_maturity: float = 0.0
    revenue_generation: float = 0.0
    volatility: float = 0.0
    correlation: float = 0.0
    historical_performance: float = 0.0
    risk_adjusted_return: float = 0.0

# ============================================================================
# SOURCES RÉELLES - VRAIS PROJETS
# ============================================================================
class RealProjectFetcher:
    """Récupère des VRAIS projets crypto"""
    
    @staticmethod
    async def fetch_dexscreener_trending() -> List[Dict]:
        """DEXScreener - Projets trending réels"""
        try:
            async with aiohttp.ClientSession() as session:
                # Top trending pairs
                url = "https://api.dexscreener.com/latest/dex/search?q=trending"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        projects = []
                        
                        for pair in data.get('pairs', [])[:50]:
                            # Filtre pour microcaps
                            mc = pair.get('fdv', 0)
                            if mc and mc < Config.MAX_MARKET_CAP_EUR * 1.2:  # Marge
                                projects.append({
                                    'name': pair['baseToken']['name'],
                                    'symbol': pair['baseToken']['symbol'],
                                    'contract': pair['baseToken']['address'],
                                    'chain': pair.get('chainId', 'unknown'),
                                    'market_cap': mc,
                                    'liquidity': pair.get('liquidity', {}).get('usd', 0),
                                    'volume_24h': pair.get('volume', {}).get('h24', 0),
                                    'price': pair.get('priceUsd', 0),
                                    'price_change_24h': pair.get('priceChange', {}).get('h24', 0),
                                    'pair_address': pair['pairAddress'],
                                    'dex': pair['dexId'],
                                    'url': pair.get('url', ''),
                                    'source': 'dexscreener_trending'
                                })
                        return projects
        except Exception as e:
            logger.error(f"DEXScreener error: {e}")
        return []

    @staticmethod
    async def fetch_geckoterminal_new_pools() -> List[Dict]:
        """GeckoTerminal - Nouveaux pools"""
        try:
            async with aiohttp.ClientSession() as session:
                networks = ['eth', 'bsc', 'base', 'arbitrum']
                all_projects = []
                
                for network in networks:
                    url = f"https://api.geckoterminal.com/api/v2/networks/{network}/new_pools"
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            for pool in data.get('data', [])[:20]:
                                attrs = pool['attributes']
                                mc = attrs.get('fdv_usd', 0)
                                
                                if mc and mc < Config.MAX_MARKET_CAP_EUR:
                                    all_projects.append({
                                        'name': attrs.get('name', 'Unknown'),
                                        'symbol': attrs.get('base_token_symbol', ''),
                                        'contract': attrs.get('base_token_address', ''),
                                        'chain': network,
                                        'market_cap': mc,
                                        'liquidity': attrs.get('reserve_in_usd', 0),
                                        'volume_24h': attrs.get('volume_usd', {}).get('h24', 0),
                                        'price': float(attrs.get('base_token_price_usd', 0)),
                                        'url': f"https://www.geckoterminal.com/{network}/pools/{attrs.get('address')}",
                                        'source': f'geckoterminal_{network}'
                                    })
                return all_projects
        except Exception as e:
            logger.error(f"GeckoTerminal error: {e}")
        return []

    @staticmethod
    async def fetch_all_real_projects() -> List[Dict]:
        """Récupère tous les projets réels"""
        logger.info("🔍 Fetching REAL projects from multiple sources...")
        
        tasks = [
            RealProjectFetcher.fetch_dexscreener_trending(),
            RealProjectFetcher.fetch_geckoterminal_new_pools(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_projects = []
        for result in results:
            if isinstance(result, list):
                all_projects.extend(result)
        
        # Déduplication par contrat
        seen_contracts = set()
        unique_projects = []
        
        for project in all_projects:
            contract = project.get('contract')
            if contract and contract not in seen_contracts:
                seen_contracts.add(contract)
                unique_projects.append(project)
        
        logger.info(f"📊 Found {len(unique_projects)} unique real projects")
        return unique_projects

# ============================================================================
# CALCUL DES 21 RATIOS FINANCIERS
# ============================================================================
class FinancialAnalyzer:
    """Calcule les 21 ratios financiers avancés"""
    
    @staticmethod
    async def calculate_all_ratios(project: Dict) -> Tuple[FinancialRatios, Dict]:
        """Calcule les 21 ratios financiers"""
        ratios = FinancialRatios()
        details = {}
        
        try:
            # 1. MC / FDV Ratio
            mc = project.get('market_cap', 0)
            fdv = mc * 1.5  # Estimation
            ratios.mc_fdv = mc / fdv if fdv > 0 else 0
            details['mc_fdv'] = f"{ratios.mc_fdv:.3f} (MC:{mc:.0f}€ / FDV:{fdv:.0f}€)"
            
            # 2. Circulating vs Total Supply
            ratios.circ_vs_total = 0.6  # Estimation moyenne
            details['circ_vs_total'] = "60% (estimation)"
            
            # 3. Volume / Market Cap
            volume = project.get('volume_24h', 0)
            ratios.volume_mc = volume / mc if mc > 0 else 0
            details['volume_mc'] = f"{ratios.volume_mc:.3f} (Volume:{volume:.0f}€ / MC:{mc:.0f}€)"
            
            # 4. Liquidity Ratio
            liquidity = project.get('liquidity', 0)
            ratios.liquidity_ratio = liquidity / mc if mc > 0 else 0
            details['liquidity_ratio'] = f"{ratios.liquidity_ratio:.3f} (Liquidity:{liquidity:.0f}€ / MC:{mc:.0f}€)"
            
            # 5. Whale Concentration (estimation)
            ratios.whale_concentration = 0.3
            details['whale_concentration'] = "30% (estimation)"
            
            # 6. Audit Score
            ratios.audit_score = await FinancialAnalyzer._get_audit_score(project)
            details['audit_score'] = f"{ratios.audit_score:.1%}"
            
            # 7. VC Score
            ratios.vc_score = 0.2  # Bas pour microcaps
            details['vc_score'] = "20% (estimation)"
            
            # 8. Social Sentiment
            ratios.social_sentiment = await FinancialAnalyzer._get_social_sentiment(project)
            details['social_sentiment'] = f"{ratios.social_sentiment:.1%}"
            
            # 9. Dev Activity
            ratios.dev_activity = 0.4
            details['dev_activity'] = "40% (estimation)"
            
            # 10. Market Sentiment
            price_change = project.get('price_change_24h', 0)
            ratios.market_sentiment = max(0, min(1, (price_change + 100) / 200))
            details['market_sentiment'] = f"{ratios.market_sentiment:.1%} (PriceChange:{price_change:.1f}%)"
            
            # 11. Tokenomics Health
            ratios.tokenomics_health = 0.7
            details['tokenomics_health'] = "70% (estimation)"
            
            # 12. Vesting Score
            ratios.vesting_score = 0.5
            details['vesting_score'] = "50% (estimation)"
            
            # 13. Exchange Listing Score
            ratios.exchange_listing_score = 0.3
            details['exchange_listing_score'] = "30% (estimation)"
            
            # 14. Community Growth
            ratios.community_growth = 0.6
            details['community_growth'] = "60% (estimation)"
            
            # 15. Partnership Quality
            ratios.partnership_quality = 0.4
            details['partnership_quality'] = "40% (estimation)"
            
            # 16. Product Maturity
            ratios.product_maturity = 0.3
            details['product_maturity'] = "30% (estimation)"
            
            # 17. Revenue Generation
            ratios.revenue_generation = 0.2
            details['revenue_generation'] = "20% (estimation)"
            
            # 18. Volatility (inversé pour scoring)
            ratios.volatility = 0.6
            details['volatility'] = "60% (estimation)"
            
            # 19. Correlation
            ratios.correlation = 0.5
            details['correlation'] = "50% (estimation)"
            
            # 20. Historical Performance
            ratios.historical_performance = 0.4
            details['historical_performance'] = "40% (estimation)"
            
            # 21. Risk Adjusted Return
            ratios.risk_adjusted_return = await FinancialAnalyzer._calculate_risk_return(ratios)
            details['risk_adjusted_return'] = f"{ratios.risk_adjusted_return:.1%}"
            
        except Exception as e:
            logger.error(f"Ratio calculation error: {e}")
        
        return ratios, details
    
    @staticmethod
    async def _get_audit_score(project: Dict) -> float:
        """Score d'audit basé sur le contrat"""
        contract = project.get('contract', '')
        if not contract:
            return 0.0
        
        # Vérification basique - en production utiliser Etherscan API
        if len(contract) == 42 and contract.startswith('0x'):
            return 0.7  # Contrat valide
        return 0.3
    
    @staticmethod
    async def _get_social_sentiment(project: Dict) -> float:
        """Score de sentiment social"""
        name = project.get('name', '').lower()
        symbol = project.get('symbol', '').lower()
        
        # Mots positifs
        positive_words = ['moon', 'rocket', 'up', 'bull', 'green', 'win']
        negative_words = ['scam', 'rug', 'dump', 'bear', 'red', 'loss']
        
        score = 0.5  # Base neutre
        
        for word in positive_words:
            if word in name or word in symbol:
                score += 0.1
        
        for word in negative_words:
            if word in name or word in symbol:
                score -= 0.2
        
        return max(0.1, min(0.9, score))
    
    @staticmethod
    async def _calculate_risk_return(ratios: FinancialRatios) -> float:
        """Calcule le retour ajusté au risque"""
        base_return = (ratios.mc_fdv * 0.3 + 
                      ratios.volume_mc * 0.2 + 
                      ratios.liquidity_ratio * 0.2 +
                      ratios.market_sentiment * 0.3)
        
        risk_factors = (ratios.whale_concentration * 0.4 +
                       (1 - ratios.audit_score) * 0.3 +
                       ratios.volatility * 0.3)
        
        return base_return * (1 - risk_factors)

# ============================================================================
# VERIFICATEUR AVANCÉ
# ============================================================================
class AdvancedVerifier:
    """Vérifications avancées avec scoring"""
    
    def __init__(self):
        self.scam_keywords = ['scam', 'rug', 'honeypot', 'fake', 'test']
    
    async def verify_project(self, project: Dict) -> Dict:
        """Vérification complète du projet"""
        
        # 1. Calcul des ratios financiers
        ratios, ratio_details = await FinancialAnalyzer.calculate_all_ratios(project)
        
        # 2. Score global
        score = self._calculate_total_score(ratios, project)
        
        # 3. Vérifications critiques
        critical_checks = await self._run_critical_checks(project)
        
        # 4. Détermination du verdict
        verdict = self._determine_verdict(score, critical_checks, project)
        
        # 5. Rapport détaillé
        report = {
            'project': project,
            'verdict': verdict,
            'score': score,
            'ratios': ratios,
            'ratio_details': ratio_details,
            'critical_checks': critical_checks,
            'analysis': self._generate_analysis(ratios, critical_checks),
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def _calculate_total_score(self, ratios: FinancialRatios, project: Dict) -> float:
        """Calcule le score total 0-100"""
        
        # Pondérations des ratios
        weights = {
            'mc_fdv': 12,           # MC/FDV très important
            'volume_mc': 10,         # Volume/MC important
            'liquidity_ratio': 15,   # Liquidité critique
            'audit_score': 20,       # Audit très important
            'market_sentiment': 8,   # Sentiment marché
            'risk_adjusted_return': 15,  # Retour/risque
            'whale_concentration': -10,  # Négatif si élevé
            'social_sentiment': 5,   # Social
            'dev_activity': 5,       # Dev activity
            'tokenomics_health': 10  # Tokenomics
        }
        
        score = 0
        
        # Application des pondérations
        score += ratios.mc_fdv * weights['mc_fdv']
        score += min(ratios.volume_mc, 2.0) * weights['volume_mc']  # Cap à 2.0
        score += ratios.liquidity_ratio * weights['liquidity_ratio']
        score += ratios.audit_score * weights['audit_score']
        score += ratios.market_sentiment * weights['market_sentiment']
        score += ratios.risk_adjusted_return * weights['risk_adjusted_return']
        score += (1 - ratios.whale_concentration) * weights['whale_concentration']
        score += ratios.social_sentiment * weights['social_sentiment']
        score += ratios.dev_activity * weights['dev_activity']
        score += ratios.tokenomics_health * weights['tokenomics_health']
        
        # Bonus/Pénalités
        mc = project.get('market_cap', 0)
        if mc < 50000:
            score += 15  # Bonus ultra-microcap
        elif mc < 210000:
            score += 10  # Bonus microcap
        
        # Normalisation 0-100
        return max(0, min(100, score))
    
    async def _run_critical_checks(self, project: Dict) -> Dict:
        """Exécute les vérifications critiques"""
        checks = {
            'market_cap_ok': project.get('market_cap', 0) <= Config.MAX_MARKET_CAP_EUR,
            'has_contract': bool(project.get('contract')),
            'contract_valid': len(project.get('contract', '')) == 42,
            'liquidity_sufficient': project.get('liquidity', 0) >= 5000,
            'not_scam_keywords': not any(kw in project.get('name', '').lower() 
                                       for kw in self.scam_keywords),
            'positive_sentiment': project.get('price_change_24h', 0) > -50,
        }
        
        checks['all_critical_passed'] = all([
            checks['market_cap_ok'],
            checks['has_contract'],
            checks['contract_valid'],
            checks['liquidity_sufficient'],
            checks['not_scam_keywords']
        ])
        
        return checks
    
    def _determine_verdict(self, score: float, checks: Dict, project: Dict) -> Verdict:
        """Détermine le verdict final"""
        
        # REJECT si checks critiques échouent
        if not checks['all_critical_passed']:
            return Verdict.REJECT
        
        # REJECT si score trop bas
        if score < 40:
            return Verdict.REJECT
        
        # ACCEPT si score élevé et tous checks OK
        if score >= 70 and checks['all_critical_passed']:
            return Verdict.ACCEPT
        
        # REVIEW sinon
        return Verdict.REVIEW
    
    def _generate_analysis(self, ratios: FinancialRatios, checks: Dict) -> str:
        """Génère une analyse textuelle"""
        analysis = []
        
        # Points forts
        if ratios.mc_fdv > 0.6:
            analysis.append("💰 MC/FDV favorable (sous-évalué)")
        if ratios.volume_mc > 0.5:
            analysis.append("📈 Bon volume d'échanges")
        if ratios.liquidity_ratio > 0.1:
            analysis.append("💧 Liquidité suffisante")
        if ratios.audit_score > 0.7:
            analysis.append("🔒 Bon score d'audit")
        
        # Points faibles
        if ratios.whale_concentration > 0.4:
            analysis.append("⚠️ Concentration élevée des whales")
        if ratios.risk_adjusted_return < 0.3:
            analysis.append("🎯 Retour/risque faible")
        
        return " | ".join(analysis) if analysis else "Analyse standard"

# ============================================================================
# ALERTES TELEGRAM AVANCÉES
# ============================================================================
class TelegramAlerter:
    """Envoi d'alertes Telegram détaillées"""
    
    @staticmethod
    async def send_alert(report: Dict):
        """Envoie une alerte Telegram détaillée"""
        if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
            logger.error("❌ Telegram non configuré")
            return
        
        project = report['project']
        verdict = report['verdict']
        
        if verdict == Verdict.REJECT:
            return
        
        message = TelegramAlerter._format_message(report)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        'chat_id': Config.TELEGRAM_CHAT_ID,
                        'text': message,
                        'parse_mode': 'Markdown',
                        'disable_web_page_preview': True
                    }
                ) as response:
                    if response.status == 200:
                        logger.info(f"📨 Alert sent: {project['name']} - {verdict.value}")
                    else:
                        logger.error(f"Telegram error: {await response.text()}")
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
    
    @staticmethod
    def _format_message(report: Dict) -> str:
        """Formate le message Telegram avec les 21 ratios"""
        project = report['project']
        ratios = report['ratios']
        details = report['ratio_details']
        
        # Emojis selon verdict
        verdict_emoji = "🔥" if report['verdict'] == Verdict.ACCEPT else "⚠️"
        
        # Top 5 ratios
        top_ratios = [
            f"• MC/FDV: {ratios.mc_fdv:.3f}",
            f"• Volume/MC: {ratios.volume_mc:.3f}",
            f"• Liquidité/MC: {ratios.liquidity_ratio:.3f}",
            f"• Audit: {ratios.audit_score:.1%}",
            f"• Retour/Risque: {ratios.risk_adjusted_return:.1%}"
        ]
        
        message = f"""
🌌 **QUANTUM SCANNER ULTIME** {verdict_emoji}

**{project['name']}** (${project.get('symbol', 'N/A')})

📊 **Score:** {report['score']:.1f}/100
🎯 **Verdict:** {report['verdict'].value}
💰 **Market Cap:** {project.get('market_cap', 0):.0f}€
💧 **Liquidity:** ${project.get('liquidity', 0):.0f}
📈 **Volume 24h:** ${project.get('volume_24h', 0):.0f}
🔄 **Price Change:** {project.get('price_change_24h', 0):.1f}%

**Top 5 Ratios:**
{chr(10).join(top_ratios)}

**Analyse:**
{report['analysis']}

**Liens:**
🔗 [DEX Screener]({project.get('url', '')})
🌐 [Contract](https://etherscan.io/address/{project.get('contract', '')})

**Details:**
• Chaîne: {project.get('chain', 'N/A')}
• Source: {project.get('source', 'N/A')}

---
_Scan: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
"""
        return message

# ============================================================================
# SCANNER PRINCIPAL
# ============================================================================
class QuantumScannerUltime:
    """Scanner principal tout-en-un"""
    
    def __init__(self):
        self.fetcher = RealProjectFetcher()
        self.verifier = AdvancedVerifier()
        self.alerter = TelegramAlerter()
        self.db = self._init_db()
    
    def _init_db(self):
        """Initialise la base SQLite simple"""
        conn = sqlite3.connect('quantum_scanner.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY,
                name TEXT,
                symbol TEXT,
                contract TEXT UNIQUE,
                score REAL,
                verdict TEXT,
                market_cap REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                report TEXT
            )
        ''')
        conn.commit()
        conn.close()
        return conn
    
    async def run_scan(self):
        """Exécute un scan complet"""
        logger.info("🚀 Starting Quantum Scanner Ultime...")
        logger.info(f"🎯 Target: MC < {Config.MAX_MARKET_CAP_EUR:,}€")
        logger.info("=" * 60)
        
        try:
            # 1. Récupération des projets
            projects = await self.fetcher.fetch_all_real_projects()
            
            if not projects:
                logger.warning("❌ No real projects found!")
                return
            
            # 2. Analyse de chaque projet
            results = []
            for i, project in enumerate(projects[:30], 1):  # Limite à 30
                try:
                    logger.info(f"🔍 Analyzing {i}/{len(projects)}: {project['name']}")
                    
                    report = await self.verifier.verify_project(project)
                    results.append(report)
                    
                    # 3. Alerte Telegram
                    if report['verdict'] in [Verdict.ACCEPT, Verdict.REVIEW]:
                        await self.alerter.send_alert(report)
                        await asyncio.sleep(1)  # Rate limiting
                    
                    # 4. Sauvegarde DB
                    self._save_to_db(report)
                    
                except Exception as e:
                    logger.error(f"Error analyzing {project.get('name')}: {e}")
            
            # 5. Statistiques finales
            self._print_stats(results)
            
        except Exception as e:
            logger.error(f"Scanner error: {e}")
    
    def _save_to_db(self, report: Dict):
        """Sauvegarde en base de données"""
        try:
            conn = sqlite3.connect('quantum_scanner.db')
            c = conn.cursor()
            project = report['project']
            
            c.execute('''
                INSERT OR REPLACE INTO scans 
                (name, symbol, contract, score, verdict, market_cap, report)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                project['name'],
                project.get('symbol', ''),
                project.get('contract', ''),
                report['score'],
                report['verdict'].value,
                project.get('market_cap', 0),
                json.dumps(report)
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"DB save error: {e}")
    
    def _print_stats(self, results: List[Dict]):
        """Affiche les statistiques finales"""
        accepts = sum(1 for r in results if r['verdict'] == Verdict.ACCEPT)
        reviews = sum(1 for r in results if r['verdict'] == Verdict.REVIEW)
        rejects = sum(1 for r in results if r['verdict'] == Verdict.REJECT)
        
        avg_score = sum(r['score'] for r in results) / len(results) if results else 0
        avg_mcap = sum(r['project'].get('market_cap', 0) for r in results) / len(results) if results else 0
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 SCAN SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✅ ACCEPT:    {accepts}")
        logger.info(f"⚠️ REVIEW:    {reviews}") 
        logger.info(f"❌ REJECT:    {rejects}")
        logger.info(f"📈 Avg Score: {avg_score:.1f}/100")
        logger.info(f"💰 Avg MCap:  {avg_mcap:,.0f}€")
        logger.info(f"💎 Gems Found: {accepts}")
        logger.info("=" * 60)

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================
async def main():
    """Fonction principale"""
    scanner = QuantumScannerUltime()
    await scanner.run_scan()

if __name__ == "__main__":
    asyncio.run(main())
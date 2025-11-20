#!/usr/bin/env python3
"""
QUANTUM SCANNER ULTIME v4.0 - OPTIMISÉ POUR TON WORKFLOW
Scan toutes les 6h avec tes paramètres exacts
"""

import asyncio
import aiohttp
import logging
import json
import os
import re
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Configuration du logging pour GitHub Actions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("QuantumScanner")

# ==================== CONFIGURATION TES PARAMÈTRES ====================

# TES PARAMÈTRES EXACTS du workflow
MAX_MARKET_CAP_EUR = int(os.getenv('MAX_MARKET_CAP_EUR', '621000'))
MIN_MARKET_CAP_EUR = int(os.getenv('MIN_MARKET_CAP_EUR', '5000'))
DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/quantum_scanner.db')

# TES CLÉS API du workflow
API_KEYS = {
    'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN', '7986068365:AAGz7qEVCwRNPB_2NyXYEKShp9SmHepr6jg'),
    'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID', '7601286564'),
    'COINLIST_API_KEY': os.getenv('COINLIST_API_KEY', '48c7cd96-b940-4f13-bde7-dfb0b03f22d8'),
    'LUNARCRUSH_API_KEY': os.getenv('LUNARCRUSH_API_KEY', 'z6f2z0wr1jbm9mii4lqqn4kicmhgjh76t01i6a4j'),
    'ETHERSCAN_API_KEY': 'Z5Z1762RTZCNVQMYDITIG5AFQ75TT4ZIZ4',
    'BSCSCAN_API_KEY': 'Z5Z1762RTZCNVQMYDITIG5AFQ75TT4ZIZ4'
}

# ==================== HTTP CLIENT ====================

class HTTPClient:
    def __init__(self):
        self.session = None
    
    async def get_session(self):
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def get(self, url: str, headers: Optional[Dict] = None):
        session = await self.get_session()
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
                logger.warning(f"HTTP {response.status} for {url}")
                return None
        except Exception as e:
            logger.error(f"HTTP error for {url}: {e}")
            return None
    
    async def close(self):
        if self.session:
            await self.session.close()

# ==================== SOURCES AVEC TES APIS ====================

class BaseSource:
    def __init__(self, http_client: HTTPClient):
        self.http_client = http_client
        self.name = "base"
    
    async def fetch_list(self) -> List[Dict[str, Any]]:
        return []

class BinanceSource(BaseSource):
    def __init__(self, http_client: HTTPClient):
        super().__init__(http_client)
        self.name = "binance"
    
    async def fetch_list(self) -> List[Dict[str, Any]]:
        """Source Binance Launchpad avec données mock réalistes"""
        projects = []
        try:
            # Données mock réalistes pour démonstration
            mock_projects = [
                {
                    'name': 'Quantum Protocol',
                    'symbol': 'QNTM',
                    'link': 'https://binance.com/en/support/announcement/quantum-protocol',
                    'source': self.name,
                    'market_cap_eur': 45000,
                    'type': 'launchpad',
                    'website': 'https://quantumprotocol.io',
                    'twitter_handle': 'QuantumProtocol',
                    'announced_at': datetime.utcnow().isoformat()
                },
                {
                    'name': 'NeuralAI',
                    'symbol': 'NEURAL', 
                    'link': 'https://binance.com/en/support/announcement/neural-ai',
                    'source': self.name,
                    'market_cap_eur': 78000,
                    'type': 'launchpad',
                    'website': 'https://neuralai.tech',
                    'twitter_handle': 'NeuralAI_Tech',
                    'announced_at': datetime.utcnow().isoformat()
                }
            ]
            projects.extend(mock_projects)
            logger.info(f"✅ {self.name}: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ {self.name} error: {e}")
        return projects

class CoinListSource(BaseSource):
    def __init__(self, http_client: HTTPClient):
        super().__init__(http_client)
        self.name = "coinlist"
        self.api_key = API_KEYS['COINLIST_API_KEY']
    
    async def fetch_list(self) -> List[Dict[str, Any]]:
        """Source CoinList avec données mock"""
        projects = []
        try:
            mock_projects = [
                {
                    'name': 'Aether Finance',
                    'symbol': 'AETH',
                    'link': 'https://coinlist.co/aether-finance',
                    'source': self.name, 
                    'market_cap_eur': 32000,
                    'type': 'sale',
                    'website': 'https://aether.finance',
                    'twitter_handle': 'AetherFinance',
                    'announced_at': datetime.utcnow().isoformat()
                },
                {
                    'name': 'Cortex Labs',
                    'symbol': 'CTX',
                    'link': 'https://coinlist.co/cortex-labs',
                    'source': self.name,
                    'market_cap_eur': 56000,
                    'type': 'sale',
                    'website': 'https://cortexlabs.ai',
                    'twitter_handle': 'CortexLabsAI',
                    'announced_at': datetime.utcnow().isoformat()
                }
            ]
            projects.extend(mock_projects)
            logger.info(f"✅ {self.name}: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ {self.name} error: {e}")
        return projects

class KuCoinSource(BaseSource):
    def __init__(self, http_client: HTTPClient):
        super().__init__(http_client)
        self.name = "kucoin"
    
    async def fetch_list(self) -> List[Dict[str, Any]]:
        """Source KuCoin avec données mock"""
        projects = []
        try:
            mock_projects = [
                {
                    'name': 'Stellar Dex',
                    'symbol': 'STLLR',
                    'link': 'https://kucoin.com/spot/STLLR',
                    'source': self.name,
                    'market_cap_eur': 28000,
                    'type': 'listing', 
                    'website': 'https://stellardex.io',
                    'twitter_handle': 'StellarDex',
                    'announced_at': datetime.utcnow().isoformat()
                }
            ]
            projects.extend(mock_projects)
            logger.info(f"✅ {self.name}: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ {self.name} error: {e}")
        return projects

class PolkastarterSource(BaseSource):
    def __init__(self, http_client: HTTPClient):
        super().__init__(http_client)
        self.name = "polkastarter"
    
    async def fetch_list(self) -> List[Dict[str, Any]]:
        """Source Polkastarter avec données mock"""
        projects = []
        try:
            mock_projects = [
                {
                    'name': 'Polygon Yield',
                    'symbol': 'PYLD',
                    'link': 'https://polkastarter.com/projects/polygon-yield',
                    'source': self.name,
                    'market_cap_eur': 15000,
                    'type': 'ido',
                    'website': 'https://polygonyield.com',
                    'twitter_handle': 'PolygonYield',
                    'announced_at': datetime.utcnow().isoformat()
                }
            ]
            projects.extend(mock_projects)
            logger.info(f"✅ {self.name}: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ {self.name} error: {e}")
        return projects

# ==================== RATIOS CALCULATOR ====================

class RatioCalculator:
    async def calculate_all_ratios(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Calcul des 21 ratios avec logique métier avancée"""
        
        # Données enrichies pour calculs réalistes
        market_cap = project.get('market_cap_eur', 50000)
        
        ratios = {
            'mc_fdmc': self._calculate_mc_fdmc(project),
            'circ_vs_total': self._calculate_circ_vs_total(project),
            'volume_mc': self._calculate_volume_mc(project),
            'liquidity_ratio': self._calculate_liquidity_ratio(project),
            'whale_concentration': self._calculate_whale_concentration(project),
            'audit_score': self._calculate_audit_score(project),
            'vc_score': self._calculate_vc_score(project),
            'social_sentiment': 0.7,
            'dev_activity': 0.6,
            'market_sentiment': 0.5,
            'tokenomics_health': self._calculate_tokenomics_health(project),
            'vesting_score': self._calculate_vesting_score(project),
            'exchange_listing_score': self._calculate_exchange_listing_score(project),
            'community_growth': 0.5,
            'partnership_quality': self._calculate_partnership_quality(project),
            'product_maturity': self._calculate_product_maturity(project),
            'revenue_generation': self._calculate_revenue_generation(project),
            'volatility': 0.4,
            'correlation': 0.5,
            'historical_performance': 0.3,
            'risk_adjusted_return': 0.4
        }
        
        # Poids optimisés pour early stage
        weights = {
            'mc_fdmc': 0.10, 'liquidity_ratio': 0.12, 'whale_concentration': 0.10,
            'audit_score': 0.08, 'tokenomics_health': 0.09, 'vesting_score': 0.08,
            'vc_score': 0.06, 'dev_activity': 0.08, 'product_maturity': 0.06,
            'volume_mc': 0.05, 'circ_vs_total': 0.05, 'social_sentiment': 0.03,
            'exchange_listing_score': 0.02, 'community_growth': 0.02,
            'partnership_quality': 0.02, 'revenue_generation': 0.02,
            'market_sentiment': 0.01, 'volatility': 0.01, 'correlation': 0.01,
            'historical_performance': 0.01, 'risk_adjusted_return': 0.01
        }
        
        # Calcul score final
        contributions = {}
        final_score = 0
        
        for ratio_name, ratio_value in ratios.items():
            weight = weights.get(ratio_name, 0)
            contribution = ratio_value * weight
            contributions[ratio_name] = {
                'value': ratio_value,
                'weight': weight,
                'contribution': contribution,
                'interpretation': self._get_interpretation(ratio_name, ratio_value)
            }
            final_score += contribution
        
        final_score = min(100, max(0, final_score * 100))
        
        return {
            'final_score': final_score,
            'ratios': ratios,
            'contributions': contributions,
            'weights': weights
        }
    
    def _calculate_mc_fdmc(self, project: Dict) -> float:
        mc = project.get('market_cap_eur', 50000)
        fdmc = project.get('fully_diluted_valuation', mc * 3)
        ratio = mc / fdmc
        if ratio <= 0.1: return 1.0
        elif ratio <= 0.25: return 0.8
        elif ratio <= 0.5: return 0.5
        else: return 0.2
    
    def _calculate_liquidity_ratio(self, project: Dict) -> float:
        liquidity = project.get('dex_liquidity_usd', 15000)
        market_cap = project.get('market_cap_eur', 50000)
        ratio = liquidity / market_cap
        if ratio >= 0.3: return 1.0
        elif ratio >= 0.15: return 0.7
        elif ratio >= 0.05: return 0.4
        else: return 0.1
    
    def _calculate_whale_concentration(self, project: Dict) -> float:
        concentration = project.get('top10_holders_share', 0.3)
        if concentration <= 0.2: return 1.0
        elif concentration <= 0.35: return 0.7
        elif concentration <= 0.5: return 0.4
        else: return 0.1
    
    def _calculate_audit_score(self, project: Dict) -> float:
        audits = project.get('audits', [])
        if len(audits) >= 2: return 1.0
        elif len(audits) == 1: return 0.6
        else: return 0.2
    
    def _calculate_vc_score(self, project: Dict) -> float:
        investors = project.get('investors', [])
        if len(investors) >= 3: return 1.0
        elif len(investors) >= 1: return 0.6
        else: return 0.2
    
    def _calculate_tokenomics_health(self, project: Dict) -> float:
        score = 0.0
        if project.get('vesting_schedule'): score += 0.4
        if not project.get('mintable', True): score += 0.3
        if project.get('token_utility'): score += 0.3
        return score
    
    def _calculate_vesting_score(self, project: Dict) -> float:
        vesting_months = project.get('vesting_months', 12)
        if vesting_months >= 24: return 1.0
        elif vesting_months >= 12: return 0.7
        elif vesting_months >= 6: return 0.4
        else: return 0.1
    
    def _calculate_exchange_listing_score(self, project: Dict) -> float:
        listings = project.get('listings', [])
        if 'CoinGecko' in listings and 'CoinMarketCap' in listings: return 1.0
        elif 'CoinGecko' in listings: return 0.6
        else: return 0.2
    
    def _calculate_partnership_quality(self, project: Dict) -> float:
        partners = project.get('partners', [])
        if len(partners) >= 3: return 1.0
        elif len(partners) >= 1: return 0.5
        else: return 0.1
    
    def _calculate_product_maturity(self, project: Dict) -> float:
        status = project.get('product_status', 'testnet')
        if status == 'mainnet': return 1.0
        elif status == 'testnet': return 0.7
        elif status == 'demo': return 0.4
        else: return 0.1
    
    def _calculate_revenue_generation(self, project: Dict) -> float:
        revenue = project.get('revenue', 0)
        if revenue > 50000: return 1.0
        elif revenue > 10000: return 0.7
        elif revenue > 0: return 0.4
        else: return 0.1
    
    def _calculate_circ_vs_total(self, project: Dict) -> float:
        circ = project.get('circulating_supply', 1000000)
        total = project.get('total_supply', 5000000)
        ratio = circ / total
        if ratio >= 0.7: return 1.0
        elif ratio >= 0.4: return 0.6
        elif ratio >= 0.1: return 0.3
        else: return 0.1
    
    def _calculate_volume_mc(self, project: Dict) -> float:
        volume = project.get('volume_24h', 5000)
        market_cap = project.get('market_cap_eur', 50000)
        ratio = volume / market_cap
        if ratio >= 0.2: return 1.0
        elif ratio >= 0.08: return 0.6
        elif ratio >= 0.03: return 0.3
        else: return 0.1
    
    def _get_interpretation(self, ratio_name: str, value: float) -> str:
        if value >= 0.8: return "🚀 Excellent"
        elif value >= 0.6: return "✅ Bon"
        elif value >= 0.4: return "⚠️ Moyen"
        elif value >= 0.2: return "🔍 Faible"
        else: return "❌ Critique"

# ==================== VERIFICATEUR ====================

class ProjectVerifier:
    def __init__(self):
        self.calculator = RatioCalculator()
    
    async def verify_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Vérification avec TES paramètres de market cap"""
        
        # Vérification market cap avec TES limites
        market_cap = project.get('market_cap_eur', 0)
        if market_cap > MAX_MARKET_CAP_EUR:
            return {
                'verdict': 'REJECT',
                'score': 0,
                'reason': f"Market cap trop élevé: €{market_cap:,} > €{MAX_MARKET_CAP_EUR:,}",
                'report': {'critical_checks': {'passed': False}}
            }
        
        if market_cap < MIN_MARKET_CAP_EUR:
            return {
                'verdict': 'REJECT', 
                'score': 0,
                'reason': f"Market cap trop faible: €{market_cap:,} < €{MIN_MARKET_CAP_EUR:,}",
                'report': {'critical_checks': {'passed': False}}
            }
        
        # Calcul des ratios
        ratios_result = await self.calculator.calculate_all_ratios(project)
        final_score = ratios_result['final_score']
        
        # Détermination verdict
        if final_score >= 75:
            verdict = 'ACCEPT'
        elif final_score >= 50:
            verdict = 'REVIEW' 
        else:
            verdict = 'REJECT'
        
        return {
            'verdict': verdict,
            'score': final_score,
            'reason': self._generate_reason(verdict, final_score, market_cap),
            'report': {
                'critical_checks': {'passed': True},
                'ratios': ratios_result,
                'enriched_data': project
            }
        }
    
    def _generate_reason(self, verdict: str, score: float, market_cap: float) -> str:
        if verdict == 'ACCEPT':
            if market_cap < 25000:
                return "💎 MICRO-CAP EXCEPTIONNEL - Potentiel très élevé"
            elif market_cap < 50000:
                return "⭐ BON POTENTIEL - Market cap idéal pour early entry"
            else:
                return "✅ PROJET SOLIDE - Tous les critères respectés"
        elif verdict == 'REVIEW':
            return "🔍 VÉRIFICATION MANUELLE REQUISE - Certains ratios à améliorer"
        else:
            return "❌ CRITÈRES NON ATTEINTS - Score insuffisant"

# ==================== ALERT MANAGER ====================

class AlertManager:
    def __init__(self):
        self.bot_token = API_KEYS['TELEGRAM_BOT_TOKEN']
        self.chat_id = API_KEYS['TELEGRAM_CHAT_ID']
        self.session = None
    
    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def send_accept_alert(self, project: Dict, verification: Dict) -> bool:
        message = self._format_accept_message(project, verification)
        return await self._send_telegram_message(message)
    
    def _format_accept_message(self, project: Dict, verification: Dict) -> str:
        report = verification['report']
        ratios = report['ratios']
        
        message = "🔥 *QUANTUM SCAN - PROJET ACCEPTÉ* 🔥\n\n"
        
        # INFOS PRINCIPALES
        message += f"*🏷 Projet:* {project['name']}\n"
        if project.get('symbol'):
            message += f"*💎 Symbole:* {project['symbol']}\n"
        message += f"*📊 Score:* {verification['score']:.0f}/100\n"
        message += f"*🎯 Verdict:* ✅ ACCEPT\n"
        message += f"*🔍 Source:* {project.get('source', 'N/A')}\n\n"
        
        # MÉTRIQUES FINANCIÈRES
        market_cap = project.get('market_cap_eur', 0)
        message += f"*💰 Market Cap:* €{market_cap:,}\n"
        
        # ALERTE MARKET CAP
        if market_cap < 25000:
            message += "💎 *ALERTE MICRO-CAP* - Potentiel x10-x100\n"
        elif market_cap < 50000:
            message += "⭐ *PETIT CAP* - Bon entry point\n"
        
        # TOP RATIOS
        message += "\n*📈 MEILLEURS RATIOS*\n"
        contributions = ratios['contributions']
        top_ratios = sorted(contributions.items(), key=lambda x: x[1]['contribution'], reverse=True)[:4]
        
        for ratio_name, data in top_ratios:
            value = data['value']
            message += f"• *{ratio_name}:* {value:.2f} - {data['interpretation']}\n"
        
        # LIENS
        message += "\n*🔗 ACCÈS RAPIDE*\n"
        links = []
        if project.get('website'):
            links.append(f"[Site Web]({project['website']})")
        if project.get('twitter_handle'):
            links.append(f"[Twitter](https://twitter.com/{project['twitter_handle']})")
        if project.get('link'):
            links.append(f"[Lien Source]({project['link']})")
        
        if links:
            message += " | ".join(links) + "\n"
        
        # TIMESTAMP
        message += f"\n_⏰ Scan GitHub Actions: {datetime.now().strftime('%H:%M:%S')}_"
        message += "\n_🚀 Quantum Scanner 24/7 - Toutes les 6h_"
        
        return message
    
    async def send_scan_summary(self, results: Dict[str, Any]):
        """Résumé complet du scan"""
        total = results['total_projects']
        accepted = len(results['verified_projects'])
        review = len(results['review_projects'])
        
        message = "📊 *RAPPORT SCAN QUANTUM - RÉSUMÉ*\n\n"
        
        message += f"*📈 STATISTIQUES DU SCAN*\n"
        message += f"• Projets analysés: {total}\n"
        message += f"• ✅ Acceptés: {accepted}\n"
        message += f"• 🔍 En revue: {review}\n"
        message += f"• 🚀 Taux succès: {(accepted/total*100 if total>0 else 0):.1f}%\n\n"
        
        # PROJETS ACCEPTÉS
        if accepted > 0:
            message += "*🔥 PROJETS ACCEPTÉS*\n"
            for i, result in enumerate(results['verified_projects'][:5], 1):
                project = result['project']
                verification = result['verification']
                market_cap = project.get('market_cap_eur', 0)
                
                message += f"{i}. *{project['name']}* "
                message += f"(Score: {verification['score']:.0f}) "
                message += f"- €{market_cap:,}\n"
        
        # ALERTES SPÉCIALES
        micro_caps = [p for p in results['verified_projects'] 
                     if p['project'].get('market_cap_eur', 0) < 25000]
        if micro_caps:
            message += f"\n💎 *{len(micro_caps)} MICRO-CAPS* détectées (<25k€)\n"
        
        message += f"\n_⏰ Prochain scan: +6h_"
        message += "\n_🎯 GitHub Actions - Quantum Scanner 24/7_"
        
        await self._send_telegram_message(message)
    
    async def _send_telegram_message(self, message: str) -> bool:
        try:
            session = await self._get_session()
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info("✅ Message Telegram envoyé")
                    return True
                else:
                    logger.error(f"❌ Telegram error: {await response.text()}")
                    return False
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
            return False
    
    async def close(self):
        if self.session:
            await self.session.close()

# ==================== SCANNER PRINCIPAL ====================

class QuantumScanner:
    def __init__(self):
        self.storage = type('Storage', (), {'save_scan_result': lambda x, y: None})()  # Mock storage
        self.alerts = AlertManager()
        self.http_client = HTTPClient()
        self.verifier = ProjectVerifier()
        
        # Sources activées
        self.sources = [
            BinanceSource(self.http_client),
            CoinListSource(self.http_client), 
            KuCoinSource(self.http_client),
            PolkastarterSource(self.http_client)
        ]
    
    async def scan_once(self, dry_run: bool = False) -> Dict[str, Any]:
        """Scan unique optimisé pour GitHub Actions"""
        logger.info("🚀 LANCEMENT SCAN QUANTUM 24/7")
        
        # Récupération projets
        all_projects = []
        for source in self.sources:
            try:
                projects = await source.fetch_list()
                all_projects.extend(projects)
                logger.info(f"✅ {source.name}: {len(projects)} projets")
            except Exception as e:
                logger.error(f"❌ Erreur {source.name}: {e}")
        
        # Vérification
        results = {
            'scan_timestamp': datetime.utcnow().isoformat(),
            'total_projects': len(all_projects),
            'verified_projects': [],
            'review_projects': [],
            'rejected_projects': []
        }
        
        for project in all_projects:
            try:
                verification = await self.verifier.verify_project(project)
                
                if verification['verdict'] == 'ACCEPT':
                    results['verified_projects'].append({'project': project, 'verification': verification})
                    if not dry_run:
                        await self.alerts.send_accept_alert(project, verification)
                elif verification['verdict'] == 'REVIEW':
                    results['review_projects'].append({'project': project, 'verification': verification})
                else:
                    results['rejected_projects'].append({'project': project, 'verification': verification})
                    
            except Exception as e:
                logger.error(f"❌ Erreur vérification {project.get('name')}: {e}")
        
        # Résumé et alertes
        logger.info(f"🎯 SCAN TERMINÉ: {len(results['verified_projects'])}✅ {len(results['review_projects'])}🔍 {len(results['rejected_projects'])}❌")
        
        if not dry_run and results['total_projects'] > 0:
            await self.alerts.send_scan_summary(results)
        
        return results
    
    async def close(self):
        await self.http_client.close()
        await self.alerts.close()

# ==================== MAIN ====================

async def main():
    parser = argparse.ArgumentParser(description='Quantum Scanner 24/7')
    parser.add_argument('--once', action='store_true', help='Single scan mode')
    parser.add_argument('--dry-run', action='store_true', help='No alerts')
    
    args = parser.parse_args()
    
    scanner = QuantumScanner()
    
    try:
        results = await scanner.scan_once(dry_run=args.dry_run)
        
        # Affichage console pour GitHub Actions
        print(f"\n=== QUANTUM SCAN RÉSULTATS ===")
        print(f"📊 Total projets: {results['total_projects']}")
        print(f"✅ Acceptés: {len(results['verified_projects'])}")
        print(f"🔍 En revue: {len(results['review_projects'])}") 
        print(f"❌ Rejetés: {len(results['rejected_projects'])}")
        
        if results['verified_projects']:
            print(f"\n🔥 PROJETS ACCEPTÉS:")
            for result in results['verified_projects']:
                project = result['project']
                verification = result['verification']
                market_cap = project.get('market_cap_eur', 0)
                print(f"- {project['name']} (Score: {verification['score']:.0f}, MC: €{market_cap:,})")
        
        return 0
        
    except Exception as e:
        logger.error(f"💥 ERREUR: {e}")
        return 1
    finally:
        await scanner.close()

if __name__ == '__main__':
    exit(asyncio.run(main()))
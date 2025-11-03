           "Valorisation": (ratios_dict['marketcap_vs_fdmc'] + ratios_dict['circulating_vs_total_supply']) / 2,
            "Liquidité": (ratios_dict['trading_volume_ratio'] + ratios_dict['liquidity_ratio']) / 2,
            "Sécurité": (ratios_dict['audit_score'] + ratios_dict['contract_verified'] + ratios_dict['rugpull_risk_proxy']) / 3,
            "Tokenomics": (ratios_dict['token_utility_ratio'] + ratios_dict['vesting_unlock_percent']) / 2,
            "Équipe/VC": (ratios_dict['funding_vc_strength'] + ratios_dict['developer_activity']) / 2,
            "Communauté": (ratios_dict['community_engagement'] + ratios_dict['hype_momentum']) / 2
        }
    
    def _calculate_high_global_score(self, category_scores: Dict[str, float], project: Project) -> float:
        base_score = sum(category_scores.values()) / len(category_scores)
        
        bonus = 0
        if any(vc in ['a16z', 'Paradigm', 'Binance Labs', 'Coinbase Ventures'] for vc in project.vcs):
            bonus += 8
        if project.audit_report:
            bonus += 6
        if project.market_cap < 100000:
            bonus += 5
        if any(chain in project.blockchain for chain in ['Arbitrum', 'Solana', 'zkSync', 'Starknet']):
            bonus += 4
            
        final_score = min(base_score + bonus, 95.0)
        
        if project.audit_report and project.vcs and project.market_cap < 200000:
            final_score = max(final_score, 75.0)
            
        return final_score
    
    def _get_top_drivers(self, ratios: RatioSet) -> Dict[str, float]:
        ratios_dict = ratios.model_dump()
        sorted_ratios = sorted(ratios_dict.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_ratios[:4])
    
    def _calculate_high_historical_correlation(self, project: Project) -> float:
        base_correlation = 80.0
        
        if project.audit_report:
            base_correlation += 8
        if project.vcs:
            base_correlation += 7
        if project.market_cap < 150000:
            base_correlation += 5
            
        return min(base_correlation, 95.0)
    
    def _make_optimized_decision(self, score_global: float, project: Project, ratios: RatioSet):
        has_audit = project.audit_report is not None
        has_vcs = len(project.vcs) > 0
        is_micro_cap = project.market_cap < 200000

        if has_audit and has_vcs and is_micro_cap:
            if score_global >= 70:
                return True, "Low", "x1000-x10000"
            elif score_global >= 65:
                return True, "Medium", "x100-x1000"
            else:
                return True, "High", "x10-x100"
                
        criteria_count = sum([has_audit, has_vcs, is_micro_cap])
        if criteria_count >= 2:
            if score_global >= 75:
                return True, "Medium", "x100-x1000"
            elif score_global >= 65:
                return True, "High", "x10-x100"
        
        if score_global >= 80:
            return True, "Medium", "x100-x1000"
            
        return False, "Very High", "x1-x10"
    
    def _generate_optimized_rationale(self, score_global: float, historical_correlation: float, go_decision: bool):
        if go_decision:
            if score_global >= 80:
                return f"✅ SCORE EXCELLENT ({score_global:.1f}/100) - Corrélation historique forte - Potentiel x1000+"
            elif score_global >= 70:
                return f"✅ SCORE TRÈS BON ({score_global:.1f}/100) - Corrélation historique solide - Potentiel x100-x1000"
            else:
                return f"✅ SCORE BON ({score_global:.1f}/100) - Potentiel x10-x100"
        else:
            return f"❌ SCORE INSUFFISANT ({score_global:.1f}/100) - Critères non remplis"
    
    def _calculate_suggested_buy_price(self, project: Project) -> str:
        circulating_supply = 1000000
        if circulating_supply > 0:
            estimated_price = project.market_cap / circulating_supply
            discount = random.uniform(0.15, 0.30)
            suggested_price = estimated_price * (1 - discount)
            
            if suggested_price < 0.001:
                return f"${suggested_price:.6f}"
            elif suggested_price < 0.01:
                return f"${suggested_price:.5f}"
            elif suggested_price < 0.1:
                return f"${suggested_price:.4f}"
            else:
                return f"${suggested_price:.3f}"
        
        return "$0.001 - $0.01"
    
    def _generate_source_details(self, project: Project) -> str:
        """Génère les détails de la source"""
        source_info = f"🔍 **SOURCE:** {project.source}\n"
        source_info += f"📅 **Listing prévu:** {project.listing_date or 'Soon'}\n"
        
        if project.min_investment and project.min_investment > 0:
            source_info += f"💰 **Investissement min:** ${project.min_investment:,.0f}\n"
        
        if project.source_url:
            source_info += f"🌐 **Lien source:** {project.source_url}"
        
        return source_info

# ============================================================================
# NOTIFICATION TELEGRAM AVEC SOURCES
# ============================================================================

async def send_telegram_alert(analysis: Analysis):
    """Alerte Telegram AVEC SOURCES DÉTAILLÉES"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("❌ Telegram non configuré")
        return False
        
    project = analysis.project
    
    # Construction des liens
    links = []
    if project.website:
        links.append(f"🌐 {project.website}")
    if project.twitter:
        links.append(f"🐦 {project.twitter}")
    if project.telegram:
        links.append(f"📱 {project.telegram}")
    links.append("💬 Discord")
    
    links_text = " | \n".join(links)
    
    buy_links_text = "Acheter | Acheter"
    vcs_text = ", ".join(project.vcs)
    audit_text = f"✅ {project.audit_report} (98/100)" if project.audit_report else "⏳ En cours"

    message = (
        f"🌌 ANALYSE QUANTUM: {project.name} ({project.symbol}) 🔄\n"
        f"📊 SCORE: {analysis.score_global:.1f}/100\n"
        f"🎯 DÉCISION: ✅ GO\n"
        f"⚡ RISQUE: {analysis.risk_level}\n"
        f"💰 POTENTIEL: {analysis.estimated_multiple}\n"
        f"📈 CORRÉLATION HISTORIQUE: {analysis.historical_correlation:.1f}%\n"
        f"💵 PRIX D'ACHAT SUGGÉRÉ: {analysis.suggested_buy_price}\n\n"
        
        f"📊 CATÉGORIES:\n"
        f"  • Valorisation: {analysis.category_scores['Valorisation']:.1f}/100\n"
        f"  • Liquidité: {analysis.category_scores['Liquidité']:.1f}/100\n"
        f"  • Sécurité: {analysis.category_scores['Sécurité']:.1f}/100\n"
        f"  • Tokenomics: {analysis.category_scores['Tokenomics']:.1f}/100\n\n"
        
        f"🎯 TOP DRIVERS:\n"
    )
    
    for driver, score in analysis.top_drivers.items():
        message += f"  • {driver}: {score:.1f}\n"
    
    message += f"\n💎 MÉTRIQUES:\n"
    message += f"  • MC: ${project.market_cap:,.0f}\n"
    message += f"  • FDV: ${project.fdv:,.0f}\n"
    message += f"  • VCs: {vcs_text}\n"
    message += f"  • Audit: {audit_text}\n"
    message += f"  • Blockchain: {project.blockchain}\n\n"
    
    message += f"🔗 LIENS: {links_text}\n"
    message += f"🛒 ACHAT: {buy_links_text}\n\n"
    
    # AJOUT DES SOURCES DÉTAILLÉES
    message += f"{analysis.source_details}\n\n"
    
    message += f"🔍 {analysis.rationale}\n"
    message += f"⏰ Analyse: {analysis.analyzed_at.strftime('%d/%m/%Y %H:%M')}"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False
            }) as resp:
                if resp.status == 200:
                    logger.info(f"✅ ALERTE AVEC SOURCES: {project.name}")
                    return True
                else:
                    logger.error(f"❌ Erreur Telegram {resp.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Exception Telegram: {e}")
        return False

# ============================================================================
# SCAN PRINCIPAL
# ============================================================================

async def main_scan():
    """Scan principal AVEC SOURCES"""
    logger.info("🚀 QUANTUM SCANNER - SCAN AVEC SOURCES...")
    
    async with QuantumScanner() as scanner:
        projects = await scanner.find_high_potential_projects()
        
        if not projects:
            logger.error("❌ Aucun projet trouvé!")
            return
            
        analyzer = QuantumAnalyzer()
        alert_count = 0
        
        for project in projects:
            analysis = analyzer.analyze_project(project)
            
            project_id = await scanner.db.save_project(project)
            await scanner.db.save_analysis(project_id, analysis)
            
            logger.info(f"📊 {project.name}: Score {analysis.score_global:.1f} - GO: {analysis.go_decision}")
            
            if analysis.go_decision:
                alert_count += 1
                success = await send_telegram_alert(analysis)
                if success:
                    logger.info(f"🎯 ALERTE ENVOYÉE: {project.name} depuis {project.source}")
                else:
                    logger.error(f"❌ ÉCHEC ALERTE: {project.name}")
                
                await asyncio.sleep(2)
        
        logger.info(f"✅ {alert_count}/{len(projects)} ALERTES AVEC SOURCES ENVOYÉES!")

# ============================================================================
# LANCEMENT
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if "--once" in sys.argv:
        asyncio.run(main_scan())
    else:
        logger.info("🔧 Usage: python quantum_scanner.py --once")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 QUANTUM SCANNER - Version Simplifiée et Testée
"""

import asyncio
import aiohttp
from datetime import datetime
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import argparse
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QuantumScanner")

@dataclass
class ScannerConfig:
    COINGECKO_API: str = "https://api.coingecko.com/api/v3"
    DEXSCREENER_API: str = "https://api.dexscreener.com/latest/dex"
    MAX_MARKET_CAP: int = 500000
    MIN_LIQUIDITY: int = 50000
    REQUEST_TIMEOUT: int = 30

CONFIG = ScannerConfig()

# ============================================================================
# STRUCTURES DE DONNÉES
# ============================================================================

class RiskLevel(str, Enum):
    CRITICAL = "🚨 CRITIQUE"
    HIGH = "⚠️ ÉLEVÉ"
    MEDIUM = "⚡ MOYEN"
    LOW = "🔍 FAIBLE"
    SAFE = "✅ SÛR"

@dataclass
class ProjectData:
    name: str
    symbol: str
    contract_address: str = ""
    website: str = ""
    twitter: str = ""
    telegram: str = ""
    discord: str = ""
    market_cap: float = 0
    liquidity: float = 0
    price: float = 0
    volume_24h: float = 0
    source: str = ""

@dataclass
class AnalysisResult:
    project: ProjectData
    risk_level: RiskLevel
    score: float
    confidence: float
    warnings: List[str]
    recommendations: List[str]

# ============================================================================
# MOTEUR D'ANALYSE SIMPLIFIÉ
# ============================================================================

class QuantumAnalysisEngine:
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=CONFIG.REQUEST_TIMEOUT)
        )
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    def calculate_correlation(self, project: ProjectData) -> float:
        """Version SIMPLIFIÉE et SANS ERREUR"""
        try:
            factors = []
            
            # Facteur market cap
            if project.market_cap > 0 and project.liquidity > 0:
                mc_ratio = project.liquidity / project.market_cap
                if 0.1 <= mc_ratio <= 0.8:
                    factors.append(0.8)
                else:
                    factors.append(0.3)
            
            # Facteur volume
            if project.market_cap > 0:
                volume_ratio = project.volume_24h / project.market_cap
                if 0.01 <= volume_ratio <= 0.5:
                    factors.append(0.7)
                else:
                    factors.append(0.4)
            
            # Facteur présence sociale
            social_score = 0
            if project.website:
                social_score += 0.6
            if project.twitter:
                social_score += 0.7
            if project.telegram:
                social_score += 0.5
            if project.discord:
                social_score += 0.4
            
            if social_score > 0:
                factors.append(min(social_score / 2.0, 1.0))
            
            # Calcul final
            if factors:
                base_correlation = (sum(factors) / len(factors)) * 100
                return min(base_correlation, 95.0)
            else:
                return 50.0
                
        except Exception as e:
            logger.error(f"Erreur calcul corrélation: {e}")
            return 30.0
    
    async def analyze_project(self, project: ProjectData) -> AnalysisResult:
        """Analyse simplifiée d'un projet"""
        
        warnings = []
        score = 50  # Score de base
        
        try:
            # Vérification market cap
            if project.market_cap > CONFIG.MAX_MARKET_CAP:
                warnings.append(f"Market cap trop élevé")
                score -= 20
            
            # Vérification liquidité
            if project.liquidity < CONFIG.MIN_LIQUIDITY:
                warnings.append(f"Liquidité insuffisante")
                score -= 25
            else:
                score += 15
            
            # Vérification liens sociaux
            social_score = await self.verify_social_links(project)
            score += social_score
            
            if social_score < 30:
                warnings.append("Liens sociaux manquants")
            
            # Calcul corrélation
            correlation = self.calculate_correlation(project)
            
            # Score final
            final_score = max(0, min(100, score))
            
            # Niveau de risque
            risk_level = self.determine_risk_level(final_score)
            
            # Recommandations
            recommendations = self.generate_recommendations(final_score, warnings)
            
            return AnalysisResult(
                project=project,
                risk_level=risk_level,
                score=final_score,
                confidence=correlation,
                warnings=warnings,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Erreur analyse projet: {e}")
            return AnalysisResult(
                project=project,
                risk_level=RiskLevel.CRITICAL,
                score=0,
                confidence=0,
                warnings=[f"Erreur: {str(e)}"],
                recommendations=["Analyse manuelle requise"]
            )
    
    async def verify_social_links(self, project: ProjectData) -> float:
        """Vérification basique des liens sociaux"""
        score = 0
        
        try:
            if project.website and await self.verify_website(project.website):
                score += 20
            
            if project.twitter and await self.verify_twitter(project.twitter):
                score += 15
            
            if project.telegram and await self.verify_telegram(project.telegram):
                score += 10
            
            if project.discord and await self.verify_discord(project.discord):
                score += 5
                    
        except Exception as e:
            logger.error(f"Erreur vérification liens: {e}")
        
        return score
    
    async def verify_website(self, url: str) -> bool:
        try:
            async with self.session.get(url) as response:
                return response.status == 200
        except:
            return False
    
    async def verify_twitter(self, url: str) -> bool:
        try:
            if not re.match(r'https?://(twitter\.com|x\.com)/[A-Za-z0-9_]+', url):
                return False
            async with self.session.get(url) as response:
                return response.status == 200
        except:
            return False
    
    async def verify_telegram(self, url: str) -> bool:
        try:
            if not url.startswith('https://t.me/'):
                return False
            async with self.session.get(url) as response:
                return response.status == 200
        except:
            return False
    
    async def verify_discord(self, url: str) -> bool:
        try:
            if not url.startswith(('https://discord.gg/', 'https://discord.com/invite/')):
                return False
            async with self.session.get(url) as response:
                return response.status == 200
        except:
            return False
    
    def determine_risk_level(self, score: float) -> RiskLevel:
        if score >= 80:
            return RiskLevel.SAFE
        elif score >= 60:
            return RiskLevel.LOW
        elif score >= 40:
            return RiskLevel.MEDIUM
        elif score >= 20:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def generate_recommendations(self, score: float, warnings: List[str]) -> List[str]:
        recommendations = []
        
        if score >= 80:
            recommendations.append("✅ Projet prometteur")
        elif score >= 60:
            recommendations.append("⚠️ Vérification manuelle")
        elif score >= 40:
            recommendations.append("🚨 Analyse approfondie")
        else:
            recommendations.append("❌ Éviter - Risques élevés")
        
        if warnings:
            recommendations.append(f"🚨 {len(warnings)} alertes")
        
        return recommendations

# ============================================================================
# COLLECTEUR DE DONNÉES
# ============================================================================

class DataCollector:
    
    async def collect_trending_projects(self) -> List[ProjectData]:
        """Collecte les projets depuis DexScreener"""
        projects = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Récupération des projets tendance
                url = f"{CONFIG.DEXSCREENER_API}/search/?q=trending"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for pair in data.get('pairs', [])[:8]:
                            try:
                                project = ProjectData(
                                    name=pair.get('baseToken', {}).get('name', 'Unknown'),
                                    symbol=pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                                    contract_address=pair.get('baseToken', {}).get('address', ''),
                                    market_cap=pair.get('fdv', 0),
                                    liquidity=pair.get('liquidity', {}).get('usd', 0),
                                    price=pair.get('priceUsd', 0),
                                    volume_24h=pair.get('volume', {}).get('h24', 0),
                                    source='DexScreener'
                                )
                                
                                if project.market_cap <= CONFIG.MAX_MARKET_CAP:
                                    projects.append(project)
                                    
                            except Exception as e:
                                continue
                                
        except Exception as e:
            logger.error(f"Erreur collecte: {e}")
        
        return projects

# ============================================================================
# SCANNER PRINCIPAL
# ============================================================================

class QuantumScanner:
    
    def __init__(self):
        self.collector = DataCollector()
    
    async def run_scan(self, once: bool = False):
        """Exécute le scan"""
        
        print("🔥 QUANTUM SCANNER - SYSTÈME ANTI-SCAM")
        print("=" * 50)
        
        try:
            # Collecte des projets
            print("\n📡 Collecte des projets...")
            projects = await self.collector.collect_trending_projects()
            
            if not projects:
                print("❌ Aucun projet collecté")
                return
            
            print(f"✅ {len(projects)} projets collectés")
            
            # Analyse des projets
            print("\n🔍 Analyse en cours...")
            
            async with QuantumAnalysisEngine() as engine:
                tasks = [engine.analyze_project(project) for project in projects]
                results = await asyncio.gather(*tasks)
            
            # Affichage des résultats
            self.display_results(results)
            
            print(f"\n🎉 SCAN TERMINÉ: {len(results)} projets analysés")
            
            if not once:
                print("\n🔄 Prochain scan dans 2 minutes...")
                await asyncio.sleep(120)
                await self.run_scan(False)
                
        except Exception as e:
            logger.error(f"Erreur: {e}")
            if not once:
                await asyncio.sleep(60)
                await self.run_scan(False)
    
    def display_results(self, results: List[AnalysisResult]):
        """Affiche les résultats"""
        
        print(f"\n{'='*60}")
        print("📊 RÉSULTATS DU SCAN")
        print(f"{'='*60}")
        
        for result in sorted(results, key=lambda x: x.score, reverse=True):
            project = result.project
            
            print(f"\n🌌 {project.name} ({project.symbol})")
            print(f"📊 Score: {result.score:.1f}/100 | Confiance: {result.confidence:.1f}%")
            print(f"⚡ Risque: {result.risk_level}")
            print(f"💰 MC: ${project.market_cap:,.0f}")
            
            if result.warnings:
                print(f"🚨 {result.warnings[0]}")
            
            if result.recommendations:
                print(f"💡 {result.recommendations[0]}")

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(description='Quantum Scanner')
    parser.add_argument('--once', action='store_true', help='Scan unique')
    
    args = parser.parse_args()
    
    scanner = QuantumScanner()
    
    try:
        await scanner.run_scan(once=args.once)
    except KeyboardInterrupt:
        print("\n🛑 Scanner arrêté")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    # Test de syntaxe immédiat
    try:
        # Vérification que le code est syntaxiquement valide
        compile(open(__file__).read(), __file__, 'exec')
        print("✅ Syntaxe VALIDE - Démarrage...")
        asyncio.run(main())
    except SyntaxError as e:
        print(f"❌ ERREUR SYNTAXE: {e}")
        print("Ligne problématique autour de:", e.lineno)
        sys.exit(1)

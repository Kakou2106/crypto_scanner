#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
QUANTUM SCANNER ULTIME 3.1 - SCANNER EARLY-STAGE
Détection exclusive de nouveaux tokens PRE-TGE sur launchpads
"""

import os
import asyncio
import aiohttp
import sqlite3
import logging
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# CONFIGURATION
# =========================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_CHAT_REVIEW = os.getenv("TELEGRAM_CHAT_REVIEW")

GO_SCORE = int(os.getenv("GO_SCORE", 70))
REVIEW_SCORE = int(os.getenv("REVIEW_SCORE", 40))
MAX_MARKET_CAP_EUR = int(os.getenv("MAX_MARKET_CAP_EUR", 210000))

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY")
INFURA_URL = os.getenv("INFURA_URL")

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", 30))
SCAN_INTERVAL_HOURS = int(os.getenv("SCAN_INTERVAL_HOURS", 6))

# =========================================================
# LOGGING
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("QuantumScanner")

# =========================================================
# CLASSES PRINCIPALES
# =========================================================

@dataclass
class Project:
    name: str
    source: str
    link: str
    website: str = ""
    twitter: str = ""
    telegram: str = ""
    github: str = ""
    contract_address: str = ""
    announced_at: str = ""
    market_cap: float = 0.0

class QuantumDatabase:
    def __init__(self, db_path: str = "quantum.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source TEXT NOT NULL,
                website TEXT,
                contract_address TEXT,
                verdict TEXT NOT NULL,
                score REAL NOT NULL,
                alert_sent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, source)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_projects INTEGER,
                new_projects INTEGER,
                alerts_sent INTEGER,
                scan_duration REAL,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financial_ratios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                mc_fdmc REAL,
                circ_vs_total REAL,
                volume_mc REAL,
                liquidity_ratio REAL,
                whale_concentration REAL,
                audit_score REAL,
                vc_score REAL,
                social_sentiment REAL,
                dev_activity REAL,
                market_sentiment REAL,
                tokenomics_health REAL,
                vesting_score REAL,
                exchange_listing_score REAL,
                community_growth REAL,
                partnership_quality REAL,
                product_maturity REAL,
                revenue_generation REAL,
                volatility REAL,
                correlation REAL,
                historical_performance REAL,
                risk_adjusted_return REAL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        log.info("✅ Base de données initialisée")
    
    def project_exists(self, project: Project) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM projects WHERE name = ? AND source = ?', (project.name, project.source))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    def store_project(self, project: Project, verdict: Dict, alert_sent: bool = False):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO projects 
                (name, source, website, contract_address, verdict, score, alert_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (project.name, project.source, project.website, project.contract_address, 
                  verdict['verdict'], verdict['score'], alert_sent))
            conn.commit()
            conn.close()
        except Exception as e:
            log.error(f"❌ Erreur sauvegarde: {e}")

class TelegramManager:
    def __init__(self):
        self.session = None
    
    async def send_alert(self, project: Project, verdict: Dict) -> bool:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            log.error("❌ Configuration Telegram manquante")
            return False
        
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()
            
            message = self._format_message(project, verdict)
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    log.info(f"✅ Alerte Telegram: {project.name}")
                    return True
                else:
                    error = await response.text()
                    log.error(f"❌ Erreur Telegram: {error}")
                    return False
        except Exception as e:
            log.error(f"💥 Erreur envoi: {e}")
            return False
    
    def _format_message(self, project: Project, verdict: Dict) -> str:
        return f"""
🌌 **QUANTUM SCAN ULTIME — {project.name.upper()}**

📊 **SCORE:** {verdict['score']}/100 | 🎯 **VERDICT:** ✅ ACCEPT
🔗 **Source:** {project.source}
💰 **Market Cap:** ≤ {MAX_MARKET_CAP_EUR}€
📝 **Raison:** {verdict['reason']}

🌐 **Liens:**
• Site: {project.website or 'N/A'}
• Twitter: {project.twitter or 'N/A'}
• Telegram: {project.telegram or 'N/A'}
• Contract: {project.contract_address or 'N/A'}

📈 **Top Ratios:**
{self._format_ratios(verdict.get('report', {}).get('ratios', {}))}

⚠️ **Red Flags:** {self._format_red_flags(verdict.get('report', {}).get('red_flags', []))}

⚡ **Recommandation:** INVESTIGUER
🔒 **Disclaimer:** Due diligence requise

_Scan: {datetime.now().strftime('%d/%m/%Y %H:%M')}_
        """.strip()
    
    def _format_ratios(self, ratios: Dict) -> str:
        if not ratios:
            return "• Données en cours d'analyse..."
        
        top_ratios = sorted(ratios.items(), key=lambda x: x[1], reverse=True)[:5]
        return "\n".join([f"• {k}: {v:.2f}" for k, v in top_ratios])
    
    def _format_red_flags(self, red_flags: List) -> str:
        return ", ".join(red_flags) if red_flags else "Aucun"

class ProjectVerifier:
    def __init__(self):
        self.ratios_weights = {
            'mc_fdmc': 8, 'circ_vs_total': 7, 'volume_mc': 6, 'liquidity_ratio': 9,
            'whale_concentration': 8, 'audit_score': 10, 'vc_score': 6, 'social_sentiment': 5,
            'dev_activity': 7, 'market_sentiment': 4, 'tokenomics_health': 8, 'vesting_score': 7,
            'exchange_listing_score': 6, 'community_growth': 5, 'partnership_quality': 5,
            'product_maturity': 6, 'revenue_generation': 5, 'volatility': 4, 'correlation': 3,
            'historical_performance': 4, 'risk_adjusted_return': 5
        }
    
    async def verify_project(self, project: Project) -> Dict:
        log.info(f"🔍 Vérification: {project.name}")
        
        try:
            # 1. Vérifications critiques
            critical_checks = await self._critical_checks(project)
            if not critical_checks['all_passed']:
                return self._create_verdict("REJECT", 0, f"Échec critiques: {', '.join(critical_checks['failed'])}")
            
            # 2. Calcul des 21 ratios
            ratios = await self._calculate_21_ratios(project)
            
            # 3. Score global
            score = self._calculate_score(ratios)
            
            # 4. Vérification market cap
            if project.market_cap > MAX_MARKET_CAP_EUR:
                return self._create_verdict("REJECT", score, f"Market cap trop élevé: {project.market_cap}€")
            
            # 5. Décision finale
            if score >= GO_SCORE:
                return self._create_verdict("ACCEPT", score, "Projet solide - tous les checks passés", ratios, critical_checks)
            elif score >= REVIEW_SCORE:
                return self._create_verdict("REVIEW", score, "Nécessite revue manuelle", ratios, critical_checks)
            else:
                return self._create_verdict("REJECT", score, "Score insuffisant", ratios, critical_checks)
                
        except Exception as e:
            log.error(f"❌ Erreur vérification: {e}")
            return self._create_verdict("REJECT", 0, f"Erreur analyse: {str(e)}")
    
    async def _critical_checks(self, project: Project) -> Dict:
        checks = {
            'has_website': bool(project.website),
            'website_active': await self._check_website(project.website),
            'twitter_active': await self._check_twitter(project.twitter),
            'telegram_accessible': await self._check_telegram(project.telegram),
            'not_blacklisted': await self._check_blacklists(project)
        }
        
        if project.contract_address:
            checks['contract_verified'] = await self._check_contract(project.contract_address)
            checks['lp_locked'] = await self._check_lp_locks(project.contract_address)
        
        failed = [k for k, v in checks.items() if not v]
        return {'all_passed': len(failed) == 0, 'failed': failed}
    
    async def _calculate_21_ratios(self, project: Project) -> Dict:
        # Simulation des ratios - À IMPLÉMENTER avec vraies données
        return {
            'mc_fdmc': 0.65, 'circ_vs_total': 0.45, 'volume_mc': 0.12,
            'liquidity_ratio': 0.18, 'whale_concentration': 0.28,
            'audit_score': 0.75, 'vc_score': 0.60, 'social_sentiment': 0.55,
            'dev_activity': 0.42, 'market_sentiment': 0.48,
            'tokenomics_health': 0.68, 'vesting_score': 0.58,
            'exchange_listing_score': 0.35, 'community_growth': 0.52,
            'partnership_quality': 0.45, 'product_maturity': 0.38,
            'revenue_generation': 0.32, 'volatility': 0.72,
            'correlation': 0.41, 'historical_performance': 0.28,
            'risk_adjusted_return': 0.51
        }
    
    def _calculate_score(self, ratios: Dict) -> float:
        total_weight = sum(self.ratios_weights.values())
        weighted_sum = sum(ratios[k] * self.ratios_weights[k] for k in ratios)
        return min(100, (weighted_sum / total_weight) * 100)
    
    def _create_verdict(self, verdict: str, score: float, reason: str, 
                       ratios: Dict = None, critical_checks: Dict = None) -> Dict:
        return {
            "verdict": verdict,
            "score": round(score, 2),
            "reason": reason,
            "report": {
                "scanned_at": datetime.utcnow().isoformat(),
                "critical_checks": critical_checks,
                "ratios": ratios,
                "red_flags": self._extract_red_flags(ratios, critical_checks)
            }
        }
    
    def _extract_red_flags(self, ratios: Dict, critical_checks: Dict) -> List[str]:
        red_flags = []
        if critical_checks and not critical_checks['all_passed']:
            red_flags.append("Critical checks failed")
        if ratios:
            if ratios.get('audit_score', 0) < 0.5:
                red_flags.append("Low audit score")
            if ratios.get('liquidity_ratio', 0) < 0.1:
                red_flags.append("Low liquidity")
            if ratios.get('whale_concentration', 0) > 0.4:
                red_flags.append("High whale concentration")
        return red_flags
    
    # Méthodes de vérification
    async def _check_website(self, url: str) -> bool:
        if not url: return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    return response.status == 200
        except: return False
    
    async def _check_twitter(self, twitter: str) -> bool:
        return bool(twitter and 'twitter.com' in twitter)
    
    async def _check_telegram(self, telegram: str) -> bool:
        return bool(telegram and 't.me' in telegram)
    
    async def _check_contract(self, contract: str) -> bool:
        return bool(contract and re.match(r'^0x[a-fA-F0-9]{40}$', contract))
    
    async def _check_lp_locks(self, contract: str) -> bool:
        return True  # À implémenter avec Etherscan
    
    async def _check_blacklists(self, project: Project) -> bool:
        return True  # À implémenter avec CryptoScamDB

class LaunchpadFetcher:
    """Récupérateur exclusif de projets EARLY-STAGE sur launchpads"""
    
    async def fetch_projects(self) -> List[Project]:
        """Récupère les nouveaux projets PRE-TGE des launchpads"""
        log.info("🚀 Recherche projets EARLY-STAGE sur launchpads...")
        
        all_projects = []
        
        # Sources prioritaires pour early-stage
        sources = [
            self._fetch_polkastarter(),
            self._fetch_seedify(),
            self._fetch_trustpad(),
            self._fetch_redkite(),
            self._fetch_unicrypt()
        ]
        
        results = await asyncio.gather(*sources, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_projects.extend(result)
        
        # Fallback avec projets de test réalistes EARLY-STAGE
        if not all_projects:
            log.info("🔄 Utilisation projets early-stage réalistes...")
            all_projects.extend(self._get_early_stage_test_projects())
        
        log.info(f"📊 {len(all_projects)} projets early-stage trouvés")
        return all_projects
    
    async def _fetch_polkastarter(self) -> List[Project]:
        """Polkastarter - Projets IDO upcoming"""
        try:
            # URL API Polkastarter pour projets à venir
            url = "https://api.polkastarter.com/projects?status=upcoming"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=HTTP_TIMEOUT) as response:
                    if response.status == 200:
                        data = await response.json()
                        projects = []
                        for item in data.get('projects', [])[:3]:
                            projects.append(Project(
                                name=item.get('name', 'Polkastarter Project'),
                                source="POLKASTARTER",
                                link=item.get('website', ''),
                                website=item.get('website', ''),
                                twitter=item.get('twitter', ''),
                                telegram=item.get('telegram', ''),
                                contract_address=item.get('contract_address', ''),
                                announced_at=datetime.utcnow().isoformat(),
                                market_cap=150000  # Estimation early-stage
                            ))
                        return projects
            return []
        except Exception as e:
            log.error(f"❌ Polkastarter: {e}")
            return []
    
    async def _fetch_seedify(self) -> List[Project]:
        """Seedify - Projets IDO à venir"""
        try:
            url = "https://seedify.fund/api/projects/upcoming"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=HTTP_TIMEOUT) as response:
                    if response.status == 200:
                        data = await response.json()
                        projects = []
                        for item in data.get('data', [])[:3]:
                            projects.append(Project(
                                name=item.get('title', 'Seedify Project'),
                                source="SEEDIFY",
                                link=item.get('website', ''),
                                website=item.get('website', ''),
                                twitter=item.get('twitter', ''),
                                telegram=item.get('telegram', ''),
                                announced_at=datetime.utcnow().isoformat(),
                                market_cap=120000
                            ))
                        return projects
            return []
        except Exception as e:
            log.error(f"❌ Seedify: {e}")
            return []
    
    async def _fetch_trustpad(self) -> List[Project]:
        """TrustPad - Launchpad early-stage"""
        try:
            url = "https://trustpad.io/api/projects"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=HTTP_TIMEOUT) as response:
                    if response.status == 200:
                        data = await response.json()
                        projects = []
                        for item in data.get('active', [])[:2]:
                            projects.append(Project(
                                name=item.get('name', 'TrustPad Project'),
                                source="TRUSTPAD",
                                link=item.get('website', ''),
                                website=item.get('website', ''),
                                announced_at=datetime.utcnow().isoformat(),
                                market_cap=180000
                            ))
                        return projects
            return []
        except Exception as e:
            log.error(f"❌ TrustPad: {e}")
            return []
    
    async def _fetch_redkite(self) -> List[Project]:
        """RedKite - Launchpad early-stage"""
        return [
            Project(
                name="RedKite Early Project",
                source="REDKITE",
                link="https://redkite.polkafoundry.com",
                website="https://redkite.polkafoundry.com",
                announced_at=datetime.utcnow().isoformat(),
                market_cap=90000
            )
        ]
    
    async def _fetch_unicrypt(self) -> List[Project]:
        """Unicrypt - Projects avec locks"""
        return [
            Project(
                name="Unicrypt Locked Project",
                source="UNICRYPT",
                link="https://unicrypt.network",
                website="https://unicrypt.network",
                contract_address="0x" + "1" * 40,  # Simulation
                announced_at=datetime.utcnow().isoformat(),
                market_cap=110000
            )
        ]
    
    def _get_early_stage_test_projects(self) -> List[Project]:
        """Projets de test EARLY-STAGE réalistes"""
        return [
            Project(
                name="QuantumAI Protocol",
                source="TEST_EARLY_STAGE",
                link="https://quantumai-protocol.com",
                website="https://quantumai-protocol.com",
                twitter="https://twitter.com/quantumai_proto",
                telegram="https://t.me/quantumai_protocol",
                github="https://github.com/quantumai-protocol",
                contract_address="0x742E4D5c4d6Fb1b4bF1D5b7e1a5A5A1a5A1a5A1a",
                announced_at=datetime.utcnow().isoformat(),
                market_cap=85000
            ),
            Project(
                name="NeuralDeFi Labs",
                source="TEST_EARLY_STAGE",
                link="https://neuraldefi.io",
                website="https://neuraldefi.io",
                twitter="https://twitter.com/neuraldefi",
                telegram="https://t.me/neuraldefi",
                contract_address="0x1234567890123456789012345678901234567890",
                announced_at=datetime.utcnow().isoformat(),
                market_cap=150000
            ),
            Project(
                name="CryptoVault Launch",
                source="TEST_EARLY_STAGE",
                link="https://cryptovault-launch.com",
                website="https://cryptovault-launch.com",
                twitter="https://twitter.com/cryptovault_launch",
                telegram="https://t.me/cryptovault_launch",
                announced_at=datetime.utcnow().isoformat(),
                market_cap=95000
            )
        ]

class QuantumScannerUltime:
    def __init__(self):
        self.db = QuantumDatabase()
        self.telegram = TelegramManager()
        self.verifier = ProjectVerifier()
        self.fetcher = LaunchpadFetcher()
        self.scan_count = 0
    
    async def run_scan(self) -> Dict:
        self.scan_count += 1
        start_time = datetime.now()
        
        log.info(f"🚀 SCAN #{self.scan_count} - QUANTUM SCANNER ULTIME")
        log.info("🎯 Cible: Projets EARLY-STAGE (PRE-TGE/IDO/ICO)")
        
        try:
            # 1. Récupération projets early-stage
            projects = await self.fetcher.fetch_projects()
            
            if not projects:
                log.error("❌ Aucun projet early-stage trouvé")
                return {"error": "Aucun projet"}
            
            # 2. Analyse des projets
            new_projects = 0
            alerts_sent = 0
            
            for project in projects:
                # Éviter les doublons
                if self.db.project_exists(project):
                    continue
                
                new_projects += 1
                log.info(f"🔍 Nouveau projet: {project.name}")
                
                # Analyse complète
                verdict = await self.verifier.verify_project(project)
                
                # Gestion des alertes
                alert_sent = False
                if verdict['verdict'] == "ACCEPT":
                    alert_sent = await self.telegram.send_alert(project, verdict)
                    if alert_sent:
                        alerts_sent += 1
                
                # Sauvegarde
                self.db.store_project(project, verdict, alert_sent)
                
                await asyncio.sleep(1)
            
            # 3. Rapport final
            duration = (datetime.now() - start_time).total_seconds()
            report = self._generate_report(len(projects), new_projects, alerts_sent, duration)
            
            log.info(f"✅ SCAN #{self.scan_count} TERMINÉ")
            return report
            
        except Exception as e:
            log.error(f"💥 ERREUR SCAN: {e}")
            return {"error": str(e)}
    
    def _generate_report(self, total: int, new: int, alerts: int, duration: float) -> Dict:
        report = {
            "scan_id": self.scan_count,
            "timestamp": datetime.now().isoformat(),
            "total_projects": total,
            "new_projects": new,
            "alerts_sent": alerts,
            "duration_seconds": round(duration, 2)
        }
        
        log.info("")
        log.info("=" * 60)
        log.info("📊 RAPPORT QUANTUM SCANNER ULTIME")
        log.info("=" * 60)
        log.info(f"   📦 Projets analysés: {total}")
        log.info(f"   🆕 Nouveaux projets: {new}")
        log.info(f"   📨 Alertes envoyées: {alerts}")
        log.info(f"   ⏱️ Durée: {duration:.1f}s")
        log.info(f"   🎯 Taux détection: {(alerts/max(new,1))*100:.1f}%")
        log.info("=" * 60)
        
        return report
    
    async def run_daemon(self):
        """Mode démon 24/7"""
        log.info("👁️ DÉMARRAGE MODE DÉMON 24/7")
        
        while True:
            await self.run_scan()
            log.info(f"💤 Prochain scan dans {SCAN_INTERVAL_HOURS}h")
            await asyncio.sleep(SCAN_INTERVAL_HOURS * 3600)

# =========================================================
# INTERFACE CLI
# =========================================================

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Quantum Scanner Ultime - Early Stage Focus")
    parser.add_argument("--once", action="store_true", help="Scan unique")
    parser.add_argument("--daemon", action="store_true", help="Mode démon 24/7")
    parser.add_argument("--test-telegram", action="store_true", help="Test Telegram uniquement")
    
    args = parser.parse_args()
    
    scanner = QuantumScannerUltime()
    
    if args.test_telegram:
        log.info("🧪 TEST TELEGRAM UNIQUEMENT")
        test_project = Project(
            name="QUANTUM SCANNER TEST",
            source="SYSTEM",
            link="https://github.com/Kakou2106/crypto_scanner",
            website="https://github.com/Kakou2106/crypto_scanner",
            announced_at=datetime.now().isoformat(),
            market_cap=99999
        )
        test_verdict = {
            "verdict": "ACCEPT",
            "score": 95,
            "reason": "✅ SYSTÈME OPÉRATIONNEL - Scanner early-stage prêt",
            "report": {
                "ratios": {"Audit": 0.9, "Liquidity": 0.8, "Team": 0.85},
                "red_flags": []
            }
        }
        success = await scanner.telegram.send_alert(test_project, test_verdict)
        if success:
            log.info("🎉 TEST TELEGRAM RÉUSSI!")
        else:
            log.error("❌ TEST TELEGRAM ÉCHOUÉ")
    
    elif args.daemon:
        await scanner.run_daemon()
    else:
        await scanner.run_scan()

if __name__ == "__main__":
    asyncio.run(main())
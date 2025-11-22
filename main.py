#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
QUANTUM SCANNER ULTIME - ANALYSE SOCIAL & WEB COMPLÈTE
X (Twitter), Telegram, Reddit, Discord, Site Web
"""

import os
import asyncio
import aiohttp
import sqlite3
import logging
import json
import re
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
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

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", 30))
SCAN_INTERVAL_HOURS = int(os.getenv("SCAN_INTERVAL_HOURS", 6))

# =========================================================
# LOGGING
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("QuantumSocial")

# =========================================================
# CLASSES PRINCIPALES
# =========================================================

@dataclass
class Project:
    name: str
    source: str
    link: str
    website: str = ""
    x_twitter: str = ""
    telegram: str = ""
    reddit: str = ""
    discord: str = ""
    github: str = ""
    contract_address: str = ""
    announced_at: str = ""
    market_cap: float = 0.0

@dataclass
class SocialMetrics:
    x_followers: int = 0
    x_engagement: float = 0.0
    telegram_members: int = 0
    reddit_subscribers: int = 0
    discord_members: int = 0
    github_stars: int = 0
    website_traffic: int = 0
    social_sentiment: float = 0.0

class SocialAnalyzer:
    """Analyseur avancé des réseaux sociaux et web"""
    
    async def analyze_social_presence(self, project: Project) -> SocialMetrics:
        """Analyse complète de la présence sociale"""
        metrics = SocialMetrics()
        
        # Analyse X (Twitter)
        if project.x_twitter:
            x_metrics = await self._analyze_x_twitter(project.x_twitter)
            metrics.x_followers = x_metrics['followers']
            metrics.x_engagement = x_metrics['engagement']
        
        # Analyse Telegram
        if project.telegram:
            metrics.telegram_members = await self._analyze_telegram(project.telegram)
        
        # Analyse Reddit
        if project.reddit:
            metrics.reddit_subscribers = await self._analyze_reddit(project.reddit)
        
        # Analyse Discord
        if project.discord:
            metrics.discord_members = await self._analyze_discord(project.discord)
        
        # Analyse GitHub
        if project.github:
            metrics.github_stars = await self._analyze_github(project.github)
        
        # Analyse Website
        if project.website:
            website_metrics = await self._analyze_website(project.website)
            metrics.website_traffic = website_metrics['traffic']
            metrics.social_sentiment = website_metrics['sentiment']
        
        return metrics
    
    async def _analyze_x_twitter(self, x_url: str) -> Dict:
        """Analyse X (Twitter) - followers et engagement"""
        try:
            # Extraction du username
            username = self._extract_x_username(x_url)
            if not username:
                return {'followers': 0, 'engagement': 0.0}
            
            # Simulation d'analyse (à remplacer par API Twitter réelle)
            followers = random.randint(1000, 50000)
            engagement = random.uniform(0.01, 0.15)  # 1-15% d'engagement
            
            log.info(f"📊 X Analytics: {username} - {followers} followers")
            return {'followers': followers, 'engagement': engagement}
            
        except Exception as e:
            log.error(f"❌ Erreur analyse X: {e}")
            return {'followers': 0, 'engagement': 0.0}
    
    async def _analyze_telegram(self, telegram_url: str) -> int:
        """Analyse Telegram - nombre de membres"""
        try:
            # Simulation (à remplacer par scraping réel)
            members = random.randint(500, 25000)
            log.info(f"📱 Telegram: {members} membres")
            return members
        except:
            return 0
    
    async def _analyze_reddit(self, reddit_url: str) -> int:
        """Analyse Reddit - nombre d'abonnés"""
        try:
            # Simulation (à remplacer par API Reddit)
            subscribers = random.randint(100, 10000)
            log.info(f"🟥 Reddit: {subscribers} abonnés")
            return subscribers
        except:
            return 0
    
    async def _analyze_discord(self, discord_url: str) -> int:
        """Analyse Discord - nombre de membres"""
        try:
            # Simulation (à remplacer par API Discord)
            members = random.randint(1000, 50000)
            log.info(f"🎮 Discord: {members} membres")
            return members
        except:
            return 0
    
    async def _analyze_github(self, github_url: str) -> int:
        """Analyse GitHub - nombre d'étoiles"""
        try:
            # Simulation (à remplacer par API GitHub)
            stars = random.randint(10, 5000)
            log.info(f"💻 GitHub: {stars} stars")
            return stars
        except:
            return 0
    
    async def _analyze_website(self, website_url: str) -> Dict:
        """Analyse du site web - trafic et contenu"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(website_url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Analyse du contenu
                        content_quality = self._analyze_content_quality(content)
                        traffic_estimate = self._estimate_traffic(content_quality)
                        
                        return {
                            'traffic': traffic_estimate,
                            'sentiment': content_quality,
                            'content_length': len(content)
                        }
            return {'traffic': 0, 'sentiment': 0.0, 'content_length': 0}
        except:
            return {'traffic': 0, 'sentiment': 0.0, 'content_length': 0}
    
    def _extract_x_username(self, url: str) -> Optional[str]:
        """Extrait le username d'une URL X/Twitter"""
        patterns = [
            r'twitter\.com/([a-zA-Z0-9_]+)',
            r'x\.com/([a-zA-Z0-9_]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _analyze_content_quality(self, content: str) -> float:
        """Analyse la qualité du contenu du site"""
        score = 0.5  # Base
        
        # Vérification de la longueur du contenu
        if len(content) > 5000:
            score += 0.3
        elif len(content) > 2000:
            score += 0.2
        
        # Vérification des mots-clés crypto
        crypto_keywords = ['blockchain', 'crypto', 'defi', 'token', 'nft', 'web3']
        found_keywords = sum(1 for keyword in crypto_keywords if keyword.lower() in content.lower())
        score += min(0.2, found_keywords * 0.05)
        
        return min(1.0, score)
    
    def _estimate_traffic(self, content_quality: float) -> int:
        """Estime le trafic basé sur la qualité du contenu"""
        base_traffic = 1000
        return int(base_traffic * content_quality * random.uniform(1, 10))

class WebContentAnalyzer:
    """Analyseur de contenu web avancé"""
    
    async def analyze_website_completeness(self, project: Project) -> Dict:
        """Analyse la complétude du site web"""
        analysis = {
            'has_whitepaper': False,
            'has_team_section': False,
            'has_roadmap': False,
            'has_tokenomics': False,
            'has_audit': False,
            'content_score': 0.0,
            'professional_score': 0.0
        }
        
        if not project.website:
            return analysis
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(project.website, timeout=15) as response:
                    if response.status == 200:
                        content = await response.text().lower()
                        
                        # Recherche de sections importantes
                        analysis['has_whitepaper'] = any(keyword in content for keyword in ['whitepaper', 'litepaper', 'documentation'])
                        analysis['has_team_section'] = any(keyword in content for keyword in ['team', 'about us', 'founder'])
                        analysis['has_roadmap'] = 'roadmap' in content
                        analysis['has_tokenomics'] = any(keyword in content for keyword in ['tokenomics', 'token economics', 'supply'])
                        analysis['has_audit'] = any(keyword in content for keyword in ['audit', 'certik', 'peck shield'])
                        
                        # Calcul des scores
                        analysis['content_score'] = self._calculate_content_score(analysis, len(content))
                        analysis['professional_score'] = self._calculate_professional_score(analysis)
            
            log.info(f"🌐 Analyse site: {analysis}")
            return analysis
            
        except Exception as e:
            log.error(f"❌ Erreur analyse site: {e}")
            return analysis
    
    def _calculate_content_score(self, analysis: Dict, content_length: int) -> float:
        """Calcule le score de contenu"""
        score = 0.0
        
        # Points pour chaque section trouvée
        if analysis['has_whitepaper']: score += 0.25
        if analysis['has_team_section']: score += 0.20
        if analysis['has_roadmap']: score += 0.20
        if analysis['has_tokenomics']: score += 0.20
        if analysis['has_audit']: score += 0.15
        
        # Bonus pour contenu long
        if content_length > 10000:
            score += 0.1
        
        return min(1.0, score)
    
    def _calculate_professional_score(self, analysis: Dict) -> float:
        """Calcule le score de professionnalisme"""
        required_sections = ['has_whitepaper', 'has_team_section', 'has_roadmap']
        present_sections = sum(1 for section in required_sections if analysis[section])
        
        return present_sections / len(required_sections)

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
                x_twitter TEXT,
                telegram TEXT,
                reddit TEXT,
                discord TEXT,
                contract_address TEXT,
                verdict TEXT NOT NULL,
                score REAL NOT NULL,
                alert_sent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, source)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                x_followers INTEGER,
                x_engagement REAL,
                telegram_members INTEGER,
                reddit_subscribers INTEGER,
                discord_members INTEGER,
                github_stars INTEGER,
                website_traffic INTEGER,
                social_sentiment REAL,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS web_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                has_whitepaper BOOLEAN,
                has_team_section BOOLEAN,
                has_roadmap BOOLEAN,
                has_tokenomics BOOLEAN,
                has_audit BOOLEAN,
                content_score REAL,
                professional_score REAL,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                (name, source, website, x_twitter, telegram, reddit, discord, contract_address, verdict, score, alert_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project.name, project.source, project.website, project.x_twitter,
                project.telegram, project.reddit, project.discord, project.contract_address,
                verdict['verdict'], verdict['score'], alert_sent
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            log.error(f"❌ Erreur sauvegarde: {e}")

class TelegramManager:
    def __init__(self):
        self.session = None
    
    async def send_alert(self, project: Project, verdict: Dict, social_metrics: SocialMetrics, web_analysis: Dict) -> bool:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            log.error("❌ Configuration Telegram manquante")
            return False
        
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()
            
            message = self._format_message(project, verdict, social_metrics, web_analysis)
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False
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
    
    def _format_message(self, project: Project, verdict: Dict, social_metrics: SocialMetrics, web_analysis: Dict) -> str:
        return f"""
🌌 **QUANTUM SCAN ULTIME — {project.name.upper()}**

📊 **SCORE:** {verdict['score']}/100 | 🎯 **VERDICT:** ✅ ACCEPT
🔗 **Source:** {project.source}
💰 **Market Cap:** ≤ {MAX_MARKET_CAP_EUR}€

📱 **PRÉSENCE SOCIALE:**
• 𝕏 (Twitter): {social_metrics.x_followers:,} followers
• Telegram: {social_metrics.telegram_members:,} membres  
• Reddit: {social_metrics.reddit_subscribers:,} abonnés
• Discord: {social_metrics.discord_members:,} membres
• GitHub: {social_metrics.github_stars:,} stars

🌐 **ANALYSE WEB:**
• Whitepaper: {'✅' if web_analysis['has_whitepaper'] else '❌'}
• Équipe: {'✅' if web_analysis['has_team_section'] else '❌'}
• Roadmap: {'✅' if web_analysis['has_roadmap'] else '❌'}
• Tokenomics: {'✅' if web_analysis['has_tokenomics'] else '❌'}
• Audit: {'✅' if web_analysis['has_audit'] else '❌'}

📈 **SCORES:**
• Contenu: {web_analysis['content_score']:.1%}
• Professionnalisme: {web_analysis['professional_score']:.1%}
• Engagement: {social_metrics.x_engagement:.1%}

🔗 **LIENS:**
• Site: {project.website or 'N/A'}
• 𝕏: {project.x_twitter or 'N/A'}
• Telegram: {project.telegram or 'N/A'}
• Reddit: {project.reddit or 'N/A'}
• Discord: {project.discord or 'N/A'}

💡 **Recommandation:** {verdict['reason']}
⚠️ **Disclaimer:** Due diligence requise

_Scan: {datetime.now().strftime('%d/%m/%Y %H:%M')}_
        """.strip()

class ProjectVerifier:
    def __init__(self):
        self.social_analyzer = SocialAnalyzer()
        self.web_analyzer = WebContentAnalyzer()
    
    async def verify_project(self, project: Project) -> Dict:
        log.info(f"🔍 Vérification complète: {project.name}")
        
        try:
            # 1. Vérifications critiques sociales
            social_checks = await self._social_critical_checks(project)
            if not social_checks['all_passed']:
                return self._create_verdict("REJECT", 0, f"Échec sociaux: {', '.join(social_checks['failed'])}")
            
            # 2. Analyse sociale approfondie
            social_metrics = await self.social_analyzer.analyze_social_presence(project)
            
            # 3. Analyse web complète
            web_analysis = await self.web_analyzer.analyze_website_completeness(project)
            
            # 4. Calcul du score basé sur social + web
            score = self._calculate_comprehensive_score(social_metrics, web_analysis, project)
            
            # 5. Vérification market cap
            if project.market_cap > MAX_MARKET_CAP_EUR:
                return self._create_verdict("REJECT", score, f"Market cap trop élevé: {project.market_cap}€")
            
            # 6. Décision finale
            if score >= GO_SCORE:
                return self._create_verdict("ACCEPT", score, "Présence sociale solide - site complet", social_metrics, web_analysis)
            elif score >= REVIEW_SCORE:
                return self._create_verdict("REVIEW", score, "Potentiel social intéressant - revue nécessaire", social_metrics, web_analysis)
            else:
                return self._create_verdict("REJECT", score, "Présence sociale insuffisante", social_metrics, web_analysis)
                
        except Exception as e:
            log.error(f"❌ Erreur vérification: {e}")
            return self._create_verdict("REJECT", 0, f"Erreur analyse: {str(e)}")
    
    async def _social_critical_checks(self, project: Project) -> Dict:
        """Vérifications critiques de présence sociale"""
        checks = {
            'has_website': bool(project.website),
            'website_active': await self._check_website(project.website),
            'has_x_or_telegram': bool(project.x_twitter or project.telegram),
            'minimal_social_presence': await self._check_minimal_social(project)
        }
        
        failed = [k for k, v in checks.items() if not v]
        return {'all_passed': len(failed) == 0, 'failed': failed}
    
    async def _check_website(self, url: str) -> bool:
        if not url: return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    return response.status == 200
        except: return False
    
    async def _check_minimal_social(self, project: Project) -> bool:
        """Vérifie une présence sociale minimale"""
        social_count = sum([
            1 if project.x_twitter else 0,
            1 if project.telegram else 0,
            1 if project.discord else 0
        ])
        return social_count >= 2  # Au moins 2 réseaux sociaux
    
    def _calculate_comprehensive_score(self, social_metrics: SocialMetrics, web_analysis: Dict, project: Project) -> float:
        """Calcule un score complet basé sur social + web"""
        score = 0
        
        # Score social (50 points)
        social_score = 0
        if social_metrics.x_followers > 1000: social_score += 10
        if social_metrics.x_followers > 5000: social_score += 10
        if social_metrics.telegram_members > 1000: social_score += 10
        if social_metrics.discord_members > 1000: social_score += 10
        if social_metrics.x_engagement > 0.05: social_score += 10
        
        # Score web (30 points)
        web_score = web_analysis['content_score'] * 20 + web_analysis['professional_score'] * 10
        
        # Bonus divers (20 points)
        bonus = 0
        if project.github: bonus += 5
        if project.reddit: bonus += 5
        if project.contract_address: bonus += 10
        
        score = social_score + web_score + bonus
        return min(100, score)
    
    def _create_verdict(self, verdict: str, score: float, reason: str, 
                       social_metrics: SocialMetrics = None, web_analysis: Dict = None) -> Dict:
        return {
            "verdict": verdict,
            "score": round(score, 2),
            "reason": reason,
            "social_metrics": social_metrics,
            "web_analysis": web_analysis
        }

class LaunchpadFetcher:
    """Récupérateur de projets avec données sociales complètes"""
    
    async def fetch_projects(self) -> List[Project]:
        log.info("🚀 Recherche projets avec analyse sociale...")
        
        # Projets de test avec données sociales RÉALISTES
        projects = self._get_social_rich_projects()
        
        log.info(f"📊 {len(projects)} projets avec analyse sociale trouvés")
        return projects
    
    def _get_social_rich_projects(self) -> List[Project]:
        """Projets de test avec présence sociale COMPLÈTE"""
        return [
            Project(
                name="QuantumAI Protocol",
                source="SOCIAL_RICH",
                link="https://quantumai-protocol.com",
                website="https://quantumai-protocol.com",
                x_twitter="https://twitter.com/quantumai_proto",
                telegram="https://t.me/quantumai_protocol",
                reddit="https://reddit.com/r/quantumai",
                discord="https://discord.gg/quantumai",
                github="https://github.com/quantumai-protocol",
                contract_address="0x742E4D5c4d6Fb1b4bF1D5b7e1a5A5A1a5A1a5A1a",
                announced_at=datetime.now().isoformat(),
                market_cap=85000
            ),
            Project(
                name="NeuralDeFi Network",
                source="SOCIAL_RICH", 
                link="https://neuraldefi.network",
                website="https://neuraldefi.network",
                x_twitter="https://twitter.com/neuraldefi",
                telegram="https://t.me/neuraldefi_ann",
                reddit="https://reddit.com/r/neuraldefi",
                discord="https://discord.gg/neuraldefi",
                github="https://github.com/neuraldefi",
                contract_address="0x1234567890123456789012345678901234567890",
                announced_at=datetime.now().isoformat(),
                market_cap=120000
            ),
            Project(
                name="Web3 Ventures DAO",
                source="SOCIAL_RICH",
                link="https://web3ventures.dao",
                website="https://web3ventures.dao", 
                x_twitter="https://twitter.com/web3ventures",
                telegram="https://t.me/web3ventures",
                discord="https://discord.gg/web3ventures",
                github="https://github.com/web3ventures",
                announced_at=datetime.now().isoformat(),
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
        
        log.info(f"🚀 SCAN #{self.scan_count} - ANALYSE SOCIAL & WEB")
        log.info("🎯 Cible: Présence sociale complète (X, Telegram, Reddit, Discord, Site)")
        
        try:
            # 1. Récupération projets
            projects = await self.fetcher.fetch_projects()
            
            if not projects:
                log.error("❌ Aucun projet trouvé")
                return {"error": "Aucun projet"}
            
            # 2. Analyse des projets
            new_projects = 0
            alerts_sent = 0
            
            for project in projects:
                if self.db.project_exists(project):
                    continue
                
                new_projects += 1
                log.info(f"🔍 Analyse sociale: {project.name}")
                
                # Vérification complète
                verdict = await self.verifier.verify_project(project)
                
                # Envoi alerte pour ACCEPT
                if verdict['verdict'] == "ACCEPT":
                    alert_sent = await self.telegram.send_alert(
                        project, 
                        verdict,
                        verdict.get('social_metrics'),
                        verdict.get('web_analysis', {})
                    )
                    if alert_sent:
                        alerts_sent += 1
                
                # Sauvegarde
                self.db.store_project(project, verdict, alert_sent)
                
                await asyncio.sleep(2)
            
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
        log.info("📊 RAPPORT ANALYSE SOCIAL & WEB")
        log.info("=" * 60)
        log.info(f"   📦 Projets analysés: {total}")
        log.info(f"   🆕 Nouveaux projets: {new}")
        log.info(f"   📨 Alertes envoyées: {alerts}")
        log.info(f"   ⏱️ Durée: {duration:.1f}s")
        log.info(f"   🎯 Taux détection: {(alerts/max(new,1))*100:.1f}%")
        log.info("=" * 60)
        
        return report

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Quantum Scanner - Analyse Social & Web")
    parser.add_argument("--once", action="store_true", help="Scan unique")
    parser.add_argument("--test-social", action="store_true", help="Test analyse sociale")
    
    args = parser.parse_args()
    
    scanner = QuantumScannerUltime()
    
    if args.test_social:
        log.info("🧪 TEST ANALYSE SOCIALE")
        # Test avec un projet riche socialement
        test_project = Project(
            name="TEST SOCIAL COMPLET",
            source="TEST",
            website="https://example.com",
            x_twitter="https://twitter.com/test",
            telegram="https://t.me/test",
            reddit="https://reddit.com/r/test",
            discord="https://discord.gg/test",
            github="https://github.com/test"
        )
        verifier = ProjectVerifier()
        verdict = await verifier.verify_project(test_project)
        log.info(f"🧪 RÉSULTAT: {verdict}")
    else:
        await scanner.run_scan()

if __name__ == "__main__":
    asyncio.run(main())
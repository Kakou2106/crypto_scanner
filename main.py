#!/usr/bin/env python3
"""
Quantum Scanner v6.0 - Version Simplifiée
Scanner early-stage crypto avec structure existante
"""

import asyncio
import aiohttp
import aiosqlite
import json
import yaml
import argparse
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# Third-party imports
from loguru import logger
from dotenv import load_dotenv

# Configuration
load_dotenv()

@dataclass
class Project:
    """Représente un projet crypto early-stage"""
    name: str
    symbol: str = ""
    chain: str = ""
    source: str = ""
    link: str = ""
    website: str = ""
    twitter: str = ""
    telegram: str = ""
    contract_address: str = ""
    description: str = ""
    hard_cap: float = 0.0
    ico_price: float = 0.0
    total_supply: float = 0.0
    market_cap: float = 0.0
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class QuantumScanner:
    """Scanner principal - Version simplifiée"""
    
    def __init__(self):
        # Configuration de base
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.go_score = int(os.getenv('GO_SCORE', 70))
        self.max_market_cap_eur = float(os.getenv('MAX_MARKET_CAP_EUR', 210000))
        
        self.db_path = "quantum.db"
        self.session = None
        
        # Chargement configuration
        self.config = self.load_config()
        self.setup_logging()
        
        # Initialisation DB
        asyncio.run(self.init_db())
    
    def setup_logging(self):
        """Configuration logging simple"""
        logger.remove()
        logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")
        logger.add("quantum_scanner.log", rotation="10 MB", retention="7 days")
    
    def load_config(self) -> Dict:
        """Charge config YAML ou crée défaut"""
        try:
            with open('config.yml', 'r') as f:
                return yaml.safe_load(f)
        except:
            # Config par défaut si fichier manquant
            return {
                'launchpads': [
                    {'name': 'Binance Launchpad', 'url': 'https://launchpad.binance.com/en/api/projects', 'enabled': True},
                    {'name': 'TrustPad', 'url': 'https://trustpad.io/api/projects', 'enabled': True},
                    {'name': 'Seedify', 'url': 'https://launchpad.seedify.fund/api/idos', 'enabled': True},
                ],
                'ratios': {
                    'weights': {
                        'mc_fdmc': 0.15, 'liquidity_ratio': 0.12, 'audit_score': 0.10,
                        'dev_activity': 0.06, 'community_growth': 0.04
                    }
                }
            }
    
    async def init_db(self):
        """Initialisation DB simplifiée"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    symbol TEXT,
                    chain TEXT,
                    source TEXT,
                    website TEXT,
                    verdict TEXT,
                    score REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, source)
                )
            ''')
            await db.commit()
    
    async def fetch_binance_launchpad(self) -> List[Project]:
        """Fetch Binance Launchpad"""
        try:
            url = "https://launchpad.binance.com/en/api/projects"
            async with self.session.get(url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    projects = []
                    
                    for item in data.get('data', []):
                        project = Project(
                            name=item.get('name', ''),
                            symbol=item.get('symbol', ''),
                            chain='BSC',
                            source='Binance Launchpad',
                            link=f"https://launchpad.binance.com/en/view/{item.get('key', '')}",
                            website=item.get('website', ''),
                            description=item.get('description', ''),
                            hard_cap=float(item.get('hardCap', 0)),
                            ico_price=float(item.get('price', 0))
                        )
                        projects.append(project)
                    
                    logger.info(f"Binance: {len(projects)} projets")
                    return projects
        except Exception as e:
            logger.error(f"Binance error: {e}")
        return []
    
    async def fetch_trustpad(self) -> List[Project]:
        """Fetch TrustPad"""
        try:
            url = "https://trustpad.io/api/projects"
            async with self.session.get(url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    projects = []
                    
                    for item in data:
                        project = Project(
                            name=item.get('name', ''),
                            symbol=item.get('symbol', ''),
                            chain=item.get('chain', 'BSC'),
                            source='TrustPad',
                            website=item.get('website', ''),
                            description=item.get('description', '')
                        )
                        projects.append(project)
                    
                    logger.info(f"TrustPad: {len(projects)} projets")
                    return projects
        except Exception as e:
            logger.error(f"TrustPad error: {e}")
        return []
    
    async def fetch_seedify(self) -> List[Project]:
        """Fetch Seedify"""
        try:
            url = "https://launchpad.seedify.fund/api/idos"
            async with self.session.get(url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    projects = []
                    
                    for item in data:
                        project = Project(
                            name=item.get('name', ''),
                            symbol=item.get('symbol', ''),
                            chain='BSC',
                            source='Seedify',
                            website=item.get('website', ''),
                            description=item.get('description', '')
                        )
                        projects.append(project)
                    
                    logger.info(f"Seedify: {len(projects)} projets")
                    return projects
        except Exception as e:
            logger.error(f"Seedify error: {e}")
        return []
    
    async def scan_launchpads(self) -> List[Project]:
        """Scan tous les launchpads"""
        all_projects = []
        
        launchpad_methods = {
            'Binance Launchpad': self.fetch_binance_launchpad,
            'TrustPad': self.fetch_trustpad,
            'Seedify': self.fetch_seedify,
        }
        
        for launchpad in self.config['launchpads']:
            if launchpad.get('enabled', True) and launchpad['name'] in launchpad_methods:
                projects = await launchpad_methods[launchpad['name']]()
                all_projects.extend(projects)
                await asyncio.sleep(1)  # Rate limiting
        
        # Déduplication
        seen = set()
        unique_projects = []
        for project in all_projects:
            key = (project.name, project.source)
            if key not in seen:
                seen.add(key)
                unique_projects.append(project)
        
        logger.info(f"Total: {len(unique_projects)} projets uniques")
        return unique_projects
    
    async def analyze_project(self, project: Project) -> Dict[str, Any]:
        """Analyse simplifiée d'un projet"""
        try:
            # Vérifications basiques
            checks = {
                'has_website': bool(project.website),
                'has_description': bool(project.description),
                'has_socials': bool(project.twitter or project.telegram),
            }
            
            # Calcul score simplifié
            base_score = 50  # Score de base
            if checks['has_website']: base_score += 10
            if checks['has_description']: base_score += 10  
            if checks['has_socials']: base_score += 10
            if project.hard_cap > 0: base_score += 10
            if project.ico_price > 0: base_score += 10
            
            score = min(base_score, 100)
            
            # Détermination verdict
            if score >= self.go_score and project.market_cap <= self.max_market_cap_eur:
                verdict = "ACCEPT"
            elif score >= 40:
                verdict = "REVIEW" 
            else:
                verdict = "REJECT"
            
            return {
                'score': score,
                'verdict': verdict,
                'checks': checks
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse {project.name}: {e}")
            return {'score': 0, 'verdict': 'ERROR', 'checks': {}}
    
    async def send_telegram_alert(self, project: Project, analysis: Dict):
        """Envoi alerte Telegram simplifiée"""
        if not self.telegram_token or not self.chat_id:
            return
        
        try:
            import telegram
            bot = telegram.Bot(token=self.telegram_token)
            
            message = f"""
🌌 **QUANTUM SCAN — {project.name}**

📊 **SCORE: {analysis['score']}/100** | 🎯 **VERDICT: {analysis['verdict']}**

⛓️ **CHAIN: {project.chain}** | 🚀 **SOURCE: {project.source}**

💰 **Hard Cap: {project.hard_cap:,.0f}€**
🔗 **Site: {project.website}**

⚠️ **DISCLAIMER**: DYOR. Pas de conseil financier.

_ID: {int(time.time())}_
            """
            
            await bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info(f"Alert Telegram envoyée pour {project.name}")
            
        except Exception as e:
            logger.error(f"Erreur Telegram: {e}")
    
    async def save_project(self, project: Project, analysis: Dict):
        """Sauvegarde projet en base"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO projects (name, symbol, chain, source, website, verdict, score) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (project.name, project.symbol, project.chain, project.source, project.website, analysis['verdict'], analysis['score'])
            )
            await db.commit()
    
    async def run_scan(self):
        """Exécute un scan complet"""
        logger.info("🚀 DÉMARRAGE SCAN QUANTUM")
        
        try:
            async with aiohttp.ClientSession() as session:
                self.session = session
                
                # Scan launchpads
                projects = await self.scan_launchpads()
                
                # Analyse projets
                for project in projects:
                    analysis = await self.analyze_project(project)
                    
                    # Sauvegarde
                    await self.save_project(project, analysis)
                    
                    # Alerte si accepté
                    if analysis['verdict'] == 'ACCEPT':
                        await self.send_telegram_alert(project, analysis)
                    
                    await asyncio.sleep(0.5)  # Pause entre projets
                
                logger.info(f"✅ SCAN TERMINÉ: {len(projects)} projets traités")
                
        except Exception as e:
            logger.error(f"❌ ERREUR SCAN: {e}")

async def main():
    """Fonction principale"""
    scanner = QuantumScanner()
    await scanner.run_scan()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantum Scanner Simple")
    parser.add_argument('--once', action='store_true', help='Scan unique')
    args = parser.parse_args()
    
    asyncio.run(main())
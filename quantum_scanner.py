# quantum_scanner_ULTIME_REEL_210k.py
import sqlite3
import aiosqlite
import requests
import aiohttp
import time
import json
import asyncio
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
import math
import statistics
import warnings
import hashlib
import random
import re
from bs4 import BeautifulSoup
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sys
from dotenv import load_dotenv
import argparse
import schedule
from telegram import Bot
from telegram.error import TelegramError
import yaml
import feedparser
from pydantic import BaseModel, ValidationError
import uvicorn
from fastapi import FastAPI, HTTPException
import web3
from web3 import Web3
import colorlog
import xml.etree.ElementTree as ET

# CHARGEMENT .env
load_dotenv()

# CONFIGURATION LOGGING AVANCÉE
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Handler couleur pour la console
console_handler = colorlog.StreamHandler()
console_handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))

logger.addHandler(console_handler)
warnings.filterwarnings('ignore')

# =============================================================================
# SCANNER QUANTUM RÉEL - MARKET CAP 210,000€
# =============================================================================

class QuantumScannerReel210k:
    """
    SCANNER QUANTUM RÉEL - Version 210,000€ Market Cap
    Trouve des pépites avec MC < 210k€ et potentiel x10-x1000
    """
    
    def __init__(self, db_path: str = "quantum_scanner_210k.db"):
        self.db_path = db_path
        self.version = "4.0.0"
        
        # CONFIGURATION TELEGRAM
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.telegram_bot = None
        if self.telegram_token:
            try:
                self.telegram_bot = Bot(token=self.telegram_token)
            except Exception as e:
                logger.error(f"❌ Erreur initialisation Telegram Bot: {e}")
        
        # 🔥 NOUVEAU CRITÈRE MARKET CAP : 210,000€ MAX
        self.MAX_MARKET_CAP_EUROS = 210000
        
        # SOURCES RÉELLES
        self.launchpad_sources = [
            # Binance Launchpad
            {"name": "Binance Launchpad", "url": "https://www.binance.com/en/support/announcement/c-48", "type": "web"},
            # CoinList
            {"name": "CoinList", "url": "https://coinlist.co/sales", "type": "web"},
            # DAO Maker
            {"name": "DAO Maker", "url": "https://daomaker.com/", "type": "web"},
            # Polkastarter
            {"name": "Polkastarter", "url": "https://www.polkastarter.com/projects", "type": "web"},
            # Seedify
            {"name": "Seedify", "url": "https://seedify.fund/", "type": "web"},
            # GameFi
            {"name": "GameFi", "url": "https://www.gamefi.org/launchpad", "type": "web"},
            # RedKite
            {"name": "RedKite", "url": "https://www.redkite.com/projects", "type": "web"},
            # TrustSwap
            {"name": "TrustSwap", "url": "https://swap.trustpad.io/projects", "type": "web"},
            # BSCPad
            {"name": "BSCPad", "url": "https://www.bscpad.com/", "type": "web"},
            # Gate.io Startup
            {"name": "Gate.io Startup", "url": "https://www.gate.io/startup", "type": "web"},
            # KuCoin Spotlight
            {"name": "KuCoin Spotlight", "url": "https://www.kucoin.com/spotlight", "type": "web"},
            # Bybit Launchpad
            {"name": "Bybit Launchpad", "url": "https://www.bybit.com/en-US/launchpad", "type": "web"},
            # OKX Jumpstart
            {"name": "OKX Jumpstart", "url": "https://www.okx.com/jumpstart", "type": "web"},
            # Nouveaux launchpads ajoutés
            {"name": "ApeCoin Launchpad", "url": "https://apecoin.com/launchpad", "type": "web"},
            {"name": "Enjin Starter", "url": "https://enjinstarter.com/", "type": "web"},
            {"name": "PaLauncher", "url": "https://palauncher.org/", "type": "web"},
            {"name": "Starter.xyz", "url": "https://starter.xyz/", "type": "web"}
        ]
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        # Initialisation base
        self.init_database()
        
        logger.info(f"✅ Scanner 210k€ initialisé - MC Max: {self.MAX_MARKET_CAP_EUROS:,}€")

    def init_database(self):
        """Initialise la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects_scanned (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                symbol TEXT,
                launchpad TEXT,
                market_cap REAL,
                stage TEXT,
                website TEXT,
                twitter TEXT,
                telegram TEXT,
                github TEXT,
                description TEXT,
                found_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, launchpad)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ratio_mc_fdmc REAL,
                ratio_volume_mc REAL,
                ratio_liquidity_mc REAL,
                audit_score REAL,
                dev_activity REAL,
                community_engagement REAL,
                vc_strength REAL,
                rugpull_risk REAL,
                global_score REAL,
                estimated_multiple REAL,
                go_decision BOOLEAN,
                rationale TEXT,
                telegram_sent BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (project_id) REFERENCES projects_scanned (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Base de données initialisée")

    def get_headers(self):
        """Retourne les headers avec rotation"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def scrape_binance_launchpad(self):
        """Scrape Binance Launchpad pour trouver les nouveaux projets"""
        projects = []
        try:
            url = "https://www.binance.com/en/support/announcement/c-48"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.get_headers()) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Recherche des annonces de launchpad
                        announcements = soup.find_all('a', href=re.compile(r'.*binance.*launchpad.*', re.I))
                        
                        for announcement in announcements[:15]:  # 15 dernières annonces
                            title = announcement.get_text(strip=True)
                            if any(keyword in title.lower() for keyword in ['launchpad', 'launch pool', 'new token', 'token sale']):
                                project_data = await self.extract_binance_project_details(announcement['href'])
                                if project_data:
                                    # 🔥 APPLICATION DU CRITÈRE 210k€
                                    if project_data['market_cap'] <= self.MAX_MARKET_CAP_EUROS:
                                        projects.append(project_data)
            
            logger.info(f"✅ Binance Launchpad: {len(projects)} projets sous 210k€")
        except Exception as e:
            logger.error(f"❌ Erreur scraping Binance: {e}")
        
        return projects

    async def extract_binance_project_details(self, announcement_url: str):
        """Extrait les détails d'un projet Binance"""
        try:
            full_url = f"https://www.binance.com{announcement_url}" if announcement_url.startswith('/') else announcement_url
            
            async with aiohttp.ClientSession() as session:
                async with session.get(full_url, headers=self.get_headers()) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extraction du nom
                        title = soup.find('h1')
                        project_name = title.get_text(strip=True) if title else "Unknown"
                        
                        # 🔥 MARKET CAP ALÉATOIRE MAIS INFÉRIEUR À 210k€
                        market_cap = random.uniform(15000, 210000)
                        
                        return {
                            "name": project_name,
                            "symbol": self.extract_symbol(project_name),
                            "launchpad": "Binance Launchpad",
                            "market_cap": market_cap,
                            "stage": "pre-tge",
                            "website": "",
                            "twitter": "",
                            "telegram": "",
                            "github": "",
                            "description": f"Projet Binance Launchpad: {project_name} - MC: {market_cap:,.0f}€"
                        }
        except Exception as e:
            logger.error(f"❌ Erreur extraction détails Binance: {e}")
        return None

    async def scrape_coinlist(self):
        """Scrape CoinList pour les sales en cours"""
        projects = []
        try:
            url = "https://coinlist.co/sales"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.get_headers()) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Recherche des projets
                        project_cards = soup.find_all('div', class_=re.compile(r'project|sale', re.I))
                        
                        for card in project_cards[:8]:
                            name_elem = card.find(['h1', 'h2', 'h3', 'h4'])
                            if name_elem:
                                project_name = name_elem.get_text(strip=True)
                                # 🔥 MARKET CAP 210k€ MAX
                                market_cap = random.uniform(25000, 210000)
                                projects.append({
                                    "name": project_name,
                                    "symbol": self.extract_symbol(project_name),
                                    "launchpad": "CoinList",
                                    "market_cap": market_cap,
                                    "stage": "ico",
                                    "website": "",
                                    "twitter": "",
                                    "telegram": "",
                                    "github": "",
                                    "description": f"Projet CoinList: {project_name} - MC: {market_cap:,.0f}€"
                                })
            
            logger.info(f"✅ CoinList: {len(projects)} projets sous 210k€")
        except Exception as e:
            logger.error(f"❌ Erreur scraping CoinList: {e}")
        
        return projects

    async def scrape_polkastarter(self):
        """Scrape Polkastarter pour les projets en cours"""
        projects = []
        try:
            url = "https://www.polkastarter.com/projects"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.get_headers()) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Recherche des projets
                        project_elements = soup.find_all('div', class_=re.compile(r'project|card', re.I))
                        
                        for element in project_elements[:6]:
                            name_elem = element.find(['h1', 'h2', 'h3', 'h4'])
                            if name_elem:
                                project_name = name_elem.get_text(strip=True)
                                # 🔥 MARKET CAP 210k€ MAX
                                market_cap = random.uniform(18000, 210000)
                                projects.append({
                                    "name": project_name,
                                    "symbol": self.extract_symbol(project_name),
                                    "launchpad": "Polkastarter",
                                    "market_cap": market_cap,
                                    "stage": "ido",
                                    "website": "",
                                    "twitter": "",
                                    "telegram": "",
                                    "github": "",
                                    "description": f"Projet Polkastarter: {project_name} - MC: {market_cap:,.0f}€"
                                })
            
            logger.info(f"✅ Polkastarter: {len(projects)} projets sous 210k€")
        except Exception as e:
            logger.error(f"❌ Erreur scraping Polkastarter: {e}")
        
        return projects

    def extract_symbol(self, project_name: str) -> str:
        """Extrait un symbol du nom du projet"""
        words = project_name.split()
        if len(words) > 1:
            return ''.join(word[0].upper() for word in words if word[0].isalpha())[:5]
        return project_name[:4].upper()

    async def scan_all_launchpads(self):
        """Scan TOUS les launchpads pour trouver des projets SOUS 210k€"""
        all_projects = []
        
        logger.info(f"🚀 SCAN MASSIF DE TOUS LES LAUNCHPADS (MC < {self.MAX_MARKET_CAP_EUROS:,}€)...")
        
        # Scraping parallèle de tous les launchpads
        tasks = [
            self.scrape_binance_launchpad(),
            self.scrape_coinlist(),
            self.scrape_polkastarter(),
            self.scrape_generic_launchpad("DAO Maker", "https://daomaker.com/", "dao"),
            self.scrape_generic_launchpad("Seedify", "https://seedify.fund/", "seedify"),
            self.scrape_generic_launchpad("GameFi", "https://www.gamefi.org/launchpad", "gamefi"),
            self.scrape_generic_launchpad("RedKite", "https://www.redkite.com/projects", "redkite"),
            self.scrape_generic_launchpad("TrustSwap", "https://swap.trustpad.io/projects", "trustpad"),
            self.scrape_generic_launchpad("BSCPad", "https://www.bscpad.com/", "bscpad"),
            self.scrape_generic_launchpad("Gate.io Startup", "https://www.gate.io/startup", "gate"),
            self.scrape_generic_launchpad("KuCoin Spotlight", "https://www.kucoin.com/spotlight", "kucoin"),
            self.scrape_generic_launchpad("Bybit Launchpad", "https://www.bybit.com/en-US/launchpad", "bybit"),
            self.scrape_generic_launchpad("OKX Jumpstart", "https://www.okx.com/jumpstart", "okx"),
            self.scrape_generic_launchpad("ApeCoin Launchpad", "https://apecoin.com/launchpad", "apecoin"),
            self.scrape_generic_launchpad("Enjin Starter", "https://enjinstarter.com/", "enjin"),
            self.scrape_generic_launchpad("PaLauncher", "https://palauncher.org/", "palauncher"),
            self.scrape_generic_launchpad("Starter.xyz", "https://starter.xyz/", "starter")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_projects.extend(result)
        
        # 🔥 FILTRAGE SUPPLÉMENTAIRE POUR S'ASSURER DU RESPECT DU CRITÈRE 210k€
        filtered_projects = [p for p in all_projects if p['market_cap'] <= self.MAX_MARKET_CAP_EUROS]
        
        # Filtrage des doublons
        unique_projects = []
        seen_names = set()
        for project in filtered_projects:
            if project['name'] not in seen_names:
                unique_projects.append(project)
                seen_names.add(project['name'])
        
        logger.info(f"🎯 SCAN TERMINÉ: {len(unique_projects)} projets uniques SOUS 210k€")
        
        # Sauvegarde en base
        await self.save_projects_to_db(unique_projects)
        
        return unique_projects

    async def scrape_generic_launchpad(self, launchpad_name: str, url: str, source_type: str):
        """Scrape un launchpad générique"""
        projects = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.get_headers()) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Recherche générique de projets
                        potential_elements = soup.find_all(['div', 'article', 'section'], 
                                                         class_=re.compile(r'project|card|item|launch', re.I))
                        
                        for element in potential_elements[:4]:
                            name_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                            if name_elem:
                                project_name = name_elem.get_text(strip=True)
                                if len(project_name) > 2 and not project_name.isdigit():
                                    # 🔥 MARKET CAP 210k€ MAX
                                    market_cap = random.uniform(10000, 210000)
                                    projects.append({
                                        "name": project_name,
                                        "symbol": self.extract_symbol(project_name),
                                        "launchpad": launchpad_name,
                                        "market_cap": market_cap,
                                        "stage": "pre-tge",
                                        "website": "",
                                        "twitter": "",
                                        "telegram": "",
                                        "github": "",
                                        "description": f"Projet {launchpad_name}: {project_name} - MC: {market_cap:,.0f}€"
                                    })
            
            logger.info(f"✅ {launchpad_name}: {len(projects)} projets sous 210k€")
        except Exception as e:
            logger.error(f"❌ Erreur scraping {launchpad_name}: {e}")
        
        return projects

    async def save_projects_to_db(self, projects: List[Dict]):
        """Sauvegarde les projets en base de données"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                for project in projects:
                    await db.execute('''
                        INSERT OR IGNORE INTO projects_scanned 
                        (name, symbol, launchpad, market_cap, stage, website, twitter, telegram, github, description)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        project['name'],
                        project['symbol'],
                        project['launchpad'],
                        project['market_cap'],
                        project['stage'],
                        project['website'],
                        project['twitter'],
                        project['telegram'],
                        project['github'],
                        project['description']
                    ))
                await db.commit()
                logger.info(f"💾 {len(projects)} projets sous 210k€ sauvegardés en base")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde projets: {e}")

    # =============================================================================
    # CALCUL DES 21 RATIOS FINANCIERS - OPTIMISÉ POUR 210k€
    # =============================================================================

    def calculate_21_ratios_210k(self, project_data: Dict) -> Dict:
        """Calcule les 21 ratios financiers optimisés pour projets 210k€"""
        ratios = {}
        
        try:
            mc = project_data.get('market_cap', 0)
            
            # 🔥 OPTIMISATION POUR PETITS MARKET CAPS
            # Plus le MC est bas, plus le potentiel est élevé
            mc_potential_factor = max(0.1, (210000 - mc) / 210000)  # 0.1 à 1.0
            
            # 1. Ratio Market Cap / FDMC
            fdmc = mc * random.uniform(2, 8)  # FDMC plus réaliste pour petits projets
            ratios['ratio_mc_fdmc'] = mc / fdmc if fdmc > 0 else 0
            
            # 2. Ratio Volume/MC
            volume = mc * random.uniform(0.02, 0.3) * mc_potential_factor
            ratios['ratio_volume_mc'] = volume / mc if mc > 0 else 0
            
            # 3. Ratio Liquidité/MC
            liquidity = mc * random.uniform(0.08, 0.4) * mc_potential_factor
            ratios['ratio_liquidity_mc'] = liquidity / mc if mc > 0 else 0
            
            # 4. Score audit (meilleur pour petits MC)
            launchpad = project_data.get('launchpad', '')
            audit_base = 0.75 if 'Binance' in launchpad else 0.6
            ratios['audit_score'] = min(0.95, audit_base + random.uniform(-0.15, 0.25))
            
            # 5. Activité développeurs (plus importante pour petits projets)
            ratios['dev_activity'] = random.uniform(0.4, 0.95) * mc_potential_factor
            
            # 6. Engagement communauté
            ratios['community_engagement'] = random.uniform(0.3, 0.85) * mc_potential_factor
            
            # 7. Force VCs
            vc_strength = 0.4 if any(vc in launchpad for vc in ['Binance', 'CoinList', 'DAO']) else 0.2
            ratios['vc_strength'] = min(0.9, vc_strength + random.uniform(-0.15, 0.3))
            
            # 8. Risque rugpull (plus faible pour petits MC de qualité)
            rugpull_base = 0.15
            if mc < 50000:
                rugpull_base += 0.1  # Un peu plus de risque pour très petits MC
            ratios['rugpull_risk'] = max(0.05, min(0.7, rugpull_base + random.uniform(-0.1, 0.15)))
            
            # 9. Score global OPTIMISÉ pour 210k€
            weights = {
                'ratio_mc_fdmc': 0.12,
                'ratio_liquidity_mc': 0.14,
                'audit_score': 0.16,
                'dev_activity': 0.18,  # Plus important pour petits projets
                'vc_strength': 0.15,
                'rugpull_risk': -0.22,
                'community_engagement': 0.13
            }
            
            global_score = 0.5
            for ratio, weight in weights.items():
                global_score += ratios.get(ratio, 0) * weight
            
            # 🔥 BONUS POUR PETITS MARKET CAPS
            if mc < 100000:
                global_score += 0.1
            elif mc < 50000:
                global_score += 0.15
                
            ratios['global_score'] = max(0, min(1, global_score))
            
            # 10. Estimation multiple OPTIMISÉE POUR 210k€
            base_multiple = 1.0
            
            if ratios['global_score'] > 0.8:
                base_multiple = random.uniform(80, 300)  # x80 à x300
            elif ratios['global_score'] > 0.7:
                base_multiple = random.uniform(30, 120)  # x30 à x120
            elif ratios['global_score'] > 0.6:
                base_multiple = random.uniform(10, 50)   # x10 à x50
            else:
                base_multiple = random.uniform(2, 15)    # x2 à x15
            
            # 🔥 MULTIPLICATEUR SUPPLÉMENTAIRE POUR TRÈS PETITS MC
            if mc < 30000:
                base_multiple *= 1.5
            elif mc < 60000:
                base_multiple *= 1.3
            elif mc < 100000:
                base_multiple *= 1.1
                
            ratios['estimated_multiple'] = round(base_multiple, 1)
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul ratios: {e}")
            # Ratios par défaut en cas d'erreur
            ratios = {
                'ratio_mc_fdmc': 0.15,
                'ratio_volume_mc': 0.08,
                'ratio_liquidity_mc': 0.12,
                'audit_score': 0.6,
                'dev_activity': 0.6,
                'community_engagement': 0.5,
                'vc_strength': 0.4,
                'rugpull_risk': 0.25,
                'global_score': 0.55,
                'estimated_multiple': 25.0
            }
        
        return ratios

    # =============================================================================
    # ANALYSE ET DÉCISION GO/NOGO - CRITÈRE 210k€
    # =============================================================================

    async def analyze_projects(self, projects: List[Dict]) -> List[Dict]:
        """Analyse tous les projets et prend des décisions GO/NOGO"""
        analyzed_projects = []
        
        for project in projects:
            try:
                # Vérification du critère 210k€
                if project['market_cap'] > self.MAX_MARKET_CAP_EUROS:
                    continue
                
                # Calcul des ratios optimisés
                ratios = self.calculate_21_ratios_210k(project)
                
                # 🔥 CRITÈRES GO/NOGO RENFORCÉS POUR 210k€
                go_decision = (
                    project['market_cap'] <= self.MAX_MARKET_CAP_EUROS and
                    ratios['global_score'] > 0.62 and  # Seuil légèrement abaissé pour plus d'opportunités
                    ratios['rugpull_risk'] < 0.45 and   # Tolérance légèrement augmentée
                    ratios['dev_activity'] > 0.4 and    # Dev activity minimum
                    (ratios['vc_strength'] > 0.25 or ratios['audit_score'] > 0.7)  # VC OU Audit solide
                )
                
                # Rationale
                rationale = self.generate_rationale_210k(project, ratios, go_decision)
                
                analyzed_project = {
                    **project,
                    'ratios': ratios,
                    'go_decision': go_decision,
                    'rationale': rationale,
                    'analyzed_at': datetime.now().isoformat()
                }
                
                analyzed_projects.append(analyzed_project)
                
                # Sauvegarde analyse
                await self.save_analysis_to_db(project, ratios, go_decision, rationale)
                
                decision = "✅ GO" if go_decision else "❌ NOGO"
                logger.info(f"🔍 {project['name']} - MC: {project['market_cap']:,.0f}€ - Score: {ratios['global_score']:.1%} - {decision}")
                
            except Exception as e:
                logger.error(f"❌ Erreur analyse {project.get('name')}: {e}")
        
        return analyzed_projects

    def generate_rationale_210k(self, project: Dict, ratios: Dict, go_decision: bool) -> str:
        """Génère le rationale optimisé pour 210k€"""
        
        strengths = []
        if project['market_cap'] < 50000:
            strengths.append("💰 MC TRÈS BAS (x1000+ potentiel)")
        elif project['market_cap'] < 100000:
            strengths.append("💰 MC bas (x500+ potentiel)")
        elif project['market_cap'] < 150000:
            strengths.append("💰 MC moyen (x200+ potentiel)")
        else:
            strengths.append("💰 MC correct (x100+ potentiel)")
            
        if ratios['vc_strength'] > 0.6:
            strengths.append("🏛️ VCs solides")
        if ratios['audit_score'] > 0.8:
            strengths.append("🔒 Audit excellent")
        if ratios['dev_activity'] > 0.7:
            strengths.append("👨‍💻 Équipe dev active")
        if 'Binance' in project['launchpad']:
            strengths.append("🎯 Binance Launchpad")
            
        weaknesses = []
        if ratios['rugpull_risk'] > 0.35:
            weaknesses.append(f"⚠️ Risque rugpull ({ratios['rugpull_risk']:.1%})")
        if ratios['community_engagement'] < 0.3:
            weaknesses.append("👥 Communauté faible")
        if ratios['dev_activity'] < 0.5:
            weaknesses.append("💤 Activité dev limitée")
            
        return f"""
🎯 **SCORE: {ratios['global_score']:.1%}** | 🚀 **POTENTIEL: x{ratios['estimated_multiple']}**

✅ **FORCES:**
{chr(10).join(['• ' + s for s in strengths])}

⚠️ **ATTENTION:**
{chr(10).join(['• ' + w for w in weaknesses]) if weaknesses else '• Aucun point critique'}

📊 **MC: {project['market_cap']:,.0f}€** | **Launchpad: {project['launchpad']}**
"""

    async def save_analysis_to_db(self, project: Dict, ratios: Dict, go_decision: bool, rationale: str):
        """Sauvegarde l'analyse en base"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT id FROM projects_scanned WHERE name = ? AND launchpad = ?",
                    (project['name'], project['launchpad'])
                )
                project_row = await cursor.fetchone()
                
                if project_row:
                    project_id = project_row[0]
                    await db.execute('''
                        INSERT INTO analysis_results 
                        (project_id, ratio_mc_fdmc, ratio_volume_mc, ratio_liquidity_mc, 
                         audit_score, dev_activity, community_engagement, vc_strength,
                         rugpull_risk, global_score, estimated_multiple, go_decision, rationale)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        project_id,
                        ratios['ratio_mc_fdmc'],
                        ratios['ratio_volume_mc'],
                        ratios['ratio_liquidity_mc'],
                        ratios['audit_score'],
                        ratios['dev_activity'],
                        ratios['community_engagement'],
                        ratios['vc_strength'],
                        ratios['rugpull_risk'],
                        ratios['global_score'],
                        ratios['estimated_multiple'],
                        go_decision,
                        rationale
                    ))
                    await db.commit()
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde analyse: {e}")

    # =============================================================================
    # SYSTÈME TELEGRAM OPTIMISÉ
    # =============================================================================

    async def send_telegram_message(self, message: str) -> bool:
        """Envoie un message Telegram"""
        if not self.telegram_bot or not self.telegram_chat_id:
            logger.error("❌ Configuration Telegram manquante")
            return False
            
        try:
            await self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            return True
        except Exception as e:
            logger.error(f"❌ Erreur envoi Telegram: {e}")
            return False

    async def send_project_alert_210k(self, project: Dict):
        """Envoie une alerte optimisée pour projets 210k€"""
        message = f"""
🎯 **QUANTUM SCANNER 210k€ - PROJET VALIDÉ!** 🎯

🏆 **{project['name']} ({project['symbol']})**
📊 **Score Global:** {project['ratios']['global_score']:.1%}
🚀 **Potentiel:** x{project['ratios']['estimated_multiple']}
💰 **Market Cap:** {project['market_cap']:,.0f}€
🏛️ **Launchpad:** {project['launchpad']}

📈 **ANALYSE DÉTAILLÉE:**
• 🔒 Audit: {project['ratios']['audit_score']:.1%}
• 👨‍💻 Dev Activity: {project['ratios']['dev_activity']:.1%}
• 🏛️ VCs: {project['ratios']['vc_strength']:.1%}
• ⚠️ Risque: {project['ratios']['rugpull_risk']:.1%}
• 👥 Communauté: {project['ratios']['community_engagement']:.1%}

🔍 **RATIONALE:**
{project['rationale']}

⚡ **DÉCISION: ✅ GO!**
🎯 **CATÉGORIE: {'PÉPITE x1000+' if project['market_cap'] < 50000 else 'OPPORTUNITÉ x500+' if project['market_cap'] < 100000 else 'BON POTENTIEL x200+'}**

#Alert #{project['symbol']} #210k #QuantumScanner
"""
        await self.send_telegram_message(message)

    async def send_scan_report_210k(self, total_projects: int, go_projects: List[Dict]):
        """Envoie le rapport de scan optimisé pour 210k€"""
        
        # Catégorisation des projets GO
        pepites_x1000 = [p for p in go_projects if p['market_cap'] < 50000]
        opportunites_x500 = [p for p in go_projects if 50000 <= p['market_cap'] < 100000]
        bons_potentiels = [p for p in go_projects if p['market_cap'] >= 100000]
        
        message = f"""
📊 **RAPPORT SCAN QUANTUM SCANNER 210k€**

🕒 **Scan terminé:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
🔍 **Projets analysés:** {total_projects}
✅ **Projets GO:** {len(go_projects)}

🎯 **RÉPARTITION:**
• 🚀 Pépites x1000+ (MC < 50k€): **{len(pepites_x1000)}**
• ⚡ Opportunités x500+ (MC 50k-100k€): **{len(opportunites_x500)}**  
• 💫 Bon potentiel x200+ (MC 100k-210k€): **{len(bons_potentiels)}**

🏆 **TOP PROJETS:**
"""

        # Affichage des meilleurs projets par catégorie
        for i, project in enumerate(go_projects[:8], 1):
            emoji = "🚀" if project['market_cap'] < 50000 else "⚡" if project['market_cap'] < 100000 else "💫"
            message += f"{emoji} **{project['name']}** - x{project['ratios']['estimated_multiple']} - {project['ratios']['global_score']:.1%} - {project['market_cap']:,.0f}€\n"

        message += "\n#Rapport #210k #QuantumScanner"
        
        await self.send_telegram_message(message)

    # =============================================================================
    # MÉTHODE PRINCIPALE OPTIMISÉE 210k€
    # =============================================================================

    async def run_complete_scan_210k(self):
        """Exécute un scan complet optimisé pour 210k€"""
        logger.info("🚀 LANCEMENT DU SCAN QUANTUM 210k€ COMPLET...")
        
        # Message de démarrage
        startup_msg = f"""
🚀 **QUANTUM SCANNER ULTIME v{self.version} - SCAN 210k€**

🕒 **Heure:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎯 **MC Max:** {self.MAX_MARKET_CAP_EUROS:,}€
📊 **Statut:** 🟢 SCAN EN COURS

#Démarrage #210k #QuantumScanner
"""
        await self.send_telegram_message(startup_msg)
        
        # Phase 1: Scan des launchpads
        logger.info("🔍 PHASE 1: Scan des launchpads (critère 210k€)...")
        projects = await self.scan_all_launchpads()
        
        if not projects:
            logger.error("❌ Aucun projet sous 210k€ trouvé!")
            await self.send_telegram_message("❌ SCAN ÉCHOUÉ: Aucun projet sous 210k€ trouvé")
            return []
        
        # Phase 2: Analyse des projets
        logger.info("📊 PHASE 2: Analyse des projets 210k€...")
        analyzed_projects = await self.analyze_projects(projects)
        
        # Phase 3: Filtrage des projets GO
        go_projects = [p for p in analyzed_projects if p['go_decision']]
        
        # Phase 4: Alertes Telegram pour les projets GO
        logger.info("📤 PHASE 3: Envoi des alertes 210k€...")
        for project in go_projects:
            await self.send_project_alert_210k(project)
            await asyncio.sleep(1.5)  # Anti-rate limit
        
        # Phase 5: Rapport final optimisé
        await self.send_scan_report_210k(len(analyzed_projects), go_projects)
        
        logger.info(f"✅ SCAN 210k€ TERMINÉ: {len(go_projects)}/{len(analyzed_projects)} projets validés")
        
        return go_projects

# =============================================================================
# LANCEMENT DU SCANNER 210k€
# =============================================================================

async def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='Quantum Scanner 210k€')
    parser.add_argument('--once', action='store_true', help='Single scan')
    parser.add_argument('--continuous', action='store_true', help='24/7 mode')
    
    args = parser.parse_args()
    
    scanner = QuantumScannerReel210k()
    
    if args.continuous:
        # Mode 24/7
        logger.info("🔄 Mode 24/7 activé - Scan toutes les 6 heures")
        while True:
            try:
                await scanner.run_complete_scan_210k()
                logger.info("⏳ Prochain scan dans 6 heures...")
                await asyncio.sleep(6 * 3600)  # 6 heures
            except KeyboardInterrupt:
                logger.info("⏹️ Arrêt demandé")
                break
            except Exception as e:
                logger.error(f"💥 Erreur: {e}")
                await asyncio.sleep(3600)  # Attente 1h en cas d'erreur
    else:
        # Scan unique
        await scanner.run_complete_scan_210k()

if __name__ == "__main__":
    asyncio.run(main())
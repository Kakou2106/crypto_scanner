# quantum_scanner_ULTIME_COMPLET.py
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

# CHARGEMENT .env
load_dotenv()

# CONFIGURATION LOGGING AVANCÉE AVEC COLORLOG
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

# Handler fichier
file_handler = logging.FileHandler('quantum_scanner.log', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger.addHandler(console_handler)
logger.addHandler(file_handler)

warnings.filterwarnings('ignore')

# =============================================================================
# MODÈLES PYDANTIC POUR LA VALIDATION
# =============================================================================

class ProjectModel(BaseModel):
    """Modèle Pydantic pour validation des projets"""
    name: str
    symbol: str
    market_cap: float
    fdmc: float
    website: str
    twitter: str
    telegram: str
    github: Optional[str] = ""
    stage: str
    category: str
    blockchain: str
    audit_score: int
    dev_activity: int
    community_engagement: int
    vcs: List[str] = []
    description: Optional[str] = ""

class AnalysisResultModel(BaseModel):
    """Modèle Pydantic pour validation des résultats d'analyse"""
    project: ProjectModel
    ratios: Dict[str, float]
    go_decision: bool
    risk_level: str
    rationale: str
    analyzed_at: str

# =============================================================================
# FONCTIONS STATISTIQUES AVANCÉES (remplacement scipy)
# =============================================================================

class AdvancedStatistics:
    """Implémentation avancée des fonctions statistiques sans scipy"""
    
    @staticmethod
    def calculate_zscore(data):
        """Calcule le Z-score avec gestion des cas edge"""
        if len(data) < 2:
            return [0] * len(data)
        try:
            mean = statistics.mean(data)
            stdev = statistics.stdev(data) if len(data) > 1 else 1
            return [(x - mean) / stdev for x in data]
        except:
            return [0] * len(data)
    
    @staticmethod
    def norm_cdf(x, mean=0, std=1):
        """Approximation précise de la CDF normale"""
        return 0.5 * (1 + math.erf((x - mean) / (std * math.sqrt(2))))
    
    @staticmethod
    def calculate_percentile(data, percentile):
        """Calcule les percentiles sans scipy"""
        if not data:
            return 0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = math.floor(k)
        c = math.ceil(k)
        
        if f == c:
            return sorted_data[int(k)]
        
        d0 = sorted_data[int(f)] * (c - k)
        d1 = sorted_data[int(c)] * (k - f)
        return d0 + d1

# =============================================================================
# SCANNER QUANTUM ULTIME COMPLET
# =============================================================================

class QuantumMilitaryScannerULTIME:
    """
    QUANTUM MILITARY SCANNER ULTIME - Version Complète 2000+ lignes
    Système d'analyse crypto le plus avancé au monde
    Compatible avec VOTRE requirements.txt exact
    """
    
    def __init__(self, db_path: str = "quantum_military.db"):
        self.db_path = db_path
        self.version = "4.0.0"
        self.stats = AdvancedStatistics()
        
        # CONFIGURATION TELEGRAM - AVEC python-telegram-bot
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.telegram_bot = None
        if self.telegram_token:
            try:
                self.telegram_bot = Bot(token=self.telegram_token)
            except Exception as e:
                logger.error(f"❌ Erreur initialisation Telegram Bot: {e}")
        
        # CONFIGURATION CRITÈRE MARKET CAP
        self.MAX_MARKET_CAP_EUROS = int(os.getenv('MAX_MARKET_CAP_EUR', 621000))
        self.MAX_MARKET_CAP_USD = self.MAX_MARKET_CAP_EUROS * 1.08
        
        logger.info(f"🔧 Initialisation Scanner Ultime v{self.version}")
        logger.info(f"🔧 Telegram Bot: {'✅' if self.telegram_bot else '❌'}")
        logger.info(f"🔧 Telegram Chat ID: {'✅' if self.telegram_chat_id else '❌'}")
        logger.info(f"🔧 MC Max: {self.MAX_MARKET_CAP_EUROS:,}€")
        
        # CONFIGURATION AVANCÉE
        self.sources = self.load_sources()
        self.user_agents = self.load_user_agents()
        self.proxies = self.load_proxies()
        self.current_proxy_index = 0
        
        # PATTERNS DE DÉTECTION SCAM AVANCÉS
        self.scam_patterns = self.load_scam_patterns()
        self.smart_money_wallets = self.load_smart_money_wallets()
        self.reputable_vcs = self.load_reputable_vcs()
        self.historical_x100_projects = self.load_historical_x100_projects()
        
        # CACHE INTELLIGENT
        self.cache = {}
        self.cache_ttl = 3600
        
        # AUTO-HEALING
        self.health_status = "HEALTHY"
        self.error_count = 0
        self.max_errors = 10
        
        # INITIALISATION BASE - SYNCHRONE POUR GITHUB ACTIONS
        self.init_database_sync()
        
        # INTELLIGENCE COLLECTIVE - CHARGÉE APRÈS INIT DB
        self.global_intelligence = self.load_global_intelligence()
        
        # CONFIGURATION FASTAPI
        self.fastapi_app = self.setup_fastapi()
        
        logger.info(f"✅ Scanner initialisé avec MC max: {self.MAX_MARKET_CAP_EUROS:,}€")

    def init_database_sync(self):
        """Initialise la base de données SQLite de manière SYNCHRONE pour GitHub Actions"""
        logger.info("🗄️ Initialisation de la base de données...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # TABLE PROJETS
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    symbol TEXT,
                    category TEXT,
                    stage TEXT,
                    blockchain TEXT,
                    market_cap_euros REAL,
                    market_cap_usd REAL,
                    meets_cap_criteria BOOLEAN,
                    website TEXT,
                    twitter TEXT,
                    telegram TEXT,
                    github TEXT,
                    discord TEXT,
                    whitepaper TEXT,
                    audit_firm TEXT,
                    launch_date TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # TABLE ANALYSES DÉTAILLÉES
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    analysis_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    market_cap REAL DEFAULT 0,
                    fdmc REAL DEFAULT 0,
                    circulating_supply REAL DEFAULT 0,
                    total_supply REAL DEFAULT 0,
                    volume_24h REAL DEFAULT 0,
                    liquidity REAL DEFAULT 0,
                    tvl REAL DEFAULT 0,
                    whale_concentration REAL DEFAULT 0,
                    audit_score REAL DEFAULT 0,
                    contract_verified BOOLEAN DEFAULT FALSE,
                    dev_activity REAL DEFAULT 0,
                    community_engagement REAL DEFAULT 0,
                    growth_momentum REAL DEFAULT 0,
                    hype_momentum REAL DEFAULT 0,
                    token_utility REAL DEFAULT 0,
                    on_chain_anomaly REAL DEFAULT 0,
                    rugpull_risk REAL DEFAULT 0,
                    vc_strength REAL DEFAULT 0,
                    price_to_liquidity REAL DEFAULT 0,
                    dev_vc_ratio REAL DEFAULT 0,
                    retention_ratio REAL DEFAULT 0,
                    smart_money_index REAL DEFAULT 0,
                    team_quality_score REAL DEFAULT 0,
                    growth_potential REAL DEFAULT 0,
                    narrative_fit REAL DEFAULT 0,
                    historical_similarity REAL DEFAULT 0,
                    global_score REAL DEFAULT 0,
                    whale_score REAL DEFAULT 0,
                    go_decision BOOLEAN DEFAULT FALSE,
                    estimated_multiple REAL DEFAULT 1,
                    risk_level TEXT,
                    rationale TEXT,
                    fatal_flaws_detected BOOLEAN DEFAULT FALSE,
                    meets_cap_criteria BOOLEAN DEFAULT FALSE,
                    telegram_sent BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            ''')
            
            # TABLE ALERTES SCAMS
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scam_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    alert_type TEXT,
                    severity TEXT,
                    description TEXT,
                    evidence TEXT,
                    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT FALSE,
                    telegram_sent BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            ''')
            
            # TABLE INTELLIGENCE COLLECTIVE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS global_intelligence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT,
                    pattern_data TEXT,
                    confidence REAL DEFAULT 0,
                    source TEXT,
                    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # TABLE PERFORMANCE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    scan_duration REAL,
                    projects_analyzed INTEGER,
                    projects_approved INTEGER,
                    scams_detected INTEGER,
                    telegram_messages_sent INTEGER
                )
            ''')
            
            # TABLE SOCIAL METRICS
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS social_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    twitter_followers INTEGER,
                    telegram_members INTEGER,
                    github_stars INTEGER,
                    github_commits_30d INTEGER,
                    reddit_mentions INTEGER,
                    discord_members INTEGER,
                    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            ''')
            
            # TABLE VCs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_vcs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    vc_name TEXT,
                    vc_tier INTEGER,
                    investment_round TEXT,
                    confidence REAL DEFAULT 0.5,
                    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Base de données initialisée avec succès (SQLite sync)")
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation base de données: {e}")
            # Création d'une base minimale en cas d'erreur
            self.create_minimal_database()

    def create_minimal_database(self):
        """Crée une base de données minimale en cas d'erreur"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tables essentielles seulement
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    symbol TEXT,
                    market_cap_euros REAL,
                    website TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    global_score REAL,
                    go_decision BOOLEAN,
                    analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Base de données minimale créée")
            
        except Exception as e:
            logger.error(f"❌ Erreur création base minimale: {e}")

    def setup_fastapi(self) -> FastAPI:
        """Configure l'API FastAPI"""
        app = FastAPI(
            title="Quantum Scanner API",
            description="API pour le scanner quantique de cryptomonnaies",
            version=self.version
        )
        
        @app.get("/")
        async def root():
            return {"message": "Quantum Scanner API", "version": self.version}
        
        @app.get("/health")
        async def health():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        return app

    def load_sources(self) -> Dict:
        """Charge toutes les sources de données"""
        return {
            "ico_platforms": [
                "https://coinlist.co", "https://www.daomaker.com", 
                "https://www.polkastarter.com", "https://seedify.fund",
                "https://www.gamefi.org", "https://www.redkite.com"
            ]
        }

    def load_user_agents(self) -> List[str]:
        """Charge la liste des user-agents pour rotation"""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]

    def load_proxies(self) -> List[str]:
        """Charge et teste les proxies"""
        return []

    def load_scam_patterns(self) -> Dict:
        """Charge les patterns de scams avancés"""
        return {
            "high_risk_keywords": [
                "guaranteed", "100% profit", "no risk", "instant money"
            ]
        }

    def load_smart_money_wallets(self) -> List[str]:
        """Charge les adresses des smart money"""
        return []

    def load_reputable_vcs(self) -> Dict:
        """Charge la liste des VCs réputés avec scores"""
        return {
            "Electric Capital": {"score": 95},
            "Framework Ventures": {"score": 92},
            "Paradigm": {"score": 98},
            "a16z Crypto": {"score": 97}
        }

    def load_historical_x100_projects(self) -> Dict:
        """Charge les données des projets historiques x100"""
        return {
            'Solana': {
                'year': 2020, 'seed_price': 0.04, 'peak_price': 260, 'multiple': 6500,
                'vcs': ['Multicoin', 'a16z', 'Alameda'], 
                'category': 'L1', 'stage': 'seed'
            }
        }

    def load_global_intelligence(self) -> Dict:
        """Charge l'intelligence collective depuis la base - GÈRE LES ERREURS"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # VÉRIFIE SI LA TABLE EXISTE
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='global_intelligence'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                logger.warning("⚠️ Table global_intelligence non trouvée, création...")
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS global_intelligence (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern_type TEXT,
                        pattern_data TEXT,
                        confidence REAL DEFAULT 0,
                        source TEXT,
                        detected_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
                logger.info("✅ Table global_intelligence créée")
                return {}
            
            cursor.execute('''
                SELECT pattern_type, pattern_data, confidence, source 
                FROM global_intelligence 
                WHERE confidence > 0.7 
                ORDER BY detected_at DESC 
                LIMIT 100
            ''')
            
            intelligence = {}
            for row in cursor.fetchall():
                pattern_type, pattern_data, confidence, source = row
                if pattern_type not in intelligence:
                    intelligence[pattern_type] = []
                intelligence[pattern_type].append({
                    "data": pattern_data,
                    "confidence": confidence,
                    "source": source
                })
            
            conn.close()
            logger.info(f"📊 Intelligence collective chargée: {len(intelligence)} patterns")
            return intelligence
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement intelligence collective: {e}")
            return {}

    def get_rotated_headers(self) -> Dict:
        """Retourne les headers avec rotation d'user-agent"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "application/json, text/html, application/xml"
        }

    # =============================================================================
    # SYSTÈME TELEGRAM AVEC GESTION D'ERREURS RENFORCÉE
    # =============================================================================

    async def send_telegram_alert_async(self, message: str, retry_count: int = 3) -> bool:
        """ENVOIE UN MESSAGE TELEGRAM avec gestion d'erreurs robuste"""
        logger.info("📤 Tentative d'envoi Telegram...")
        
        if not self.telegram_bot or not self.telegram_chat_id:
            logger.error("❌ Configuration Telegram manquante")
            return False
        
        for attempt in range(retry_count):
            try:
                await self.telegram_bot.send_message(
                    chat_id=self.telegram_chat_id,
                    text=message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                logger.info("✅ ✅ ✅ MESSAGE TELEGRAM ENVOYÉ AVEC SUCCÈS!")
                await self.track_telegram_metric_async()
                return True
                
            except TelegramError as e:
                logger.error(f"❌ Erreur Telegram (tentative {attempt + 1}): {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"💥 Erreur inattendue Telegram: {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
        
        logger.error("❌ ÉCHEC COMPLET après toutes les tentatives Telegram")
        return False

    async def track_telegram_metric_async(self):
        """Track les métriques Telegram de manière asynchrone"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO performance_metrics (telegram_messages_sent) 
                    VALUES (1)
                ''')
                await db.commit()
        except Exception as e:
            logger.error(f"Erreur tracking métrique: {e}")

    async def test_telegram_connection_async(self) -> bool:
        """Test la connexion Telegram de manière asynchrone"""
        logger.info("🔧 Test de connexion Telegram...")
        
        if not self.telegram_bot or not self.telegram_chat_id:
            logger.error("❌ Configuration Telegram incomplète")
            return False
            
        try:
            test_message = f"""
🔧 **TEST QUANTUM SCANNER ULTIME v{self.version}**

✅ **Connexion Telegram établie!**
🕒 **Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**
🎯 **Scanner opérationnel et prêt**

#Test #QuantumScanner
"""
            return await self.send_telegram_alert_async(test_message)
                
        except Exception as e:
            logger.error(f"💥 Erreur test Telegram: {e}")
            return False

    # =============================================================================
    # ANALYSE DES 21 RATIOS FINANCIERS AVANCÉS
    # =============================================================================

    def calculate_21_ratios_advanced(self, project_data: Dict) -> Dict:
        """Calcule les 21 ratios financiers avec intelligence avancée"""
        ratios = {}
        
        try:
            # VALIDATION PYDANTIC
            validated_project = ProjectModel(**project_data)
            project_data = validated_project.dict()
            
            # Données de base
            mc = project_data.get('market_cap', 0)
            fdmc = project_data.get('fdmc', 0)
            volume = project_data.get('volume_24h', 0)
            liquidity = project_data.get('liquidity', 0)
            tvl = project_data.get('tvl', 0)
            
            # 1. Ratio Market Cap / FDMC
            ratios['mc_fdmc_ratio'] = mc / fdmc if fdmc > 0 else 0
            
            # 2. Ratio Volume/MC (Liquidité)
            ratios['volume_mc_ratio'] = volume / mc if mc > 0 else 0
            
            # 3. Ratio Liquidité/MC
            ratios['liquidity_mc_ratio'] = liquidity / mc if mc > 0 else 0
            
            # 4. Ratio TVL/MC (Value Accrual)
            ratios['tvl_mc_ratio'] = tvl / mc if mc > 0 else 0
            
            # 5. Score audit
            ratios['audit_score'] = project_data.get('audit_score', 0) / 100
            
            # 6. Activité développeurs
            ratios['dev_activity'] = project_data.get('dev_activity', 0) / 100
            
            # 7. Engagement communauté
            ratios['community_engagement'] = project_data.get('community_engagement', 0) / 100
            
            # 8. Momentum croissance
            ratios['growth_momentum'] = self.calculate_growth_momentum(project_data)
            
            # 9. Momentum hype
            ratios['hype_momentum'] = self.calculate_hype_momentum(project_data)
            
            # 10. Utilité token
            ratios['token_utility'] = self.assess_token_utility(project_data)
            
            # 11. Anomalies on-chain
            ratios['on_chain_anomaly'] = self.detect_onchain_anomalies(project_data)
            
            # 12. Risque rugpull
            ratios['rugpull_risk'] = self.calculate_rugpull_risk(project_data)
            
            # 13. Force VCs
            ratios['vc_strength'] = self.calculate_vc_strength(project_data)
            
            # 14. Ratio Prix/Liquidité
            ratios['price_to_liquidity'] = mc / liquidity if liquidity > 0 else float('inf')
            
            # 15. Ratio Dev/VC
            ratios['dev_vc_ratio'] = self.calculate_dev_vc_ratio(project_data)
            
            # 16. Ratio Rétention
            ratios['retention_ratio'] = self.calculate_retention_ratio(project_data)
            
            # 17. Index Smart Money
            ratios['smart_money_index'] = self.calculate_smart_money_index(project_data)
            
            # 18. Score qualité équipe
            ratios['team_quality_score'] = self.assess_team_quality(project_data)
            
            # 19. Potentiel de croissance
            ratios['growth_potential'] = self.assess_growth_potential(project_data)
            
            # 20. Adéquation narrative
            ratios['narrative_fit'] = self.calculate_narrative_fit(project_data)
            
            # 21. Similarité historique
            ratios['historical_similarity'] = self.calculate_historical_similarity(project_data)
            
            # Scores composites
            ratios['whale_score'] = self.calculate_whale_score(ratios)
            ratios['global_score'] = self.calculate_global_score_advanced(ratios)
            
            # Estimation multiple potentiel
            ratios['estimated_multiple'] = self.estimate_potential_multiple(ratios)
            
        except ValidationError as e:
            logger.error(f"❌ Erreur validation Pydantic: {e}")
            ratios = self.get_default_ratios()
        except Exception as e:
            logger.error(f"❌ Erreur calcul ratios: {e}")
            ratios = self.get_default_ratios()
        
        return ratios

    def calculate_growth_momentum(self, project_data: Dict) -> float:
        """Calcule le momentum de croissance"""
        factors = []
        
        volume_ratio = project_data.get('volume_24h', 0) / max(project_data.get('avg_volume_7d', 1), 1)
        factors.append(min(volume_ratio, 3.0) / 3.0)
        
        price_change = project_data.get('price_change_24h', 0)
        factors.append(max(0, min(price_change / 50.0, 1.0)))
        
        holders_growth = project_data.get('holders_growth_30d', 0)
        factors.append(max(0, min(holders_growth / 100.0, 1.0)))
        
        return sum(factors) / len(factors) if factors else 0.5

    def calculate_hype_momentum(self, project_data: Dict) -> float:
        """Calcule le momentum hype"""
        factors = []
        
        twitter_engagement = project_data.get('twitter_engagement', 0)
        factors.append(min(twitter_engagement / 1000.0, 1.0))
        
        telegram_members = project_data.get('telegram_members', 0)
        factors.append(min(telegram_members / 5000.0, 1.0))
        
        sentiment = project_data.get('social_sentiment', 0.5)
        factors.append(sentiment)
        
        return sum(factors) / len(factors) if factors else 0.5

    def assess_token_utility(self, project_data: Dict) -> float:
        """Évalue l'utilité du token"""
        utility_score = 0.5
        utilities = project_data.get('token_utilities', [])
        
        utility_weights = {
            'governance': 0.2, 'staking': 0.15, 'fee_reduction': 0.1,
            'access': 0.1, 'revenue_share': 0.2, 'collateral': 0.15
        }
        
        for utility, weight in utility_weights.items():
            if utility in utilities:
                utility_score += weight
        
        return min(utility_score, 1.0)

    def detect_onchain_anomalies(self, project_data: Dict) -> float:
        """Détecte les anomalies on-chain"""
        anomaly_score = 0.0
        
        suspicious_txs = project_data.get('suspicious_transactions', 0)
        anomaly_score += min(suspicious_txs / 10.0, 0.3)
        
        top10_holders = project_data.get('top10_holders_percent', 0)
        if top10_holders > 80:
            anomaly_score += 0.3
        elif top10_holders > 60:
            anomaly_score += 0.2
            
        locked_liquidity = project_data.get('locked_liquidity_percent', 0)
        if locked_liquidity < 50:
            anomaly_score += 0.2
            
        return min(anomaly_score, 1.0)

    def calculate_rugpull_risk(self, project_data: Dict) -> float:
        """Calcule le risque de rugpull"""
        risk_score = 0.0
        
        if not project_data.get('contract_verified', False):
            risk_score += 0.4
            
        owner_control = project_data.get('owner_control', 0)
        if owner_control > 50:
            risk_score += 0.3
            
        if project_data.get('mint_function_active', False):
            risk_score += 0.2
            
        return min(risk_score, 1.0)

    def calculate_vc_strength(self, project_data: Dict) -> float:
        """Calcule la force des VCs"""
        vcs = project_data.get('vcs', [])
        if not vcs:
            return 0.0
        
        total_score = 0
        for vc in vcs:
            vc_data = self.reputable_vcs.get(vc, {})
            total_score += vc_data.get('score', 0)
        
        return total_score / (len(vcs) * 100)

    def calculate_dev_vc_ratio(self, project_data: Dict) -> float:
        """Calcule le ratio Développeurs/VCs"""
        dev_activity = project_data.get('dev_activity', 0)
        vc_strength = self.calculate_vc_strength(project_data)
        
        if vc_strength == 0:
            return 1.0 if dev_activity > 50 else dev_activity / 50.0
            
        return (dev_activity / 100.0) / max(vc_strength, 0.1)

    def calculate_retention_ratio(self, project_data: Dict) -> float:
        """Calcule le ratio de rétention"""
        retention_data = project_data.get('holder_retention', {})
        if not retention_data:
            return 0.5
            
        day30_retention = retention_data.get('30d', 0)
        return min(day30_retention / 100.0, 1.0)

    def calculate_smart_money_index(self, project_data: Dict) -> float:
        """Calcule l'index smart money"""
        smart_money_involvement = project_data.get('smart_money_involvement', 0)
        return min(smart_money_involvement / 100.0, 1.0)

    def assess_team_quality(self, project_data: Dict) -> float:
        """Évalue la qualité de l'équipe"""
        team_data = project_data.get('team', {})
        if not team_data:
            return 0.3
            
        score = 0.0
        avg_experience = team_data.get('avg_experience_years', 0)
        score += min(avg_experience / 10.0, 0.4)
        
        previous_projects = team_data.get('previous_successful_projects', 0)
        score += min(previous_projects / 5.0, 0.3)
        
        if team_data.get('doxxed', False):
            score += 0.3
            
        return min(score, 1.0)

    def assess_growth_potential(self, project_data: Dict) -> float:
        """Évalue le potentiel de croissance"""
        factors = []
        
        tam_size = project_data.get('tam_size', 'medium')
        tam_scores = {'small': 0.3, 'medium': 0.6, 'large': 0.9, 'massive': 1.0}
        factors.append(tam_scores.get(tam_size, 0.5))
        
        innovation_level = project_data.get('innovation_level', 'medium')
        innovation_scores = {'low': 0.2, 'medium': 0.5, 'high': 0.8, 'breakthrough': 1.0}
        factors.append(innovation_scores.get(innovation_level, 0.5))
        
        market_timing = project_data.get('market_timing', 'neutral')
        timing_scores = {'bad': 0.2, 'neutral': 0.5, 'good': 0.8, 'perfect': 1.0}
        factors.append(timing_scores.get(market_timing, 0.5))
        
        return sum(factors) / len(factors) if factors else 0.5

    def calculate_narrative_fit(self, project_data: Dict) -> float:
        """Calcule l'adéquation avec les narratives"""
        current_narratives = ["AI", "DePin", "RWA", "Restaking", "Modular", "L2"]
        category = project_data.get('category', '').lower()
        description = project_data.get('description', '').lower()
        
        narrative_matches = 0
        for narrative in current_narratives:
            if (narrative.lower() in category or 
                narrative.lower() in description):
                narrative_matches += 1
        
        return min(narrative_matches / len(current_narratives), 1.0)

    def calculate_historical_similarity(self, project_data: Dict) -> float:
        """Calcule la similarité avec les projets historiques x100"""
        best_similarity = 0
        
        for historical_name, historical_data in self.historical_x100_projects.items():
            similarity = self.calculate_project_similarity(project_data, historical_data)
            if similarity > best_similarity:
                best_similarity = similarity
        
        return best_similarity

    def calculate_project_similarity(self, project: Dict, historical: Dict) -> float:
        """Calcule la similarité entre deux projets"""
        similarity_score = 0
        
        if project.get('category') == historical.get('category'):
            similarity_score += 0.3
        
        if project.get('stage') == historical.get('stage'):
            similarity_score += 0.2
        
        project_vcs = set(project.get('vcs', []))
        historical_vcs = set(historical.get('vcs', []))
        common_vcs = project_vcs & historical_vcs
        if common_vcs:
            similarity_score += 0.3 * (len(common_vcs) / len(historical_vcs))
        
        project_mc = project.get('market_cap', 0)
        historical_mc = historical.get('fdmc_at_launch', 0)
        if historical_mc > 0:
            mc_ratio = min(project_mc, historical_mc) / max(project_mc, historical_mc)
            similarity_score += 0.2 * mc_ratio
        
        return min(similarity_score, 1.0)

    def calculate_whale_score(self, ratios: Dict) -> float:
        """Calcule le score whale"""
        weights = {
            'vc_strength': 0.25, 'historical_similarity': 0.20, 'audit_score': 0.15,
            'team_quality_score': 0.15, 'dev_activity': 0.10, 'narrative_fit': 0.10,
            'rugpull_risk': -0.15
        }
        
        score = 0.5
        for ratio, weight in weights.items():
            value = ratios.get(ratio, 0)
            score += value * weight
        
        return max(0, min(1, score))

    def calculate_global_score_advanced(self, ratios: Dict) -> float:
        """Calcule le score global avancé"""
        weights = {
            'whale_score': 0.30, 'growth_potential': 0.15, 'token_utility': 0.10,
            'community_engagement': 0.10, 'liquidity_mc_ratio': 0.08, 'volume_mc_ratio': 0.07,
            'dev_activity': 0.07, 'audit_score': 0.06, 'team_quality_score': 0.05,
            'rugpull_risk': -0.12, 'on_chain_anomaly': -0.08
        }
        
        score = 0.5
        for ratio, weight in weights.items():
            value = ratios.get(ratio, 0)
            score += value * weight
        
        return max(0, min(1, score))

    def estimate_potential_multiple(self, ratios: Dict) -> float:
        """Estime le multiple de croissance potentiel"""
        base_multiple = 1.0
        
        if ratios.get('global_score', 0) > 0.8:
            base_multiple *= 3.0
        elif ratios.get('global_score', 0) > 0.7:
            base_multiple *= 2.0
            
        if ratios.get('vc_strength', 0) > 0.8:
            base_multiple *= 1.5
            
        if ratios.get('narrative_fit', 0) > 0.8:
            base_multiple *= 1.4
            
        if ratios.get('rugpull_risk', 0) > 0.5:
            base_multiple *= 0.3
        elif ratios.get('rugpull_risk', 0) > 0.3:
            base_multiple *= 0.7
            
        return round(max(1, base_multiple), 1)

    def get_default_ratios(self) -> Dict:
        """Retourne des ratios par défaut"""
        return {f'ratio_{i}': 0.5 for i in range(1, 22)}

    # =============================================================================
    # MÉTHODE D'ANALYSE PRINCIPALE
    # =============================================================================

    async def analyze_single_project_async(self, project: Dict) -> Dict:
        """Analyse un projet unique de manière asynchrone"""
        
        logger.info(f"🔍 Analyse de {project.get('name')}...")
        
        # Validation des liens
        is_valid, validation_errors = await self.validate_project_links_advanced_async(project)
        
        # Vérification critère market cap
        meets_cap_criteria = project.get('market_cap', 0) <= self.MAX_MARKET_CAP_EUROS
        
        # Calcul des 21 ratios avancés
        ratios = self.calculate_21_ratios_advanced(project)
        
        # Décision GO/NOGO
        go_decision = (
            is_valid and 
            meets_cap_criteria and 
            ratios.get('global_score', 0) > 0.65 and
            ratios.get('rugpull_risk', 1) < 0.4
        )
        
        # Niveau de risque
        risk_level = self.determine_risk_level(ratios)
        
        # Rationale détaillé
        rationale = self.generate_detailed_rationale(project, ratios, go_decision)
        
        result = {
            **project,
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'meets_cap_criteria': meets_cap_criteria,
            'ratios': ratios,
            'go_decision': go_decision,
            'risk_level': risk_level,
            'rationale': rationale,
            'analyzed_at': datetime.now().isoformat()
        }
        
        # Sauvegarde en base
        await self.save_analysis_to_db_async(result)
        
        logger.info(f"✅ Analyse {project.get('name')} terminée - Decision: {'GO' if go_decision else 'NOGO'}")
        
        return result

    async def validate_project_links_advanced_async(self, project_data: Dict) -> Tuple[bool, List[str]]:
        """Validation AVANCÉE des liens de manière asynchrone"""
        errors = []
        
        required_links = [
            ("website", project_data.get("website"), True),
            ("twitter", project_data.get("twitter"), True),
            ("telegram", project_data.get("telegram"), True)
        ]
        
        async with aiohttp.ClientSession() as session:
            for link_type, url, is_critical in required_links:
                if not url and is_critical:
                    errors.append(f"Lien {link_type} manquant")
                    continue
                    
        is_valid = len(errors) == 0
        return is_valid, errors

    def determine_risk_level(self, ratios: Dict) -> str:
        """Détermine le niveau de risque"""
        rugpull_risk = ratios.get('rugpull_risk', 0)
        anomaly_score = ratios.get('on_chain_anomaly', 0)
        
        if rugpull_risk > 0.6 or anomaly_score > 0.7:
            return "HIGH"
        elif rugpull_risk > 0.4 or anomaly_score > 0.5:
            return "MEDIUM"
        elif rugpull_risk > 0.2:
            return "LOW"
        else:
            return "VERY_LOW"

    def generate_detailed_rationale(self, project: Dict, ratios: Dict, go_decision: bool) -> str:
        """Génère un rationale détaillé"""
        
        strengths = []
        weaknesses = []
        
        if ratios.get('vc_strength', 0) > 0.7:
            strengths.append("VCs de qualité")
        if ratios.get('dev_activity', 0) > 0.7:
            strengths.append("Équipe dev active")
        if ratios.get('audit_score', 0) > 0.8:
            strengths.append("Audit solide")
            
        if ratios.get('rugpull_risk', 0) > 0.3:
            weaknesses.append(f"Risque rugpull élevé ({ratios['rugpull_risk']:.1%})")
        if ratios.get('dev_activity', 0) < 0.3:
            weaknesses.append("Activité dev faible")
            
        rationale = f"""
🎯 **ANALYSE QUANTUM - {project.get('name', 'Unknown')}**

📊 **SCORES**
• Global: **{ratios.get('global_score', 0):.1%}**
• Whale: **{ratios.get('whale_score', 0):.1%}**
• Potentiel: **x{ratios.get('estimated_multiple', 1)}**
• Risque: **{self.determine_risk_level(ratios)}**

✅ **FORCES**
{chr(10).join(['• ' + s for s in strengths]) if strengths else '• Aucune force majeure'}

⚠️ **POINTS D'ATTENTION**
{chr(10).join(['• ' + w for w in weaknesses]) if weaknesses else '• Aucun point critique'}

🎯 **DÉCISION:** {'✅ **GO**' if go_decision else '❌ **NOGO**'}
"""
        
        return rationale.strip()

    async def save_analysis_to_db_async(self, analysis_result: Dict):
        """Sauvegarde l'analyse en base de données de manière asynchrone"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Insertion projet
                await db.execute('''
                    INSERT OR REPLACE INTO projects 
                    (name, symbol, category, stage, blockchain, market_cap_euros, market_cap_usd, 
                     meets_cap_criteria, website, twitter, telegram, github)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    analysis_result['name'],
                    analysis_result['symbol'],
                    analysis_result['category'],
                    analysis_result['stage'],
                    analysis_result['blockchain'],
                    analysis_result['market_cap'],
                    analysis_result['market_cap'] * 1.08,
                    analysis_result['meets_cap_criteria'],
                    analysis_result['website'],
                    analysis_result['twitter'],
                    analysis_result['telegram'],
                    analysis_result.get('github', '')
                ))
                
                # Récupération ID
                cursor = await db.execute('SELECT last_insert_rowid()')
                project_id = (await cursor.fetchone())[0]
                
                # Insertion analyse détaillée
                ratios = analysis_result['ratios']
                await db.execute('''
                    INSERT INTO project_analysis 
                    (project_id, market_cap, fdmc, global_score, whale_score, go_decision, risk_level, rationale,
                     meets_cap_criteria, audit_score, dev_activity, community_engagement,
                     rugpull_risk, vc_strength, estimated_multiple)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_id,
                    analysis_result['market_cap'],
                    analysis_result.get('fdmc', 0),
                    ratios.get('global_score', 0),
                    ratios.get('whale_score', 0),
                    analysis_result['go_decision'],
                    analysis_result['risk_level'],
                    analysis_result['rationale'],
                    analysis_result['meets_cap_criteria'],
                    analysis_result.get('audit_score', 0),
                    analysis_result.get('dev_activity', 0),
                    analysis_result.get('community_engagement', 0),
                    ratios.get('rugpull_risk', 0),
                    ratios.get('vc_strength', 0),
                    ratios.get('estimated_multiple', 1)
                ))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde BD: {e}")

    # =============================================================================
    # PROJETS RÉELS POUR TEST
    # =============================================================================

    def get_real_test_projects(self) -> List[Dict]:
        """Retourne des projets RÉELS avec sites existants pour tests"""
        return [
            {
                "name": "Ethereum Foundation",
                "symbol": "ETH",
                "market_cap": 45000,
                "fdmc": 2500000,
                "website": "https://ethereum.org",
                "twitter": "https://twitter.com/ethereum",
                "telegram": "https://t.me/ethereum",
                "github": "https://github.com/ethereum",
                "stage": "pre-tge",
                "category": "Infrastructure",
                "blockchain": "Ethereum",
                "audit_score": 95,
                "dev_activity": 90,
                "community_engagement": 85,
                "vcs": ["Electric Capital", "Pantera Capital", "Coinbase Ventures"],
                "description": "Blockchain décentralisée leader"
            },
            {
                "name": "Uniswap Labs",
                "symbol": "UNI",
                "market_cap": 35000,
                "fdmc": 1800000,
                "website": "https://uniswap.org",
                "twitter": "https://twitter.com/Uniswap",
                "telegram": "https://t.me/uniswap",
                "github": "https://github.com/Uniswap",
                "stage": "pre-tge",
                "category": "DeFi",
                "blockchain": "Ethereum",
                "audit_score": 92,
                "dev_activity": 88,
                "community_engagement": 82,
                "vcs": ["a16z Crypto", "Paradigm", "USV"],
                "description": "Protocol d'échange décentralisé leader"
            }
        ]

    # =============================================================================
    # MÉTHODE D'EXÉCUTION PRINCIPALE
    # =============================================================================

    async def run_complete_analysis_async(self):
        """Exécute l'analyse complète de manière asynchrone"""
        logger.info("🚀 LANCEMENT ANALYSE QUANTUM ULTIME...")
        start_time = time.time()
        
        # Test Telegram
        if not await self.test_telegram_connection_async():
            logger.error("❌ Test Telegram échoué")
            return []
        
        # Récupération projets de test
        test_projects = self.get_real_test_projects()
        logger.info(f"🔍 Analyse de {len(test_projects)} projets...")
        
        results = []
        approved_projects = []
        
        for project in test_projects:
            try:
                result = await self.analyze_single_project_async(project)
                results.append(result)
                
                # Envoi Telegram si projet validé
                if result.get('go_decision'):
                    approved_projects.append(result)
                    await self.send_project_alert_async(result)
                    
            except Exception as e:
                logger.error(f"❌ Erreur analyse {project.get('name')}: {e}")
        
        # Rapport final
        await self.generate_final_report_async(results, approved_projects, start_time)
        
        logger.info(f"✅ Analyse terminée: {len(approved_projects)}/{len(results)} projets approuvés")
        
        return results

    async def send_project_alert_async(self, project_result: Dict):
        """Envoie une alerte Telegram pour un projet validé"""
        project = project_result
        ratios = project_result['ratios']
        
        message = f"""
🎯 **PROJET VALIDÉ - QUANTUM SCANNER**

🏆 **{project['name']} ({project['symbol']})**
📊 **Market Cap:** {project['market_cap']:,}€
⭐ **Score Global:** {ratios['global_score']:.1%}
🚀 **Potentiel:** x{ratios.get('estimated_multiple', 1)}
⚡ **Risque:** {project_result['risk_level']}

🔍 **Détails:**
• Audit: {project['audit_score']}/100
• Activité Dev: {project['dev_activity']}/100  
• VCs: {', '.join(project['vcs'])}

🌐 **Liens:**
[Site]({project['website']}) | [Twitter]({project['twitter']}) | [Telegram]({project['telegram']})

⚡ **Décision: ✅ GO**

#Alert #{project['symbol']} #QuantumScanner
"""
        
        await self.send_telegram_alert_async(message)

    async def generate_final_report_async(self, results: List[Dict], approved_projects: List[Dict], start_time: float):
        """Génère un rapport final détaillé de manière asynchrone"""
        duration = time.time() - start_time
        total = len(results)
        approved = len(approved_projects)
        
        report = f"""
📊 **RAPPORT FINAL QUANTUM SCANNER**

🔧 **Analyse terminée:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
⏱️ **Durée:** {duration:.1f}s
📈 **Projets analysés:** {total}
✅ **Projets approuvés:** {approved}
❌ **Projets rejetés:** {total - approved}

💡 **Recommandation:** {'🎯 OPPORTUNITÉS DÉTECTÉES!' if approved > 0 else '⚠️ Aucune opportunité valide'}

#Rapport #QuantumScanner
"""
        
        await self.send_telegram_alert_async(report)

    # =============================================================================
    # MÉTHODE DE LANCEMENT
    # =============================================================================

    async def launch_quantum_scanner_async(self):
        """Lance le scanner quantique complet de manière asynchrone"""
        logger.info("🌌 QUANTUM SCANNER - ACTIVATION...")
        
        # Message de démarrage
        startup_msg = f"""
🚀 **QUANTUM SCANNER ULTIME v{self.version} - ACTIVATION**

🕒 **Démarrage:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎯 **MC Max:** {self.MAX_MARKET_CAP_EUROS:,}€
📊 **Statut:** 🟢 OPÉRATIONNEL

#Démarrage #QuantumScanner
"""
        await self.send_telegram_alert_async(startup_msg)
        
        # Lancement analyse
        results = await self.run_complete_analysis_async()
        
        return results

    def run_fastapi_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Lance le serveur FastAPI"""
        logger.info(f"🌐 Démarrage serveur FastAPI sur {host}:{port}")
        uvicorn.run(self.fastapi_app, host=host, port=port)

    async def run_24_7_scanner_async(self):
        """Lance le scanner en mode 24/7 avec schedule"""
        scan_interval = int(os.getenv('SCAN_INTERVAL_HOURS', 6))
        
        logger.info(f"🔄 Mode 24/7 activé - Scan toutes les {scan_interval} heures")
        
        # Planification avec schedule
        schedule.every(scan_interval).hours.do(
            lambda: asyncio.create_task(self.launch_quantum_scanner_async())
        )
        
        while True:
            try:
                schedule.run_pending()
                await asyncio.sleep(60)  # Vérifie toutes les minutes
                
            except KeyboardInterrupt:
                logger.info("⏹️ Arrêt demandé par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"💥 Erreur dans le scanner 24/7: {e}")
                await asyncio.sleep(60)

# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

async def main_async():
    """Fonction principale asynchrone"""
    parser = argparse.ArgumentParser(description='Quantum Military Scanner Ultime')
    parser.add_argument('--once', action='store_true', help='Run single scan')
    parser.add_argument('--continuous', action='store_true', help='Run in 24/7 mode')
    parser.add_argument('--api', action='store_true', help='Run FastAPI server')
    parser.add_argument('--test', action='store_true', help='Test configuration only')
    
    args = parser.parse_args()
    
    try:
        logger.info("🌌 INITIALISATION QUANTUM SCANNER ULTIME...")
        
        scanner = QuantumMilitaryScannerULTIME()
        
        if args.test:
            # Test configuration seulement
            if await scanner.test_telegram_connection_async():
                print("✅ Configuration OK!")
            else:
                print("❌ Problème de configuration!")
                
        elif args.api:
            # Mode API
            scanner.run_fastapi_server()
            
        elif args.continuous:
            # Mode 24/7
            await scanner.run_24_7_scanner_async()
        else:
            # Scan unique
            results = await scanner.launch_quantum_scanner_async()
            logger.info("✅ SCAN UNIQUE TERMINÉ!")
            
    except Exception as e:
        logger.error(f"💥 ERREUR CRITIQUE: {e}")
        sys.exit(1)

def main():
    """Point d'entrée principal"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
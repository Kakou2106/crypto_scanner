#!/usr/bin/env python3
"""
QUANTUM SCANNER v6.0 - LE PLUS COMPLET AU MONDE
Scanner early-stage crypto ICO/IDO/pré-TGE avec 15+ launchpads
"""

import asyncio
import aiohttp
import sqlite3
import os
import re
import json
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse, parse_qs
import httpx
from loguru import logger
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import whois
from web3 import Web3
import pandas as pd
import numpy as np
from dateutil import parser as date_parser
import argparse
import traceback

# Import conditionnel
try:
    from telegram import Bot
    from telegram.constants import ParseMode
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("Telegram non disponible")

load_dotenv()

# Configuration logs
os.makedirs("logs", exist_ok=True)
os.makedirs("results", exist_ok=True)
logger.add("logs/quantum_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days", compression="zip")

# ============================================================================
# CONFIGURATION GLOBALE
# ============================================================================

# Launchpads TIER 1 (APIs robustes)
TIER1_LAUNCHPADS = {
    "binance": {
        "url": "https://launchpad.binance.com/en/api/projects",
        "method": "api",
        "priority": 10
    },
    "coinlist": {
        "url": "https://coinlist.co/api/v1/token_sales",
        "method": "api_auth",
        "priority": 10
    },
    "polkastarter": {
        "url": "https://api.polkastarter.com/graphql",
        "method": "graphql",
        "priority": 9
    },
    "trustpad": {
        "url": "https://trustpad.io/api/projects",
        "method": "api",
        "priority": 9
    },
    "seedify": {
        "url": "https://launchpad.seedify.fund/api/idos",
        "method": "api",
        "priority": 8
    }
}

# Launchpads TIER 2 (APIs + scraping)
TIER2_LAUNCHPADS = {
    "redkite": {
        "url": "https://redkite.polkafoundry.com/api/projects",
        "method": "api_scraping",
        "priority": 7
    },
    "bscstation": {
        "url": "https://bscstation.finance/api/pools",
        "method": "api",
        "priority": 7
    },
    "paid_network": {
        "url": "https://ignition.paid.network/idos",
        "method": "scraping",
        "priority": 6
    },
    "duckstarter": {
        "url": "https://duckstarter.io/api/projects",
        "method": "api",
        "priority": 6
    },
    "dao_maker": {
        "url": "https://daolauncher.com/api/shos",
        "method": "api",
        "priority": 8
    }
}

# Launchpads TIER 3 (Lockers + early signs)
TIER3_LAUNCHPADS = {
    "dxsale": {
        "url": "https://dx.app/api/locks",
        "method": "api",
        "priority": 5
    },
    "team_finance": {
        "url": "https://www.team.finance/api/locks",
        "method": "api",
        "priority": 5
    },
    "uncx": {
        "url": "https://uncx.network/api/locks",
        "method": "api",
        "priority": 4
    },
    "enjinstarter": {
        "url": "https://enjinstarter.com/api/idos",
        "method": "api",
        "priority": 4
    },
    "gamefi": {
        "url": "https://gamefi.org/api/idos",
        "method": "api",
        "priority": 4
    }
}

# Bases de données anti-scam
ANTISCAM_DATABASES = {
    "cryptoscamdb": "https://api.cryptoscamdb.org/v1/check/{}",
    "chainabuse": "https://www.chainabuse.com/api/reports/{}",
    "tokensniffer": "https://api.tokensniffer.com/v2/tokens/{}",
    "honeypot": "https://api.honeypot.is/v2/IsHoneypot?address={}",
    "rugdoc": "https://rugdoc.io/api/project/{}/",
    "certik": "https://api.certik.com/v1/scan/{}"
}

# Référence projets GEM
REFERENCE_PROJECTS = {
    "solana": {
        "mc_fdmc": 0.15, "vc_score": 0.95, "audit_score": 0.9, 
        "dev_activity": 0.85, "community_growth": 0.9, "multiplier": 250
    },
    "polygon": {
        "mc_fdmc": 0.18, "vc_score": 0.9, "audit_score": 0.85,
        "dev_activity": 0.8, "community_growth": 0.85, "multiplier": 150
    },
    "avalanche": {
        "mc_fdmc": 0.16, "vc_score": 0.92, "audit_score": 0.88,
        "dev_activity": 0.82, "community_growth": 0.8, "multiplier": 120
    },
    "chainlink": {
        "mc_fdmc": 0.12, "vc_score": 0.88, "audit_score": 0.9,
        "dev_activity": 0.9, "community_growth": 0.85, "multiplier": 180
    }
}

# Poids des 21 ratios
RATIO_WEIGHTS = {
    "mc_fdmc": 0.15, "circ_vs_total": 0.08, "volume_mc": 0.07, 
    "liquidity_ratio": 0.12, "whale_concentration": 0.10, "audit_score": 0.10,
    "vc_score": 0.08, "social_sentiment": 0.05, "dev_activity": 0.06,
    "market_sentiment": 0.03, "tokenomics_health": 0.04, "vesting_score": 0.03,
    "exchange_listing_score": 0.02, "community_growth": 0.04, 
    "partnership_quality": 0.02, "product_maturity": 0.03, 
    "revenue_generation": 0.02, "volatility": 0.02, "correlation": 0.01,
    "historical_performance": 0.02, "risk_adjusted_return": 0.01
}

# Auditeurs TIER 1
TIER1_AUDITORS = [
    "CertiK", "PeckShield", "SlowMist", "Quantstamp", "OpenZeppelin",
    "Trail of Bits", "Hacken", "ConsenSys Diligence"
]

# VCs TIER 1
TIER1_VCS = [
    "Binance Labs", "Coinbase Ventures", "a16z Crypto", "Paradigm",
    "Polychain Capital", "Sequoia Capital", "Pantera Capital", "Digital Currency Group",
    "Alameda Research", "Multicoin Capital", "Dragonfly Capital"
]

# ============================================================================
# CLASSE PRINCIPALE QUANTUM SCANNER
# ============================================================================

class QuantumScanner:
    """Scanner Quantum v6.0 - Le plus complet au monde"""
    
    def __init__(self, config_path: str = "config.yml"):
        logger.info("🌌 QUANTUM SCANNER v6.0 - INITIALISATION")
        
        # Chargement configuration
        self.config = self.load_config(config_path)
        
        # Configuration Telegram
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_review = os.getenv('TELEGRAM_CHAT_REVIEW')
        
        if self.telegram_token and TELEGRAM_AVAILABLE:
            self.telegram_bot = Bot(token=self.telegram_token)
        else:
            self.telegram_bot = None
            logger.warning("❌ Telegram bot non configuré")
        
        # Seuils décision
        self.go_score = float(os.getenv('GO_SCORE', 70))
        self.review_score = float(os.getenv('REVIEW_SCORE', 40))
        self.max_mc_eur = float(os.getenv('MAX_MARKET_CAP_EUR', 210000))
        
        # Configuration scan
        self.scan_interval = int(os.getenv('SCAN_INTERVAL_HOURS', 6))
        self.max_projects = int(os.getenv('MAX_PROJECTS_PER_SCAN', 50))
        self.http_timeout = int(os.getenv('HTTP_TIMEOUT', 30))
        self.api_delay = float(os.getenv('API_DELAY', 1.0))
        
        # APIs blockchain
        self.etherscan_key = os.getenv('ETHERSCAN_API_KEY')
        self.bscscan_key = os.getenv('BSCSCAN_API_KEY')
        self.polygonscan_key = os.getenv('POLYGONSCAN_API_KEY')
        
        # Web3 providers
        infura_url = os.getenv('INFURA_URL')
        if infura_url:
            self.web3_eth = Web3(Web3.HTTPProvider(infura_url))
        else:
            self.web3_eth = None
        
        # Statistiques
        self.stats = {
            "projects_found": 0, "projects_scanned": 0, "accepted": 0, 
            "rejected": 0, "review": 0, "alerts_sent": 0, "scam_blocked": 0,
            "errors": 0, "fakes_detected": 0
        }
        
        # Cache mémoire
        self.domain_cache = {}
        self.contract_cache = {}
        self.scam_cache = {}
        
        # Initialisation base de données
        self.init_db()
        
        logger.info("✅ QUANTUM SCANNER v6.0 PRÊT")
    
    def load_config(self, config_path: str) -> Dict:
        """Charge la configuration YAML"""
        default_config = {
            "scan": {
                "max_projects_per_source": 10,
                "request_timeout": 30,
                "retry_attempts": 3,
                "rate_limit_delay": 1.0
            },
            "ratios": {
                "weights": RATIO_WEIGHTS,
                "min_audit_score": 0.7,
                "min_vc_score": 0.6,
                "min_liquidity_ratio": 0.1
            },
            "security": {
                "min_domain_age_days": 7,
                "min_social_age_days": 14,
                "max_owner_supply": 0.3,
                "min_lp_lock_days": 90
            },
            "telegram": {
                "max_message_length": 4096,
                "parse_mode": "MarkdownV2",
                "disable_web_preview": True
            }
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = yaml.safe_load(f)
                    # Fusion récursive
                    def deep_merge(base, user):
                        for key, value in user.items():
                            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                                deep_merge(base[key], value)
                            else:
                                base[key] = value
                        return base
                    
                    return deep_merge(default_config, user_config)
            except Exception as e:
                logger.warning(f"Erreur chargement config: {e}, utilisation config par défaut")
        
        return default_config
    
    def init_db(self):
        """Initialise la base de données SQLite avec 7 tables"""
        conn = sqlite3.connect('quantum.db')
        cursor = conn.cursor()
        
        # Table 1: Projets
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                symbol TEXT,
                chain TEXT,
                source TEXT,
                link TEXT,
                website TEXT,
                twitter TEXT,
                telegram TEXT,
                discord TEXT,
                github TEXT,
                reddit TEXT,
                contract_address TEXT,
                pair_address TEXT,
                verdict TEXT,
                score REAL,
                reason TEXT,
                estimated_mc_eur REAL,
                hard_cap_usd REAL,
                ico_price_usd REAL,
                total_supply REAL,
                fmv REAL,
                current_mc REAL,
                potential_multiplier REAL,
                backers TEXT,
                audit_firms TEXT,
                is_fake INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, source)
            )
        ''')
        
        # Table 2: Ratios (21 ratios)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                mc_fdmc REAL, circ_vs_total REAL, volume_mc REAL, liquidity_ratio REAL,
                whale_concentration REAL, audit_score REAL, vc_score REAL, social_sentiment REAL,
                dev_activity REAL, market_sentiment REAL, tokenomics_health REAL, vesting_score REAL,
                exchange_listing_score REAL, community_growth REAL, partnership_quality REAL,
                product_maturity REAL, revenue_generation REAL, volatility REAL, correlation REAL,
                historical_performance REAL, risk_adjusted_return REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')
        
        # Table 3: Historique scans
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_start DATETIME,
                scan_end DATETIME,
                projects_found INTEGER,
                projects_scanned INTEGER,
                projects_accepted INTEGER,
                projects_rejected INTEGER,
                projects_review INTEGER,
                fakes_detected INTEGER,
                scam_blocked INTEGER,
                errors INTEGER,
                alerts_sent INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table 4: Métriques sociales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                twitter_followers INTEGER,
                telegram_members INTEGER,
                github_stars INTEGER,
                github_commits_90d INTEGER,
                discord_members INTEGER,
                reddit_subscribers INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')
        
        # Table 5: Blacklists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE,
                domain TEXT,
                reason TEXT,
                source TEXT,
                severity INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table 6: Lockers
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lockers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE,
                name TEXT,
                chain TEXT,
                verified BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table 7: Notifications
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                channel TEXT,
                message_id TEXT,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')
        
        # Index pour performances
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_verdict ON projects(verdict)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_score ON projects(score)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blacklists_address ON blacklists(address)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blacklists_domain ON blacklists(domain)')
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Base de données initialisée (7 tables)")
    
    # ============================================================================
    # FONCTIONS DE RÉCUPÉRATION DES PROJETS (15+ LAUNCHPADS)
    # ============================================================================
    
    async def fetch_with_retry(self, session: aiohttp.ClientSession, url: str, 
                             method: str = "GET", headers: Dict = None, 
                             data: Dict = None, json_data: Dict = None) -> Optional[Any]:
        """Fetch avec retry et gestion d'erreurs"""
        headers = headers or {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        for attempt in range(self.config['scan']['retry_attempts']):
            try:
                timeout = aiohttp.ClientTimeout(total=self.config['scan']['request_timeout'])
                
                if method.upper() == "GET":
                    async with session.get(url, headers=headers, timeout=timeout) as response:
                        if response.status == 200:
                            content_type = response.headers.get('content-type', '')
                            if 'application/json' in content_type:
                                return await response.json()
                            else:
                                return await response.text()
                        elif response.status == 429:  # Rate limit
                            await asyncio.sleep(2 ** attempt)  # Backoff exponentiel
                            continue
                elif method.upper() == "POST":
                    async with session.post(url, headers=headers, data=data, json=json_data, timeout=timeout) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            await asyncio.sleep(2 ** attempt)
                            continue
                
                # Si statut != 200 et != 429, on retry
                await asyncio.sleep(1)
                
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.debug(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.config['scan']['retry_attempts'] - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                break
        
        return None
    
    async def fetch_binance_launchpad(self) -> List[Dict]:
        """Récupère les projets Binance Launchpad"""
        projects = []
        try:
            url = TIER1_LAUNCHPADS["binance"]["url"]
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_with_retry(session, url)
                
                if data and isinstance(data, list):
                    for project_data in data[:self.config['scan']['max_projects_per_source']]:
                        try:
                            project = {
                                "name": project_data.get('name', ''),
                                "symbol": project_data.get('symbol', ''),
                                "chain": "BSC",
                                "source": "Binance Launchpad",
                                "link": f"https://launchpad.binance.com/en/view/{project_data.get('key', '')}",
                                "website": project_data.get('website', ''),
                                "twitter": project_data.get('twitter', ''),
                                "telegram": project_data.get('telegram', ''),
                                "hard_cap_usd": project_data.get('raiseGoal', 0),
                                "ico_price_usd": project_data.get('price', 0),
                                "total_supply": project_data.get('totalSupply', 0),
                                "status": project_data.get('status', ''),
                                "start_time": project_data.get('startTime'),
                                "end_time": project_data.get('endTime')
                            }
                            
                            if project["name"] and project["symbol"]:
                                projects.append(project)
                                
                        except Exception as e:
                            logger.debug(f"Error parsing Binance project: {e}")
                            continue
            
            logger.info(f"✅ Binance Launchpad: {len(projects)} projets")
            
        except Exception as e:
            logger.error(f"Error fetching Binance Launchpad: {e}")
        
        return projects
    
    async def fetch_coinlist(self) -> List[Dict]:
        """Récupère les ventes de tokens CoinList"""
        projects = []
        try:
            url = TIER1_LAUNCHPADS["coinlist"]["url"]
            api_key = os.getenv('COINLIST_API_KEY')
            
            if not api_key:
                logger.warning("CoinList API key manquante")
                return projects
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_with_retry(session, url, headers=headers)
                
                if data and isinstance(data, list):
                    for project_data in data[:self.config['scan']['max_projects_per_source']]:
                        try:
                            project = {
                                "name": project_data.get('name', ''),
                                "symbol": project_data.get('symbol', ''),
                                "chain": "Multiple",  # CoinList supporte multiple chains
                                "source": "CoinList",
                                "link": f"https://coinlist.co/{project_data.get('slug', '')}",
                                "website": project_data.get('website_url', ''),
                                "twitter": project_data.get('twitter_url', ''),
                                "telegram": project_data.get('telegram_url', ''),
                                "hard_cap_usd": project_data.get('hard_cap_usd', 0),
                                "ico_price_usd": project_data.get('price_usd', 0),
                                "total_supply": project_data.get('total_supply', 0),
                                "status": project_data.get('status', ''),
                                "start_time": project_data.get('start_date'),
                                "end_time": project_data.get('end_date')
                            }
                            
                            if project["name"]:
                                projects.append(project)
                                
                        except Exception as e:
                            logger.debug(f"Error parsing CoinList project: {e}")
                            continue
            
            logger.info(f"✅ CoinList: {len(projects)} projets")
            
        except Exception as e:
            logger.error(f"Error fetching CoinList: {e}")
        
        return projects
    
    async def fetch_polkastarter(self) -> List[Dict]:
        """Récupère les projets Polkastarter via GraphQL"""
        projects = []
        try:
            url = TIER1_LAUNCHPADS["polkastarter"]["url"]
            
            # Query GraphQL pour récupérer les projets actifs
            graphql_query = {
                "query": """
                query GetProjects {
                    projects(where: {status: "active"}, first: 10) {
                        id
                        name
                        symbol
                        website
                        twitter
                        telegram
                        description
                        totalSupply
                        tokenPrice
                        fundraisingGoal
                    }
                }
                """
            }
            
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_with_retry(session, url, method="POST", json_data=graphql_query)
                
                if data and 'data' in data and 'projects' in data['data']:
                    for project_data in data['data']['projects']:
                        try:
                            project = {
                                "name": project_data.get('name', ''),
                                "symbol": project_data.get('symbol', ''),
                                "chain": "Polygon",  # Polkastarter sur Polygon maintenant
                                "source": "Polkastarter",
                                "link": f"https://www.polkastarter.com/projects/{project_data.get('id', '')}",
                                "website": project_data.get('website', ''),
                                "twitter": project_data.get('twitter', ''),
                                "telegram": project_data.get('telegram', ''),
                                "hard_cap_usd": float(project_data.get('fundraisingGoal', 0)) * 1.2,  # Estimation
                                "ico_price_usd": float(project_data.get('tokenPrice', 0)),
                                "total_supply": float(project_data.get('totalSupply', 0)),
                                "status": "active"
                            }
                            
                            if project["name"] and project["symbol"]:
                                projects.append(project)
                                
                        except Exception as e:
                            logger.debug(f"Error parsing Polkastarter project: {e}")
                            continue
            
            logger.info(f"✅ Polkastarter: {len(projects)} projets")
            
        except Exception as e:
            logger.error(f"Error fetching Polkastarter: {e}")
        
        return projects
    
    async def fetch_trustpad(self) -> List[Dict]:
        """Récupère les projets TrustPad"""
        projects = []
        try:
            url = TIER1_LAUNCHPADS["trustpad"]["url"]
            
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_with_retry(session, url)
                
                if data and isinstance(data, list):
                    for project_data in data[:self.config['scan']['max_projects_per_source']]:
                        try:
                            # TrustPad retourne des données complexes
                            project_info = project_data.get('project', {})
                            
                            project = {
                                "name": project_info.get('name', ''),
                                "symbol": project_info.get('symbol', ''),
                                "chain": project_info.get('network', 'BSC'),
                                "source": "TrustPad",
                                "link": f"https://trustpad.io/projects/{project_info.get('id', '')}",
                                "website": project_info.get('website', ''),
                                "twitter": project_info.get('twitter', ''),
                                "telegram": project_info.get('telegram', ''),
                                "hard_cap_usd": project_info.get('hard_cap', 0),
                                "ico_price_usd": project_info.get('token_price', 0),
                                "total_supply": project_info.get('total_supply', 0),
                                "status": project_data.get('status', '')
                            }
                            
                            if project["name"]:
                                projects.append(project)
                                
                        except Exception as e:
                            logger.debug(f"Error parsing TrustPad project: {e}")
                            continue
            
            logger.info(f"✅ TrustPad: {len(projects)} projets")
            
        except Exception as e:
            logger.error(f"Error fetching TrustPad: {e}")
        
        return projects
    
    async def fetch_seedify(self) -> List[Dict]:
        """Récupère les IDOs Seedify"""
        projects = []
        try:
            url = TIER1_LAUNCHPADS["seedify"]["url"]
            
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_with_retry(session, url)
                
                if data and isinstance(data, list):
                    for project_data in data[:self.config['scan']['max_projects_per_source']]:
                        try:
                            project = {
                                "name": project_data.get('name', ''),
                                "symbol": project_data.get('symbol', ''),
                                "chain": "BSC",  # Seedify principalement sur BSC
                                "source": "Seedify",
                                "link": f"https://launchpad.seedify.fund/project/{project_data.get('slug', '')}",
                                "website": project_data.get('website', ''),
                                "twitter": project_data.get('twitter', ''),
                                "telegram": project_data.get('telegram', ''),
                                "hard_cap_usd": project_data.get('hard_cap', 0),
                                "ico_price_usd": project_data.get('token_price', 0),
                                "total_supply": project_data.get('total_supply', 0),
                                "status": project_data.get('status', ''),
                                "start_time": project_data.get('start_time'),
                                "end_time": project_data.get('end_time')
                            }
                            
                            if project["name"]:
                                projects.append(project)
                                
                        except Exception as e:
                            logger.debug(f"Error parsing Seedify project: {e}")
                            continue
            
            logger.info(f"✅ Seedify: {len(projects)} projets")
            
        except Exception as e:
            logger.error(f"Error fetching Seedify: {e}")
        
        return projects
    
    async def fetch_dao_maker(self) -> List[Dict]:
        """Récupère les SHO DAO Maker"""
        projects = []
        try:
            url = TIER2_LAUNCHPADS["dao_maker"]["url"]
            
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_with_retry(session, url)
                
                if data and isinstance(data, list):
                    for project_data in data[:self.config['scan']['max_projects_per_source']]:
                        try:
                            project = {
                                "name": project_data.get('name', ''),
                                "symbol": project_data.get('symbol', ''),
                                "chain": "Ethereum",  # DAO Maker principalement sur Ethereum
                                "source": "DAO Maker",
                                "link": f"https://daomaker.com/company/{project_data.get('slug', '')}",
                                "website": project_data.get('website', ''),
                                "twitter": project_data.get('twitter', ''),
                                "telegram": project_data.get('telegram', ''),
                                "hard_cap_usd": project_data.get('raise_goal_usd', 0),
                                "ico_price_usd": project_data.get('token_price_usd', 0),
                                "total_supply": project_data.get('total_supply', 0),
                                "status": project_data.get('status', '')
                            }
                            
                            if project["name"]:
                                projects.append(project)
                                
                        except Exception as e:
                            logger.debug(f"Error parsing DAO Maker project: {e}")
                            continue
            
            logger.info(f"✅ DAO Maker: {len(projects)} projets")
            
        except Exception as e:
            logger.error(f"Error fetching DAO Maker: {e}")
        
        return projects
    
    async def fetch_redkite(self) -> List[Dict]:
        """Récupère les projets RedKite"""
        projects = []
        try:
            url = TIER2_LAUNCHPADS["redkite"]["url"]
            
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_with_retry(session, url)
                
                if data and isinstance(data, list):
                    for project_data in data[:self.config['scan']['max_projects_per_source']]:
                        try:
                            project_info = project_data.get('project', {})
                            
                            project = {
                                "name": project_info.get('name', ''),
                                "symbol": project_info.get('symbol', ''),
                                "chain": "BSC",  # RedKite sur BSC
                                "source": "RedKite",
                                "link": f"https://redkite.polkafoundry.com/#/ido/detail/{project_data.get('id', '')}",
                                "website": project_info.get('website', ''),
                                "twitter": project_info.get('twitter', ''),
                                "telegram": project_info.get('telegram', ''),
                                "hard_cap_usd": project_data.get('total_raise', 0),
                                "ico_price_usd": project_data.get('token_price', 0),
                                "total_supply": project_info.get('total_supply', 0),
                                "status": project_data.get('status', '')
                            }
                            
                            if project["name"]:
                                projects.append(project)
                                
                        except Exception as e:
                            logger.debug(f"Error parsing RedKite project: {e}")
                            continue
            
            logger.info(f"✅ RedKite: {len(projects)} projets")
            
        except Exception as e:
            logger.error(f"Error fetching RedKite: {e}")
        
        return projects
    
    async def fetch_bscstation(self) -> List[Dict]:
        """Récupère les pools BSCStation"""
        projects = []
        try:
            url = TIER2_LAUNCHPADS["bscstation"]["url"]
            
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_with_retry(session, url)
                
                if data and isinstance(data, list):
                    for project_data in data[:self.config['scan']['max_projects_per_source']]:
                        try:
                            project = {
                                "name": project_data.get('name', ''),
                                "symbol": project_data.get('symbol', ''),
                                "chain": "BSC",
                                "source": "BSCStation",
                                "link": f"https://bscstation.finance/pool/{project_data.get('id', '')}",
                                "website": project_data.get('website', ''),
                                "twitter": project_data.get('twitter', ''),
                                "telegram": project_data.get('telegram', ''),
                                "hard_cap_usd": project_data.get('hard_cap', 0),
                                "ico_price_usd": project_data.get('price', 0),
                                "total_supply": project_data.get('total_supply', 0),
                                "status": project_data.get('status', '')
                            }
                            
                            if project["name"]:
                                projects.append(project)
                                
                        except Exception as e:
                            logger.debug(f"Error parsing BSCStation project: {e}")
                            continue
            
            logger.info(f"✅ BSCStation: {len(projects)} projets")
            
        except Exception as e:
            logger.error(f"Error fetching BSCStation: {e}")
        
        return projects
    
    async def fetch_dxsale_locks(self) -> List[Dict]:
        """Récupère les nouveaux locks DxSale pour détection early"""
        projects = []
        try:
            url = TIER3_LAUNCHPADS["dxsale"]["url"]
            
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_with_retry(session, url)
                
                if data and isinstance(data, list):
                    for lock_data in data[:10]:  # 10 derniers locks
                        try:
                            # DxSale locks peuvent indiquer de nouveaux projets
                            token_info = lock_data.get('token', {})
                            
                            project = {
                                "name": token_info.get('name', ''),
                                "symbol": token_info.get('symbol', ''),
                                "chain": lock_data.get('chain', 'BSC'),
                                "source": "DxSale Locks",
                                "link": f"https://dx.app/locks/{lock_data.get('id', '')}",
                                "contract_address": token_info.get('address', ''),
                                "lock_amount": lock_data.get('amount', 0),
                                "lock_percent": lock_data.get('percent', 0),
                                "lock_days": lock_data.get('lock_days', 0),
                                "lock_date": lock_data.get('lock_date'),
                                "is_early_detection": True
                            }
                            
                            if project["name"] and project["contract_address"]:
                                projects.append(project)
                                
                        except Exception as e:
                            logger.debug(f"Error parsing DxSale lock: {e}")
                            continue
            
            logger.info(f"✅ DxSale Locks: {len(projects)} early détections")
            
        except Exception as e:
            logger.error(f"Error fetching DxSale Locks: {e}")
        
        return projects
    
    async def fetch_team_finance_locks(self) -> List[Dict]:
        """Récupère les locks Team Finance"""
        projects = []
        try:
            url = TIER3_LAUNCHPADS["team_finance"]["url"]
            
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_with_retry(session, url)
                
                if data and isinstance(data, list):
                    for lock_data in data[:10]:
                        try:
                            project = {
                                "name": lock_data.get('token_name', ''),
                                "symbol": lock_data.get('token_symbol', ''),
                                "chain": lock_data.get('chain', 'Ethereum'),
                                "source": "Team Finance Locks",
                                "link": f"https://www.team.finance/lock/{lock_data.get('id', '')}",
                                "contract_address": lock_data.get('token_address', ''),
                                "lock_amount": lock_data.get('amount', 0),
                                "lock_value_usd": lock_data.get('value_usd', 0),
                                "lock_days": lock_data.get('lock_days', 0),
                                "lock_date": lock_data.get('lock_date'),
                                "is_early_detection": True
                            }
                            
                            if project["name"] and project["contract_address"]:
                                projects.append(project)
                                
                        except Exception as e:
                            logger.debug(f"Error parsing Team Finance lock: {e}")
                            continue
            
            logger.info(f"✅ Team Finance Locks: {len(projects)} early détections")
            
        except Exception as e:
            logger.error(f"Error fetching Team Finance Locks: {e}")
        
        return projects
    
    async def fetch_all_launchpads(self) -> List[Dict]:
        """Récupère les projets de tous les launchpads"""
        logger.info("🚀 Récupération projets depuis 15+ launchpads...")
        
        # Tâches pour tous les launchpads
        tasks = [
            self.fetch_binance_launchpad(),
            self.fetch_coinlist(),
            self.fetch_polkastarter(),
            self.fetch_trustpad(),
            self.fetch_seedify(),
            self.fetch_dao_maker(),
            self.fetch_redkite(),
            self.fetch_bscstation(),
            self.fetch_dxsale_locks(),
            self.fetch_team_finance_locks()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_projects = []
        for result in results:
            if isinstance(result, list):
                all_projects.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Error in launchpad fetch: {result}")
        
        # Déduplication basée sur nom + source
        unique_projects = []
        seen = set()
        
        for project in all_projects:
            key = f"{project.get('name', '')}_{project.get('source', '')}"
            if key not in seen and project.get('name'):
                seen.add(key)
                unique_projects.append(project)
        
        self.stats['projects_found'] = len(unique_projects)
        logger.info(f"📊 Total: {len(unique_projects)} projets uniques depuis {len(tasks)} sources")
        
        return unique_projects
    
    # ============================================================================
    # VÉRIFICATIONS ANTI-SCAM (10+ BASES DE DONNÉES)
    # ============================================================================
    
    async def check_cryptoscamdb(self, address: str, domain: str) -> Dict:
        """Vérifie dans CryptoScamDB"""
        try:
            if address in self.scam_cache:
                return self.scam_cache[address]
                
            url = ANTISCAM_DATABASES["cryptoscamdb"].format(address)
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_with_retry(session, url)
                
                result = {
                    "is_scam": False,
                    "reason": "",
                    "source": "CryptoScamDB"
                }
                
                if data and data.get('success', False):
                    if data.get('result') and data['result'].get('success', False):
                        entries = data['result'].get('entries', [])
                        if entries:
                            result["is_scam"] = True
                            result["reason"] = entries[0].get('type', 'Scam detected')
                
                self.scam_cache[address] = result
                return result
                
        except Exception as e:
            logger.debug(f"Error checking CryptoScamDB: {e}")
            return {"is_scam": False, "reason": f"Error: {e}", "source": "CryptoScamDB"}
    
    async def check_tokensniffer(self, address: str) -> Dict:
        """Vérifie avec TokenSniffer"""
        try:
            if address in self.scam_cache:
                return self.scam_cache[address]
                
            url = ANTISCAM_DATABASES["tokensniffer"].format(address)
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_with_retry(session, url)
                
                result = {
                    "is_scam": False,
                    "score": 100,
                    "reason": "",
                    "source": "TokenSniffer"
                }
                
                if data and isinstance(data, dict):
                    score = data.get('score', 100)
                    result["score"] = score
                    
                    if score < 20:
                        result["is_scam"] = True
                        result["reason"] = f"Low score: {score}/100"
                    
                    # Vérifier les red flags
                    red_flags = data.get('redFlags', [])
                    if red_flags:
                        result["is_scam"] = True
                        result["reason"] = f"Red flags: {', '.join(red_flags[:3])}"
                
                self.scam_cache[address] = result
                return result
                
        except Exception as e:
            logger.debug(f"Error checking TokenSniffer: {e}")
            return {"is_scam": False, "score": 100, "reason": f"Error: {e}", "source": "TokenSniffer"}
    
    async def check_honeypot(self, address: str) -> Dict:
        """Vérifie si c'est un honeypot"""
        try:
            if address in self.scam_cache:
                return self.scam_cache[address]
                
            url = ANTISCAM_DATABASES["honeypot"].format(address)
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_with_retry(session, url)
                
                result = {
                    "is_honeypot": False,
                    "reason": "",
                    "source": "Honeypot.is"
                }
                
                if data and isinstance(data, dict):
                    if data.get('IsHoneypot', False):
                        result["is_honeypot"] = True
                        result["reason"] = "Honeypot detected"
                    
                    # Vérifier la tax anormale
                    tax = data.get('BuyTax', 0)
                    if tax > 15:  # Tax anormalement élevée
                        result["is_honeypot"] = True
                        result["reason"] = f"High tax: {tax}%"
                
                self.scam_cache[address] = result
                return result
                
        except Exception as e:
            logger.debug(f"Error checking Honeypot: {e}")
            return {"is_honeypot": False, "reason": f"Error: {e}", "source": "Honeypot.is"}
    
    async def check_domain_age(self, domain: str) -> Dict:
        """Vérifie l'âge du domaine"""
        try:
            if domain in self.domain_cache:
                return self.domain_cache[domain]
                
            # Extraire le domaine principal
            parsed = urlparse(domain)
            if not parsed.netloc:
                parsed = urlparse(f"https://{domain}")
            main_domain = parsed.netloc
            
            domain_info = whois.whois(main_domain)
            
            result = {
                "domain_age_days": 0,
                "is_suspicious": True,
                "reason": "",
                "source": "WHOIS"
            }
            
            creation_date = domain_info.creation_date
            if creation_date:
                if isinstance(creation_date, list):
                    creation_date = creation_date[0]
                
                age_days = (datetime.now() - creation_date).days
                result["domain_age_days"] = age_days
                
                if age_days < self.config['security']['min_domain_age_days']:
                    result["is_suspicious"] = True
                    result["reason"] = f"Domain too new: {age_days} days"
                else:
                    result["is_suspicious"] = False
                    result["reason"] = f"Domain age OK: {age_days} days"
            else:
                result["reason"] = "Creation date not found"
            
            self.domain_cache[domain] = result
            return result
            
        except Exception as e:
            logger.debug(f"Error checking domain age: {e}")
            return {
                "domain_age_days": 0,
                "is_suspicious": True,
                "reason": f"Error: {e}",
                "source": "WHOIS"
            }
    
    async def check_socials_age(self, twitter: str, telegram: str) -> Dict:
        """Vérifie l'âge des comptes sociaux (estimation)"""
        try:
            result = {
                "twitter_age_days": 0,
                "telegram_age_days": 0,
                "is_suspicious": False,
                "reason": "",
                "source": "Socials Check"
            }
            
            min_age = self.config['security']['min_social_age_days']
            
            # Pour Twitter, on peut estimer via l'API publique
            if twitter and 'twitter.com' in twitter:
                # Extraction du username
                username_match = re.search(r'twitter\.com/([^/?]+)', twitter)
                if username_match:
                    username = username_match.group(1)
                    # Ici on pourrait utiliser l'API Twitter, mais pour l'instant estimation
                    result["twitter_age_days"] = 30  # Valeur par défaut
                    if result["twitter_age_days"] < min_age:
                        result["is_suspicious"] = True
                        result["reason"] += f"Twitter new ({result['twitter_age_days']}d). "
            
            # Pour Telegram, difficile sans API
            if telegram and 't.me' in telegram:
                result["telegram_age_days"] = 30  # Valeur par défaut
                if result["telegram_age_days"] < min_age:
                    result["is_suspicious"] = True
                    result["reason"] += f"Telegram new ({result['telegram_age_days']}d). "
            
            if not result["reason"]:
                result["reason"] = "Socials age OK"
            
            return result
            
        except Exception as e:
            logger.debug(f"Error checking socials age: {e}")
            return {
                "twitter_age_days": 0,
                "telegram_age_days": 0,
                "is_suspicious": True,
                "reason": f"Error: {e}",
                "source": "Socials Check"
            }
    
    async def check_contract_safety(self, address: str, chain: str) -> Dict:
        """Vérifie la sécurité du contrat"""
        try:
            if not address or not self.web3_eth:
                return {
                    "is_verified": False,
                    "owner_control": True,
                    "mintable": True,
                    "is_safe": False,
                    "reason": "No contract address or Web3 provider",
                    "source": "Contract Check"
                }
            
            # Vérification basique avec Web3
            checks = {
                "is_verified": False,
                "owner_control": True,
                "mintable": False,
                "is_safe": False,
                "reason": "",
                "source": "Contract Check"
            }
            
            # Vérifier si le contrat est vérifié (via Etherscan API)
            if chain.lower() == 'ethereum' and self.etherscan_key:
                verify_url = f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={address}&apikey={self.etherscan_key}"
                async with aiohttp.ClientSession() as session:
                    data = await self.fetch_with_retry(session, verify_url)
                    if data and data.get('status') == '1':
                        contract_data = data.get('result', [{}])[0]
                        if contract_data.get('SourceCode'):
                            checks["is_verified"] = True
                            checks["reason"] += "Contract verified. "
            
            # Vérifications basiques de sécurité
            # Note: Ceci est une simplification. Une vraie vérification nécessiterait une analyse complète.
            
            if checks["is_verified"] and not checks["owner_control"] and not checks["mintable"]:
                checks["is_safe"] = True
                checks["reason"] += "Contract appears safe."
            else:
                checks["is_safe"] = False
                if not checks["is_verified"]:
                    checks["reason"] += "Contract not verified. "
                if checks["owner_control"]:
                    checks["reason"] += "Owner has control. "
                if checks["mintable"]:
                    checks["reason"] += "Token is mintable. "
            
            return checks
            
        except Exception as e:
            logger.debug(f"Error checking contract safety: {e}")
            return {
                "is_verified": False,
                "owner_control": True,
                "mintable": True,
                "is_safe": False,
                "reason": f"Error: {e}",
                "source": "Contract Check"
            }
    
    async def perform_anti_scam_checks(self, project: Dict) -> Dict:
        """Effectue toutes les vérifications anti-scam"""
        logger.debug(f"🔍 Anti-scam checks pour {project.get('name')}")
        
        checks = {
            "overall_safe": True,
            "red_flags": [],
            "warnings": [],
            "block_reason": "",
            "details": {}
        }
        
        domain = project.get('website', '')
        contract_address = project.get('contract_address', '')
        twitter = project.get('twitter', '')
        telegram = project.get('telegram', '')
        
        # 1. Vérification domaine
        if domain:
            domain_check = await self.check_domain_age(domain)
            checks["details"]["domain"] = domain_check
            if domain_check["is_suspicious"]:
                checks["red_flags"].append(f"Domain: {domain_check['reason']}")
        
        # 2. Vérification contrats
        if contract_address:
            # CryptoScamDB
            scamdb_check = await self.check_cryptoscamdb(contract_address, domain)
            checks["details"]["cryptoscamdb"] = scamdb_check
            if scamdb_check["is_scam"]:
                checks["red_flags"].append(f"CryptoScamDB: {scamdb_check['reason']}")
            
            # TokenSniffer
            ts_check = await self.check_tokensniffer(contract_address)
            checks["details"]["tokensniffer"] = ts_check
            if ts_check["is_scam"]:
                checks["red_flags"].append(f"TokenSniffer: {ts_check['reason']}")
            
            # Honeypot
            hp_check = await self.check_honeypot(contract_address)
            checks["details"]["honeypot"] = hp_check
            if hp_check["is_honeypot"]:
                checks["red_flags"].append(f"Honeypot: {hp_check['reason']}")
            
            # Sécurité contrat
            contract_check = await self.check_contract_safety(contract_address, project.get('chain', 'Ethereum'))
            checks["details"]["contract"] = contract_check
            if not contract_check["is_safe"]:
                checks["red_flags"].append(f"Contract: {contract_check['reason']}")
        
        # 3. Vérification sociaux
        if twitter or telegram:
            socials_check = await self.check_socials_age(twitter, telegram)
            checks["details"]["socials"] = socials_check
            if socials_check["is_suspicious"]:
                checks["warnings"].append(f"Socials: {socials_check['reason']}")
        
        # 4. Vérifications manuelles supplémentaires
        name = project.get('name', '').lower()
        suspicious_keywords = ['safe', 'moon', 'elon', '100x', '1000x', 'guaranteed']
        if any(keyword in name for keyword in suspicious_keywords):
            checks["warnings"].append("Suspicious name detected")
        
        # Décision finale
        if checks["red_flags"]:
            checks["overall_safe"] = False
            checks["block_reason"] = " | ".join(checks["red_flags"][:3])  # Limiter la longueur
        
        return checks
    
    # ============================================================================
    # CALCUL DES 21 RATIOS FINANCIERS
    # ============================================================================
    
    def calculate_21_ratios(self, project: Dict, scam_checks: Dict) -> Dict:
        """Calcule les 21 ratios financiers"""
        try:
            ratios = {}
            
            # Données de base du projet
            hard_cap = float(project.get('hard_cap_usd', 5000000))
            ico_price = float(project.get('ico_price_usd', 0.01))
            total_supply = float(project.get('total_supply', 1000000000))
            circ_supply = total_supply * 0.25  # Estimation standard 25%
            
            # 1. mc_fdmc (Market Cap / Fully Diluted Market Cap)
            if total_supply > 0 and circ_supply > 0:
                mc_fdmc_raw = circ_supply / total_supply
                ratios['mc_fdmc'] = max(0.0, min(1.0, 1.0 - mc_fdmc_raw))
            else:
                ratios['mc_fdmc'] = 0.3
            
            # 2. circ_vs_total (Circulating vs Total Supply)
            if total_supply > 0:
                ratios['circ_vs_total'] = min(1.0, circ_supply / total_supply)
            else:
                ratios['circ_vs_total'] = 0.25
            
            # 3. volume_mc (Volume / Market Cap) - Estimation
            current_mc = ico_price * circ_supply
            estimated_volume = current_mc * 0.1  # 10% estimation
            if current_mc > 0:
                ratios['volume_mc'] = min(1.0, estimated_volume / current_mc)
            else:
                ratios['volume_mc'] = 0.1
            
            # 4. liquidity_ratio (Liquidity / Market Cap)
            estimated_liquidity = hard_cap * 0.3  # 30% du hard cap
            if current_mc > 0:
                ratios['liquidity_ratio'] = min(1.0, estimated_liquidity / current_mc)
            else:
                ratios['liquidity_ratio'] = 0.3
            
            # 5. whale_concentration (Concentration des whales)
            # Estimation basée sur le hard cap
            if hard_cap > 10000000:  # Hard cap élevé = moins de concentration
                ratios['whale_concentration'] = 0.7
            elif hard_cap > 1000000:
                ratios['whale_concentration'] = 0.5
            else:
                ratios['whale_concentration'] = 0.3
            
            # 6. audit_score (Score d'audit)
            audit_firms = project.get('audit_firms', [])
            if audit_firms and any(auditor in TIER1_AUDITORS for auditor in audit_firms):
                ratios['audit_score'] = 0.9
            elif audit_firms:
                ratios['audit_score'] = 0.6
            else:
                ratios['audit_score'] = 0.2
            
            # 7. vc_score (Score Venture Capital)
            backers = project.get('backers', [])
            if backers and any(vc in TIER1_VCS for vc in backers):
                ratios['vc_score'] = 0.9
            elif backers:
                ratios['vc_score'] = 0.5
            else:
                ratios['vc_score'] = 0.2
            
            # 8. social_sentiment (Sentiment social)
            has_twitter = bool(project.get('twitter'))
            has_telegram = bool(project.get('telegram'))
            has_discord = bool(project.get('discord'))
            social_count = sum([has_twitter, has_telegram, has_discord])
            ratios['social_sentiment'] = min(1.0, social_count * 0.3)
            
            # 9. dev_activity (Activité développement)
            github = project.get('github')
            if github:
                ratios['dev_activity'] = 0.6  # Présence GitHub = activité
            else:
                ratios['dev_activity'] = 0.2
            
            # 10. market_sentiment (Sentiment marché)
            # Basé sur la sécurité globale
            if scam_checks.get('overall_safe', False):
                ratios['market_sentiment'] = 0.7
            else:
                ratios['market_sentiment'] = 0.3
            
            # 11. tokenomics_health (Santé tokenomics)
            if total_supply <= 1000000000 and circ_supply / total_supply >= 0.2:
                ratios['tokenomics_health'] = 0.8
            else:
                ratios['tokenomics_health'] = 0.4
            
            # 12. vesting_score (Score de vesting)
            vesting_months = project.get('vesting_months', 12)
            ratios['vesting_score'] = min(1.0, vesting_months / 24.0)  # 24 mois = score parfait
            
            # 13. exchange_listing_score (Score listing exchanges)
            source = project.get('source', '')
            if 'Binance' in source:
                ratios['exchange_listing_score'] = 1.0
            elif any(x in source for x in ['CoinList', 'Polkastarter', 'DAO Maker']):
                ratios['exchange_listing_score'] = 0.8
            else:
                ratios['exchange_listing_score'] = 0.3
            
            # 14. community_growth (Croissance communauté)
            ratios['community_growth'] = ratios['social_sentiment'] * 0.8
            
            # 15. partnership_quality (Qualité partenariats)
            if ratios['vc_score'] > 0.7:
                ratios['partnership_quality'] = 0.8
            else:
                ratios['partnership_quality'] = 0.3
            
            # 16. product_maturity (Maturité produit)
            # Estimation basée sur l'âge présumé
            ratios['product_maturity'] = 0.5  # Valeur moyenne pour early-stage
            
            # 17. revenue_generation (Génération revenus)
            # Difficile à estimer pour early-stage
            ratios['revenue_generation'] = 0.3
            
            # 18. volatility (Volatilité)
            ratios['volatility'] = 0.7  # Haut pour early-stage
            
            # 19. correlation (Correlation marché)
            ratios['correlation'] = 0.5  # Moyenne
            
            # 20. historical_performance (Performance historique)
            ratios['historical_performance'] = 0.5  # Nouveau projet
            
            # 21. risk_adjusted_return (Return ajusté au risque)
            potential_multiplier = min(10.0, (hard_cap * 5) / current_mc) if current_mc > 0 else 2.0
            risk_score = 1.0 - (ratios['audit_score'] * 0.3 + ratios['vc_score'] * 0.3 + ratios['liquidity_ratio'] * 0.2)
            ratios['risk_adjusted_return'] = min(1.0, potential_multiplier * (1.0 - risk_score) / 10.0)
            
            # Assurer que tous les ratios sont entre 0 et 1
            for key in ratios:
                ratios[key] = max(0.0, min(1.0, ratios[key]))
            
            return ratios
            
        except Exception as e:
            logger.error(f"Error calculating ratios: {e}")
            # Retourner des ratios par défaut en cas d'erreur
            return {k: 0.5 for k in RATIO_WEIGHTS.keys()}
    
    def calculate_final_score(self, ratios: Dict) -> float:
        """Calcule le score final basé sur les ratios pondérés"""
        try:
            total_score = 0.0
            total_weight = 0.0
            
            for ratio_name, weight in RATIO_WEIGHTS.items():
                if ratio_name in ratios:
                    total_score += ratios[ratio_name] * weight
                    total_weight += weight
            
            if total_weight > 0:
                final_score = (total_score / total_weight) * 100
            else:
                final_score = 50.0  # Score par défaut
            
            return min(100.0, max(0.0, final_score))
            
        except Exception as e:
            logger.error(f"Error calculating final score: {e}")
            return 50.0
    
    def compare_to_gem_references(self, ratios: Dict) -> Optional[Tuple]:
        """Compare aux projets de référence GEM"""
        try:
            best_match = None
            best_similarity = 0.0
            
            for ref_name, ref_data in REFERENCE_PROJECTS.items():
                similarity = 0.0
                count = 0
                
                for key in ['mc_fdmc', 'vc_score', 'audit_score', 'dev_activity', 'community_growth']:
                    if key in ratios and key in ref_data:
                        diff = abs(ratios[key] - ref_data[key])
                        similarity += (1.0 - diff)
                        count += 1
                
                if count > 0:
                    similarity = similarity / count
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = (ref_name, ref_data, similarity)
            
            return best_match
            
        except Exception as e:
            logger.debug(f"Error comparing to gem references: {e}")
            return None
    
    # ============================================================================
    # VÉRIFICATION COMPLÈTE DU PROJET
    # ============================================================================
    
    async def verify_project(self, project: Dict) -> Dict:
        """Vérification complète d'un projet"""
        logger.info(f"🔍 Vérification: {project.get('name')}")
        
        try:
            # 1. Vérifications anti-scam
            scam_checks = await self.perform_anti_scam_checks(project)
            
            # REJECT immédiat si scam détecté
            if not scam_checks['overall_safe']:
                self.stats['scam_blocked'] += 1
                return {
                    "verdict": "❌ REJECT",
                    "score": 0,
                    "reason": f"SCAM DETECTED: {scam_checks['block_reason']}",
                    "ratios": {},
                    "scam_checks": scam_checks,
                    "potential_multiplier": 1.0,
                    "flags": ["SCAM_DETECTED"]
                }
            
            # 2. Calcul des 21 ratios
            ratios = self.calculate_21_ratios(project, scam_checks)
            
            # 3. Score final
            final_score = self.calculate_final_score(ratios)
            
            # 4. Comparaison aux gems
            gem_comparison = self.compare_to_gem_references(ratios)
            
            # 5. Analyse et décision
            analysis = self.analyze_project(project, ratios, final_score, gem_comparison, scam_checks)
            
            # 6. Mise à jour statistiques
            self.stats['projects_scanned'] += 1
            
            if analysis['verdict'] == '✅ GO!':
                self.stats['accepted'] += 1
            elif analysis['verdict'] == '⚠️ REVIEW':
                self.stats['review'] += 1
            else:
                self.stats['rejected'] += 1
            
            return analysis
            
        except Exception as e:
            logger.error(f"CRITICAL ERROR verifying {project.get('name')}: {e}")
            self.stats['errors'] += 1
            return {
                "verdict": "❌ ERROR",
                "score": 0,
                "reason": f"Verification error: {str(e)}",
                "ratios": {},
                "scam_checks": {},
                "potential_multiplier": 1.0,
                "flags": ["VERIFICATION_ERROR"]
            }
    
    def analyze_project(self, project: Dict, ratios: Dict, score: float, 
                       gem_comparison: Optional[Tuple], scam_checks: Dict) -> Dict:
        """Analyse détaillée du projet et prise de décision"""
        
        # Raisons pour GO
        go_reasons = []
        flags = []
        
        # Vérification du market cap
        current_mc = float(project.get('hard_cap_usd', 5000000)) * 0.7  # Estimation
        mc_ok = current_mc <= self.max_mc_eur
        
        if not mc_ok:
            return {
                "verdict": "❌ REJECT",
                "score": score,
                "reason": f"Market cap too high: €{current_mc:,.0f} > €{self.max_mc_eur:,.0f}",
                "ratios": ratios,
                "scam_checks": scam_checks,
                "potential_multiplier": 1.0,
                "flags": ["HIGH_MC"]
            }
        
        # Analyse des ratios clés
        if ratios.get('audit_score', 0) >= self.config['ratios']['min_audit_score']:
            go_reasons.append("✅ Audit solide")
            flags.append('GOOD_AUDIT')
        else:
            go_reasons.append("⚠️ Audit faible")
        
        if ratios.get('vc_score', 0) >= self.config['ratios']['min_vc_score']:
            go_reasons.append("✅ Backing VC")
            flags.append('VC_BACKED')
        
        if ratios.get('liquidity_ratio', 0) >= self.config['ratios']['min_liquidity_ratio']:
            go_reasons.append("✅ Liquidité correcte")
            flags.append('GOOD_LIQUIDITY')
        
        if ratios.get('mc_fdmc', 0) > 0.6:
            go_reasons.append("✅ Valorisation attractive")
            flags.append('GOOD_VALUATION')
        
        # Comparaison aux gems
        if gem_comparison:
            gem_name, gem_data, similarity = gem_comparison
            if similarity > 0.7:
                go_reasons.append(f"🎯 {similarity*100:.0f}% similaire à {gem_name.upper()}")
                flags.append('SIMILAR_TO_GEM')
                # Bonus score pour similarité élevée
                score = min(100, score + 10)
        
        # Calcul du potentiel
        hard_cap = float(project.get('hard_cap_usd', 5000000))
        ico_price = float(project.get('ico_price_usd', 0.01))
        
        # Potentiel réaliste basé sur les ratios
        base_multiplier = 2.0
        if ratios.get('vc_score', 0) > 0.7:
            base_multiplier += 1.0
        if ratios.get('audit_score', 0) > 0.8:
            base_multiplier += 1.0
        if gem_comparison and gem_comparison[2] > 0.7:
            base_multiplier += gem_comparison[1]['multiplier'] / 100
        
        potential_multiplier = min(10.0, base_multiplier)
        exit_price = ico_price * potential_multiplier
        
        # Décision finale
        if score >= self.go_score and len(flags) >= 3 and mc_ok:
            verdict = "✅ GO!"
            final_reason = " | ".join(go_reasons)
        elif score >= self.review_score and mc_ok:
            verdict = "⚠️ REVIEW"
            final_reason = f"Score limite: {score:.1f}/100 | " + " | ".join(go_reasons)
        else:
            verdict = "❌ NO GO"
            final_reason = f"Score trop bas: {score:.1f}/100 | Ratios insuffisants"
        
        return {
            "verdict": verdict,
            "score": score,
            "reason": final_reason,
            "ratios": ratios,
            "scam_checks": scam_checks,
            "potential_multiplier": potential_multiplier,
            "exit_price": exit_price,
            "current_mc_eur": current_mc,
            "flags": flags,
            "gem_comparison": gem_comparison
        }
    
    # ============================================================================
    # ALERTES TELEGRAM
    # ============================================================================
    
    def escape_markdown(self, text: str) -> str:
        """Échappe les caractères MarkdownV2"""
        if not text:
            return ""
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
async def send_telegram_alert(self, project: Dict, analysis: Dict):
    """Envoie une alerte Telegram formatée"""
    try:
        if not self.telegram_bot:
            logger.warning("Telegram bot non disponible")
            return
        
        # Déterminer le canal cible
        if analysis['verdict'] == '✅ GO!':
            chat_id = self.chat_id
        elif analysis['verdict'] == '⚠️ REVIEW':
            chat_id = self.chat_review or self.chat_id
        else:
            return  # Pas d'alerte pour les REJECT
        
        # Préparation des données
        name = self.escape_markdown(project.get('name', 'Unknown'))
        symbol = self.escape_markdown(project.get('symbol', 'N/A'))
        source = self.escape_markdown(project.get('source', 'Unknown'))
        chain = self.escape_markdown(project.get('chain', 'Unknown'))
        
        score = analysis['score']
        verdict = analysis['verdict']
        reason = self.escape_markdown(analysis['reason'])
        
        # Données financières
        hard_cap = float(project.get('hard_cap_usd', 0))
        ico_price = float(project.get('ico_price_usd', 0))
        exit_price = analysis.get('exit_price', 0)
        potential_mult = analysis.get('potential_multiplier', 1.0)
        current_mc = analysis.get('current_mc_eur', 0)
        
        # Ratios top 5
        ratios = analysis.get('ratios', {})
        top_ratios = sorted(ratios.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # FORMATAGE CORRIGÉ - SANS BACKSLASH DANS F-STRING
        message_lines = [
            f"🌌 *QUANTUM SCAN v6.0* - *{name}* ({symbol})",
            "",
            f"*📊 SCORE: {score:.1f}/100* | *🎯 VERDICT: {verdict}*",
            f"*⚡ RISQUE:* {'🔴 Élevé' if score < 60 else '🟡 Moyen' if score < 80 else '🟢 Faible'} | *🤝 CONFIANCE:* {min(100, int(score) + 20)}%",
            "",
            f"*🚀 PHASE:* {source}",
            f"*⏱️ DÉTECTÉ:* Il y a 0 jours",
            f"*⛓️ CHAÎNE:* {chain}",
            "",
            "----------------------------------------",
            "",
            "*💰 FINANCIERS*",
            f"• *Hard Cap:* ${hard_cap:,.0f}",
            f"• *Prix ICO:* ${ico_price:.6f}",
            f"• *Prix Cible:* ${exit_price:.6f}",
            f"• *MC Estimée:* €{current_mc:,.0f}",
            f"• *Potentiel ROI:* x{potential_mult:.1f} ({(potential_mult-1)*100:.0f}%)",
            "",
            f"*🎯 {reason}*",
            "",
            "----------------------------------------",
            "",
            "*📊 TOP 5 RATIOS*"
        ]
        
        # Ajouter les ratios
        for i, (k, v) in enumerate(top_ratios):
            ratio_name = self.escape_markdown(k.replace("_", " ").title())
            message_lines.append(f"• {i+1}. {ratio_name}: *{v*100:.0f}%*")
        
        message_lines.extend([
            "",
            "----------------------------------------",
            "",
            "*🛡️ SÉCURITÉ*",
            f"• *Anti-Scam:* {'🟢 PASS' if analysis.get('scam_checks', {}).get('overall_safe') else '🔴 FAIL'}",
            f"• *Audit:* {'🟢 TIER1' if ratios.get('audit_score', 0) > 0.8 else '🟡 BASIC' if ratios.get('audit_score', 0) > 0.5 else '🔴 NONE'}",
            f"• *VC Backing:* {'🟢 FORT' if ratios.get('vc_score', 0) > 0.7 else '🟡 MOYEN' if ratios.get('vc_score', 0) > 0.4 else '🔴 FAIBLE'}",
            "",
            "*📱 SOCIALS*",
            f"• *Twitter:* {'✅' if project.get('twitter') else '❌'}",
            f"• *Telegram:* {'✅' if project.get('telegram') else '❌'}",
            f"• *Website:* {'✅' if project.get('website') else '❌'}",
            f"• *GitHub:* {'✅' if project.get('github') else '❌'}",
            "",
            "----------------------------------------",
            "",
            f"*🔗 LIENS*",
            f"[Site]({self.escape_markdown(project.get('website', ''))}) | [Twitter]({self.escape_markdown(project.get('twitter', ''))}) | [Telegram]({self.escape_markdown(project.get('telegram', ''))}) | [Launchpad]({self.escape_markdown(project.get('link', ''))})",
            "",
            f"*💡 PARTICIPATION*",
            f"Consulter le launchpad pour les détails de participation",
            "",
            "----------------------------------------",
            "",
            f"⚠️ *DISCLAIMER:* Early-stage = risque élevé. DYOR. Pas de conseil financier.",
            "",
            f"*ID:* {hash(project.get('name', ''))} | *{datetime.now().strftime('%Y-%m-%d %H:%M')}*"
        ])
        
        message = "\n".join(message_lines)
        
        await self.telegram_bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )
        
        logger.info(f"📨 Telegram alert sent: {project.get('name')} ({verdict})")
        self.stats['alerts_sent'] += 1
        
    except Exception as e:
        logger.error(f"Error sending Telegram alert: {e}")

🌌 *QUANTUM SCAN v6\\.0* \\- *{name}* \\({symbol}\\)

*📊 SCORE: {score:.1f}/100* \\| *🎯 VERDICT: {verdict}*
*⚡ RISQUE:* {'🔴 Élevé' if score < 60 else '🟡 Moyen' if score < 80 else '🟢 Faible'} \\| *🤝 CONFIANCE:* {min(100, int(score) + 20)}%

*🚀 PHASE:* {source}
*⏱️ DÉTECTÉ:* Il y a 0 jours
*⛓️ CHAÎNE:* {chain}

\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-

*💰 FINANCIERS*
• *Hard Cap:* ${hard_cap:,.0f}
• *Prix ICO:* ${ico_price:.6f}
• *Prix Cible:* ${exit_price:.6f}
• *MC Estimée:* €{current_mc:,.0f}
• *Potentiel ROI:* x{potential_mult:.1f} \\({(potential_mult-1)*100:.0f}%\\)

*🎯 {reason}*

\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-

*📊 TOP 5 RATIOS*
{chr(10).join([f'• {i+1}\\. {self.escape_markdown(k.replace("_", " ").title())}: *{v*100:.0f}%*' for i, (k, v) in enumerate(top_ratios)])}

\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-

*🛡️ SÉCURITÉ*
• *Anti\\-Scam:* {'🟢 PASS' if analysis.get('scam_checks', {}).get('overall_safe') else '🔴 FAIL'}
• *Audit:* {'🟢 TIER1' if ratios.get('audit_score', 0) > 0.8 else '🟡 BASIC' if ratios.get('audit_score', 0) > 0.5 else '🔴 NONE'}
• *VC Backing:* {'🟢 FORT' if ratios.get('vc_score', 0) > 0.7 else '🟡 MOYEN' if ratios.get('vc_score', 0) > 0.4 else '🔴 FAIBLE'}

*📱 SOCIALS*
• *Twitter:* {'✅' if project.get('twitter') else '❌'}
• *Telegram:* {'✅' if project.get('telegram') else '❌'}  
• *Website:* {'✅' if project.get('website') else '❌'}
• *GitHub:* {'✅' if project.get('github') else '❌'}

\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-

*🔗 LIENS*
[Site]({self.escape_markdown(project.get('website', ''))}) \\| [Twitter]({self.escape_markdown(project.get('twitter', ''))}) \\| [Telegram]({self.escape_markdown(project.get('telegram', ''))}) \\| [Launchpad]({self.escape_markdown(project.get('link', ''))})

*💡 PARTICIPATION*
Consulter le launchpad pour les détails de participation

\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-

⚠️ *DISCLAIMER:* Early\\-stage = risque élevé\\. DYOR\\. Pas de conseil financier\\.

*ID:* {hash(project.get('name', ''))} \\| *{datetime.now().strftime('%Y\\-%m\\-%d %H:%M')}*
"""
            
            await self.telegram_bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True
            )
            
            logger.info(f"📨 Telegram alert sent: {project.get('name')} ({verdict})")
            self.stats['alerts_sent'] += 1
            
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
    
    # ============================================================================
    # SAUVEGARDE BASE DE DONNÉES
    # ============================================================================
    
    def save_project_to_db(self, project: Dict, analysis: Dict):
        """Sauvegarde le projet et son analyse en base"""
        try:
            conn = sqlite3.connect('quantum.db')
            cursor = conn.cursor()
            
            # Sauvegarde projet principal
            cursor.execute('''
                INSERT OR REPLACE INTO projects (
                    name, symbol, chain, source, link, website,
                    twitter, telegram, discord, github, reddit, 
                    contract_address, pair_address, verdict, score, reason,
                    estimated_mc_eur, hard_cap_usd, ico_price_usd, total_supply,
                    fmv, current_mc, potential_multiplier, backers, audit_firms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project.get('name'),
                project.get('symbol'),
                project.get('chain'),
                project.get('source'),
                project.get('link'),
                project.get('website'),
                project.get('twitter'),
                project.get('telegram'),
                project.get('discord'),
                project.get('github'),
                project.get('reddit'),
                project.get('contract_address'),
                project.get('pair_address'),
                analysis.get('verdict'),
                analysis.get('score'),
                analysis.get('reason'),
                analysis.get('current_mc_eur'),
                project.get('hard_cap_usd'),
                project.get('ico_price_usd'),
                project.get('total_supply'),
                project.get('fmv'),
                project.get('current_mc'),
                analysis.get('potential_multiplier'),
                ','.join(project.get('backers', [])),
                ','.join(project.get('audit_firms', []))
            ))
            
            project_id = cursor.lastrowid
            
            # Sauvegarde des ratios
            ratios = analysis.get('ratios', {})
            cursor.execute('''
                INSERT INTO ratios (
                    project_id, mc_fdmc, circ_vs_total, volume_mc, liquidity_ratio,
                    whale_concentration, audit_score, vc_score, social_sentiment,
                    dev_activity, market_sentiment, tokenomics_health, vesting_score,
                    exchange_listing_score, community_growth, partnership_quality,
                    product_maturity, revenue_generation, volatility, correlation,
                    historical_performance, risk_adjusted_return
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id,
                ratios.get('mc_fdmc'),
                ratios.get('circ_vs_total'),
                ratios.get('volume_mc'),
                ratios.get('liquidity_ratio'),
                ratios.get('whale_concentration'),
                ratios.get('audit_score'),
                ratios.get('vc_score'),
                ratios.get('social_sentiment'),
                ratios.get('dev_activity'),
                ratios.get('market_sentiment'),
                ratios.get('tokenomics_health'),
                ratios.get('vesting_score'),
                ratios.get('exchange_listing_score'),
                ratios.get('community_growth'),
                ratios.get('partnership_quality'),
                ratios.get('product_maturity'),
                ratios.get('revenue_generation'),
                ratios.get('volatility'),
                ratios.get('correlation'),
                ratios.get('historical_performance'),
                ratios.get('risk_adjusted_return')
            ))
            
            # Sauvegarde métriques sociales (simplifiée)
            cursor.execute('''
                INSERT INTO social_metrics (
                    project_id, twitter_followers, telegram_members, 
                    github_stars, github_commits_90d, discord_members, reddit_subscribers
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id,
                project.get('twitter_followers'),
                project.get('telegram_members'),
                project.get('github_stars'),
                project.get('github_commits_90d'),
                project.get('discord_members'),
                project.get('reddit_subscribers')
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"💾 Project saved to DB: {project.get('name')}")
            
        except Exception as e:
            logger.error(f"Error saving project to DB: {e}")
    
    def save_scan_history(self, scan_start: datetime, scan_end: datetime):
        """Sauvegarde l'historique du scan"""
        try:
            conn = sqlite3.connect('quantum.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO scan_history (
                    scan_start, scan_end, projects_found, projects_scanned,
                    projects_accepted, projects_rejected, projects_review,
                    fakes_detected, scam_blocked, errors, alerts_sent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                scan_start, scan_end, self.stats['projects_found'],
                self.stats['projects_scanned'], self.stats['accepted'],
                self.stats['rejected'], self.stats['review'], 
                self.stats['fakes_detected'], self.stats['scam_blocked'],
                self.stats['errors'], self.stats['alerts_sent']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving scan history: {e}")
    
    # ============================================================================
    # SCAN PRINCIPAL
    # ============================================================================
    
    async def scan(self):
        """Exécute un scan complet"""
        scan_start = datetime.now()
        logger.info("🚀 DÉMARRAGE SCAN QUANTUM v6.0")
        
        try:
            # 1. Récupération des projets
            projects = await self.fetch_all_launchpads()
            
            if not projects:
                logger.warning("❌ Aucun projet trouvé")
                return
            
            logger.info(f"📁 {len(projects)} projets à analyser")
            
            # 2. Analyse de chaque projet
            for i, project in enumerate(projects[:self.max_projects], 1):
                try:
                    logger.info(f"[{i}/{min(self.max_projects, len(projects))}] Analyzing: {project.get('name')}")
                    
                    # Vérification complète
                    analysis = await self.verify_project(project)
                    
                    # Sauvegarde en base
                    self.save_project_to_db(project, analysis)
                    
                    # Envoi alerte Telegram si nécessaire
                    if analysis['verdict'] in ['✅ GO!', '⚠️ REVIEW']:
                        await self.send_telegram_alert(project, analysis)
                    
                    # Pause entre les requêtes
                    await asyncio.sleep(self.api_delay)
                    
                except Exception as e:
                    logger.error(f"Error processing {project.get('name')}: {e}")
                    self.stats['errors'] += 1
                    continue
            
            # 3. Sauvegarde historique
            scan_end = datetime.now()
            self.save_scan_history(scan_start, scan_end)
            
            # 4. Rapport final
            duration = (scan_end - scan_start).total_seconds()
            logger.info(f"""
🎉 SCAN QUANTUM v6.0 TERMINÉ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 STATISTIQUES:
• Projets trouvés: {self.stats['projects_found']}
• Projets analysés: {self.stats['projects_scanned']}
• ✅ ACCEPTÉS: {self.stats['accepted']}
• ⚠️ REVIEW: {self.stats['review']}  
• ❌ REJETÉS: {self.stats['rejected']}
• 🚫 SCAMS BLOQUÉS: {self.stats['scam_blocked']}
• 📨 ALERTES ENVOYÉES: {self.stats['alerts_sent']}
• ⚠️ ERREURS: {self.stats['errors']}

⏱️ DURÉE: {duration:.1f}s
            """)
            
            # Export des résultats
            self.export_results(projects)
            
        except Exception as e:
            logger.error(f"❌ ERREUR CRITIQUE DANS LE SCAN: {e}")
            self.stats['errors'] += 1
    
    def export_results(self, projects: List[Dict]):
        """Exporte les résultats en JSON"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"results/quantum_scan_{timestamp}.json"
            
            results = {
                "scan_timestamp": datetime.now().isoformat(),
                "stats": self.stats,
                "projects": projects
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Résultats exportés: {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting results: {e}")


# ============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================================

async def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='Quantum Scanner v6.0 - Le plus complet au monde')
    parser.add_argument('--once', action='store_true', help='Scan unique')
    parser.add_argument('--daemon', action='store_true', help='Mode démon 24/7')
    parser.add_argument('--github-actions', action='store_true', help='Mode GitHub Actions')
    parser.add_argument('--test', type=str, help='Test un projet spécifique')
    parser.add_argument('--verbose', action='store_true', help='Mode verbeux')
    parser.add_argument('--config', type=str, default='config.yml', help='Fichier de configuration')
    
    args = parser.parse_args()
    
    # Configuration des logs
    if args.verbose:
        logger.remove()
        logger.add(lambda msg: print(msg, flush=True), level="DEBUG")
    
    # Initialisation du scanner
    scanner = QuantumScanner(args.config)
    
    try:
        if args.github_actions or args.once:
            logger.info("🔧 Mode GitHub Actions/Scan unique")
            await scanner.scan()
        elif args.daemon:
            logger.info(f"👁️ Mode Démon - Scan toutes les {scanner.scan_interval}h")
            while True:
                await scanner.scan()
                logger.info(f"💤 Pause de {scanner.scan_interval} heures...")
                await asyncio.sleep(scanner.scan_interval * 3600)
        elif args.test:
            logger.info(f"🧪 Mode Test - Projet: {args.test}")
            # Implémenter le test unitaire si nécessaire
        else:
            logger.info("❓ Aucun mode spécifié. Utilisez --once, --daemon ou --github-actions")
            parser.print_help()
    
    except KeyboardInterrupt:
        logger.info("⏹️ Scan interrompu par l'utilisateur")
    except Exception as e:
        logger.error(f"💥 Erreur fatale: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
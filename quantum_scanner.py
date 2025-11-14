# quantum_scanner_ULTIME_COMPLET.py
import sqlite3
import requests
import time
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
from scipy import stats
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

# CHARGEMENT .env
load_dotenv()

warnings.filterwarnings('ignore')

# CONFIGURATION LOGGING AVANCÉE
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quantum_scanner.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class QuantumMilitaryScannerULTIME:
    """
    QUANTUM MILITARY SCANNER ULTIME - Version Complète 2000+ lignes
    Système d'analyse crypto le plus avancé au monde
    """
    
    def __init__(self, db_path: str = "quantum_military.db"):
        self.db_path = db_path
        self.version = "4.0.0"
        
        # CONFIGURATION TELEGRAM - CRITIQUE
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # CONFIGURATION CRITÈRE MARKET CAP
        self.MAX_MARKET_CAP_EUROS = int(os.getenv('MAX_MARKET_CAP_EUR', 621000))
        self.MAX_MARKET_CAP_USD = self.MAX_MARKET_CAP_EUROS * 1.08
        
        logger.info(f"🔧 Initialisation Scanner Ultime v{self.version}")
        logger.info(f"🔧 Telegram Token: {'✅' if self.telegram_token else '❌'}")
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
        
        # CACHE INTELLIGENT
        self.cache = {}
        self.cache_ttl = 3600
        
        # AUTO-HEALING
        self.health_status = "HEALTHY"
        self.error_count = 0
        self.max_errors = 10
        
        # INTELLIGENCE COLLECTIVE
        self.global_intelligence = self.load_global_intelligence()
        
        # INITIALISATION BASE
        self.init_database()
        
        logger.info(f"✅ Scanner initialisé avec MC max: {self.MAX_MARKET_CAP_EUROS:,}€")

    def init_database(self):
        """Initialise la base de données SQLite complète"""
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
                global_score REAL DEFAULT 0,
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
        
        conn.commit()
        conn.close()
        logger.info("✅ Base de données initialisée avec succès")

    def load_sources(self) -> Dict:
        """Charge toutes les sources de données"""
        return {
            "ico_platforms": [
                "https://coinlist.co", "https://www.daomaker.com", 
                "https://www.polkastarter.com", "https://www.trustswap.com",
                "https://seedify.fund", "https://www.pinksale.finance",
                "https://www.gempad.app", "https://www.chainboost.com",
                "https://www.trustpad.io", "https://www.bscpad.com",
                "https://www.gamefi.org", "https://www.redkite.com",
                "https://www.occam.fi", "https://www.impossible.finance",
                "https://www.apeswap.finance", "https://www.poolz.finance"
            ],
            "data_apis": {
                "coinmarketcap": "https://pro-api.coinmarketcap.com/v1/",
                "coingecko": "https://api.coingecko.com/api/v3/",
                "dex_screener": "https://api.dexscreener.com/latest/",
                "moralis": "https://deep-index.moralis.io/api/v2/",
                "etherscan": "https://api.etherscan.io/api",
                "bscscan": "https://api.bscscan.com/api",
                "solanascan": "https://api.solscan.io/v2/",
                "polygonscan": "https://api.polygonscan.com/api"
            },
            "social_platforms": [
                "https://twitter.com/", "https://t.me/", 
                "https://discord.gg/", "https://github.com/",
                "https://reddit.com/r/", "https://medium.com/"
            ],
            "aggregators": [
                "https://icodrops.com", "https://icobench.com",
                "https://cryptorank.io", "https://coinmarketcal.com",
                "https://defillama.com", "https://dappradar.com"
            ]
        }

    def load_user_agents(self) -> List[str]:
        """Charge la liste des user-agents pour rotation"""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36"
        ]

    def load_proxies(self) -> List[str]:
        """Charge et teste les proxies"""
        # Liste de proxies gratuits (à remplacer par vos propres proxies)
        test_proxies = [
            # "http://proxy1:port", 
            # "http://proxy2:port",
        ]
        
        working_proxies = []
        for proxy in test_proxies:
            if self.test_proxy(proxy):
                working_proxies.append(proxy)
                logger.info(f"✅ Proxy actif: {proxy}")
        
        return working_proxies

    def test_proxy(self, proxy: str) -> bool:
        """Teste la validité d'un proxy"""
        try:
            response = requests.get(
                "https://httpbin.org/ip",
                proxies={"http": proxy, "https": proxy},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

    def load_scam_patterns(self) -> Dict:
        """Charge les patterns de scams avancés"""
        return {
            "high_risk_keywords": [
                "guaranteed", "100% profit", "no risk", "instant money",
                "zero risk", "can't lose", "guaranteed returns", "risk-free",
                "get rich quick", "easy money", "double your money"
            ],
            "suspicious_domains": [
                ".xyz", ".top", ".club", ".win", ".biz", ".info",
                ".online", ".site", ".website", ".space"
            ],
            "fake_audit_patterns": [
                "certik-fake", "hacken-fake", "quantstamp-fake",
                "fake-audit", "audit-by-unknown", "self-audit"
            ],
            "rugpull_indicators": [
                "owner_balance_high", "liquidity_locked_low",
                "mint_function_active", "blacklist_function",
                "hidden_owner", "proxy_contract"
            ],
            "honeypot_indicators": [
                "cannot_sell", "max_tx_amount_low", "blacklist_owners",
                "tax_too_high", "transfer_disabled"
            ]
        }

    def load_smart_money_wallets(self) -> List[str]:
        """Charge les adresses des smart money (exemples)"""
        return [
            "0x0000000000000000000000000000000000000000",  # Exemple
            "0x0000000000000000000000000000000000000001",  # Exemple
        ]

    def load_reputable_vcs(self) -> Dict:
        """Charge la liste des VCs réputés avec scores"""
        return {
            "Electric Capital": {"score": 95, "focus": ["DeFi", "Infrastructure"]},
            "Framework Ventures": {"score": 92, "focus": ["DeFi", "Gaming"]},
            "Paradigm": {"score": 98, "focus": ["DeFi", "Infrastructure"]},
            "a16z Crypto": {"score": 97, "focus": ["Multi-sector"]},
            "Polychain Capital": {"score": 94, "focus": ["Infrastructure", "DeFi"]},
            "Coinbase Ventures": {"score": 91, "focus": ["Multi-sector"]},
            "Binance Labs": {"score": 96, "focus": ["Multi-sector"]},
            "Multicoin Capital": {"score": 93, "focus": ["Infrastructure", "DeFi"]},
            "Dragonfly Capital": {"score": 89, "focus": ["DeFi", "Gaming"]},
            "Pantera Capital": {"score": 90, "focus": ["Multi-sector"]},
            "Alameda Research": {"score": 88, "focus": ["Trading", "DeFi"]},
            "Three Arrows Capital": {"score": 87, "focus": ["Macro", "DeFi"]}
        }

    def load_global_intelligence(self) -> Dict:
        """Charge l'intelligence collective depuis la base"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT pattern_type, pattern_data, confidence, source 
            FROM global_intelligence 
            WHERE confidence > 0.7 
            ORDER BY detected_at DESC 
            LIMIT 1000
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

    def get_rotated_headers(self) -> Dict:
        """Retourne les headers avec rotation d'user-agent"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "application/json, text/html, application/xml",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none"
        }

    def make_advanced_request(self, url: str, method: str = "GET", 
                            retries: int = 3, delay: float = 1.0) -> Optional[Any]:
        """Effectue une requête HTTP avancée avec gestion d'erreurs"""
        
        # Vérification du cache
        cache_key = hashlib.md5(url.encode()).hexdigest()
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(f"📦 Cache hit: {url}")
                return cached_data
        
        for attempt in range(retries):
            try:
                headers = self.get_rotated_headers()
                
                # Rotation des proxies
                if self.proxies:
                    proxy = self.proxies[self.current_proxy_index % len(self.proxies)]
                    self.current_proxy_index += 1
                    proxies = {"http": proxy, "https": proxy}
                else:
                    proxies = None
                
                # Backoff exponentiel
                time.sleep(delay * (2 ** attempt))
                
                if method.upper() == "GET":
                    response = requests.get(
                        url, 
                        headers=headers, 
                        proxies=proxies,
                        timeout=15,
                        allow_redirects=True
                    )
                else:
                    response = requests.request(
                        method, 
                        url,
                        headers=headers,
                        proxies=proxies,
                        timeout=15,
                        allow_redirects=True
                    )
                
                if response.status_code == 200:
                    # Mise en cache
                    data = response.json() if 'application/json' in response.headers.get('content-type', '') else response.text
                    self.cache[cache_key] = (data, time.time())
                    return data
                    
                elif response.status_code in [429, 503]:  # Rate limiting
                    logger.warning(f"⏳ Rate limiting détecté pour {url}, attente augmentée")
                    time.sleep(10 * (attempt + 1))
                else:
                    logger.warning(f"⚠️ Statut HTTP {response.status_code} pour {url}")
                    
            except requests.exceptions.Timeout:
                logger.error(f"⏰ Timeout pour {url} (tentative {attempt + 1})")
            except requests.exceptions.ConnectionError:
                logger.error(f"🔌 Erreur de connexion pour {url}")
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Erreur requête pour {url}: {e}")
            except Exception as e:
                logger.error(f"💥 Erreur inattendue pour {url}: {e}")
            
            # Auto-healing: ajustement dynamique
            self.error_count += 1
            if self.error_count > self.max_errors:
                self.health_status = "DEGRADED"
                self.perform_auto_healing()
        
        logger.error(f"❌ Échec après {retries} tentatives pour {url}")
        return None

    def perform_auto_healing(self):
        """Système auto-réparateur"""
        logger.warning("🩺 Activation de l'auto-healing...")
        
        # Réinitialisation des compteurs d'erreur
        self.error_count = 0
        
        # Nettoyage du cache
        current_time = time.time()
        self.cache = {k: v for k, v in self.cache.items() 
                     if current_time - v[1] < self.cache_ttl}
        
        # Re-test des proxies
        self.proxies = self.load_proxies()
        
        # Réinitialisation de l'index proxy
        self.current_proxy_index = 0
        
        self.health_status = "HEALTHY"
        logger.info("✅ Auto-healing terminé")

    async def make_async_request(self, session: aiohttp.ClientSession, 
                               url: str) -> Optional[Any]:
        """Effectue une requête asynchrone"""
        try:
            headers = self.get_rotated_headers()
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"⚠️ Statut HTTP {response.status} pour {url}")
        except Exception as e:
            logger.error(f"❌ Erreur async requête {url}: {e}")
        return None

    # SYSTÈME TELEGRAM ULTIME
    def send_telegram_alert(self, message: str, retry_count: int = 3) -> bool:
        """
        ENVOIE UN MESSAGE TELEGRAM - Version Ultime avec gestion d'erreurs complète
        """
        logger.info("📤 Tentative d'envoi Telegram...")
        
        # VÉRIFICATION CRITIQUE
        if not self.telegram_token:
            logger.error("❌ TELEGRAM_BOT_TOKEN manquant dans .env")
            return False
            
        if not self.telegram_chat_id:
            logger.error("❌ TELEGRAM_CHAT_ID manquant dans .env")
            return False
        
        logger.info(f"🔧 Token: {self.telegram_token[:10]}...")
        logger.info(f"🔧 Chat ID: {self.telegram_chat_id}")
        
        for attempt in range(retry_count):
            try:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                payload = {
                    "chat_id": self.telegram_chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True
                }
                
                logger.info(f"🔧 Envoi vers: {url}")
                response = requests.post(url, json=payload, timeout=30)
                
                logger.info(f"🔧 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    logger.info("✅ ✅ ✅ MESSAGE TELEGRAM ENVOYÉ AVEC SUCCÈS!")
                    self.track_telegram_metric()
                    return True
                else:
                    logger.error(f"❌ Erreur HTTP {response.status_code}: {response.text}")
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)  # Backoff exponentiel
                        
            except requests.exceptions.Timeout:
                logger.error(f"⏰ Timeout Telegram (tentative {attempt + 1})")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
            except requests.exceptions.ConnectionError:
                logger.error(f"🔌 Erreur connexion Telegram (tentative {attempt + 1})")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"💥 Erreur inattendue Telegram (tentative {attempt + 1}): {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
        
        logger.error("❌ ÉCHEC COMPLET après toutes les tentatives Telegram")
        return False

    def track_telegram_metric(self):
        """Track les métriques Telegram"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO performance_metrics (telegram_messages_sent) 
                VALUES (1)
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Erreur tracking métrique: {e}")

    def test_telegram_connection(self) -> bool:
        """Test la connexion Telegram de manière complète"""
        logger.info("🔧 Test de connexion Telegram...")
        
        if not self.telegram_token or not self.telegram_chat_id:
            logger.error("❌ Configuration Telegram incomplète")
            return False
            
        try:
            # Test de l'API Telegram
            url = f"https://api.telegram.org/bot{self.telegram_token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                logger.info(f"✅ Bot Telegram: {bot_info['result']['username']}")
                
                # Test d'envoi de message
                test_message = f"""
🔧 **TEST QUANTUM SCANNER ULTIME v{self.version}**

✅ **Connexion Telegram établie!**
🕒 **Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**
🎯 **Scanner opérationnel et prêt**

🔧 **Détails:**
• Version: {self.version}
• MC Max: {self.MAX_MARKET_CAP_EUROS:,}€
• Statut: 🟢 ACTIF

#Test #QuantumScanner #Ultime
                """
                
                if self.send_telegram_alert(test_message):
                    logger.info("✅ Test Telegram COMPLET - Tout fonctionne!")
                    return True
                else:
                    logger.error("❌ Échec envoi message test")
                    return False
            else:
                logger.error(f"❌ Token Telegram invalide: {response.status_code}")
                logger.error(f"❌ Détails: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"💥 Erreur test Telegram: {e}")
            return False

    # PROJETS RÉELS POUR TEST
    def get_real_test_projects(self) -> List[Dict]:
        """
        Retourne des projets RÉELS avec sites existants pour tests
        """
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
                "description": "Blockchain décentralisée leader avec smart contracts"
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
            },
            {
                "name": "Aave Protocol",
                "symbol": "AAVE",
                "market_cap": 28000,
                "fdmc": 1500000,
                "website": "https://aave.com",
                "twitter": "https://twitter.com/AaveAave",
                "telegram": "https://t.me/Aavesome",
                "github": "https://github.com/aave",
                "stage": "pre-tge",
                "category": "DeFi",
                "blockchain": "Ethereum",
                "audit_score": 94,
                "dev_activity": 85,
                "community_engagement": 80,
                "vcs": ["Framework Ventures", "Three Arrows Capital"],
                "description": "Protocol de prêt et emprunt décentralisé"
            }
        ]

    # VALIDATION DES LIENS AVANCÉE
    def validate_project_links_advanced(self, project_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validation AVANCÉE des liens avec vérifications multiples
        """
        errors = []
        warnings_list = []
        
        required_links = [
            ("website", project_data.get("website"), True),
            ("twitter", project_data.get("twitter"), True),
            ("telegram", project_data.get("telegram"), True),
            ("github", project_data.get("github"), False)
        ]
        
        for link_type, url, is_critical in required_links:
            if not url and is_critical:
                errors.append(f"Lien {link_type} manquant (critique)")
                continue
            elif not url:
                warnings_list.append(f"Lien {link_type} manquant")
                continue
                
            validation_result = self.validate_single_link(link_type, url)
            
            if not validation_result["valid"]:
                if is_critical:
                    errors.extend(validation_result["errors"])
                else:
                    warnings_list.extend(validation_result["errors"])
            else:
                warnings_list.extend(validation_result["warnings"])
        
        # Vérification de cohérence cross-platform
        consistency_errors = self.check_cross_platform_consistency(project_data)
        errors.extend(consistency_errors)
        
        is_valid = len(errors) == 0
        
        if warnings_list:
            logger.warning(f"⚠️ Avertissements pour {project_data.get('name')}: {warnings_list}")
        
        return is_valid, errors + warnings_list

    def validate_single_link(self, link_type: str, url: str) -> Dict:
        """Valide un lien unique avec multiples vérifications"""
        result = {"valid": True, "errors": [], "warnings": []}
        
        try:
            response = requests.get(url, timeout=10, allow_redirects=True)
            
            # Vérification statut HTTP
            if response.status_code != 200:
                result["valid"] = False
                result["errors"].append(f"Lien {link_type} inaccessible: HTTP {response.status_code}")
                return result
            
            content = response.text.lower()
            
            # Détection de pages parking/suspectes
            parking_indicators = [
                "for sale", "domain parked", "buy this domain", 
                "parking page", "this domain may be for sale",
                "godaddy", "namecheap parking", "domain for sale"
            ]
            
            if any(indicator in content for indicator in parking_indicators):
                result["valid"] = False
                result["errors"].append(f"Lien {link_type} semble être un domaine parking")
                return result
            
            # Vérifications spécifiques par type
            if link_type == "website":
                website_checks = self.validate_website_content(content, url)
                result["errors"].extend(website_checks["errors"])
                result["warnings"].extend(website_checks["warnings"])
                
            elif link_type == "twitter":
                twitter_checks = self.validate_twitter_content(content, url)
                result["warnings"].extend(twitter_checks)
                
            elif link_type == "github":
                github_checks = self.validate_github_content(content, url)
                result["warnings"].extend(github_checks)
                
        except requests.exceptions.RequestException as e:
            result["valid"] = False
            result["errors"].append(f"Erreur connexion {link_type}: {str(e)}")
        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Erreur validation {link_type}: {str(e)}")
        
        return result

    def validate_website_content(self, content: str, url: str) -> Dict:
        """Valide le contenu du site web"""
        checks = {"errors": [], "warnings": []}
        
        # Vérification présence page team
        if "team" not in content and "about" not in content and "contact" not in content:
            checks["warnings"].append("Page 'Team'/'About' non détectée")
        
        # Vérification présence whitepaper/litepaper
        if "whitepaper" not in content and "litepaper" not in content and "documentation" not in content:
            checks["warnings"].append("Whitepaper/Documentation non détecté")
        
        # Vérification contact
        if "contact" not in content and "mailto:" not in content and "support" not in content:
            checks["warnings"].append("Informations de contact manquantes")
        
        # Détection de templates génériques
        generic_indicators = ["lorem ipsum", "coming soon", "under construction"]
        if any(indicator in content for indicator in generic_indicators):
            checks["warnings"].append("Contenu générique/template détecté")
        
        return checks

    def validate_twitter_content(self, content: str, url: str) -> List[str]:
        """Valide le contenu Twitter (basique)"""
        warnings = []
        
        # Ces vérifications nécessiteraient l'API Twitter
        # Pour l'instant, vérifications basiques
        if "account suspended" in content:
            warnings.append("Compte Twitter suspendu")
        if "this account doesn't exist" in content:
            warnings.append("Compte Twitter inexistant")
        
        return warnings

    def validate_github_content(self, content: str, url: str) -> List[str]:
        """Valide le contenu GitHub"""
        warnings = []
        
        if "this repository is empty" in content:
            warnings.append("Dépôt GitHub vide")
        if "page not found" in content:
            warnings.append("Dépôt GitHub non trouvé")
        
        return warnings

    def check_cross_platform_consistency(self, project_data: Dict) -> List[str]:
        """Vérifie la cohérence cross-platform"""
        errors = []
        project_name = project_data.get("name", "").lower().replace(" ", "").replace("-", "")
        
        # Vérification Twitter
        twitter_url = project_data.get("twitter", "")
        if twitter_url and project_name:
            twitter_handle = twitter_url.rstrip('/').split('/')[-1].lower()
            if project_name not in twitter_handle and twitter_handle not in project_name:
                errors.append(f"Incohérence Twitter: handle '{twitter_handle}' ne correspond pas au nom")
        
        # Vérification Telegram
        telegram_url = project_data.get("telegram", "")
        if telegram_url and project_name:
            telegram_handle = telegram_url.rstrip('/').split('/')[-1].lower()
            if project_name not in telegram_handle and telegram_handle not in project_name:
                errors.append(f"Incohérence Telegram: handle '{telegram_handle}' ne correspond pas au nom")
        
        return errors

    # CALCUL DES 21 RATIOS FINANCIERS
    def calculate_21_ratios_advanced(self, project_data: Dict) -> Dict:
        """
        Calcule les 21 ratios financiers avec intelligence avancée
        et focus sur MC < 621,000€
        """
        ratios = {}
        
        try:
            # Données de base
            mc = project_data.get('market_cap', 0)
            fdmc = project_data.get('fdmc', 0)
            volume = project_data.get('volume_24h', 0)
            liquidity = project_data.get('liquidity', 0)
            tvl = project_data.get('tvl', 0)
            circulating_supply = project_data.get('circulating_supply', 0)
            total_supply = project_data.get('total_supply', 0)
            
            # 1. Ratio Market Cap / FDMC
            ratios['mc_fdmc_ratio'] = mc / fdmc if fdmc > 0 else 0
            
            # 2. Ratio Volume/MC (Liquidité)
            ratios['volume_mc_ratio'] = volume / mc if mc > 0 else 0
            
            # 3. Ratio Liquidité/MC
            ratios['liquidity_mc_ratio'] = liquidity / mc if mc > 0 else 0
            
            # 4. Ratio TVL/MC (Value Accrual)
            ratios['tvl_mc_ratio'] = tvl / mc if mc > 0 else 0
            
            # 5. Concentration whales
            ratios['whale_concentration'] = project_data.get('whale_concentration', 0.1)
            
            # 6. Score audit
            ratios['audit_score'] = project_data.get('audit_score', 0) / 100
            
            # 7. Activité développeurs
            ratios['dev_activity'] = project_data.get('dev_activity', 0) / 100
            
            # 8. Engagement communauté
            ratios['community_engagement'] = project_data.get('community_engagement', 0) / 100
            
            # 9. Momentum croissance
            ratios['growth_momentum'] = self.calculate_growth_momentum(project_data)
            
            # 10. Momentum hype
            ratios['hype_momentum'] = self.calculate_hype_momentum(project_data)
            
            # 11. Utilité token
            ratios['token_utility'] = self.assess_token_utility(project_data)
            
            # 12. Anomalies on-chain
            ratios['on_chain_anomaly'] = self.detect_onchain_anomalies(project_data)
            
            # 13. Risque rugpull
            ratios['rugpull_risk'] = self.calculate_rugpull_risk(project_data)
            
            # 14. Force VCs
            ratios['vc_strength'] = self.calculate_vc_strength(project_data)
            
            # 15. Ratio Prix/Liquidité
            ratios['price_to_liquidity'] = mc / liquidity if liquidity > 0 else float('inf')
            
            # 16. Ratio Dev/VC
            ratios['dev_vc_ratio'] = self.calculate_dev_vc_ratio(project_data)
            
            # 17. Ratio Rétention
            ratios['retention_ratio'] = self.calculate_retention_ratio(project_data)
            
            # 18. Index Smart Money
            ratios['smart_money_index'] = self.calculate_smart_money_index(project_data)
            
            # 19. Score qualité équipe
            ratios['team_quality_score'] = self.assess_team_quality(project_data)
            
            # 20. Potentiel de croissance
            ratios['growth_potential'] = self.assess_growth_potential(project_data)
            
            # 21. Score global pondéré
            ratios['global_score'] = self.calculate_global_score(ratios)
            
            # Estimation multiple potentiel
            ratios['estimated_multiple'] = self.estimate_potential_multiple(ratios)
            
        except Exception as e:
            logger.error(f"Erreur calcul ratios: {e}")
            # Valeurs par défaut en cas d'erreur
            ratios = {f'ratio_{i}': 0 for i in range(1, 22)}
        
        return ratios

    def calculate_growth_momentum(self, project_data: Dict) -> float:
        """Calcule le momentum de croissance basé sur plusieurs facteurs"""
        factors = []
        
        # Facteur 1: Volume récent vs volume historique
        volume_ratio = project_data.get('volume_24h', 0) / max(project_data.get('avg_volume_7d', 1), 1)
        factors.append(min(volume_ratio, 3.0) / 3.0)  # Normalisé 0-1
        
        # Facteur 2: Croissance prix récente
        price_change = project_data.get('price_change_24h', 0)
        factors.append(max(0, min(price_change / 50.0, 1.0)))  # +50% = 1.0
        
        # Facteur 3: Adoption (holders growth)
        holders_growth = project_data.get('holders_growth_30d', 0)
        factors.append(max(0, min(holders_growth / 100.0, 1.0)))  # +100% = 1.0
        
        return sum(factors) / len(factors)

    def calculate_hype_momentum(self, project_data: Dict) -> float:
        """Calcule le momentum hype (social sentiment)"""
        factors = []
        
        # Facteur 1: Engagement Twitter
        twitter_engagement = project_data.get('twitter_engagement', 0)
        factors.append(min(twitter_engagement / 1000.0, 1.0))
        
        # Facteur 2: Taille communauté Telegram
        telegram_members = project_data.get('telegram_members', 0)
        factors.append(min(telegram_members / 5000.0, 1.0))
        
        # Facteur 3: Sentiment général
        sentiment = project_data.get('social_sentiment', 0.5)
        factors.append(sentiment)
        
        return sum(factors) / len(factors)

    def assess_token_utility(self, project_data: Dict) -> float:
        """Évalue l'utilité du token"""
        utility_score = 0.5  # Base
        
        # Bonus pour utilités spécifiques
        utilities = project_data.get('token_utilities', [])
        
        if 'governance' in utilities:
            utility_score += 0.2
        if 'staking' in utilities:
            utility_score += 0.15
        if 'fee_reduction' in utilities:
            utility_score += 0.1
        if 'access' in utilities:
            utility_score += 0.1
        if 'revenue_share' in utilities:
            utility_score += 0.2
            
        return min(utility_score, 1.0)

    def detect_onchain_anomalies(self, project_data: Dict) -> float:
        """Détecte les anomalies on-chain (plus bas = mieux)"""
        anomaly_score = 0.0
        
        # Anomalie 1: Transactions suspectes
        suspicious_txs = project_data.get('suspicious_transactions', 0)
        anomaly_score += min(suspicious_txs / 10.0, 0.3)
        
        # Anomalie 2: Concentration excessive
        top10_holders = project_data.get('top10_holders_percent', 0)
        if top10_holders > 80:
            anomaly_score += 0.3
        elif top10_holders > 60:
            anomaly_score += 0.2
            
        # Anomalie 3: Liquidité verrouillée faible
        locked_liquidity = project_data.get('locked_liquidity_percent', 0)
        if locked_liquidity < 50:
            anomaly_score += 0.2
        elif locked_liquidity < 80:
            anomaly_score += 0.1
            
        return min(anomaly_score, 1.0)

    def calculate_rugpull_risk(self, project_data: Dict) -> float:
        """Calcule le risque de rugpull (plus bas = mieux)"""
        risk_score = 0.0
        
        # Risque 1: Contract non vérifié
        if not project_data.get('contract_verified', False):
            risk_score += 0.4
            
        # Risque 2: Owner avec trop de pouvoir
        owner_control = project_data.get('owner_control', 0)
        if owner_control > 50:
            risk_score += 0.3
            
        # Risque 3: Mint function active
        if project_data.get('mint_function_active', False):
            risk_score += 0.2
            
        # Risque 4: Blacklist function
        if project_data.get('blacklist_function', False):
            risk_score += 0.1
            
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
        """Calcule le ratio de rétention des holders"""
        retention_data = project_data.get('holder_retention', {})
        
        if not retention_data:
            return 0.5  # Valeur par défaut
            
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
        # Expérience moyenne de l'équipe
        avg_experience = team_data.get('avg_experience_years', 0)
        score += min(avg_experience / 10.0, 0.4)
        
        # Track record
        previous_projects = team_data.get('previous_successful_projects', 0)
        score += min(previous_projects / 5.0, 0.3)
        
        # Transparence
        if team_data.get('doxxed', False):
            score += 0.3
            
        return min(score, 1.0)

    def assess_growth_potential(self, project_data: Dict) -> float:
        """Évalue le potentiel de croissance"""
        factors = []
        
        # TAM (Total Addressable Market)
        tam_size = project_data.get('tam_size', 'medium')
        tam_scores = {'small': 0.3, 'medium': 0.6, 'large': 0.9, 'massive': 1.0}
        factors.append(tam_scores.get(tam_size, 0.5))
        
        # Innovation
        innovation_level = project_data.get('innovation_level', 'medium')
        innovation_scores = {'low': 0.2, 'medium': 0.5, 'high': 0.8, 'breakthrough': 1.0}
        factors.append(innovation_scores.get(innovation_level, 0.5))
        
        # Timing marché
        market_timing = project_data.get('market_timing', 'neutral')
        timing_scores = {'bad': 0.2, 'neutral': 0.5, 'good': 0.8, 'perfect': 1.0}
        factors.append(timing_scores.get(market_timing, 0.5))
        
        return sum(factors) / len(factors)

    def calculate_global_score(self, ratios: Dict) -> float:
        """Calcule le score global pondéré"""
        weights = {
            'mc_fdmc_ratio': 0.05,
            'volume_mc_ratio': 0.08,
            'liquidity_mc_ratio': 0.1,
            'tvl_mc_ratio': 0.07,
            'audit_score': 0.08,
            'dev_activity': 0.09,
            'community_engagement': 0.06,
            'growth_momentum': 0.07,
            'hype_momentum': 0.05,
            'token_utility': 0.06,
            'vc_strength': 0.08,
            'rugpull_risk': -0.15,  # Négatif car risque
            'on_chain_anomaly': -0.10,  # Négatif car anomalie
            'smart_money_index': 0.12,
            'team_quality_score': 0.08
        }
        
        score = 0.5  # Score de base
        
        for ratio, weight in weights.items():
            value = ratios.get(ratio, 0)
            score += value * weight
        
        return max(0, min(1, score))  # Normalisé entre 0 et 1

    def estimate_potential_multiple(self, ratios: Dict) -> float:
        """Estime le multiple de croissance potentiel"""
        base_multiple = 1.0
        
        # Facteurs boostant le multiple
        if ratios.get('global_score', 0) > 0.8:
            base_multiple *= 3.0
        elif ratios.get('global_score', 0) > 0.7:
            base_multiple *= 2.0
        elif ratios.get('global_score', 0) > 0.6:
            base_multiple *= 1.5
            
        # Boost par VC strength
        if ratios.get('vc_strength', 0) > 0.8:
            base_multiple *= 1.5
            
        # Boost par smart money
        if ratios.get('smart_money_index', 0) > 0.7:
            base_multiple *= 1.3
            
        # Réduction par risque
        if ratios.get('rugpull_risk', 0) > 0.5:
            base_multiple *= 0.3
        elif ratios.get('rugpull_risk', 0) > 0.3:
            base_multiple *= 0.7
            
        return round(base_multiple, 1)

    # MÉTHODE D'ANALYSE PRINCIPALE
    def analyze_single_project(self, project: Dict) -> Dict:
        """Analyse un projet unique de manière complète"""
        
        logger.info(f"🔍 Analyse détaillée de {project.get('name')}...")
        
        # Validation des liens
        is_valid, validation_errors = self.validate_project_links_advanced(project)
        
        # Vérification critère market cap
        meets_cap_criteria = project.get('market_cap', 0) <= self.MAX_MARKET_CAP_EUROS
        
        # Calcul des 21 ratios avancés
        ratios = self.calculate_21_ratios_advanced(project)
        
        # Décision GO/NOGO
        go_decision = (
            is_valid and 
            meets_cap_criteria and 
            ratios.get('global_score', 0) > 0.65 and
            ratios.get('rugpull_risk', 1) < 0.4 and
            ratios.get('on_chain_anomaly', 1) < 0.5
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
        self.save_analysis_to_db(result)
        
        logger.info(f"✅ Analyse {project.get('name')} terminée - Decision: {'GO' if go_decision else 'NOGO'}")
        
        return result

    def determine_risk_level(self, ratios: Dict) -> str:
        """Détermine le niveau de risque"""
        rugpull_risk = ratios.get('rugpull_risk', 0)
        anomaly_score = ratios.get('on_chain_anomaly', 0)
        global_score = ratios.get('global_score', 0)
        
        if rugpull_risk > 0.6 or anomaly_score > 0.7:
            return "EXTREME"
        elif rugpull_risk > 0.4 or anomaly_score > 0.5:
            return "HIGH"
        elif rugpull_risk > 0.2 or global_score < 0.5:
            return "MEDIUM"
        else:
            return "LOW"

    def generate_detailed_rationale(self, project: Dict, ratios: Dict, go_decision: bool) -> str:
        """Génère un rationale détaillé pour la décision"""
        
        strengths = []
        weaknesses = []
        
        # Forces
        if ratios.get('vc_strength', 0) > 0.7:
            strengths.append("VCs de qualité")
        if ratios.get('dev_activity', 0) > 0.7:
            strengths.append("Équipe dev active")
        if ratios.get('audit_score', 0) > 0.8:
            strengths.append("Audit solide")
        if ratios.get('smart_money_index', 0) > 0.6:
            strengths.append("Smart money présente")
        if ratios.get('token_utility', 0) > 0.7:
            strengths.append("Utilité token forte")
            
        # Faiblesses
        if ratios.get('rugpull_risk', 0) > 0.3:
            weaknesses.append(f"Risque rugpull élevé ({ratios['rugpull_risk']:.1%})")
        if ratios.get('on_chain_anomaly', 0) > 0.4:
            weaknesses.append(f"Anomalies on-chain ({ratios['on_chain_anomaly']:.1%})")
        if ratios.get('dev_activity', 0) < 0.3:
            weaknesses.append("Activité dev faible")
        if ratios.get('community_engagement', 0) < 0.4:
            weaknesses.append("Engagement communauté faible")
            
        rationale = f"""
Score Global: {ratios.get('global_score', 0):.1%}
Multiple Estimé: {ratios.get('estimated_multiple', 1)}x

FORCES: {', '.join(strengths) if strengths else 'Aucune force majeure'}

FAIBLESSES: {', '.join(weaknesses) if weaknesses else 'Aucune faiblesse critique'}

DÉCISION: {'✅ APPROUVÉ' if go_decision else '❌ REJETÉ'}
        """.strip()
        
        return rationale

    def save_analysis_to_db(self, analysis_result: Dict):
        """Sauvegarde l'analyse en base de données"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insertion projet
            cursor.execute('''
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
                analysis_result['market_cap'] * 1.08,  # Conversion USD
                analysis_result['meets_cap_criteria'],
                analysis_result['website'],
                analysis_result['twitter'],
                analysis_result['telegram'],
                analysis_result['github']
            ))
            
            project_id = cursor.lastrowid
            
            # Insertion analyse détaillée
            ratios = analysis_result['ratios']
            cursor.execute('''
                INSERT INTO project_analysis 
                (project_id, market_cap, fdmc, global_score, go_decision, risk_level, rationale,
                 meets_cap_criteria, audit_score, dev_activity, community_engagement,
                 rugpull_risk, vc_strength, estimated_multiple)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id,
                analysis_result['market_cap'],
                analysis_result.get('fdmc', 0),
                ratios.get('global_score', 0),
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
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde BD: {e}")

    # MÉTHODE D'EXÉCUTION PRINCIPALE
    def run_complete_analysis(self):
        """Exécute l'analyse complète"""
        logger.info("🚀 LANCEMENT ANALYSE QUANTUM ULTIME...")
        start_time = time.time()
        
        # Test Telegram CRITIQUE
        if not self.test_telegram_connection():
            logger.error("❌ Test Telegram échoué - vérifiez la configuration")
            return []
        
        # Récupération projets de test RÉELS
        test_projects = self.get_real_test_projects()
        logger.info(f"🔍 Analyse de {len(test_projects)} projets...")
        
        results = []
        approved_projects = []
        
        for project in test_projects:
            try:
                result = self.analyze_single_project(project)
                results.append(result)
                
                # Envoi Telegram si projet validé
                if result.get('go_decision'):
                    approved_projects.append(result)
                    self.send_project_alert(result)
                    
            except Exception as e:
                logger.error(f"❌ Erreur analyse {project.get('name')}: {e}")
        
        # Rapport final
        self.generate_final_report(results, approved_projects, start_time)
        
        logger.info(f"✅ Analyse terminée: {len(approved_projects)}/{len(results)} projets approuvés")
        
        return results

    def send_project_alert(self, project_result: Dict):
        """Envoie une alerte Telegram pour un projet validé"""
        project = project_result
        ratios = project_result['ratios']
        
        message = f"""
🎯 **PROJET VALIDÉ - QUANTUM SCANNER ULTIME**

🏆 **{project['name']} ({project['symbol']})**
📊 **Market Cap:** {project['market_cap']:,}€
⭐ **Score Global:** {ratios['global_score']:.1%}
🚀 **Potentiel:** {ratios.get('estimated_multiple', 1)}x
⚡ **Risque:** {project_result['risk_level']}

🔍 **Détails:**
• Audit: {project['audit_score']}/100
• Activité Dev: {project['dev_activity']}/100  
• VCs: {', '.join(project['vcs'])}
• Catégorie: {project['category']}

📈 **Ratios Clés:**
• Force VCs: {ratios.get('vc_strength', 0):.1%}
• Risque Rugpull: {ratios.get('rugpull_risk', 0):.1%}
• Smart Money: {ratios.get('smart_money_index', 0):.1%}

🌐 **Liens:**
[Site]({project['website']}) | [Twitter]({project['twitter']}) | [Telegram]({project['telegram']})

💡 **Rationale:**
{project_result['rationale'][:200]}...

⚡ **Décision: ✅ GO**

#Alert #{project['symbol']} #QuantumScanner #Opportunité
"""
        
        if self.send_telegram_alert(message):
            # Marquer comme envoyé en BD
            self.mark_telegram_sent(project_result)

    def mark_telegram_sent(self, project_result: Dict):
        """Marque l'alerte comme envoyée en BD"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE project_analysis 
                SET telegram_sent = 1 
                WHERE project_id = (
                    SELECT id FROM projects WHERE name = ?
                )
            ''', (project_result['name'],))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Erreur marquage Telegram: {e}")

    def generate_final_report(self, results: List[Dict], approved_projects: List[Dict], start_time: float):
        """Génère un rapport final détaillé"""
        duration = time.time() - start_time
        total = len(results)
        approved = len(approved_projects)
        
        # Calcul des métriques
        avg_score = np.mean([r['ratios'].get('global_score', 0) for r in results]) if results else 0
        avg_multiple = np.mean([r['ratios'].get('estimated_multiple', 1) for r in approved_projects]) if approved_projects else 0
        
        report = f"""
📊 **RAPPORT FINAL QUANTUM SCANNER ULTIME**

🔧 **Analyse terminée:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
⏱️ **Durée:** {duration:.1f}s
📈 **Projets analysés:** {total}
✅ **Projets approuvés:** {approved}
❌ **Projets rejetés:** {total - approved}
🎯 **Taux de succès:** {approved/total:.1% if total > 0 else 0}%

📊 **Métriques:**
• Score moyen: {avg_score:.1%}
• Multiple moyen: {avg_multiple:.1f}x
• Meilleur projet: {max([r['ratios'].get('global_score', 0) for r in results]):.1% if results else 'N/A'}

🏆 **Top Projets Approuvés:**
{chr(10).join([f"• {p['name']} ({p['ratios'].get('global_score', 0):.1%}) - {p['ratios'].get('estimated_multiple', 1)}x" for p in approved_projects[:3]]) if approved_projects else '• Aucun'}

💡 **Recommandation:** {'🎯 OPPORTUNITÉS DÉTECTÉES!' if approved > 0 else '⚠️ Aucune opportunité valide'}

#Rapport #QuantumScanner #Final
"""
        
        self.send_telegram_alert(report)
        
        # Sauvegarde métriques performance
        self.save_performance_metrics(duration, total, approved, 0, len(approved_projects))

    def save_performance_metrics(self, duration: float, analyzed: int, approved: int, scams: int, telegram_sent: int):
        """Sauvegarde les métriques de performance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics 
                (scan_duration, projects_analyzed, projects_approved, scams_detected, telegram_messages_sent)
                VALUES (?, ?, ?, ?, ?)
            ''', (duration, analyzed, approved, scams, telegram_sent))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Erreur sauvegarde métriques: {e}")

    # MÉTHODE DE LANCEMENT
    def launch_quantum_scanner(self):
        """Lance le scanner quantique complet"""
        logger.info("🌌 QUANTUM MILITARY SCANNER ULTIME - ACTIVATION...")
        
        # Message de démarrage
        startup_msg = f"""
🚀 **QUANTUM SCANNER ULTIME v{self.version} - ACTIVATION**

🕒 **Démarrage:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔧 **Version:** {self.version}
🎯 **MC Max:** {self.MAX_MARKET_CAP_EUROS:,}€
📊 **Statut:** 🟢 OPÉRATIONNEL

💡 **Objectif:** Détection projets < 621k€ avec fort potentiel

#Démarrage #QuantumScanner #Ultime
"""
        self.send_telegram_alert(startup_msg)
        
        # Lancement analyse
        results = self.run_complete_analysis()
        
        return results

    # SYSTÈME 24/7 AVEC SCHEDULER
    def run_24_7_scanner(self):
        """Lance le scanner en mode 24/7"""
        scan_interval = int(os.getenv('SCAN_INTERVAL_HOURS', 6)) * 3600
        
        logger.info(f"🔄 Mode 24/7 activé - Scan toutes les {scan_interval/3600} heures")
        
        while True:
            try:
                self.launch_quantum_scanner()
                logger.info(f"⏰ Prochain scan dans {scan_interval/3600} heures...")
                time.sleep(scan_interval)
                
            except KeyboardInterrupt:
                logger.info("⏹️ Arrêt demandé par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"💥 Erreur dans le scanner 24/7: {e}")
                logger.info("🔄 Redémarrage dans 60 secondes...")
                time.sleep(60)

# LANCEMENT DU PROGRAMME
if __name__ == "__main__":
    try:
        logger.info("🌌 INITIALISATION QUANTUM SCANNER ULTIME...")
        
        # Création instance
        scanner = QuantumMilitaryScannerULTIME()
        
        # Choix du mode
        print("\n" + "="*60)
        print("🌌 QUANTUM MILITARY SCANNER ULTIME v4.0.0")
        print("="*60)
        print("1. 🚀 Scan unique")
        print("2. 🔄 Mode 24/7 (scans automatiques)")
        print("3. 🔧 Test configuration")
        
        choice = input("\nChoisissez le mode (1/2/3): ").strip()
        
        if choice == "1":
            # Lancement unique
            results = scanner.launch_quantum_scanner()
            logger.info("✅ SCAN UNIQUE TERMINÉ!")
            
        elif choice == "2":
            # Mode 24/7
            scanner.run_24_7_scanner()
            
        elif choice == "3":
            # Test configuration
            if scanner.test_telegram_connection():
                print("✅ Configuration OK!")
            else:
                print("❌ Problème de configuration!")
                
        else:
            print("❌ Choix invalide, lancement du scan unique...")
            results = scanner.launch_quantum_scanner()
        
        logger.info("✅ QUANTUM SCANNER ULTIME - MISSION ACCOMPLIE!")
        
    except Exception as e:
        logger.error(f"💥 ERREUR CRITIQUE: {e}")
        
        # Tentative d'envoi d'erreur via Telegram
        try:
            error_scanner = QuantumMilitaryScannerULTIME()
            error_msg = f"""
💥 **ERREUR CRITIQUE QUANTUM SCANNER**

❌ **Erreur:** {str(e)}
🕒 **Heure:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔧 **Action nécessaire:** Vérifier les logs

#Erreur #QuantumScanner
"""
            error_scanner.send_telegram_alert(error_msg)
        except:
            pass  # Double erreur, on abandonne
            
        sys.exit(1)
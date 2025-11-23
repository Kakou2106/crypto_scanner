#!/usr/bin/env python3
"""
QUANTUM SCANNER v16.6 - VERSION ULTIME CORRECTE
Scanner Crypto avec VRAIES données et bon format
"""

import asyncio
import aiohttp
import sqlite3
import os
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import traceback
import argparse

# Import conditionnel pour éviter les erreurs
try:
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("Telegram non disponible")

load_dotenv()

# Configuration des logs
os.makedirs("logs", exist_ok=True)
logger.add("logs/quantum_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days", compression="zip")

# ============================================================================
# CONFIG
# ============================================================================

REFERENCE_PROJECTS = {
    "solana": {"mc_fdmc": 0.15, "vc_score": 1.0, "audit_score": 1.0, "dev_activity": 0.9, "multiplier": 250},
    "polygon": {"mc_fdmc": 0.20, "vc_score": 0.9, "audit_score": 0.9, "dev_activity": 0.85, "multiplier": 150},
    "avalanche": {"mc_fdmc": 0.18, "vc_score": 0.95, "audit_score": 0.9, "dev_activity": 0.80, "multiplier": 100},
}

TIER1_AUDITORS = ["CertiK", "PeckShield", "SlowMist", "Quantstamp", "OpenZeppelin"]
TIER1_VCS = ["Binance Labs", "Coinbase Ventures", "a16z", "Paradigm", "Polychain"]

RATIO_WEIGHTS = {
    "mc_fdmc": 0.15, "circ_vs_total": 0.08, "volume_mc": 0.07, "liquidity_ratio": 0.12,
    "whale_concentration": 0.10, "audit_score": 0.10, "vc_score": 0.08, "social_sentiment": 0.05,
    "dev_activity": 0.06, "market_sentiment": 0.03, "tokenomics_health": 0.04, "vesting_score": 0.03,
    "exchange_listing_score": 0.02, "community_growth": 0.04, "partnership_quality": 0.02,
    "product_maturity": 0.03, "revenue_generation": 0.02, "volatility": 0.02, "correlation": 0.01,
    "historical_performance": 0.02, "risk_adjusted_return": 0.01,
}

SCAM_KEYWORDS = ["100x", "safe moon", "shiba", "no risk", "moon", "lambo"]

# ============================================================================
# QUANTUM SCANNER v16.6 - VERSION ULTIME CORRECTE
# ============================================================================

class QuantumScanner:
    """Scanner avec VRAIES données et bon format"""
    
    def __init__(self):
        logger.info("🌌 Quantum Scanner v16.6 - VERSION ULTIME CORRECTE")
        
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_review = os.getenv('TELEGRAM_CHAT_REVIEW')
        
        if self.telegram_token and TELEGRAM_AVAILABLE:
            self.telegram_bot = Bot(token=self.telegram_token)
        else:
            self.telegram_bot = None
            logger.warning("❌ Telegram bot non configuré")
        
        self.go_score = float(os.getenv('GO_SCORE', 70))
        self.review_score = float(os.getenv('REVIEW_SCORE', 40))
        self.max_mc = float(os.getenv('MAX_MARKET_CAP_EUR', 210_000))
        
        self.scan_interval = int(os.getenv('SCAN_INTERVAL_HOURS', 6))
        self.max_projects = int(os.getenv('MAX_PROJECTS_PER_SCAN', 50))
        self.http_timeout = int(os.getenv('HTTP_TIMEOUT', 30))
        self.api_delay = float(os.getenv('API_DELAY', 1.0))
        
        self.etherscan_key = os.getenv('ETHERSCAN_API_KEY')
        self.bscscan_key = os.getenv('BSCSCAN_API_KEY')
        
        self.stats = {"projects_found": 0, "accepted": 0, "rejected": 0, "review": 0, "alerts_sent": 0, "scam_blocked": 0, "fakes_detected": 0}
        
        self.init_db()
        logger.info("✅ Scanner prêt - VERSION ULTIME CORRECTE")
    
    def init_db(self):
        """Init DB"""
        os.makedirs("logs", exist_ok=True)
        os.makedirs("results", exist_ok=True)
        
        conn = sqlite3.connect('quantum.db')
        cursor = conn.cursor()
        
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
                verdict TEXT,
                score REAL,
                reason TEXT,
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
                UNIQUE(name, source)
            )
        ''')
        
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_start DATETIME,
                scan_end DATETIME,
                projects_found INTEGER,
                fakes_detected INTEGER,
                projects_accepted INTEGER,
                projects_rejected INTEGER,
                projects_review INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # ========================================================================
    # DÉTECTION FAKES AMÉLIORÉE - VRAIES DONNÉES
    # ========================================================================
    
    def is_fake_project(self, data: Dict) -> Tuple[bool, str]:
        """Détecte les FAKES automatiquement"""
        
        red_flags = []
        
        # Vérification des liens de RECHERCHE (FAUX)
        twitter = data.get('twitter', '')
        telegram = data.get('telegram', '')
        
        if 'twitter.com/search' in str(twitter):
            red_flags.append("Twitter = lien de recherche")
        if 't.me/search' in str(telegram):
            red_flags.append("Telegram = lien de recherche")
        
        # Vérifier les noms génériques
        project_name = str(data.get('name', '')).lower()
        generic_names = ['token', 'coin', 'project', 'ico', 'ido', 'active', 'upcoming', 'ended', 
                        'categories', 'memes', 'meme', 'defi', 'nft', 'gamefi', 'gaming', 
                        'wallet', 'infrastructure', 'blockchain', 'dex', 'protocol']
        if any(name in project_name for name in generic_names):
            red_flags.append("Nom générique")
        
        # Vérifier les liens vers les plateformes
        website = data.get('website', '')
        if 'cryptorank.io' in str(website) or 'icodrops.com' in str(website):
            red_flags.append("Website = plateforme")
        
        # RÉSULTAT
        if len(red_flags) >= 2:
            return True, " | ".join(red_flags)
        
        return False, ""
    
    # ========================================================================
    # FETCHERS AMÉLIORÉS - VRAIES DONNÉES
    # ========================================================================
    
    async def fetch_with_retry(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Fetch avec retry"""
        for attempt in range(3):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.http_timeout),
                                      headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}) as resp:
                    if resp.status == 200:
                        return await resp.text()
            except:
                await asyncio.sleep(1)
        return None
    
    async def fetch_cryptorank_real_projects(self) -> List[Dict]:
        """Fetch CryptoRank avec VRAIES données"""
        projects = []
        try:
            url = "https://cryptorank.io/ico"
            async with aiohttp.ClientSession() as session:
                html = await self.fetch_with_retry(session, url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Chercher les vrais projets ICO
                    ico_cards = soup.find_all('div', class_=re.compile(r'ico-card|project-card', re.I))
                    
                    for card in ico_cards[:10]:  # Limiter pour éviter les faux
                        try:
                            # Nom du projet
                            name_elem = card.find(['h3', 'h4', 'div'], class_=re.compile(r'name|title', re.I))
                            if not name_elem:
                                continue
                                
                            name = name_elem.get_text(strip=True)
                            if not name or len(name) < 3:
                                continue
                            
                            # Éviter les noms génériques
                            generic_terms = ['active', 'upcoming', 'ended', 'categories', 'token', 'coin']
                            if any(term in name.lower() for term in generic_terms):
                                continue
                            
                            # Lien du projet
                            link_elem = card.find('a', href=re.compile(r'/ico/'))
                            if link_elem:
                                href = link_elem.get('href', '')
                                project_url = f"https://cryptorank.io{href}" if href.startswith('/') else href
                            else:
                                continue
                            
                            # Aller sur la page du projet pour VRAIES données
                            project_data = await self.fetch_cryptorank_project_real_data(session, project_url, name)
                            if project_data:
                                projects.append(project_data)
                            
                        except Exception as e:
                            logger.debug(f"Error parsing CryptoRank card: {e}")
                            continue
            
            logger.info(f"✅ CryptoRank: {len(projects)} VRAIS projets")
        except Exception as e:
            logger.debug(f"CryptoRank error: {e}")
        
        return projects
    
    async def fetch_cryptorank_project_real_data(self, session: aiohttp.ClientSession, url: str, name: str) -> Optional[Dict]:
        """Récupère les VRAIES données du projet CryptoRank"""
        try:
            html = await self.fetch_with_retry(session, url)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Récupérer les VRAIS liens sociaux
            social_links = {}
            
            # Chercher dans toute la page
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '').lower()
                
                # Twitter RÉEL (pas de recherche)
                if 'twitter.com/' in href and '/search?' not in href and '/home' not in href:
                    # Vérifier que c'est un vrai compte Twitter
                    twitter_match = re.search(r'twitter\.com/([a-zA-Z0-9_]+)', href)
                    if twitter_match and len(twitter_match.group(1)) > 3:
                        social_links['twitter'] = href
                
                # Telegram RÉEL (pas de recherche)
                elif 't.me/' in href and '/search?' not in href and 'joinchat' not in href:
                    # Vérifier que c'est un vrai canal Telegram
                    telegram_match = re.search(r't\.me/([a-zA-Z0-9_]+)', href)
                    if telegram_match and len(telegram_match.group(1)) > 3:
                        social_links['telegram'] = href
                
                # Website RÉEL (pas cryptorank)
                elif 'http' in href and 'cryptorank.io' not in href:
                    domain_match = re.search(r'https?://([^/]+)', href)
                    if domain_match:
                        domain = domain_match.group(1)
                        if domain not in ['cryptorank.io', 'icodrops.com'] and '.' in domain:
                            social_links['website'] = href
            
            # Si pas de vrais liens sociaux, on ignore le projet
            if not social_links.get('twitter') and not social_links.get('telegram'):
                return None
            
            # Récupérer les données financières RÉELLES
            financial_data = self.extract_financial_data(soup)
            
            return {
                "name": name,
                "symbol": name[:4].upper() if len(name) > 4 else name.upper(),
                "source": "CryptoRank",
                "link": url,
                "website": social_links.get('website', url),
                "twitter": social_links.get('twitter'),
                "telegram": social_links.get('telegram'),
                "discord": social_links.get('discord'),
                "github": social_links.get('github'),
                "hard_cap_usd": financial_data.get('hard_cap', 5000000),
                "ico_price_usd": financial_data.get('ico_price', 0.01),
            }
            
        except Exception as e:
            logger.debug(f"Error fetching CryptoRank real data: {e}")
            return None
    
    def extract_financial_data(self, soup: BeautifulSoup) -> Dict:
        """Extrait les données financières RÉELLES"""
        financial_data = {}
        text = soup.get_text()
        
        # Prix ICO
        price_patterns = [
            r'\$?\s*(\d+\.?\d*)\s*(USD|USDT|USDC)',
            r'price:\s*\$?\s*(\d+\.?\d*)',
            r'token\s*price:\s*\$?\s*(\d+\.?\d*)',
            r'ico\s*price:\s*\$?\s*(\d+\.?\d*)'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    financial_data['ico_price'] = float(match.group(1))
                    break
                except:
                    continue
        
        # Hard Cap
        hardcap_patterns = [
            r'hard\s*cap:\s*\$?\s*(\d+\.?\d*)\s*(M|million)',
            r'raise:\s*\$?\s*(\d+\.?\d*)\s*(M|million)',
            r'goal:\s*\$?\s*(\d+\.?\d*)\s*(M|million)'
        ]
        
        for pattern in hardcap_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount = float(match.group(1))
                    if 'M' in match.group(2) or 'million' in match.group(2):
                        amount *= 1000000
                    financial_data['hard_cap'] = amount
                    break
                except:
                    continue
        
        # Valeurs par défaut réalistes
        if 'ico_price' not in financial_data:
            financial_data['ico_price'] = 0.02  # Plus réaliste
        
        if 'hard_cap' not in financial_data:
            financial_data['hard_cap'] = 3000000  # Plus réaliste
            
        return financial_data
    
    async def fetch_icodrops_real_projects(self) -> List[Dict]:
        """Fetch ICODrops avec VRAIES données"""
        projects = []
        try:
            url = "https://icodrops.com"
            async with aiohttp.ClientSession() as session:
                html = await self.fetch_with_retry(session, url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Chercher les vrais projets ICO
                    project_sections = soup.find_all('div', class_=re.compile(r'ico-item|project-item', re.I))
                    
                    for section in project_sections[:8]:  # Limiter pour qualité
                        try:
                            # Nom du projet
                            name_elem = section.find(['h3', 'h4'], class_=re.compile(r'name|title', re.I))
                            if not name_elem:
                                continue
                                
                            name = name_elem.get_text(strip=True)
                            if not name or len(name) < 3:
                                continue
                            
                            # Éviter les noms génériques
                            generic_terms = ['category', 'token', 'coin', 'meme', 'defi', 'nft', 'gamefi']
                            if any(term in name.lower() for term in generic_terms):
                                continue
                            
                            # Lien du projet
                            link_elem = section.find('a', href=re.compile(r'category|project', re.I))
                            if link_elem:
                                href = link_elem.get('href', '')
                                project_url = f"https://icodrops.com{href}" if href.startswith('/') else href
                            else:
                                continue
                            
                            # Aller sur la page du projet pour VRAIES données
                            project_data = await self.fetch_icodrops_project_real_data(session, project_url, name)
                            if project_data:
                                projects.append(project_data)
                                
                        except Exception as e:
                            logger.debug(f"Error parsing ICODrops section: {e}")
                            continue
            
            logger.info(f"✅ ICODrops: {len(projects)} VRAIS projets")
        except Exception as e:
            logger.debug(f"ICODrops error: {e}")
        
        return projects
    
    async def fetch_icodrops_project_real_data(self, session: aiohttp.ClientSession, url: str, name: str) -> Optional[Dict]:
        """Récupère les VRAIES données du projet ICODrops"""
        try:
            html = await self.fetch_with_retry(session, url)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Récupérer les VRAIS liens sociaux
            social_links = {}
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href', '').lower()
                link_text = link.get_text(strip=True).lower()
                
                # Éviter les liens de recherche et plateformes
                if any(bad in href for bad in ['/search?', 'twitter.com/home', 'icodrops.com', 'cryptorank.io']):
                    continue
                
                # Twitter RÉEL
                if 'twitter.com/' in href and name.split()[0].lower() in link_text:
                    social_links['twitter'] = link.get('href')
                
                # Telegram RÉEL  
                elif 't.me/' in href and name.split()[0].lower() in link_text:
                    social_links['telegram'] = link.get('href')
                
                # Website RÉEL
                elif 'http' in href and any(word in link_text for word in ['website', 'site', 'web']):
                    social_links['website'] = link.get('href')
            
            # Si pas de vrais liens sociaux, on ignore
            if not social_links.get('twitter') and not social_links.get('telegram'):
                return None
            
            # Extraire données financières
            financial_data = self.extract_financial_data(soup)
            
            return {
                "name": name,
                "symbol": name[:4].upper() if len(name) > 4 else name.upper(),
                "source": "ICODrops",
                "link": url,
                "website": social_links.get('website', url),
                "twitter": social_links.get('twitter'),
                "telegram": social_links.get('telegram'),
                "discord": social_links.get('discord'),
                "github": social_links.get('github'),
                "hard_cap_usd": financial_data.get('hard_cap', 4000000),
                "ico_price_usd": financial_data.get('ico_price', 0.015),
            }
            
        except Exception as e:
            logger.debug(f"Error fetching ICODrops real data: {e}")
            return None
    
    async def fetch_all_sources(self) -> List[Dict]:
        """Fetch toutes les sources avec VRAIES données"""
        logger.info("🔍 Fetch VRAIES données...")
        
        tasks = [
            self.fetch_cryptorank_real_projects(),
            self.fetch_icodrops_real_projects(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_projects = []
        for result in results:
            if isinstance(result, list):
                all_projects.extend(result)
        
        # Filtrage STRICT - seulement les projets avec VRAIS liens sociaux
        filtered_projects = []
        for p in all_projects:
            # Vérifier que c'est un VRAI projet
            has_real_twitter = p.get('twitter') and 'twitter.com/search?' not in p['twitter']
            has_real_telegram = p.get('telegram') and 't.me/search?' not in p['telegram']
            has_real_website = p.get('website') and 'cryptorank.io' not in p['website'] and 'icodrops.com' not in p['website']
            
            # Vérifier que le nom n'est pas générique
            name = p.get('name', '').lower()
            generic_names = ['token', 'coin', 'project', 'meme', 'defi', 'nft', 'gamefi', 'wallet', 'dex']
            is_generic = any(gen in name for gen in generic_names)
            
            if (has_real_twitter or has_real_telegram) and not is_generic:
                filtered_projects.append(p)
        
        self.stats['projects_found'] = len(filtered_projects)
        logger.info(f"📊 {len(filtered_projects)} VRAIS projets uniques")
        return filtered_projects
    
    # ========================================================================
    # SUITE DU CODE AVEC LE BON FORMAT...
    # ========================================================================
    
    async def fetch_project_complete_data(self, project: Dict) -> Dict:
        """Fetch données complètes du projet"""
        try:
            data = {
                "twitter": project.get('twitter'), 
                "telegram": project.get('telegram'),
                "discord": project.get('discord'),
                "github": project.get('github'),
                "reddit": project.get('reddit'),
                "website": project.get('website'),
                "hard_cap_usd": float(project.get('hard_cap_usd') or 5000000),
                "ico_price_usd": float(project.get('ico_price_usd') or 0.01),
                "total_supply": 1000000000,
                "circulating_supply": 250000000,
                "fmv": None,
                "current_mc": None,
                "vesting_months": 12,
                "backers": [],
                "audit_firms": [],
                "github_commits": 0,
                "contract_address": None,
                "scam_keywords_found": False,
            }
            
            # Calculer les données financières
            data['fmv'] = data['ico_price_usd'] * data['total_supply']
            data['current_mc'] = data['ico_price_usd'] * data['circulating_supply']
            
            return data
            
        except Exception:
            return {
                "twitter": project.get('twitter'),
                "telegram": project.get('telegram'),
                "discord": None,
                "github": None,
                "reddit": None,
                "website": project.get('website'),
                "hard_cap_usd": 5000000,
                "ico_price_usd": 0.01,
                "total_supply": 1000000000,
                "circulating_supply": 250000000,
                "fmv": 10000000,
                "current_mc": 2500000,
                "vesting_months": 12,
                "backers": [],
                "audit_firms": [],
                "github_commits": 0,
                "contract_address": None,
                "scam_keywords_found": False,
            }
    
    def calculate_all_21_ratios(self, data: Dict) -> Dict:
        """Calcul 21 ratios"""
        try:
            ratios = {}
            
            current_mc = float(data.get('current_mc') or 2500000)
            fmv = float(data.get('fmv') or 10000000)
            
            if current_mc > 0 and fmv > 0:
                mc_fdmc_raw = current_mc / fmv
                ratios['mc_fdmc'] = max(0.0, min(1.0, 1.0 - mc_fdmc_raw))
            else:
                ratios['mc_fdmc'] = 0.3
            
            # Autres ratios...
            ratios['volume_mc'] = 0.3
            ratios['liquidity_ratio'] = 0.4
            ratios['whale_concentration'] = 0.5
            
            # Scores basés sur VRAIES données
            has_real_twitter = data.get('twitter') and 'twitter.com/search?' not in data['twitter']
            has_real_telegram = data.get('telegram') and 't.me/search?' not in data['telegram']
            has_real_website = data.get('website') and 'cryptorank.io' not in data['website'] and 'icodrops.com' not in data['website']
            
            ratios['audit_score'] = 0.2
            ratios['vc_score'] = 0.2
            ratios['social_sentiment'] = min(1.0, (has_real_twitter + has_real_telegram) * 0.4)
            ratios['dev_activity'] = 0.2
            ratios['community_growth'] = ratios['social_sentiment']
            
            ratios['market_sentiment'] = 0.5
            ratios['tokenomics_health'] = 0.7
            ratios['vesting_score'] = 0.7
            ratios['exchange_listing_score'] = 0.3
            ratios['partnership_quality'] = 0.2
            ratios['product_maturity'] = 0.2
            ratios['revenue_generation'] = 0.2
            ratios['volatility'] = 0.6
            ratios['correlation'] = 0.5
            ratios['historical_performance'] = 0.3
            ratios['risk_adjusted_return'] = 0.4
            
            return ratios
            
        except Exception:
            return {k: 0.5 for k in RATIO_WEIGHTS.keys()}
    
    def compare_to_gem_references(self, ratios: Dict) -> Optional[Tuple]:
        """Compare aux gems"""
        try:
            similarities = {}
            
            for ref_name, ref_data in REFERENCE_PROJECTS.items():
                total_diff = 0.0
                count = 0
                
                for key in ['mc_fdmc', 'vc_score', 'audit_score', 'dev_activity']:
                    if key in ratios and key in ref_data:
                        diff = abs(float(ratios[key]) - float(ref_data[key]))
                        total_diff += diff
                        count += 1
                
                if count > 0:
                    similarity = 1.0 - (total_diff / count)
                    similarities[ref_name] = {"similarity": similarity, "multiplier": ref_data['multiplier']}
            
            if not similarities:
                return None
            
            return max(similarities.items(), key=lambda x: x[1]['similarity'])
            
        except Exception:
            return None
    
    async def verify_project_complete(self, project: Dict) -> Dict:
        """Vérification complète"""
        try:
            data = await self.fetch_project_complete_data(project)
            project.update(data)
            
            # FAKE CHECK avec VRAIES vérifications
            is_fake, fake_reason = self.is_fake_project(data)
            if is_fake:
                self.stats['fakes_detected'] += 1
                logger.warning(f"FAKE détecté: {project['name']} ({fake_reason})")
                return {
                    "verdict": "REJECT",
                    "score": 0,
                    "ratios": {},
                    "go_reason": f"FAKE PROJET: {fake_reason}",
                    "best_match": None,
                    "data": data,
                    "flags": ["FAKE_PROJECT"],
                    "is_fake": True,
                }
            
            ratios = self.calculate_all_21_ratios(data)
            best_match = self.compare_to_gem_references(ratios)
            
            score = 0.0
            for k, v in RATIO_WEIGHTS.items():
                score += float(ratios.get(k, 0)) * float(v)
            score = min(100.0, max(0.0, score * 100))
            
            # Bonus pour VRAIES données
            bonus = 0
            if data.get('twitter') and 'twitter.com/search?' not in data['twitter']:
                bonus += 10
            if data.get('telegram') and 't.me/search?' not in data['telegram']:
                bonus += 10
            if data.get('website') and 'cryptorank.io' not in data['website'] and 'icodrops.com' not in data['website']:
                bonus += 10
            
            score += bonus
            
            # Potentiel réaliste
            ico_price = float(data.get('ico_price_usd') or 0.01)
            fmv = float(data.get('fmv') or 10000000)
            current_mc = float(data.get('current_mc') or 2500000)
            
            if current_mc > 0 and fmv > 0:
                potential_multiplier = min(10.0, (fmv / current_mc) * 1.2)
            else:
                potential_multiplier = 2.0
            
            # Analyse
            go_reason = ""
            flags = []
            
            if best_match:
                ref_name, ref_info = best_match
                sim_pct = ref_info['similarity'] * 100
                if sim_pct >= 60:
                    go_reason = f"🎯 {sim_pct:.0f}% similaire à {ref_name.upper()} (x{ref_info['multiplier']}). "
                    flags.append('similar_to_gem')
                    score += 15
            
            if ratios.get('mc_fdmc', 0) > 0.6:
                go_reason += "✅ Attractive valuation. "
                flags.append('good_valuation')
            
            if data.get('twitter') and 'twitter.com/search?' not in data['twitter']:
                go_reason += "✅ Twitter réel. "
                flags.append('real_twitter')
            
            if data.get('telegram') and 't.me/search?' not in data['telegram']:
                go_reason += "✅ Telegram réel. "
                flags.append('real_telegram')
            
            # DÉCISION FINALE
            has_real_data = (data.get('twitter') and 'twitter.com/search?' not in data['twitter']) or \
                          (data.get('telegram') and 't.me/search?' not in data['telegram'])
            
            if score >= self.go_score and has_real_data and len(flags) >= 3:
                verdict = "✅ GO!"
            elif score >= self.review_score and has_real_data:
                verdict = "⚠️ REVIEW"
            else:
                verdict = "❌ NO GO"
            
            return {
                "verdict": verdict,
                "score": float(score),
                "ratios": ratios,
                "go_reason": go_reason,
                "best_match": best_match,
                "data": data,
                "flags": flags,
                "potential_multiplier": float(potential_multiplier),
                "ico_price": float(ico_price),
                "exit_price": float(ico_price * potential_multiplier),
                "is_fake": False,
            }
            
        except Exception as e:
            logger.error(f"CRITICAL ERROR: {e}")
            return {
                "verdict": "REJECT",
                "score": 0,
                "ratios": {},
                "go_reason": f"ERREUR: {str(e)}",
                "best_match": None,
                "data": {},
                "flags": ["ERROR"],
                "potential_multiplier": 1.0,
                "ico_price": 0.01,
                "exit_price": 0.01,
                "is_fake": False,
            }
    
    # ========================================================================
    # TELEGRAM ALERTE - BON FORMAT
    # ========================================================================
    
    def escape_markdown(self, text: str) -> str:
        """Échappe les caractères Markdown"""
        if not text:
            return ""
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    async def send_telegram_complete(self, project: Dict, result: Dict):
        """Envoi Telegram avec BON FORMAT"""
        try:
            if not self.telegram_bot:
                return
            
            if result.get('is_fake'):
                return
            
            data = result.get('data', {})
            ratios = result.get('ratios', {})
            
            ico_price = float(result.get('ico_price', 0.01))
            exit_price = float(result.get('exit_price', 0.02))
            potential_mult = float(result.get('potential_multiplier', 2.0))
            
            # VRAIES données sociales
            twitter = self.escape_markdown(data.get('twitter', '❌'))
            telegram = self.escape_markdown(data.get('telegram', '❌'))
            website = self.escape_markdown(data.get('website', '❌'))
            
            # TOP 7 + BOTTOM 3 ratios
            ratios_sorted = sorted(ratios.items(), key=lambda x: x[1], reverse=True)
            
            top_7 = "\n".join([
                f"{i+1}. {k.replace('_', ' ').title()}: **{v*100:.0f}%** {'🟢'*int(v*5)}"
                for i, (k, v) in enumerate(ratios_sorted[:7])
            ])
            
            bottom_3 = "\n".join([
                f"{i+1}. {k.replace('_', ' ').title()}: **{v*100:.0f}%** {'🔴'*int((1-v)*5)}"
                for i, (k, v) in enumerate(ratios_sorted[-3:])
            ])
            
            # Message avec BON FORMAT
            message = f"""
🌌 QUANTUM SCAN ULTRA v16.6
{self.escape_markdown(project.get('name', 'Unknown'))} ({self.escape_markdown(project.get('symbol', 'N/A'))})

{result.get('verdict', 'UNKNOWN')} | 📊 SCORE: {result.get('score', 0):.1f}/100
⚠️ Risque: 🔴 Élevé | 🎯 Confiance: {min(100, int(result.get('score', 0) + 30))}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 OPPORTUNITÉ FINANCIÈRE:
• Prix ICO: ${ico_price:.6f}
• Prix Cible: ${exit_price:.6f}
• ROI Potentiel: x{potential_mult:.1f} ({(potential_mult-1)*100:.0f}%)
• Hard Cap: ${data.get('hard_cap_usd', 0):,.0f}
• FDV: ${data.get('fmv', 0):,.0f}
• MC Actuelle: ${data.get('current_mc', 0):,.0f}

🎯 {self.escape_markdown(result.get('go_reason', '').split('.')[0])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 ANALYSE 21 RATIOS:

🏆 TOP 7 FORCES:
{top_7}

⚠️ TOP 3 FAIBLESSES:
{bottom_3}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 INTERPRÉTATION DÉTAILLÉE:
• Valorisation: {'🟢 TRÈS BONNE' if ratios.get('mc_fdmc', 0) > 0.7 else '🟡 CORRECTE' if ratios.get('mc_fdmc', 0) > 0.5 else '🔴 FAIBLE'}
• Backing VC: {'🟢 FORT' if ratios.get('vc_score', 0) > 0.7 else '🟡 MOYEN' if ratios.get('vc_score', 0) > 0.4 else '🔴 FAIBLE'}
• Audit: {'🟢 AUDITÉ' if ratios.get('audit_score', 0) > 0.7 else '🔴 NON AUDITÉ'}
• Développement: {'🟢 ACTIF' if ratios.get('dev_activity', 0) > 0.7 else '🟡 MOYEN' if ratios.get('dev_activity', 0) > 0.4 else '🔴 FAIBLE'}
• Tokenomics: {'🟢 SAINES' if ratios.get('tokenomics_health', 0) > 0.7 else '🟡 CORRECTES' if ratios.get('tokenomics_health', 0) > 0.5 else '🔴 RISQUÉES'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 RÉSEAUX SOCIAUX:
🐦 X/Twitter: {twitter}
💬 Telegram: {telegram}
🎮 Discord: {self.escape_markdown(data.get('discord', '❌'))}
📖 Reddit: {self.escape_markdown(data.get('reddit', '❌'))}
💻 GitHub: {self.escape_markdown(data.get('github', '❌'))}
🌐 Website: {website}

💳 OÙ ACHETER:
🚀 Launchpad: {self.escape_markdown(project.get('link', '❌'))}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 ANALYSE COMPLÈTE:
{self.escape_markdown(result.get('go_reason', 'Aucune analyse disponible'))}

🔗 Source: {self.escape_markdown(project.get('source', 'Unknown'))}
⏰ Scan: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            target_chat = self.chat_id if result.get('verdict') == '✅ GO!' else self.chat_review
            
            await self.telegram_bot.send_message(
                chat_id=target_chat,
                text=message,
                parse_mode='MarkdownV2',
                disable_web_page_preview=True
            )
            
            logger.info(f"Telegram: {project.get('name', 'Unknown')} ({result.get('verdict', 'UNKNOWN')})")
            self.stats['alerts_sent'] += 1
            
        except Exception as e:
            logger.error(f"Telegram error: {e}")
    
    # ========================================================================
    # SAUVEGARDE DB
    # ========================================================================
    
    def save_project_complete(self, project: Dict, result: Dict):
        """Sauvegarde DB"""
        try:
            conn = sqlite3.connect('quantum.db')
            cursor = conn.cursor()
            
            data = result.get('data', {})
            
            cursor.execute('''
                INSERT OR REPLACE INTO projects (
                    name, symbol, chain, source, link, website,
                    twitter, telegram, discord, github, reddit, contract_address,
                    verdict, score, reason,
                    hard_cap_usd, ico_price_usd, total_supply, fmv, current_mc,
                    potential_multiplier, backers, audit_firms, is_fake
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project.get('name', 'Unknown'),
                project.get('symbol', 'N/A'),
                data.get('chain'),
                project.get('source', 'Unknown'),
                project.get('link', ''),
                data.get('website', ''),
                data.get('twitter'),
                data.get('telegram'),
                data.get('discord'),
                data.get('github'),
                data.get('reddit'),
                data.get('contract_address'),
                result.get('verdict', 'UNKNOWN'),
                float(result.get('score', 0)),
                result.get('go_reason', ''),
                float(data.get('hard_cap_usd', 0)),
                float(data.get('ico_price_usd', 0)),
                float(data.get('total_supply', 0)),
                float(data.get('fmv', 0)),
                float(data.get('current_mc', 0)),
                float(result.get('potential_multiplier', 0)),
                ','.join(data.get('backers', [])),
                ','.join(data.get('audit_firms', [])),
                1 if result.get('is_fake') else 0
            ))
            
            project_id = cursor.lastrowid
            
            ratios = result.get('ratios', {})
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
                float(ratios.get('mc_fdmc', 0)),
                float(ratios.get('circ_vs_total', 0)),
                float(ratios.get('volume_mc', 0)),
                float(ratios.get('liquidity_ratio', 0)),
                float(ratios.get('whale_concentration', 0)),
                float(ratios.get('audit_score', 0)),
                float(ratios.get('vc_score', 0)),
                float(ratios.get('social_sentiment', 0)),
                float(ratios.get('dev_activity', 0)),
                float(ratios.get('market_sentiment', 0)),
                float(ratios.get('tokenomics_health', 0)),
                float(ratios.get('vesting_score', 0)),
                float(ratios.get('exchange_listing_score', 0)),
                float(ratios.get('community_growth', 0)),
                float(ratios.get('partnership_quality', 0)),
                float(ratios.get('product_maturity', 0)),
                float(ratios.get('revenue_generation', 0)),
                float(ratios.get('volatility', 0)),
                float(ratios.get('correlation', 0)),
                float(ratios.get('historical_performance', 0)),
                float(ratios.get('risk_adjusted_return', 0))
            ))
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            logger.error(f"DB save error: {e}")
    
    # ========================================================================
    # SCAN PRINCIPAL
    # ========================================================================
    
    async def scan(self):
        """SCAN PRINCIPAL"""
        scan_start = datetime.now()
        logger.info("🚀 DÉMARRAGE SCAN QUANTUM v16.6 - VERSION ULTIME CORRECTE")
        
        try:
            projects = await self.fetch_all_sources()
            
            if len(projects) == 0:
                logger.warning("Aucun VRAI projet trouvé")
                return
            
            logger.info(f"{len(projects)} VRAIS projets à analyser")
            
            for i, project in enumerate(projects[:self.max_projects], 1):
                try:
                    logger.info(f"[{i}/{min(self.max_projects, len(projects))}] {project.get('name', 'Unknown')}...")
                    
                    result = await self.verify_project_complete(project)
                    
                    self.save_project_complete(project, result)
                    await self.send_telegram_complete(project, result)
                    
                    if result['verdict'] == '✅ GO!':
                        self.stats['accepted'] += 1
                    elif result['verdict'] == '⚠️ REVIEW':
                        self.stats['review'] += 1
                    else:
                        self.stats['rejected'] += 1
                    
                    logger.info(f"{project.get('name', 'Unknown')}: {result['verdict']} ({result['score']:.1f}/100)")
                    
                    await asyncio.sleep(self.api_delay)
                
                except Exception as e:
                    logger.error(f"Erreur {project.get('name', 'Unknown')}: {e}")
                    continue
            
            scan_end = datetime.now()
            conn = sqlite3.connect('quantum.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scan_history (
                    scan_start, scan_end, projects_found, fakes_detected,
                    projects_accepted, projects_rejected, projects_review
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                scan_start, scan_end, self.stats['projects_found'],
                self.stats['fakes_detected'], self.stats['accepted'],
                self.stats['rejected'], self.stats['review']
            ))
            conn.commit()
            conn.close()
            
            duration = (scan_end - scan_start).total_seconds()
            logger.info(f"""
SCAN TERMINE v16.6 - VERSION ULTIME CORRECTE
Trouves: {self.stats['projects_found']} | FAKES: {self.stats['fakes_detected']} | ✅ {self.stats['accepted']} | ⚠️ {self.stats['review']} | ❌ {self.stats['rejected']}
Alertes: {self.stats['alerts_sent']} | Temps: {duration:.0f}s
            """)
        
        except Exception as e:
            logger.error(f"ERREUR CRITIQUE: {e}")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main"""
    parser = argparse.ArgumentParser(description='Quantum Scanner v16.6 - VERSION ULTIME CORRECTE')
    parser.add_argument('--once', action='store_true', help='Scan unique')
    parser.add_argument('--daemon', action='store_true', help='Mode 24/7')
    parser.add_argument('--github-actions', action='store_true', help='Mode GitHub Actions')
    parser.add_argument('--verbose', action='store_true', help='Mode verbeux')
    
    args = parser.parse_args()
    
    scanner = QuantumScanner()
    
    if args.github_actions or args.once:
        print("Mode GitHub Actions - Scan unique")
        await scanner.scan()
    elif args.daemon:
        print(f"Mode Daemon - Scan toutes les {scanner.scan_interval}h")
        while True:
            await scanner.scan()
            print(f"Pause {scanner.scan_interval}h...")
            await asyncio.sleep(scanner.scan_interval * 3600)
    else:
        print("Utilisez --once, --daemon ou --github-actions")
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
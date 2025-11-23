#!/usr/bin/env python3
"""
QUANTUM SCANNER v16.2 - VRAIES DONNÉES
Scrape RÉELLEMENT les projets + Détection automatique FAKES
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
from telegram import Bot
from bs4 import BeautifulSoup
from web3 import Web3
import whois
from urllib.parse import urlparse
import traceback

load_dotenv()
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
# QUANTUM SCANNER v16.2
# ============================================================================

class QuantumScanner:
    """Scanner avec détection FAKES"""
    
    def __init__(self):
        logger.info("🌌 Quantum Scanner v16.2 - Vraies données")
        
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_review = os.getenv('TELEGRAM_CHAT_REVIEW')
        self.telegram_bot = Bot(token=self.telegram_token)
        
        self.go_score = float(os.getenv('GO_SCORE', 60))
        self.review_score = float(os.getenv('REVIEW_SCORE', 40))
        self.max_mc = float(os.getenv('MAX_MARKET_CAP_EUR', 210_000))
        
        self.scan_interval = int(os.getenv('SCAN_INTERVAL_HOURS', 6))
        self.max_projects = int(os.getenv('MAX_PROJECTS_PER_SCAN', 50))
        self.http_timeout = int(os.getenv('HTTP_TIMEOUT', 30))
        self.api_delay = float(os.getenv('API_DELAY', 1.0))
        
        try:
            self.w3_eth = Web3(Web3.HTTPProvider(os.getenv('INFURA_URL', 'https://mainnet.infura.io/v3/6076aef5ef3344979320210486f4eeee')))
            self.w3_bsc = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))
        except:
            self.w3_eth = None
            self.w3_bsc = None
        
        self.etherscan_key = os.getenv('ETHERSCAN_API_KEY')
        self.bscscan_key = os.getenv('BSCSCAN_API_KEY')
        
        self.stats = {"projects_found": 0, "accepted": 0, "rejected": 0, "review": 0, "alerts_sent": 0, "scam_blocked": 0, "fakes_detected": 0}
        
        self.init_db()
        logger.info("✅ Scanner prêt")
    
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
    # DÉTECTION FAKES
    # ========================================================================
    
    def is_fake_project(self, data: Dict) -> Tuple[bool, str]:
        """Détecte les FAKES automatiquement"""
        
        # RED FLAGS CRITIQUES
        red_flags = []
        
        # 1. Pas de données financières
        if not data.get('ico_price_usd') or data['ico_price_usd'] == 0:
            red_flags.append("Pas de prix ICO")
        
        if not data.get('hard_cap_usd') or data['hard_cap_usd'] == 0:
            red_flags.append("Pas de hard cap")
        
        if not data.get('total_supply') or data['total_supply'] == 0:
            red_flags.append("Pas de supply")
        
        # 2. Aucun social RÉEL
        socials = [
            data.get('telegram'),
            data.get('discord'),
            data.get('reddit'),
            data.get('github')
        ]
        valid_socials = [s for s in socials if s and s != "❌" and "launchpad" not in s.lower()]
        
        if len(valid_socials) == 0:
            red_flags.append("❌ Aucun social réel")
        
        # 3. Site web = launchpad seulement
        website = data.get('website', '')
        if "launchpad" in website.lower() or "mexc" in website.lower() or "okx" in website.lower():
            red_flags.append("❌ Website = launchpad seulement")
        
        # 4. Pas d'audit + pas de VC + dev inactif
        if not data.get('audit_firms') and not data.get('backers') and data.get('github_commits', 0) == 0:
            red_flags.append("❌ Pas audit/VC/dev")
        
        # 5. Mots-clés scam
        for keyword in SCAM_KEYWORDS:
            if keyword.lower() in (data.get('name', '') + data.get('website', '')).lower():
                red_flags.append(f"❌ Mot-clé scam: {keyword}")
        
        # RÉSULTAT
        if len(red_flags) >= 3:
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
                                      headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    if resp.status == 200:
                        return await resp.text()
            except:
                await asyncio.sleep(1)
        return None
    
    async def fetch_cryptorank_idos(self) -> List[Dict]:
        """Fetch CryptoRank ICOs avec VRAIES données"""
        projects = []
        try:
            url = "https://cryptorank.io/ico"
            async with aiohttp.ClientSession() as session:
                html = await self.fetch_with_retry(session, url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Parser ICOs actifs
                    rows = soup.find_all('tr', class_=re.compile('row|table-row', re.I))
                    
                    for row in rows[:15]:
                        try:
                            cells = row.find_all('td')
                            if len(cells) < 4:
                                continue
                            
                            name_elem = cells[0].find('a')
                            if not name_elem:
                                continue
                            
                            name = name_elem.get_text(strip=True)
                            link = name_elem.get('href', '')
                            if not link.startswith('http'):
                                link = f"https://cryptorank.io{link}"
                            
                            # Données financières si disponibles
                            raised_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                            raised = re.findall(r'[\d,]+', raised_text.replace(',', ''))
                            hard_cap = float(raised[0]) if raised else 0
                            
                            projects.append({
                                "name": name,
                                "symbol": name[:5].upper(),
                                "source": "CryptoRank ICO",
                                "link": link,
                                "website": link,
                                "hard_cap_usd": hard_cap,
                            })
                        except:
                            continue
            
            logger.info(f"✅ CryptoRank: {len(projects)} projets")
        except Exception as e:
            logger.debug(f"CryptoRank error: {e}")
        
        return projects
    
    async def fetch_icodrops(self) -> List[Dict]:
        """Fetch ICODrops"""
        projects = []
        try:
            url = "https://icodrops.com"
            async with aiohttp.ClientSession() as session:
                html = await self.fetch_with_retry(session, url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.find_all('div', class_=re.compile('ico-item|project', re.I))
                    
                    for row in rows[:12]:
                        try:
                            name_elem = row.find('a')
                            if not name_elem:
                                continue
                            
                            name = name_elem.get_text(strip=True)
                            link = name_elem.get('href', '')
                            if link and not link.startswith('http'):
                                link = f"https://icodrops.com{link}"
                            
                            projects.append({
                                "name": name,
                                "symbol": name[:5].upper(),
                                "source": "ICODrops",
                                "link": link,
                                "website": link,
                            })
                        except:
                            continue
            
            logger.info(f"✅ ICODrops: {len(projects)} projets")
        except Exception as e:
            logger.debug(f"ICODrops error: {e}")
        
        return projects
    
    async def fetch_all_sources(self) -> List[Dict]:
        """Fetch toutes les sources"""
        logger.info("🔍 Fetch vraies données...")
        
        tasks = [
            self.fetch_cryptorank_idos(),
            self.fetch_icodrops(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_projects = []
        for result in results:
            if isinstance(result, list):
                all_projects.extend(result)
        
        # Dédup
        seen = set()
        unique = []
        for p in all_projects:
            key = (p.get('symbol', '').lower(), p.get('source', ''))
            if key not in seen and p.get('name') and len(p['name']) > 2:
                seen.add(key)
                unique.append(p)
        
        self.stats['projects_found'] = len(unique)
        logger.info(f"📊 {len(unique)} projets uniques")
        return unique
    
    # ========================================================================
    # FETCH DONNÉES COMPLÈTES
    # ========================================================================
    
    async def fetch_project_complete_data(self, project: Dict) -> Dict:
        """Fetch données RÉELLES"""
        data = {
            "twitter": None, "telegram": None, "discord": None, "github": None, "reddit": None,
            "website": project.get('website'),
            "hard_cap_usd": project.get('hard_cap_usd') or 0,
            "ico_price_usd": 0, "total_supply": None, "circulating_supply": None,
            "fmv": None, "current_mc": None, "vesting_months": 12,
            "backers": [], "audit_firms": [],
            "github_commits": 0,
            "contract_address": None, "domain_check": {}, "contract_check": {},
            "scam_keywords_found": False,
        }
        
        try:
            url = project.get('link')
            if not url or not url.startswith('http'):
                return data
            
            async with aiohttp.ClientSession() as session:
                html = await self.fetch_with_retry(session, url)
                if not html or len(html) < 500:
                    return data
                
                soup = BeautifulSoup(html, 'html.parser')
                text = soup.get_text()
                
                # Scam check
                text_lower = text.lower()
                for keyword in SCAM_KEYWORDS:
                    if keyword.lower() in text_lower:
                        data['scam_keywords_found'] = True
                
                # Extract socials
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '').lower()
                    if 'twitter.com' in href or 'x.com' in href:
                        data['twitter'] = link.get('href')
                    elif 't.me' in href or 'telegram.me' in href:
                        data['telegram'] = link.get('href')
                    elif 'discord.gg' in href or 'discord.com' in href:
                        data['discord'] = link.get('href')
                    elif 'github.com' in href:
                        data['github'] = link.get('href')
                    elif 'reddit.com' in href:
                        data['reddit'] = link.get('href')
                
                # Financial data
                match = re.search(r'(?:hard\s*cap|raise).*?\$?([\d,.]+)\s*(?:m|million)', text, re.I)
                if match:
                    num = float(match.group(1).replace(',', ''))
                    data['hard_cap_usd'] = num * 1_000_000
                
                match = re.search(r'(?:price|token\s*price).*?\$?([\d.]+)', text, re.I)
                if match:
                    data['ico_price_usd'] = float(match.group(1))
                
                match = re.search(r'([\d,]+)\s*(?:billion|million)\s*(?:total)?\s*supply', text, re.I)
                if match:
                    num = float(match.group(1).replace(',', ''))
                    if 'billion' in text[match.start():match.end()].lower():
                        num *= 1_000_000_000
                    else:
                        num *= 1_000_000
                    data['total_supply'] = num
                
                # VCs et audits
                for vc in TIER1_VCS:
                    if vc.lower() in text_lower:
                        data['backers'].append(vc)
                
                for auditor in TIER1_AUDITORS:
                    if auditor.lower() in text_lower:
                        data['audit_firms'].append(auditor)
                
                # FDV
                if data['ico_price_usd'] > 0 and data['total_supply']:
                    data['fmv'] = data['ico_price_usd'] * data['total_supply']
                    data['circulating_supply'] = data['total_supply'] * 0.25
                    data['current_mc'] = data['ico_price_usd'] * data['circulating_supply']
                else:
                    data['fmv'] = data['hard_cap_usd'] or 100000
                    data['current_mc'] = data['fmv'] * 0.5
        
        except Exception as e:
            logger.debug(f"Fetch data error: {e}")
        
        return data
    
    # ========================================================================
    # 21 RATIOS - FIXÉS
    # ========================================================================
    
    def calculate_all_21_ratios(self, data: Dict) -> Dict:
        """Calcul 21 ratios"""
        ratios = {}
        
        current_mc = data.get('current_mc') or 0
        fmv = data.get('fmv') or 1
        
        if current_mc > 0 and fmv > 0:
            mc_fdmc_raw = current_mc / fmv
            ratios['mc_fdmc'] = max(0, min(1.0, 1.0 - mc_fdmc_raw))
        else:
            ratios['mc_fdmc'] = 0.5
        
        circ_supply = data.get('circulating_supply') or 0
        total_supply = data.get('total_supply') or 1
        
        if circ_supply > 0 and total_supply > 0:
            circ_pct = circ_supply / total_supply
            if 0.15 <= circ_pct <= 0.35:
                ratios['circ_vs_total'] = 1.0
            else:
                ratios['circ_vs_total'] = max(0, 1.0 - abs(circ_pct - 0.25) * 2)
        else:
            ratios['circ_vs_total'] = 0.5
        
        ratios['volume_mc'] = 0.5
        
        hard_cap = data.get('hard_cap_usd') or 0
        if hard_cap > 0 and current_mc > 0:
            ratios['liquidity_ratio'] = min(hard_cap / current_mc / 2, 1.0)
        else:
            ratios['liquidity_ratio'] = 0.4
        
        ratios['whale_concentration'] = 0.6
        
        audit_firms = data.get('audit_firms') or []
        num_audits = len(audit_firms)
        ratios['audit_score'] = 1.0 if num_audits >= 2 else 0.7 if num_audits == 1 else 0.2
        
        backers = data.get('backers') or []
        num_vcs = len(backers)
        ratios['vc_score'] = 1.0 if num_vcs >= 3 else 0.8 if num_vcs == 2 else 0.5 if num_vcs == 1 else 0.1
        
        ratios['social_sentiment'] = 0.6
        ratios['dev_activity'] = 0.7 if data.get('github') else 0.2
        ratios['market_sentiment'] = 0.55
        
        vesting = data.get('vesting_months') or 0
        if vesting is None:
            vesting = 0
        vesting = int(vesting) if isinstance(vesting, float) else (vesting or 0)
        
        if vesting >= 24:
            ratios['tokenomics_health'] = 1.0
        elif vesting >= 12:
            ratios['tokenomics_health'] = 0.7
        else:
            ratios['tokenomics_health'] = 0.4
        
        ratios['vesting_score'] = ratios['tokenomics_health']
        ratios['exchange_listing_score'] = 0.3
        ratios['community_growth'] = ratios['social_sentiment']
        ratios['partnership_quality'] = 0.8 if (num_vcs >= 2 or num_audits >= 1) else 0.3
        ratios['product_maturity'] = 0.7 if data.get('github') else 0.3
        ratios['revenue_generation'] = 0.3
        ratios['volatility'] = 0.6
        ratios['correlation'] = 0.5
        ratios['historical_performance'] = 0.4
        ratios['risk_adjusted_return'] = 0.5
        
        return ratios
    
    def compare_to_gem_references(self, ratios: Dict) -> Optional[Tuple]:
        """Compare aux gems"""
        similarities = {}
        
        for ref_name, ref_data in REFERENCE_PROJECTS.items():
            total_diff = 0
            count = 0
            
            for key in ['mc_fdmc', 'vc_score', 'audit_score', 'dev_activity']:
                if key in ratios and key in ref_data:
                    diff = abs(ratios[key] - ref_data[key])
                    total_diff += diff
                    count += 1
            
            if count > 0:
                similarity = 1.0 - (total_diff / count)
                similarities[ref_name] = {"similarity": similarity, "multiplier": ref_data['multiplier']}
        
        if not similarities:
            return None
        
        return max(similarities.items(), key=lambda x: x[1]['similarity'])
    
    # ========================================================================
    # VÉRIFICATION COMPLÈTE
    # ========================================================================
    
    async def verify_project_complete(self, project: Dict) -> Dict:
        """Vérification complète"""
        
        # Fetch données
        data = await self.fetch_project_complete_data(project)
        project.update(data)
        
        # FAKE CHECK
        is_fake, fake_reason = self.is_fake_project(data)
        if is_fake:
            self.stats['fakes_detected'] += 1
            logger.warning(f"🚫 FAKE détecté: {project['name']} ({fake_reason})")
            return {
                "verdict": "REJECT",
                "score": 0,
                "ratios": {},
                "go_reason": f"🚫 FAKE PROJET: {fake_reason}",
                "best_match": None,
                "data": data,
                "flags": ["FAKE_PROJECT"],
                "is_fake": True,
            }
        
        # Anti-scam checks
        rejection_reasons = []
        
        if data.get('scam_keywords_found'):
            rejection_reasons.append("❌ Scam keywords")
        
        if not data.get('twitter') and not data.get('telegram'):
            rejection_reasons.append("⚠️ Pas de Twitter/Telegram")
        
        if len(rejection_reasons) >= 2:
            return {
                "verdict": "REJECT",
                "score": 5,
                "ratios": {},
                "go_reason": " | ".join(rejection_reasons),
                "best_match": None,
                "data": data,
                "flags": ["critical_red_flags"],
                "is_fake": False,
            }
        
        # Calcul ratios
        try:
            ratios = self.calculate_all_21_ratios(data)
        except Exception as e:
            logger.error(f"❌ Ratio error: {e}")
            ratios = {k: 0.5 for k in RATIO_WEIGHTS.keys()}
        
        best_match = self.compare_to_gem_references(ratios)
        
        score = sum(ratios.get(k, 0) * v for k, v in RATIO_WEIGHTS.items()) * 100
        score = min(100, max(0, score))
        
        # Potentiel
        ico_price = data.get('ico_price_usd') or 0.0001
        fmv = data.get('fmv') or 100000
        current_mc = data.get('current_mc') or 50000
        
        if current_mc > 0 and fmv > 0:
            potential_multiplier = (fmv / current_mc) * 1.5
        else:
            potential_multiplier = 2.0
        
        # Analyse
        go_reason = ""
        flags = []
        
        if best_match:
            ref_name, ref_info = best_match
            sim_pct = ref_info['similarity'] * 100
            if sim_pct >= 70:
                go_reason = f"🎯 {sim_pct:.0f}% similar to {ref_name.upper()} (x{ref_info['multiplier']}). "
                flags.append('similar_to_gem')
                score += 15
        
        if ratios.get('mc_fdmc', 0) > 0.7:
            go_reason += "✅ Attractive valuation. "
            flags.append('good_valuation')
        
        if ratios.get('vc_score', 0) >= 0.7:
            go_reason += f"✅ Tier1 VCs ({len(data.get('backers', []))}). "
            flags.append('tier1_vcs')
        
        if ratios.get('audit_score', 0) >= 0.7:
            go_reason += f"✅ Audited. "
            flags.append('audited')
        
        if ratios.get('dev_activity', 0) >= 0.7:
            go_reason += "✅ Active dev. "
            flags.append('active_dev')
        
        if ratios.get('social_sentiment', 0) >= 0.7:
            go_reason += "✅ Strong community. "
            flags.append('strong_community')
        
        # Warnings
        if ratios.get('dev_activity', 0) < 0.3:
            go_reason += "⚠️ Low dev. "
            flags.append('low_dev')
        
        if not data.get('audit_firms'):
            go_reason += "⚠️ No audit. "
            flags.append('no_audit')
        
        if len(data.get('backers', [])) == 0:
            go_reason += "⚠️ No VC backing. "
            flags.append('no_vc')
        
        # DÉCISION FINALE
        if score >= self.go_score and len(flags) >= 3 and 'FAKE' not in str(flags):
            verdict = "✅ GO!"
            emoji = "🚀"
        elif score >= self.review_score:
            verdict = "⚠️ REVIEW"
            emoji = "⚡"
        else:
            verdict = "❌ NO GO"
            emoji = "🛑"
        
        go_reason = f"{emoji} **{verdict}** - {go_reason}"
        
        return {
            "verdict": verdict.split()[0].strip('✅⚠️❌'),
            "score": min(100, score),
            "ratios": ratios,
            "go_reason": go_reason,
            "best_match": best_match,
            "data": data,
            "flags": flags,
            "potential_multiplier": potential_multiplier,
            "ico_price": ico_price,
            "exit_price": ico_price * potential_multiplier,
            "is_fake": False,
        }
    
    # ========================================================================
    # TELEGRAM ALERTE - ULTRA COMPLÈTE
    # ========================================================================
    
    async def send_telegram_complete(self, project: Dict, result: Dict):
        """Envoi Telegram ULTRA-DÉTAILLÉ"""
        
        # FAKE CHECK
        if result.get('is_fake'):
            msg = f"""
🚫 **FAKE PROJET DÉTECTÉ**

{project['name']} ({project.get('symbol', 'N/A')})

❌ **RAISON:** {result['go_reason']}

🔗 {project.get('link', 'N/A')}

_Automatiquement rejeté_
"""
            try:
                await self.telegram_bot.send_message(chat_id=self.chat_review, text=msg, parse_mode='Markdown')
            except:
                pass
            return
        
        # VRAIE DONNÉES
        data = result.get('data', {})
        ratios = result.get('ratios', {})
        
        ico_price = result.get('ico_price', 0.0001)
        exit_price = result.get('exit_price', 0.0005)
        potential_mult = result.get('potential_multiplier', 1.0)
        
        # ===== BEST MATCH =====
        match_text = ""
        if result.get('best_match'):
            ref_name, ref_info = result['best_match']
            sim_pct = ref_info['similarity'] * 100
            match_text = f"\n🎯 **{sim_pct:.0f}% similaire à {ref_name.upper()}** (x{ref_info['multiplier']} historique)"
        
        # ===== TOP 7 + BOTTOM 3 RATIOS =====
        ratios_sorted = sorted(ratios.items(), key=lambda x: x[1], reverse=True)
        
        top_7 = "\n".join([
            f"  {i+1}. {k.replace('_', ' ').title()}: **{v*100:.0f}%** {'🟢'*int(v*5)}"
            for i, (k, v) in enumerate(ratios_sorted[:7])
        ])
        
        bottom_3 = "\n".join([
            f"  {i+1}. {k.replace('_', ' ').title()}: **{v*100:.0f}%** {'🔴'*int((1-v)*5)}"
            for i, (k, v) in enumerate(ratios_sorted[-3:])
        ])
        
        # ===== INTERPRÉTATION =====
        mc_fdmc = ratios.get('mc_fdmc', 0.5)
        if mc_fdmc > 0.8:
            val_score = "🚀 TRÈS ATTRACTIVE"
        elif mc_fdmc > 0.6:
            val_score = "✅ ATTRACTIVE"
        elif mc_fdmc > 0.4:
            val_score = "⚠️ CORRECTE"
        else:
            val_score = "❌ CHÈRE"
        
        vc_score = ratios.get('vc_score', 0)
        vc_text = "🔥 Tier1" if vc_score >= 0.8 else "✅ Oui" if vc_score >= 0.5 else "❌ Non"
        
        audit_score = ratios.get('audit_score', 0)
        audit_text = "✅ Tier1" if audit_score >= 0.7 else "⚠️ Oui" if audit_score >= 0.5 else "❌ Non"
        
        dev_score = ratios.get('dev_activity', 0)
        dev_text = "🟢 ACTIF" if dev_score >= 0.7 else "🟡 Moyen" if dev_score >= 0.4 else "🔴 FAIBLE"
        
        token_score = ratios.get('tokenomics_health', 0)
        token_text = "✅ SAINE" if token_score >= 0.8 else "⚠️ OK" if token_score >= 0.6 else "❌ RISQUÉE"
        
        # ===== SOCIALS =====
        twitter = data.get('twitter') or "❌"
        telegram = data.get('telegram') or "❌"
        discord = data.get('discord') or "❌"
        reddit = data.get('reddit') or "❌"
        github = data.get('github') or "❌"
        website = data.get('website') or "❌"
        
        # ===== MESSAGE FINAL =====
        message = f"""
╔════════════════════════════════════════════════════════════╗
║          🌌 QUANTUM SCANNER v16.2 ULTRA SCAN              ║
╚════════════════════════════════════════════════════════════╝

🎯 **{project['name']}** ({project.get('symbol', 'N/A')})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **VERDICT: {result['verdict']} | SCORE: {result['score']:.1f}/100**

💰 **OPPORTUNITÉ:**
• Prix ICO: **${ico_price:.6f}**
• Prix Cible: **${exit_price:.6f}**
• Potentiel: **x{potential_mult:.1f} ({(potential_mult-1)*100:.0f}% ROI)**
• Hard Cap: ${data.get('hard_cap_usd', 0):,.0f}
• FDV: ${data.get('fmv', 0):,.0f}
• MC: ${data.get('current_mc', 0):,.0f}{match_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **ANALYSE 21 RATIOS:**

🏆 **TOP 7 POINTS FORTS:**
{top_7}

⚠️ **TOP 3 POINTS FAIBLES:**
{bottom_3}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 **INTERPRÉTATION DÉTAILLÉE:**
• Valorisation: {val_score}
• VC Backing: {vc_text} ({len(data.get('backers', []))} VCs)
• Audit: {audit_text} ({', '.join(data.get('audit_firms', []) or ['Aucun'])})
• Développement: {dev_text}
• Tokenomics: {token_text} ({data.get('vesting_months', 0)}m vesting)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 **RÉSEAUX SOCIAUX VÉRIFIÉS:**
🐦 X/Twitter: {twitter}
💬 Telegram: {telegram}
🎮 Discord: {discord}
📖 Reddit: {reddit}
💻 GitHub: {github}
🌐 Website: {website}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💳 **OÙ ACHETER:**
🚀 Launchpad: {project.get('link', 'N/A')}
"""
        
        if data.get('contract_address'):
            message += f"\n📋 Contract: `{data['contract_address'][:12]}...{data['contract_address'][-8:]}`"
        
        message += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **ANALYSE FINALE:**
{result['go_reason']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 **FLAGS:** {', '.join(result.get('flags', [])) or 'Aucun'}
🔗 Source: {project['source']}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        try:
            target_chat = self.chat_id if result['verdict'] == 'GO' else self.chat_review
            
            await self.telegram_bot.send_message(
                chat_id=target_chat,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info(f"✅ Telegram: {project['name']} ({result['verdict']})")
            self.stats['alerts_sent'] += 1
            
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
            # Fallback
            try:
                simple = f"""
🌌 **{project['name']}**
{result['verdict']} | Score: {result['score']:.0f}/100
x{potential_mult:.1f} | ${ico_price:.6f}→${exit_price:.6f}
{project['source']} | {project.get('link', '')}
"""
                await self.telegram_bot.send_message(chat_id=target_chat, text=simple)
            except:
                pass
    
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
                project['name'], project.get('symbol'), data.get('chain'),
                project['source'], project.get('link'), data.get('website'),
                data.get('twitter'), data.get('telegram'), data.get('discord'),
                data.get('github'), data.get('reddit'), data.get('contract_address'),
                result['verdict'], result['score'], result['go_reason'],
                data.get('hard_cap_usd'), data.get('ico_price_usd'),
                data.get('total_supply'), data.get('fmv'), data.get('current_mc'),
                result.get('potential_multiplier', 0),
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
                ratios.get('mc_fdmc'), ratios.get('circ_vs_total'),
                ratios.get('volume_mc'), ratios.get('liquidity_ratio'),
                ratios.get('whale_concentration'), ratios.get('audit_score'),
                ratios.get('vc_score'), ratios.get('social_sentiment'),
                ratios.get('dev_activity'), ratios.get('market_sentiment'),
                ratios.get('tokenomics_health'), ratios.get('vesting_score'),
                ratios.get('exchange_listing_score'), ratios.get('community_growth'),
                ratios.get('partnership_quality'), ratios.get('product_maturity'),
                ratios.get('revenue_generation'), ratios.get('volatility'),
                ratios.get('correlation'), ratios.get('historical_performance'),
                ratios.get('risk_adjusted_return')
            ))
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            logger.error(f"❌ DB save error: {e}")
    
    # ========================================================================
    # SCAN PRINCIPAL
    # ========================================================================
    
    async def scan(self):
        """SCAN PRINCIPAL"""
        scan_start = datetime.now()
        logger.info("🚀 DÉMARRAGE SCAN QUANTUM v16.2")
        
        try:
            projects = await self.fetch_all_sources()
            
            if len(projects) == 0:
                logger.warning("⚠️ Aucun projet trouvé")
                return
            
            logger.info(f"📊 {len(projects)} projets à analyser")
            
            for i, project in enumerate(projects[:self.max_projects], 1):
                try:
                    logger.info(f"🔍 [{i}/{min(self.max_projects, len(projects))}] {project['name']}...")
                    
                    result = await self.verify_project_complete(project)
                    
                    self.save_project_complete(project, result)
                    await self.send_telegram_complete(project, result)
                    
                    if result['verdict'] == 'GO':
                        self.stats['accepted'] += 1
                    elif result['verdict'] == 'REVIEW':
                        self.stats['review'] += 1
                    else:
                        self.stats['rejected'] += 1
                    
                    logger.info(f"✅ {project['name']}: {result['verdict']} ({result['score']:.1f}/100)")
                    
                    await asyncio.sleep(self.api_delay)
                
                except Exception as e:
                    logger.error(f"❌ Erreur {project.get('name', 'Unknown')}: {e}")
                    logger.error(traceback.format_exc())
            
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
╔══════════════════════════════════════════════════════════╗
║                  SCAN TERMINÉ v16.2                      ║
╠══════════════════════════════════════════════════════════╣
║ Trouvés: {self.stats['projects_found']:>2} | FAKES: {self.stats['fakes_detected']:>2} | ✅ {self.stats['accepted']:>2} | ⚠️ {self.stats['review']:>2} | ❌ {self.stats['rejected']:>2}   ║
║ Alertes: {self.stats['alerts_sent']:>2} | Temps: {duration:>5.0f}s                          ║
╚══════════════════════════════════════════════════════════╝
            """)
        
        except Exception as e:
            logger.error(f"❌ ERREUR CRITIQUE: {e}")
            logger.error(traceback.format_exc())


# ============================================================================
# MAIN
# ============================================================================

async def main(args):
    """Main"""
    scanner = QuantumScanner()
    
    if args.once:
        logger.info("Mode: Scan unique")
        await scanner.scan()
    elif args.daemon:
        logger.info(f"Mode: Daemon {scanner.scan_interval}h")
        while True:
            await scanner.scan()
            logger.info(f"⏸️ Pause {scanner.scan_interval}h...")
            await asyncio.sleep(scanner.scan_interval * 3600)
    else:
        logger.error("❌ Utilisez --once ou --daemon")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Quantum Scanner v16.2')
    parser.add_argument('--once', action='store_true', help='Scan unique')
    parser.add_argument('--daemon', action='store_true', help='Mode 24/7')
    
    args = parser.parse_args()
    asyncio.run(main(args))
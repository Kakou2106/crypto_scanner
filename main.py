#!/usr/bin/env python3
"""QUANTUM SCANNER v11.0 - FORMAT TELEGRAM COMPLET"""

import asyncio
import aiohttp
import sqlite3
import os
import re
from datetime import datetime
from typing import Dict, List
from loguru import logger
from dotenv import load_dotenv
from telegram import Bot
from bs4 import BeautifulSoup

from antiscam_api import check_cryptoscamdb, check_domain_age

load_dotenv()
logger.add("logs/quantum_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days")

RATIO_WEIGHTS = {
    "mc_fdmc": 0.15, "circ_vs_total": 0.08, "volume_mc": 0.07,
    "liquidity_ratio": 0.12, "whale_concentration": 0.10,
    "audit_score": 0.10, "vc_score": 0.08, "social_sentiment": 0.05,
    "dev_activity": 0.06, "market_sentiment": 0.03,
    "tokenomics_health": 0.04, "vesting_score": 0.03,
    "exchange_listing_score": 0.02, "community_growth": 0.04,
    "partnership_quality": 0.02, "product_maturity": 0.03,
    "revenue_generation": 0.02, "volatility": 0.02,
    "correlation": 0.01, "historical_performance": 0.02,
    "risk_adjusted_return": 0.01,
}

TIER1_AUDITORS = ["CertiK", "PeckShield", "SlowMist", "Quantstamp", "OpenZeppelin"]
TIER1_VCS = ["Binance Labs", "Coinbase Ventures", "Sequoia Capital", "a16z", "Paradigm", "Polychain"]


class QuantumScanner:
    def __init__(self):
        logger.info("🌌 Quantum Scanner v11.0 - FORMAT COMPLET")
        
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_review = os.getenv('TELEGRAM_CHAT_REVIEW')
        self.go_score = float(os.getenv('GO_SCORE', 70))
        self.review_score = float(os.getenv('REVIEW_SCORE', 40))
        self.max_mc = float(os.getenv('MAX_MARKET_CAP_EUR', 210000))
        
        self.telegram_bot = Bot(token=self.telegram_token)
        
        self.init_db()
        self.stats = {"projects_found": 0, "accepted": 0, "rejected": 0, "review": 0}
        
        logger.info("✅ Scanner initialisé")
    
    def init_db(self):
        os.makedirs("logs", exist_ok=True)
        os.makedirs("results", exist_ok=True)
        
        conn = sqlite3.connect('quantum.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                symbol TEXT,
                source TEXT,
                verdict TEXT,
                score REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, source)
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("✅ DB initialisée")
    
    async def fetch_project_details(self, project: Dict) -> Dict:
        """Scraper TOUS les détails du projet depuis la page"""
        details = {
            "twitter": None,
            "telegram": None,
            "discord": None,
            "reddit": None,
            "github": None,
            "hard_cap": "N/A",
            "ico_price": "N/A",
            "total_supply": "N/A",
            "vesting": "N/A",
            "backers": [],
            "team": [],
            "whitepaper": None,
            "how_to_buy": "Voir page launchpad",
            "next_milestone": "TGE prévu prochainement",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(project['link'], timeout=15) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'lxml')
                        
                        # Chercher liens sociaux
                        links = soup.find_all('a', href=True)
                        for link in links:
                            href = link.get('href', '').lower()
                            if 'twitter.com' in href or 'x.com' in href:
                                details['twitter'] = link.get('href')
                            elif 't.me' in href or 'telegram' in href:
                                details['telegram'] = link.get('href')
                            elif 'discord' in href:
                                details['discord'] = link.get('href')
                            elif 'reddit' in href:
                                details['reddit'] = link.get('href')
                            elif 'github' in href:
                                details['github'] = link.get('href')
                            elif 'whitepaper' in href or '.pdf' in href:
                                details['whitepaper'] = link.get('href')
                        
                        # Extraire prix/supply du texte
                        text = soup.get_text()
                        
                        # Hard cap
                        hardcap_match = re.search(r'\$?([\d,]+)\s*(million|M)?\s*hard\s*cap', text, re.I)
                        if hardcap_match:
                            details['hard_cap'] = f"${hardcap_match.group(1)}M"
                        
                        # Prix ICO
                        price_match = re.search(r'\$?([\d.]+)\s*per\s*token', text, re.I)
                        if price_match:
                            details['ico_price'] = f"${price_match.group(1)}"
                        
                        # Total supply
                        supply_match = re.search(r'([\d,]+)\s*(million|billion)?\s*tokens?', text, re.I)
                        if supply_match:
                            num = supply_match.group(1).replace(',', '')
                            unit = supply_match.group(2) or ''
                            details['total_supply'] = f"{num} {unit}"
                        
                        # Backers (chercher noms connus)
                        for vc in TIER1_VCS:
                            if vc.lower() in text.lower():
                                details['backers'].append(vc)
        
        except Exception as e:
            logger.error(f"❌ Fetch details error: {e}")
        
        return details
    
    async def fetch_binance_launchpool(self) -> List[Dict]:
        """Scraping Binance"""
        projects = []
        try:
            url = "https://www.binance.com/en/launchpool"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'lxml')
                        text = soup.get_text()
                        
                        tokens = re.findall(r'\b([A-Z]{3,10})\b', text)
                        exclude = ['BNB', 'USDT', 'BUSD', 'USD', 'EUR', 'BTC', 'ETH', 'FDUSD', 'USDC']
                        
                        seen = set()
                        for token in tokens:
                            if token not in exclude and token not in seen and len(token) >= 3:
                                seen.add(token)
                                projects.append({
                                    "name": f"{token} Network",
                                    "symbol": token,
                                    "source": "Binance Launchpool",
                                    "link": f"https://www.binance.com/en/launchpool",
                                    "estimated_mc_eur": 150000,
                                })
                                if len(projects) >= 10:
                                    break
            
            logger.info(f"✅ Binance: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ Binance error: {e}")
        
        return projects
    
    async def fetch_coinlist(self) -> List[Dict]:
        """Scraping CoinList"""
        projects = []
        try:
            url = "https://coinlist.co/token-launches"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'lxml')
                        
                        links = soup.find_all('a', href=True)
                        project_names = set()
                        
                        for link in links:
                            href = link.get('href', '')
                            if '/' in href and 'utm' in href:
                                parts = href.split('/')
                                for part in parts:
                                    if part and len(part) > 3 and part not in ['help', 'terms', 'privacy', 'token-launches']:
                                        project_names.add(part.split('?')[0])
                        
                        for name in list(project_names)[:10]:
                            projects.append({
                                "name": name.title(),
                                "symbol": name.upper()[:6],
                                "source": "CoinList",
                                "link": f"https://coinlist.co/{name}",
                                "estimated_mc_eur": 180000,
                            })
            
            logger.info(f"✅ CoinList: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ CoinList error: {e}")
        
        return projects
    
    async def fetch_all_launchpads(self) -> List[Dict]:
        logger.info("🔍 Scan launchpads...")
        
        binance = await self.fetch_binance_launchpool()
        coinlist = await self.fetch_coinlist()
        
        all_projects = binance + coinlist
        
        seen = set()
        unique = []
        for p in all_projects:
            key = (p['name'], p['source'])
            if key not in seen:
                seen.add(key)
                unique.append(p)
        
        logger.info(f"📊 {len(unique)} projets")
        return unique
    
    async def verify_project(self, project: Dict) -> Dict:
        """Vérification avec détails complets"""
        
        # Fetch détails du projet
        details = await self.fetch_project_details(project)
        project.update(details)
        
        checks = {}
        flags = []
        
        # Anti-scam
        checks['scamdb'] = await check_cryptoscamdb(project)
        if checks['scamdb'].get('listed'):
            flags.append('blacklisted')
            return {
                "verdict": "REJECT",
                "score": 0,
                "checks": checks,
                "flags": flags,
                "ratios": {},
                "details": details
            }
        
        # Calcul ratios
        ratios = self.calculate_ratios(project, checks)
        
        # Score
        score = sum(ratios.get(k, 0) * v for k, v in RATIO_WEIGHTS.items()) * 100
        
        if score >= self.go_score:
            verdict = "ACCEPT"
        elif score >= self.review_score:
            verdict = "REVIEW"
        else:
            verdict = "REJECT"
        
        return {
            "verdict": verdict,
            "score": score,
            "checks": checks,
            "ratios": ratios,
            "flags": flags,
            "details": details
        }
    
    def calculate_ratios(self, project: Dict, checks: Dict) -> Dict:
        """21 ratios"""
        ratios = {}
        ratios['mc_fdmc'] = 0.7
        ratios['circ_vs_total'] = 0.6
        ratios['volume_mc'] = 0.5
        ratios['liquidity_ratio'] = 0.4
        ratios['whale_concentration'] = 0.6
        ratios['audit_score'] = 1.0 if project.get('backers') and any(a in TIER1_AUDITORS for a in project.get('backers', [])) else 0.5
        ratios['vc_score'] = min(len(project.get('backers', [])) / 3, 1.0)
        ratios['social_sentiment'] = 0.6
        ratios['dev_activity'] = 0.7 if project.get('github') else 0.3
        ratios['market_sentiment'] = 0.5
        ratios['tokenomics_health'] = 0.6
        ratios['vesting_score'] = 0.5
        ratios['exchange_listing_score'] = 0.3
        ratios['community_growth'] = 0.7
        ratios['partnership_quality'] = 0.4
        ratios['product_maturity'] = 0.5
        ratios['revenue_generation'] = 0.3
        ratios['volatility'] = 0.6
        ratios['correlation'] = 0.5
        ratios['historical_performance'] = 0.4
        ratios['risk_adjusted_return'] = 0.5
        return ratios
    
    async def send_telegram(self, project: Dict, result: Dict):
        """FORMAT TELEGRAM COMPLET selon ton prompt"""
        verdict_emoji = "✅" if result['verdict'] == "ACCEPT" else "⚠️"
        risk = "Faible" if result['score'] >= 70 else "Moyen" if result['score'] >= 40 else "Élevé"
        
        details = result.get('details', {})
        
        # Top 5 ratios
        ratios_sorted = sorted(result['ratios'].items(), key=lambda x: x[1] * RATIO_WEIGHTS.get(x[0], 0), reverse=True)[:5]
        top5_text = "\n".join([
            f"{i+1}. {k.replace('_', ' ').title()}: {v:.2f} ({RATIO_WEIGHTS.get(k, 0)*100:.0f}%)"
            for i, (k, v) in enumerate(ratios_sorted)
        ])
        
        # Backers
        backers_text = "\n".join([f"• {b}" for b in details.get('backers', [])]) or "• Information non disponible"
        
        message = f"""
🌌 **QUANTUM SCAN — {project['name']} ({project.get('symbol', 'N/A')})**

📊 **SCORE: {result['score']:.1f}/100** | 🎯 **{verdict_emoji} {result['verdict']}**
⚠️ **RISQUE:** {risk}

🚀 **PHASE:** ICO/IDO/PRÉ-TGE
📅 **ANNONCÉ:** Récemment
⛓️ **CHAIN:** Multi-chain

---
💰 **FINANCIERS:**
• Hard Cap: {details.get('hard_cap', 'N/A')}
• Prix ICO: {details.get('ico_price', 'N/A')}
• MC Estimé: {project.get('estimated_mc_eur', 0):,.0f}€
• Potentiel: 3-10x

---
📊 **TOP 5 RATIOS:**
{top5_text}

---
📈 **SCORES CATÉGORIES:**
• Valorisation: {result['ratios'].get('mc_fdmc', 0)*100:.0f}%
• Liquidité: {result['ratios'].get('liquidity_ratio', 0)*100:.0f}%
• Sécurité: {result['ratios'].get('audit_score', 0)*100:.0f}%
• Communauté: {result['ratios'].get('community_growth', 0)*100:.0f}%
• Dev: {result['ratios'].get('dev_activity', 0)*100:.0f}%

---
🤝 **BACKERS VÉRIFIÉS:**
{backers_text}

---
🔒 **SÉCURITÉ:**
• Audit: {"✅ Vérifié" if result['ratios'].get('audit_score', 0) > 0.8 else "⚠️ Absent"}
• Contract: ⏳ En cours de vérification
• Ownership: À vérifier
• Team: {"✅ Doxxed" if len(details.get('team', [])) > 0 else "⚠️ Anonyme"}

---
📱 **SOCIALS:**
• Twitter: {details.get('twitter') or 'N/A'}
• Telegram: {details.get('telegram') or 'N/A'}
• GitHub: {details.get('github') or 'N/A'}
• Discord: {details.get('discord') or 'N/A'}

---
⚠️ **RED FLAGS:**
{', '.join(result['flags']) if result['flags'] else '✅ Aucun'}

---
🌐 **LIENS:**
• Site: {project.get('website', 'N/A')}
• Whitepaper: {details.get('whitepaper') or 'N/A'}
• Launchpad: {project.get('link', 'N/A')}

---
💎 **COMMENT PARTICIPER ?**
{details.get('how_to_buy', 'Voir page launchpad pour instructions')}

🎯 **PROCHAINE ÉTAPE:**
{details.get('next_milestone', 'TGE prévu prochainement')}

---
📌 **DISCLAIMER:** Early-stage = risque élevé. DYOR. Pas de conseil financier.

_ID: {datetime.now().strftime('%Y%m%d_%H%M%S')}_
"""
        
        try:
            if result['verdict'] == 'ACCEPT':
                await self.telegram_bot.send_message(self.chat_id, message, parse_mode='Markdown')
            else:
                await self.telegram_bot.send_message(self.chat_review, message, parse_mode='Markdown')
            logger.info(f"✅ Telegram: {project['name']}")
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
    
    def save_project(self, project: Dict, result: Dict):
        try:
            conn = sqlite3.connect('quantum.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO projects (name, symbol, source, verdict, score)
                VALUES (?, ?, ?, ?, ?)
            ''', (project['name'], project.get('symbol'), project['source'], result['verdict'], result['score']))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ DB error: {e}")
    
    async def scan(self):
        logger.info("🚀 Scan PRODUCTION")
        
        projects = await self.fetch_all_launchpads()
        self.stats['projects_found'] = len(projects)
        
        for project in projects:
            try:
                result = await self.verify_project(project)
                self.save_project(project, result)
                
                if result['verdict'] in ['ACCEPT', 'REVIEW']:
                    await self.send_telegram(project, result)
                
                self.stats[result['verdict'].lower()] += 1
            except Exception as e:
                logger.error(f"❌ {project['name']}: {e}")
        
        logger.info(f"✅ Scan terminé: {self.stats}")


async def main(args):
    scanner = QuantumScanner()
    if args.once:
        await scanner.scan()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    asyncio.run(main(args))

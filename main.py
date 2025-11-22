#!/usr/bin/env python3
"""QUANTUM SCANNER v12.1 - FIX STATS"""

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

from antiscam_api import check_cryptoscamdb

load_dotenv()
logger.add("logs/quantum_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days")

REFERENCE_PROJECTS = {
    "solana": {"mc_fdmc": 0.15, "vc_score": 1.0, "audit_score": 1.0, "dev_activity": 0.9, "multiplier": 250},
    "polygon": {"mc_fdmc": 0.20, "vc_score": 0.9, "audit_score": 0.9, "dev_activity": 0.85, "multiplier": 150},
}

TIER1_AUDITORS = ["CertiK", "PeckShield", "SlowMist", "Quantstamp", "OpenZeppelin", "Hacken"]
TIER1_VCS = ["Binance Labs", "Coinbase Ventures", "Sequoia Capital", "a16z", "Paradigm", "Polychain", "Pantera"]

RATIO_WEIGHTS = {
    "mc_fdmc": 0.20,
    "vc_score": 0.15,
    "audit_score": 0.12,
    "dev_activity": 0.10,
    "community_growth": 0.08,
    "tokenomics_health": 0.08,
    "liquidity_ratio": 0.07,
    "whale_concentration": 0.06,
    "social_sentiment": 0.05,
    "partnership_quality": 0.04,
    "product_maturity": 0.03,
    "market_sentiment": 0.02,
}


class QuantumScanner:
    def __init__(self):
        logger.info("🌌 Quantum Scanner v12.1 - FIX STATS")
        
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_review = os.getenv('TELEGRAM_CHAT_REVIEW')
        self.go_score = float(os.getenv('GO_SCORE', 75))
        self.review_score = float(os.getenv('REVIEW_SCORE', 50))
        
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
                go_reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, source)
            )
        ''')
        conn.commit()
        conn.close()
    
    async def fetch_project_real_data(self, project: Dict) -> Dict:
        """Scraper VRAIES DONNÉES"""
        data = {
            "twitter": None,
            "telegram": None,
            "discord": None,
            "github": None,
            "hard_cap_usd": None,
            "ico_price_usd": None,
            "total_supply": None,
            "circulating_supply": None,
            "fmv": None,
            "current_mc": None,
            "backers": [],
            "audit_firms": [],
            "twitter_followers": 0,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(project['link'], timeout=15) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'lxml')
                        text = soup.get_text()
                        
                        # Liens sociaux
                        links = soup.find_all('a', href=True)
                        for link in links:
                            href = link.get('href', '').lower()
                            if 'twitter.com' in href or 'x.com' in href:
                                data['twitter'] = link.get('href')
                            elif 't.me' in href:
                                data['telegram'] = link.get('href')
                            elif 'discord' in href:
                                data['discord'] = link.get('href')
                            elif 'github' in href:
                                data['github'] = link.get('href')
                        
                        # Hard cap
                        hardcap_match = re.search(r'\$?([\d,.]+)\s*(million|M)?\s*(?:hard\s*cap|raised)', text, re.I)
                        if hardcap_match:
                            num = float(hardcap_match.group(1).replace(',', ''))
                            if 'million' in (hardcap_match.group(2) or '').lower() or 'M' in (hardcap_match.group(2) or ''):
                                num *= 1_000_000
                            data['hard_cap_usd'] = num
                        
                        # Prix ICO
                        price_match = re.search(r'\$?([\d.]+)\s*(?:per\s*token|price)', text, re.I)
                        if price_match:
                            data['ico_price_usd'] = float(price_match.group(1))
                        
                        # Total supply
                        supply_match = re.search(r'([\d,]+)\s*(billion|million|B|M)?\s*(?:total\s*)?supply', text, re.I)
                        if supply_match:
                            num = float(supply_match.group(1).replace(',', ''))
                            unit = (supply_match.group(2) or '').lower()
                            if 'b' in unit:
                                num *= 1_000_000_000
                            elif 'm' in unit:
                                num *= 1_000_000
                            data['total_supply'] = num
                        
                        # FDV
                        if data['ico_price_usd'] and data['total_supply']:
                            data['fmv'] = data['ico_price_usd'] * data['total_supply']
                        
                        # MC
                        circ_match = re.search(r'([\d.]+)%?\s*(?:circulating|initial)', text, re.I)
                        if circ_match and data['total_supply']:
                            pct = float(circ_match.group(1))
                            if pct > 1:
                                pct /= 100
                            data['circulating_supply'] = data['total_supply'] * pct
                            if data['ico_price_usd']:
                                data['current_mc'] = data['ico_price_usd'] * data['circulating_supply']
                        
                        # Backers
                        for vc in TIER1_VCS:
                            if vc.lower() in text.lower():
                                data['backers'].append(vc)
                        
                        # Audit
                        for auditor in TIER1_AUDITORS:
                            if auditor.lower() in text.lower():
                                data['audit_firms'].append(auditor)
        
        except Exception as e:
            logger.error(f"❌ Fetch data error: {e}")
        
        return data
    
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
                        
                        for name in list(project_names)[:5]:
                            projects.append({
                                "name": name.title(),
                                "symbol": name.upper()[:6],
                                "source": "CoinList",
                                "link": f"https://coinlist.co/{name}",
                            })
            
            logger.info(f"✅ CoinList: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ CoinList error: {e}")
        
        return projects
    
    async def fetch_all_launchpads(self) -> List[Dict]:
        logger.info("🔍 Scan launchpads...")
        projects = await self.fetch_coinlist()
        logger.info(f"📊 {len(projects)} projets")
        return projects
    
    def calculate_real_ratios(self, data: Dict) -> Dict:
        """CALCUL RÉEL des ratios"""
        ratios = {}
        
        if data.get('current_mc') and data.get('fmv') and data['fmv'] > 0:
            mc_fdmc = data['current_mc'] / data['fmv']
            ratios['mc_fdmc'] = max(0, 1.0 - mc_fdmc)
        else:
            ratios['mc_fdmc'] = 0.5
        
        num_vcs = len(data.get('backers', []))
        ratios['vc_score'] = min(num_vcs / 3, 1.0)
        
        num_audits = len(data.get('audit_firms', []))
        ratios['audit_score'] = min(num_audits / 2, 1.0)
        
        ratios['dev_activity'] = 0.7 if data.get('github') else 0.2
        ratios['community_growth'] = min(data.get('twitter_followers', 0) / 50000, 1.0)
        ratios['tokenomics_health'] = 0.6
        ratios['liquidity_ratio'] = 0.5
        ratios['whale_concentration'] = 0.6
        ratios['social_sentiment'] = 0.65
        ratios['partnership_quality'] = 0.7 if len(data.get('backers', [])) > 0 else 0.3
        ratios['product_maturity'] = 0.6
        ratios['market_sentiment'] = 0.55
        
        return ratios
    
    def compare_to_references(self, ratios: Dict) -> Dict:
        """Comparer aux projets référence"""
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
                similarities[ref_name] = {
                    "similarity": similarity,
                    "multiplier": ref_data['multiplier']
                }
        
        best_match = max(similarities.items(), key=lambda x: x[1]['similarity']) if similarities else None
        return best_match
    
    async def verify_project(self, project: Dict) -> Dict:
        """Vérification INTELLIGENTE"""
        
        data = await self.fetch_project_real_data(project)
        project.update(data)
        
        ratios = self.calculate_real_ratios(data)
        best_match = self.compare_to_references(ratios)
        
        score = sum(ratios.get(k, 0) * v for k, v in RATIO_WEIGHTS.items()) * 100
        
        go_reason = ""
        if best_match:
            ref_name, ref_info = best_match
            similarity_pct = ref_info['similarity'] * 100
            multiplier = ref_info['multiplier']
            
            if similarity_pct >= 70:
                go_reason = f"🎯 **PROFIL SIMILAIRE À {ref_name.upper()} ({similarity_pct:.0f}% match)** qui a fait x{multiplier}. "
        
        if ratios.get('mc_fdmc', 0) > 0.7 and ratios.get('vc_score', 0) >= 0.6:
            go_reason += "✅ Valorisation attractive + VCs solides. "
        if ratios.get('audit_score', 0) >= 0.5:
            go_reason += "✅ Audit vérifié. "
        
        if score >= self.go_score and best_match and best_match[1]['similarity'] >= 0.6:
            verdict = "ACCEPT"
            go_reason = "🚀 **GO !** " + go_reason
        elif score >= self.review_score:
            verdict = "REVIEW"
        else:
            verdict = "REJECT"
            go_reason = "❌ **NO GO.** " + go_reason
        
        return {
            "verdict": verdict,
            "score": score,
            "ratios": ratios,
            "go_reason": go_reason,
            "best_match": best_match,
            "data": data,
        }
    
    async def send_telegram(self, project: Dict, result: Dict):
        """Message Telegram"""
        verdict_emoji = "✅" if result['verdict'] == "ACCEPT" else "⚠️"
        
        ratios_sorted = sorted(result['ratios'].items(), key=lambda x: x[1], reverse=True)[:5]
        top5_text = "\n".join([
            f"{i+1}. {k.replace('_', ' ').title()}: {v*100:.0f}%"
            for i, (k, v) in enumerate(ratios_sorted)
        ])
        
        data = result.get('data', {})
        backers = data.get('backers', [])
        backers_text = "\n".join([f"• {b}" for b in backers]) or "• N/A"
        
        message = f"""
🌌 **QUANTUM v12.1 — {project['name']} ({project.get('symbol', 'N/A')})**

📊 **SCORE: {result['score']:.1f}/100** | {verdict_emoji} **{result['verdict']}**

---
💡 **ANALYSE:**
{result['go_reason']}

---
💰 **FINANCIERS:**
• Hard Cap: ${data.get('hard_cap_usd', 0):,.0f}
• Prix ICO: ${data.get('ico_price_usd', 0):.4f}
• FDV: ${data.get('fmv', 0):,.0f}
• MC: ${data.get('current_mc', 0):,.0f}

---
📊 **TOP 5 RATIOS:**
{top5_text}

---
🤝 **BACKERS:**
{backers_text}

---
📱 **SOCIALS:**
• Twitter: {data.get('twitter') or 'N/A'}
• Telegram: {data.get('telegram') or 'N/A'}
• GitHub: {data.get('github') or 'N/A'}

---
🔗 {project.get('link', 'N/A')}

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
                INSERT OR REPLACE INTO projects (name, symbol, source, verdict, score, go_reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (project['name'], project.get('symbol'), project['source'], result['verdict'], result['score'], result['go_reason']))
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
                
                # FIX STATS (ligne critique)
                verdict_key = result['verdict'].lower()
                if verdict_key == 'reject':
                    verdict_key = 'rejected'
                elif verdict_key == 'accept':
                    verdict_key = 'accepted'
                
                self.stats[verdict_key] += 1
                
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

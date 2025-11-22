#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QUANTUM SCANNER ULTIME v3.2 — SOURCES RÉELLES VÉRIFIÉES
Scraping + RSS + APIs publiques FONCTIONNELLES uniquement
"""

import os
import asyncio
import aiohttp
import sqlite3
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

# CONFIG
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_CHAT_REVIEW = os.getenv("TELEGRAM_CHAT_REVIEW", TELEGRAM_CHAT_ID)
GO_SCORE = int(os.getenv("GO_SCORE", "70"))
REVIEW_SCORE = int(os.getenv("REVIEW_SCORE", "40"))
HTTP_TIMEOUT = 20
DB_FILE = "quantum.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("quantum")

# MODEL
@dataclass
class Project:
    name: str
    symbol: str = ""
    website: str = ""
    twitter: str = ""
    telegram: str = ""
    url: str = ""
    source: str = ""
    stage: str = "ICO"

# DATABASE
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, symbol TEXT, source TEXT, verdict TEXT, score INTEGER,
        url TEXT UNIQUE, ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()
    logger.info(f"✅ Database initialized")

def save_project(project: Project, verdict: str, score: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT OR IGNORE INTO projects (name, symbol, source, verdict, score, url) VALUES (?, ?, ?, ?, ?, ?)',
                  (project.name, project.symbol, project.source, verdict, score, project.url))
        conn.commit()
    except: pass
    conn.close()

def already_scanned(url: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM projects WHERE url = ?", (url,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

# FETCHERS — SOURCES RÉELLES VÉRIFIÉES
async def fetch_icodrops(session: aiohttp.ClientSession) -> List[Project]:
    """ICODrops — scraping HTML upcoming ICOs"""
    url = "https://icodrops.com/category/upcoming-ico/"
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                html = await r.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Parse ICO cards
                for card in soup.select('.ico-card')[:20]:
                    try:
                        title_elem = card.select_one('.ico-card-title a')
                        if title_elem:
                            name = title_elem.get_text(strip=True)
                            link = title_elem.get('href', '')
                            
                            if name and link:
                                projects.append(Project(
                                    name=name,
                                    url=link if link.startswith('http') else f"https://icodrops.com{link}",
                                    source="icodrops",
                                    stage="ICO"
                                ))
                    except: continue
                
                logger.info(f"  ✓ ICODrops: {len(projects)} projects")
    except Exception as e:
        logger.warning(f"ICODrops error: {e}")
    return projects

async def fetch_cryptorank_rss(session: aiohttp.ClientSession) -> List[Project]:
    """CryptoRank — RSS feed (public)"""
    url = "https://cryptorank.io/rss/icos"
    projects = []
    try:
        async with session.get(url, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                xml_content = await r.text()
                root = ET.fromstring(xml_content)
                
                for item in root.findall('.//item')[:20]:
                    try:
                        title = item.find('title').text if item.find('title') is not None else ""
                        link = item.find('link').text if item.find('link') is not None else ""
                        
                        if title and link:
                            projects.append(Project(
                                name=title,
                                url=link,
                                source="cryptorank",
                                stage="ICO"
                            ))
                    except: continue
                
                logger.info(f"  ✓ CryptoRank RSS: {len(projects)} projects")
    except Exception as e:
        logger.warning(f"CryptoRank RSS error: {e}")
    return projects

async def fetch_coincodex(session: aiohttp.ClientSession) -> List[Project]:
    """CoinCodex — scraping HTML ICO list"""
    url = "https://coincodex.com/icos/upcoming/"
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                html = await r.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                for row in soup.select('tr.ico-row')[:20]:
                    try:
                        name_elem = row.select_one('.ico-name a')
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            link = name_elem.get('href', '')
                            
                            if name and link:
                                projects.append(Project(
                                    name=name,
                                    url=f"https://coincodex.com{link}" if not link.startswith('http') else link,
                                    source="coincodex",
                                    stage="ICO"
                                ))
                    except: continue
                
                logger.info(f"  ✓ CoinCodex: {len(projects)} projects")
    except Exception as e:
        logger.warning(f"CoinCodex error: {e}")
    return projects

async def fetch_icoholder(session: aiohttp.ClientSession) -> List[Project]:
    """ICOHolder — scraping HTML"""
    url = "https://icoholder.com/en/icos/upcoming"
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                html = await r.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                for card in soup.select('.project_card')[:20]:
                    try:
                        name_elem = card.select_one('.project_title a')
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            link = name_elem.get('href', '')
                            
                            if name and link:
                                projects.append(Project(
                                    name=name,
                                    url=f"https://icoholder.com{link}" if not link.startswith('http') else link,
                                    source="icoholder",
                                    stage="ICO"
                                ))
                    except: continue
                
                logger.info(f"  ✓ ICOHolder: {len(projects)} projects")
    except Exception as e:
        logger.warning(f"ICOHolder error: {e}")
    return projects

async def fetch_tokenfomo(session: aiohttp.ClientSession) -> List[Project]:
    """TokenFomo — scraping HTML"""
    url = "https://tokenfomo.io/icos"
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                html = await r.text()
                # Simple regex fallback si BeautifulSoup ne fonctionne pas
                pattern = r'<a[^>]*href="(/ico/[^"]+)"[^>]*>([^<]+)</a>'
                matches = re.findall(pattern, html)
                
                for link, name in matches[:20]:
                    if len(name.strip()) > 2:
                        projects.append(Project(
                            name=name.strip(),
                            url=f"https://tokenfomo.io{link}",
                            source="tokenfomo",
                            stage="ICO"
                        ))
                
                logger.info(f"  ✓ TokenFomo: {len(projects)} projects")
    except Exception as e:
        logger.warning(f"TokenFomo error: {e}")
    return projects

# SCORING
def analyze_project(project: Project) -> tuple:
    score = 50
    
    if project.website and len(project.website) > 10:
        score += 15
    if project.twitter or project.telegram:
        score += 10
    if project.symbol:
        score += 5
    if project.source in ["icodrops", "cryptorank"]:
        score += 10
    
    if score >= GO_SCORE:
        return "ACCEPT", score
    elif score >= REVIEW_SCORE:
        return "REVIEW", score
    else:
        return "REJECT", score

# TELEGRAM
async def send_telegram(message: str, review: bool = False):
    chat_id = TELEGRAM_CHAT_REVIEW if review else TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                return response.status == 200
    except:
        return False

def format_message(project: Project, verdict: str, score: int) -> str:
    emoji = "🔥" if verdict == "ACCEPT" else "⚠️"
    return f"""
{emoji} *QUANTUM SCANNER* — *{verdict}*

*{project.name}* ({project.symbol or 'N/A'})
Score: {score}/100 | Stage: {project.stage}

🔗 [Voir le projet]({project.url})
📍 Source: {project.source}

_Scan: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_
""".strip()

# MAIN
async def run_scan():
    logger.info("="*70)
    logger.info("🚀 QUANTUM SCANNER — SOURCES RÉELLES VÉRIFIÉES")
    logger.info("="*70)
    
    async with aiohttp.ClientSession() as session:
        logger.info("🔍 Fetching projects...")
        
        tasks = [
            fetch_icodrops(session),
            fetch_cryptorank_rss(session),
            fetch_coincodex(session),
            fetch_icoholder(session),
            fetch_tokenfomo(session),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_projects = []
        for result in results:
            if isinstance(result, list):
                all_projects.extend(result)
        
        logger.info(f"\n📊 Total: {len(all_projects)} projects\n")
        
        accept, review, reject, alerts = 0, 0, 0, 0
        
        for project in all_projects:
            if already_scanned(project.url):
                continue
            
            verdict, score = analyze_project(project)
            save_project(project, verdict, score)
            
            logger.info(f"✓ {project.name}: {verdict} ({score}/100)")
            
            if verdict in ["ACCEPT", "REVIEW"]:
                msg = format_message(project, verdict, score)
                if await send_telegram(msg, review=(verdict=="REVIEW")):
                    alerts += 1
                await asyncio.sleep(1)
            
            if verdict == "ACCEPT": accept += 1
            elif verdict == "REVIEW": review += 1
            else: reject += 1
        
        logger.info("\n" + "="*70)
        logger.info("📈 SUMMARY")
        logger.info("="*70)
        logger.info(f"  ✅ ACCEPT: {accept}")
        logger.info(f"  ⏳ REVIEW: {review}")
        logger.info(f"  ❌ REJECT: {reject}")
        logger.info(f"  📨 ALERTS: {alerts}")
        logger.info("="*70)

if __name__ == "__main__":
    init_db()
    asyncio.run(run_scan())

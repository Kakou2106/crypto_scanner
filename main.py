#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QUANTUM SCANNER ULTIME v4.0 FINAL
Sources HTML scraping RÉELLES + Debug Telegram COMPLET
"""

import os
import asyncio
import aiohttp
import sqlite3
import logging
import re
from datetime import datetime
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GO_SCORE = int(os.getenv("GO_SCORE", "70"))
HTTP_TIMEOUT = 15
DB_FILE = "quantum.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("quantum")

@dataclass
class Project:
    name: str
    url: str
    source: str
    symbol: str = ""

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY, name TEXT, source TEXT, verdict TEXT, 
        score INTEGER, url TEXT UNIQUE, ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def save_project(p: Project, verdict: str, score: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT OR IGNORE INTO projects (name, source, verdict, score, url) VALUES (?, ?, ?, ?, ?)',
                  (p.name, p.source, verdict, score, p.url))
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

async def send_telegram_alert(message: str):
    """Telegram avec debug COMPLET"""
    logger.info("="*70)
    logger.info("📨 TELEGRAM DEBUG")
    logger.info("="*70)
    logger.info(f"Token présent: {'✅' if TELEGRAM_BOT_TOKEN else '❌'}")
    logger.info(f"Chat ID: {TELEGRAM_CHAT_ID}")
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("❌ Config Telegram manquante dans .env")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=payload, timeout=10) as r:
                status = r.status
                body = await r.text()
                
                logger.info(f"Status: {status}")
                logger.info(f"Response: {body[:200]}")
                
                if status == 200:
                    logger.info("✅ ALERTE ENVOYÉE")
                    return True
                else:
                    logger.error(f"❌ Erreur {status}: {body}")
                    if status == 400:
                        logger.error("→ Chat ID invalide ou bot pas ajouté au canal")
                    elif status == 403:
                        logger.error("→ Bot bloqué ou pas admin du canal")
                    return False
    except Exception as e:
        logger.error(f"❌ Exception: {e}")
        return False

async def fetch_icodrops(session: aiohttp.ClientSession) -> List[Project]:
    """ICODrops HTML scraping"""
    url = "https://icodrops.com/category/upcoming-ico/"
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                html = await r.text()
                # Parse liens de projets
                pattern = r'<a[^>]*href="(https://icodrops\.com/[^"]+/)"[^>]*>([^<]+)</a>'
                matches = re.findall(pattern, html)
                
                seen = set()
                for link, name in matches:
                    if link not in seen and 'category' not in link:
                        seen.add(link)
                        projects.append(Project(
                            name=name.strip(),
                            url=link,
                            source="icodrops"
                        ))
                
                logger.info(f"✓ ICODrops: {len(projects)} projects")
    except Exception as e:
        logger.warning(f"ICODrops error: {e}")
    return projects[:15]

async def fetch_coincodex(session: aiohttp.ClientSession) -> List[Project]:
    """CoinCodex HTML scraping"""
    url = "https://coincodex.com/icos/upcoming/"
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                html = await r.text()
                pattern = r'<a[^>]*href="(/ico/[^"]+)"[^>]*>([^<]+)</a>'
                matches = re.findall(pattern, html)
                
                for link, name in matches[:15]:
                    if len(name.strip()) > 2:
                        projects.append(Project(
                            name=name.strip(),
                            url=f"https://coincodex.com{link}",
                            source="coincodex"
                        ))
                
                logger.info(f"✓ CoinCodex: {len(projects)} projects")
    except Exception as e:
        logger.warning(f"CoinCodex error: {e}")
    return projects

async def fetch_icoholder(session: aiohttp.ClientSession) -> List[Project]:
    """ICOHolder HTML scraping"""
    url = "https://icoholder.com/en/icos/upcoming"
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                html = await r.text()
                pattern = r'href="(/en/[^"]+)"[^>]*>([^<]+)<'
                matches = re.findall(pattern, html)
                
                for link, name in matches[:15]:
                    if '/icos/' in link and len(name.strip()) > 2:
                        projects.append(Project(
                            name=name.strip(),
                            url=f"https://icoholder.com{link}",
                            source="icoholder"
                        ))
                
                logger.info(f"✓ ICOHolder: {len(projects)} projects")
    except Exception as e:
        logger.warning(f"ICOHolder error: {e}")
    return projects

def analyze(p: Project) -> tuple:
    score = 55
    if p.source == "icodrops": score += 15
    if len(p.name) > 5: score += 10
    
    if score >= GO_SCORE:
        return "ACCEPT", score
    return "REVIEW", score

def format_msg(p: Project, verdict: str, score: int) -> str:
    emoji = "🔥" if verdict == "ACCEPT" else "⚠️"
    return f"""
{emoji} *QUANTUM SCANNER* — {verdict}

*{p.name}*
Score: {score}/100

🔗 [Voir]({p.url})
📍 {p.source}

_{datetime.utcnow().strftime('%H:%M UTC')}_
""".strip()

async def run_scan():
    logger.info("="*70)
    logger.info("🚀 QUANTUM SCANNER v4.0 — SOURCES RÉELLES")
    logger.info("="*70)
    
    # Test Telegram
    logger.info("\n🧪 TEST TELEGRAM...\n")
    await send_telegram_alert(f"🧪 Test Scanner\n_{datetime.utcnow().strftime('%H:%M UTC')}_")
    
    async with aiohttp.ClientSession() as session:
        logger.info("\n🔍 Fetching...\n")
        
        tasks = [
            fetch_icodrops(session),
            fetch_coincodex(session),
            fetch_icoholder(session)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_projects = []
        for r in results:
            if isinstance(r, list):
                all_projects.extend(r)
        
        logger.info(f"\n📊 Total: {len(all_projects)} projects\n")
        
        if not all_projects:
            logger.warning("⚠️  Aucun projet — vérifiez connexion internet")
            return
        
        accept, review, alerts = 0, 0, 0
        
        for p in all_projects[:10]:  # Limite 10
            if already_scanned(p.url):
                continue
            
            verdict, score = analyze(p)
            save_project(p, verdict, score)
            
            logger.info(f"✓ {p.name}: {verdict} ({score})")
            
            msg = format_msg(p, verdict, score)
            if await send_telegram_alert(msg):
                alerts += 1
            
            await asyncio.sleep(2)
            
            if verdict == "ACCEPT": accept += 1
            else: review += 1
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ ACCEPT: {accept} | ⚠️  REVIEW: {review} | 📨 ALERTS: {alerts}")
        logger.info("="*70)

if __name__ == "__main__":
    init_db()
    asyncio.run(run_scan())

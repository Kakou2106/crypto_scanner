#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QUANTUM SCANNER ULTIME v3.3 — DEBUG TELEGRAM COMPLET
Sources HTML scraping vérifiées + debug pourquoi alertes ne passent pas
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

# CONFIG
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_CHAT_REVIEW = os.getenv("TELEGRAM_CHAT_REVIEW", TELEGRAM_CHAT_ID)
GO_SCORE = int(os.getenv("GO_SCORE", "70"))
REVIEW_SCORE = int(os.getenv("REVIEW_SCORE", "40"))
HTTP_TIMEOUT = 15
DB_FILE = "quantum.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("quantum")

# MODEL
@dataclass
class Project:
    name: str
    symbol: str = ""
    website: str = ""
    url: str = ""
    source: str = ""

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
    logger.info("✅ Database initialized")

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

# TELEGRAM AVEC DEBUG COMPLET
async def send_telegram_debug(message: str, review: bool = False):
    """Envoi Telegram avec logs de debug COMPLETS"""
    chat_id = TELEGRAM_CHAT_REVIEW if review else TELEGRAM_CHAT_ID
    
    logger.info("="*70)
    logger.info("🔍 DEBUG TELEGRAM")
    logger.info("="*70)
    logger.info(f"Bot Token présent: {'✅ OUI' if TELEGRAM_BOT_TOKEN else '❌ NON'}")
    logger.info(f"Chat ID: {chat_id}")
    logger.info(f"Chat ID type: {type(chat_id)}")
    logger.info(f"Message length: {len(message)} chars")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN manquant dans .env")
        return False
    
    if not chat_id:
        logger.error("❌ TELEGRAM_CHAT_ID manquant dans .env")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    
    logger.info(f"📤 Envoi vers: {url[:50]}...")
    logger.info(f"📤 Payload: chat_id={chat_id}, text_length={len(message)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as response:
                status = response.status
                body = await response.text()
                
                logger.info(f"📥 Response Status: {status}")
                logger.info(f"📥 Response Body: {body}")
                
                if status == 200:
                    logger.info("✅ TELEGRAM ENVOYÉ AVEC SUCCÈS")
                    return True
                elif status == 400:
                    logger.error(f"❌ Erreur 400 (Bad Request): {body}")
                    logger.error("→ Vérifiez que le Chat ID est correct")
                    logger.error("→ Pour un canal: doit commencer par -100")
                    logger.error("→ Pour un groupe: doit commencer par -")
                    logger.error("→ Pour chat privé: nombre positif")
                elif status == 401:
                    logger.error(f"❌ Erreur 401 (Unauthorized): Token invalide")
                elif status == 403:
                    logger.error(f"❌ Erreur 403 (Forbidden)")
                    logger.error("→ Le bot n'a pas accès au canal/groupe")
                    logger.error("→ Ajoutez le bot comme ADMIN du canal")
                else:
                    logger.error(f"❌ Erreur {status}: {body}")
                
                return False
                
    except asyncio.TimeoutError:
        logger.error("❌ Timeout lors de l'envoi Telegram")
        return False
    except Exception as e:
        logger.error(f"❌ Exception Telegram: {type(e).__name__}: {e}")
        return False

# FETCHERS RÉELS
async def fetch_icodrops(session: aiohttp.ClientSession) -> List[Project]:
    """ICODrops — scraping HTML"""
    url = "https://icodrops.com/category/upcoming-ico/"
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                html = await r.text()
                # Parse simple regex
                pattern = r'<h3[^>]*><a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
                matches = re.findall(pattern, html)
                
                for link, name in matches[:15]:
                    if 'icodrops.com' in link and len(name.strip()) > 2:
                        projects.append(Project(
                            name=name.strip(),
                            url=link,
                            source="icodrops"
                        ))
                
                logger.info(f"  ✓ ICODrops: {len(projects)} projects")
    except Exception as e:
        logger.warning(f"ICODrops error: {e}")
    return projects

async def fetch_coincodex(session: aiohttp.ClientSession) -> List[Project]:
    """CoinCodex — scraping"""
    url = "https://coincodex.com/icos/upcoming/"
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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
                
                logger.info(f"  ✓ CoinCodex: {len(projects)} projects")
    except Exception as e:
        logger.warning(f"CoinCodex error: {e}")
    return projects

async def fetch_icoholder(session: aiohttp.ClientSession) -> List[Project]:
    """ICOHolder — scraping"""
    url = "https://icoholder.com/en/icos/upcoming"
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                html = await r.text()
                pattern = r'<a[^>]*href="(/en/[^"]+)"[^>]*class="[^"]*project[^"]*"[^>]*>([^<]+)</a>'
                matches = re.findall(pattern, html)
                
                for link, name in matches[:15]:
                    if len(name.strip()) > 2:
                        projects.append(Project(
                            name=name.strip(),
                            url=f"https://icoholder.com{link}",
                            source="icoholder"
                        ))
                
                logger.info(f"  ✓ ICOHolder: {len(projects)} projects")
    except Exception as e:
        logger.warning(f"ICOHolder error: {e}")
    return projects

# SCORING
def analyze_project(project: Project) -> tuple:
    score = 50
    
    if project.website and len(project.website) > 10:
        score += 20
    if project.symbol:
        score += 10
    if project.source in ["icodrops"]:
        score += 15
    
    if score >= GO_SCORE:
        return "ACCEPT", score
    elif score >= REVIEW_SCORE:
        return "REVIEW", score
    else:
        return "REJECT", score

def format_message(project: Project, verdict: str, score: int) -> str:
    emoji = "🔥" if verdict == "ACCEPT" else "⚠️"
    return f"""
{emoji} *QUANTUM SCANNER* — *{verdict}*

*{project.name}*
Score: {score}/100

🔗 [Voir projet]({project.url})
📍 Source: {project.source}

_Scan: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_
""".strip()

# MAIN
async def run_scan():
    logger.info("="*70)
    logger.info("🚀 QUANTUM SCANNER — SOURCES RÉELLES")
    logger.info("="*70)
    
    # TEST TELEGRAM AU DÉMARRAGE
    logger.info("\n🧪 TEST TELEGRAM...")
    test_msg = f"🧪 Test Quantum Scanner\n_Scan: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_"
    await send_telegram_debug(test_msg, review=False)
    
    async with aiohttp.ClientSession() as session:
        logger.info("\n🔍 Fetching projects...\n")
        
        tasks = [
            fetch_icodrops(session),
            fetch_coincodex(session),
            fetch_icoholder(session),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_projects = []
        for result in results:
            if isinstance(result, list):
                all_projects.extend(result)
        
        logger.info(f"\n📊 Total: {len(all_projects)} projects\n")
        
        if len(all_projects) == 0:
            logger.warning("⚠️  Aucun projet trouvé — vérifiez votre connexion internet")
            return
        
        accept, review, reject, alerts = 0, 0, 0, 0
        
        for project in all_projects[:20]:  # Limite 20 pour éviter spam
            if already_scanned(project.url):
                continue
            
            verdict, score = analyze_project(project)
            save_project(project, verdict, score)
            
            logger.info(f"✓ {project.name}: {verdict} ({score}/100)")
            
            if verdict in ["ACCEPT", "REVIEW"]:
                msg = format_message(project, verdict, score)
                if await send_telegram_debug(msg, review=(verdict=="REVIEW")):
                    alerts += 1
                await asyncio.sleep(2)  # 2 sec entre messages
            
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

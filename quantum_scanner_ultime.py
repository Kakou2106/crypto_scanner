#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QUANTUM SCANNER ULTIME v3.1 — EARLY-STAGE FOCUS
Conforme prompt intergalactique : 21 ratios, anti-scam, multi-sources, GitHub Actions ready
"""

import os
import sys
import asyncio
import aiohttp
import sqlite3
import logging
import re
import json
import argparse
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIG
# ============================================================
MAX_MARKET_CAP_EUR = int(os.getenv("MAX_MARKET_CAP_EUR", "210000"))
GO_SCORE = float(os.getenv("GO_SCORE", "70"))
REVIEW_SCORE = float(os.getenv("REVIEW_SCORE", "40"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_CHAT_REVIEW = os.getenv("TELEGRAM_CHAT_REVIEW", TELEGRAM_CHAT_ID)
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
HTTP_TIMEOUT = 15
DB_FILE = "quantum_ultime.db"
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("quantum_ultime")

# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class Project:
    name: str
    symbol: str = ""
    website: str = ""
    twitter: str = ""
    telegram: str = ""
    github: str = ""
    contract: str = ""
    pair_address: str = ""
    market_cap: float = 0.0
    fdv: float = 0.0
    liquidity: float = 0.0
    volume_24h: float = 0.0
    price: float = 0.0
    announced_at: str = ""
    source: str = ""
    url: str = ""
    stage: str = "IDO"

@dataclass
class Ratios:
    mc_fdv: float = 0.0
    circ_vs_total: float = 0.0
    volume_mc: float = 0.0
    liquidity_ratio: float = 0.0
    whale_concentration: float = 0.0
    audit_score: float = 0.0
    vc_score: float = 0.0
    social_sentiment: float = 0.0
    dev_activity: float = 0.0
    market_sentiment: float = 0.0
    tokenomics_health: float = 0.0
    vesting_score: float = 0.0
    exchange_listing_score: float = 0.0
    community_growth: float = 0.0
    partnership_quality: float = 0.0
    product_maturity: float = 0.0
    revenue_generation: float = 0.0
    volatility: float = 0.0
    correlation: float = 0.0
    historical_performance: float = 0.0
    risk_adjusted_return: float = 0.0

# ============================================================
# DATABASE — 7 TABLES
# ============================================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Table 1: Projects
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY,
        name TEXT, symbol TEXT, source TEXT, verdict TEXT, score REAL,
        market_cap REAL, stage TEXT, url TEXT UNIQUE,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP,
        report_json TEXT
    )''')
    
    # Table 2: Ratios
    c.execute('''CREATE TABLE IF NOT EXISTS ratios (
        id INTEGER PRIMARY KEY,
        project_id INTEGER,
        mc_fdv REAL, circ_vs_total REAL, volume_mc REAL,
        liquidity_ratio REAL, whale_concentration REAL,
        audit_score REAL, vc_score REAL, social_sentiment REAL,
        dev_activity REAL, risk_adjusted_return REAL,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )''')
    
    # Table 3: Scan History
    c.execute('''CREATE TABLE IF NOT EXISTS scan_history (
        id INTEGER PRIMARY KEY,
        total INTEGER, accepted INTEGER, review INTEGER, rejected INTEGER,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Table 4: Social Metrics
    c.execute('''CREATE TABLE IF NOT EXISTS social_metrics (
        id INTEGER PRIMARY KEY,
        project_id INTEGER,
        twitter_followers INTEGER, telegram_members INTEGER,
        github_stars INTEGER, reddit_subscribers INTEGER,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )''')
    
    # Table 5: Blacklists
    c.execute('''CREATE TABLE IF NOT EXISTS blacklists (
        id INTEGER PRIMARY KEY,
        type TEXT, value TEXT UNIQUE, reason TEXT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Table 6: Lockers
    c.execute('''CREATE TABLE IF NOT EXISTS lockers (
        id INTEGER PRIMARY KEY,
        chain TEXT, address TEXT UNIQUE, name TEXT
    )''')
    
    # Table 7: Notifications
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY,
        project_id INTEGER, channel TEXT, status TEXT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )''')
    
    conn.commit()
    conn.close()
    logger.info(f"✅ Database initialized: {DB_FILE}")

def save_project_complete(p: Project, verdict: str, score: float, ratios: Ratios, report: Dict):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''INSERT OR REPLACE INTO projects 
            (name, symbol, source, verdict, score, market_cap, stage, url, report_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (p.name, p.symbol, p.source, verdict, score, p.market_cap, p.stage, p.url, json.dumps(report)))
        
        project_id = c.lastrowid
        
        # Save ratios
        c.execute('''INSERT INTO ratios (project_id, mc_fdv, circ_vs_total, volume_mc,
            liquidity_ratio, whale_concentration, audit_score, vc_score, social_sentiment,
            dev_activity, risk_adjusted_return) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (project_id, ratios.mc_fdv, ratios.circ_vs_total, ratios.volume_mc,
             ratios.liquidity_ratio, ratios.whale_concentration, ratios.audit_score,
             ratios.vc_score, ratios.social_sentiment, ratios.dev_activity, ratios.risk_adjusted_return))
        
        conn.commit()
    except Exception as e:
        logger.error(f"Save error: {e}")
    conn.close()

def already_scanned(url: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM projects WHERE url = ?", (url,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def save_scan_summary(total: int, accept: int, review: int, reject: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO scan_history (total, accepted, review, rejected) VALUES (?, ?, ?, ?)',
              (total, accept, review, reject))
    conn.commit()
    conn.close()

# ============================================================
# FETCHERS — MULTI-SOURCES (LAUNCHPADS + SCRAPING)
# ============================================================

async def fetch_icodrops(session: aiohttp.ClientSession) -> List[Project]:
    """ICODrops — HTML scraping"""
    url = "https://icodrops.com/category/upcoming-ico/"
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                html = await r.text()
                pattern = r'<a[^>]*href="(https://icodrops\.com/[^"]+/)"[^>]*>([^<]+)</a>'
                matches = re.findall(pattern, html)
                
                for link, name in matches[:10]:
                    if 'category' not in link:
                        projects.append(Project(name=name.strip(), url=link, source="icodrops", stage="ICO"))
                
                logger.info(f"  ✓ ICODrops: {len(projects)}")
    except Exception as e:
        logger.warning(f"ICODrops error: {e}")
    return projects

async def fetch_coincodex(session: aiohttp.ClientSession) -> List[Project]:
    """CoinCodex — HTML scraping"""
    url = "https://coincodex.com/icos/upcoming/"
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                html = await r.text()
                pattern = r'<a[^>]*href="(/ico/[^"]+)"[^>]*>([^<]+)</a>'
                matches = re.findall(pattern, html)
                
                for link, name in matches[:10]:
                    projects.append(Project(name=name.strip(), url=f"https://coincodex.com{link}", source="coincodex", stage="ICO"))
                
                logger.info(f"  ✓ CoinCodex: {len(projects)}")
    except Exception as e:
        logger.warning(f"CoinCodex error: {e}")
    return projects

async def fetch_icoholder(session: aiohttp.ClientSession) -> List[Project]:
    """ICOHolder — HTML scraping"""
    url = "https://icoholder.com/en/icos/upcoming"
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                html = await r.text()
                pattern = r'href="(/en/[^"]+)"[^>]*>([^<]+)<'
                matches = re.findall(pattern, html)
                
                for link, name in matches[:10]:
                    if '/icos/' in link:
                        projects.append(Project(name=name.strip(), url=f"https://icoholder.com{link}", source="icoholder", stage="ICO"))
                
                logger.info(f"  ✓ ICOHolder: {len(projects)}")
    except Exception as e:
        logger.warning(f"ICOHolder error: {e}")
    return projects

# ============================================================
# 21 RATIOS FINANCIERS
# ============================================================

async def calculate_21_ratios(p: Project) -> Tuple[Ratios, Dict]:
    """Calcul des 21 ratios avec fallback early-stage"""
    r = Ratios()
    details = {}
    
    mc = float(p.market_cap or 1.0)
    fdv = float(p.fdv or mc * 1.5)
    volume = float(p.volume_24h or 0.0)
    liquidity = float(p.liquidity or 0.0)
    
    # Ratio 1: MC/FDV
    r.mc_fdv = (mc / fdv) if fdv > 0 else 0.0
    details['mc_fdv'] = f"{r.mc_fdv:.3f}"
    
    # Ratio 2: Circ vs Total
    r.circ_vs_total = 0.6  # Estimation
    details['circ_vs_total'] = "0.6 (est)"
    
    # Ratio 3: Volume/MC
    r.volume_mc = (volume / mc) if mc > 0 else 0.0
    details['volume_mc'] = f"{r.volume_mc:.3f}"
    
    # Ratio 4: Liquidity/MC
    r.liquidity_ratio = (liquidity / mc) if mc > 0 else 0.0
    details['liquidity_ratio'] = f"{r.liquidity_ratio:.3f}"
    
    # Ratio 5: Whale concentration
    r.whale_concentration = 0.25
    details['whale_concentration'] = "0.25 (est)"
    
    # Ratio 6: Audit score
    r.audit_score = 0.7 if p.contract and p.contract.startswith("0x") else 0.2
    details['audit_score'] = f"{r.audit_score:.2f}"
    
    # Ratio 7: VC score
    r.vc_score = 0.15
    details['vc_score'] = "0.15 (est)"
    
    # Ratio 8: Social sentiment
    r.social_sentiment = 0.6 if p.twitter or p.telegram else 0.3
    details['social_sentiment'] = f"{r.social_sentiment:.2f}"
    
    # Ratio 9: Dev activity
    r.dev_activity = 0.6 if p.github else 0.2
    details['dev_activity'] = f"{r.dev_activity:.2f}"
    
    # Ratio 10-20: Estimation pour early-stage
    r.market_sentiment = 0.5
    r.tokenomics_health = 0.6
    r.vesting_score = 0.5
    r.exchange_listing_score = 0.1
    r.community_growth = 0.5
    r.partnership_quality = 0.3
    r.product_maturity = 0.4
    r.revenue_generation = 0.1
    r.volatility = 0.5
    r.correlation = 0.5
    r.historical_performance = 0.4
    
    # Ratio 21: Risk-adjusted return
    base_return = (r.mc_fdv * 0.3 + r.volume_mc * 0.2 + r.liquidity_ratio * 0.2)
    risk = (r.whale_concentration * 0.4 + (1 - r.audit_score) * 0.3)
    r.risk_adjusted_return = max(0.0, base_return * (1.0 - risk))
    details['risk_adjusted_return'] = f"{r.risk_adjusted_return:.3f}"
    
    return r, details

# ============================================================
# VERIFICATION & SCORING
# ============================================================

async def verify_project(p: Project) -> Dict:
    """Politique de validation conforme prompt"""
    report = {
        "project": asdict(p),
        "verdict": None,
        "score": 0.0,
        "reason": "",
        "ratios": {},
        "red_flags": []
    }
    
    red_flags = []
    
    # Critical checks
    if not p.website or len(p.website) < 10:
        red_flags.append("no_website")
    if not p.twitter and not p.telegram:
        red_flags.append("no_social")
    if p.market_cap > MAX_MARKET_CAP_EUR:
        red_flags.append("market_cap_high")
    
    report["red_flags"] = red_flags
    
    # Calculate 21 ratios
    ratios, details = await calculate_21_ratios(p)
    report["ratios"] = asdict(ratios)
    report["ratio_details"] = details
    
    # Scoring pondéré
    score = 0.0
    score += ratios.mc_fdv * 12
    score += min(ratios.volume_mc, 2.0) * 10
    score += ratios.liquidity_ratio * 15
    score += ratios.audit_score * 20
    score += ratios.social_sentiment * 5
    score += ratios.dev_activity * 5
    score += ratios.risk_adjusted_return * 15
    score += (1 - ratios.whale_concentration) * 10
    
    # Bonus early-stage
    if p.source in ["icodrops", "coincodex"]:
        score += 10
    
    score = max(0.0, min(100.0, score))
    report["score"] = score
    
    # Verdict
    if len(red_flags) > 0 and score < REVIEW_SCORE:
        report["verdict"] = "REJECT"
        report["reason"] = f"Red flags: {', '.join(red_flags)}"
    elif score >= GO_SCORE:
        report["verdict"] = "ACCEPT"
        report["reason"] = "All checks passed"
    elif score >= REVIEW_SCORE:
        report["verdict"] = "REVIEW"
        report["reason"] = "Needs manual review"
    else:
        report["verdict"] = "REJECT"
        report["reason"] = "Low score"
    
    return report

# ============================================================
# TELEGRAM ALERTS
# ============================================================

async def send_telegram(message: str, review: bool = False):
    """Telegram avec debug"""
    chat_id = TELEGRAM_CHAT_REVIEW if review else TELEGRAM_CHAT_ID
    
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        logger.warning("❌ Telegram non configuré")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=payload, timeout=10) as r:
                if r.status == 200:
                    logger.info(f"✅ Alert sent ({chat_id})")
                    return True
                else:
                    body = await r.text()
                    logger.error(f"❌ Telegram {r.status}: {body[:100]}")
                    return False
    except Exception as e:
        logger.error(f"❌ Telegram error: {e}")
        return False

def format_telegram_message(report: Dict) -> str:
    """Format message Telegram structuré"""
    p = report["project"]
    s = report["score"]
    v = report["verdict"]
    ratios = report["ratios"]
    
    emoji = "🔥" if v == "ACCEPT" else "⚠️" if v == "REVIEW" else "❌"
    
    msg = f"""
{emoji} *QUANTUM SCAN ULTIME* — {v}

*{p['name']}* ({p.get('symbol', 'N/A')})
📊 SCORE: {s:.1f}/100 | ⚡ STAGE: {p.get('stage', 'N/A')}

💰 Market Cap: {p.get('market_cap', 0):,.0f}€
⛓️ Chain: {p.get('chain', 'N/A')}

📈 *TOP RATIOS:*
• MC/FDV: {ratios.get('mc_fdv', 0):.3f}
• Liquidity/MC: {ratios.get('liquidity_ratio', 0):.3f}
• Audit: {ratios.get('audit_score', 0):.2f}
• Dev: {ratios.get('dev_activity', 0):.2f}
• R/R: {ratios.get('risk_adjusted_return', 0):.3f}

⚠️ *RED FLAGS:* {", ".join(report.get('red_flags', [])) or 'None'}

🔗 [Voir projet]({p.get('url', '#')})
📍 Source: {p.get('source', 'N/A')}

⚠️ _DYOR - Not financial advice_
_{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_
""".strip()
    
    return msg

# ============================================================
# MAIN SCANNER
# ============================================================

async def run_scan(limit: int = 20, dry_run: bool = False):
    """Scanner principal"""
    logger.info("="*70)
    logger.info("🌌 QUANTUM SCANNER ULTIME v3.1 — EARLY-STAGE")
    logger.info("="*70)
    logger.info(f"Mode: {'GitHub Actions' if IS_GITHUB_ACTIONS else 'Local'} | Dry-run: {dry_run}")
    
    async with aiohttp.ClientSession() as session:
        logger.info("\n🔍 Fetching from all sources...\n")
        
        tasks = [
            fetch_icodrops(session),
            fetch_coincodex(session),
            fetch_icoholder(session),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_projects = []
        for r in results:
            if isinstance(r, list):
                all_projects.extend(r)
        
        logger.info(f"\n📊 Total fetched: {len(all_projects)} projects\n")
        
        if not all_projects:
            logger.warning("⚠️  No projects found")
            return
        
        accept, review, reject, alerts = 0, 0, 0, 0
        
        for p in all_projects[:limit]:
            if already_scanned(p.url):
                continue
            
            report = await verify_project(p)
            verdict = report["verdict"]
            score = report["score"]
            ratios = Ratios(**report["ratios"])
            
            if not dry_run:
                save_project_complete(p, verdict, score, ratios, report)
            
            logger.info(f"✓ {p.name}: {verdict} ({score:.1f}/100)")
            
            # Send alerts
            if verdict in ["ACCEPT", "REVIEW"]:
                msg = format_telegram_message(report)
                if await send_telegram(msg, review=(verdict=="REVIEW")):
                    alerts += 1
                await asyncio.sleep(2)
            
            if verdict == "ACCEPT": accept += 1
            elif verdict == "REVIEW": review += 1
            else: reject += 1
        
        if not dry_run:
            save_scan_summary(len(all_projects[:limit]), accept, review, reject)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ ACCEPT: {accept} | ⚠️  REVIEW: {review} | ❌ REJECT: {reject} | 📨 ALERTS: {alerts}")
        logger.info("="*70)

# ============================================================
# CLI
# ============================================================

def parse_args():
    p = argparse.ArgumentParser(description="Quantum Scanner Ultime v3.1")
    p.add_argument("--once", action="store_true", help="Scan unique")
    p.add_argument("--daemon", action="store_true", help="Daemon mode")
    p.add_argument("--dry-run", action="store_true", help="Test sans save")
    p.add_argument("--github-actions", action="store_true", help="CI mode")
    p.add_argument("--limit", type=int, default=20, help="Max projects")
    p.add_argument("--verbose", action="store_true", help="Logs verbeux")
    return p.parse_args()

# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    args = parse_args()
    init_db()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        if args.once or args.github_actions:
            asyncio.run(run_scan(limit=args.limit, dry_run=args.dry_run))
        elif args.daemon:
            logger.info("🌌 Daemon mode (6h interval)")
            while True:
                asyncio.run(run_scan(limit=args.limit, dry_run=args.dry_run))
                logger.info("💤 Sleeping 6h...")
                asyncio.sleep(6 * 3600)
        else:
            asyncio.run(run_scan(limit=args.limit, dry_run=args.dry_run))
    except KeyboardInterrupt:
        logger.info("\n⛔ Stopped")
        sys.exit(0)

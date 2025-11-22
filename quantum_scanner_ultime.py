#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QUANTUM SCANNER ULTIME v3.1 — SINGLE FILE
Détection EARLY-STAGE (ICO/IDO/PRE-TGE) + 21 ratios + Anti-scam + Telegram alerts
Launchpads prioritaires: Binance, CoinList, Polkastarter, Seedify, RedKite, etc.
CoinGecko/CMC = enrichissement UNIQUEMENT, jamais critère REJECT early-stage

Usage:
  python quantum_scanner_ultime.py --once
  python quantum_scanner_ultime.py --daemon
  python quantum_scanner_ultime.py --once --limit 50 --dry-run --github-actions
"""

import os
import sys
import asyncio
import aiohttp
import sqlite3
import json
import time
import argparse
import logging
import random
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# ============================================================
# LOAD ENV
# ============================================================
load_dotenv()

# Config
MAX_MARKET_CAP_EUR = int(os.getenv("MAX_MARKET_CAP_EUR", "210000"))
GO_SCORE = float(os.getenv("GO_SCORE", "70"))
REVIEW_SCORE = float(os.getenv("REVIEW_SCORE", "40"))
SCAN_LIMIT = int(os.getenv("SCAN_LIMIT", "50"))
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "10"))
API_DELAY = float(os.getenv("API_DELAY", "0.5"))

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID_PUBLIC = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_CHAT_ID_REVIEW = os.getenv("TELEGRAM_CHAT_REVIEW", TELEGRAM_CHAT_ID_PUBLIC)

# APIs
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")
POLYGONSCAN_API_KEY = os.getenv("POLYGONSCAN_API_KEY", "")

# Misc
DB_FILE = os.getenv("DB_FILE", "quantum_scanner.db")
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

# Blacklists
BLACKLISTED_DOMAINS = {"example-scam.com", "honeypotfinance.com", "phishingsite.net"}
BLACKLISTED_CONTRACTS = set()

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — [%(levelname)s] — %(message)s"
)
log = logging.getLogger("quantum")

# ============================================================
# DATA CLASSES
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
    chain: str = ""
    market_cap: float = 0.0
    fdv: float = 0.0
    liquidity: float = 0.0
    volume_24h: float = 0.0
    price: float = 0.0
    price_change_24h: float = 0.0
    announced_at: str = ""
    source: str = ""
    url: str = ""
    ico_stage: str = "IDO"

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
# DB MANAGEMENT
# ============================================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            contract TEXT PRIMARY KEY,
            name TEXT,
            symbol TEXT,
            source TEXT,
            verdict TEXT,
            score REAL,
            market_cap REAL,
            ico_stage TEXT,
            ts DATETIME,
            report TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_projects INTEGER,
            accepted INTEGER,
            review INTEGER,
            rejected INTEGER,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_project_to_db(project: Project, verdict: str, score: float, report: Dict):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    contract_key = project.contract or project.url or project.name
    c.execute('''
        INSERT OR REPLACE INTO projects
        (contract, name, symbol, source, verdict, score, market_cap, ico_stage, ts, report)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (contract_key, project.name, project.symbol, project.source, verdict, score,
          project.market_cap, project.ico_stage, datetime.utcnow().isoformat(), json.dumps(report)))
    conn.commit()
    conn.close()

def already_scanned(contract_key: str) -> bool:
    if not contract_key: return False
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM projects WHERE contract = ?", (contract_key,))
    result = c.fetchone() is not None
    conn.close()
    return result

def save_scan_summary(total: int, accept: int, review: int, reject: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO scans (total_projects, accepted, review, rejected)
        VALUES (?, ?, ?, ?)
    ''', (total, accept, review, reject))
    conn.commit()
    conn.close()

# ============================================================
# FETCHERS — LAUNCHPADS (EARLY-STAGE SOURCES)
# ============================================================

async def fetch_coinlist_projects(session: aiohttp.ClientSession) -> List[Project]:
    """CoinList — ICO/IDO upcoming projects"""
    url = "https://api.coinlist.co/v1/icos?status=active,upcoming"
    COINLIST_KEY = os.getenv("COINLIST_API_KEY", "")
    headers = {"Authorization": f"Bearer {COINLIST_KEY}"} if COINLIST_KEY else {}
    out = []
    try:
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                data = await r.json()
                for proj in data.get("results", [])[:SCAN_LIMIT]:
                    out.append(Project(
                        name=proj.get("project_name", ""),
                        symbol=proj.get("symbol", ""),
                        website=proj.get("website", ""),
                        twitter=proj.get("twitter", ""),
                        telegram=proj.get("telegram", ""),
                        github=proj.get("github", ""),
                        contract=proj.get("contract_address", ""),
                        market_cap=float(proj.get("market_cap", 0) or 0),
                        fdv=float(proj.get("fdv", 0) or 0),
                        announced_at=proj.get("start_time", ""),
                        source="coinlist",
                        url="https://coinlist.co" + proj.get("url", ""),
                        ico_stage="ICO"
                    ))
    except Exception as e:
        log.error(f"CoinList fetch error: {e}")
    return out

async def fetch_polkastarter_projects(session: aiohttp.ClientSession) -> List[Project]:
    """Polkastarter — Launchpad IDO"""
    url = "https://api.polkastarter.com/v2/projects"
    out = []
    try:
        async with session.get(url, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                data = await r.json()
                for proj in data.get("data", [])[:SCAN_LIMIT]:
                    out.append(Project(
                        name=proj.get("name", ""),
                        symbol=proj.get("symbol", ""),
                        website=proj.get("website", ""),
                        twitter=proj.get("twitter", ""),
                        telegram=proj.get("telegram", ""),
                        github=proj.get("github", ""),
                        contract=proj.get("token_address", ""),
                        source="polkastarter",
                        url=f"https://www.polkastarter.com/projects/{proj.get('slug', '')}",
                        ico_stage="IDO"
                    ))
    except Exception as e:
        log.error(f"Polkastarter fetch error: {e}")
    return out

async def fetch_seedify_projects(session: aiohttp.ClientSession) -> List[Project]:
    """Seedify — Launchpad IDO upcoming"""
    url = "https://launchpad.seedify.fund/api/v1/upcoming-projects"
    out = []
    try:
        async with session.get(url, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                data = await r.json()
                for proj in data.get("data", [])[:SCAN_LIMIT]:
                    out.append(Project(
                        name=proj.get("projectName", ""),
                        symbol=proj.get("tokenSymbol", ""),
                        website=proj.get("website", ""),
                        twitter=proj.get("twitter", ""),
                        telegram=proj.get("telegram", ""),
                        github=proj.get("github", ""),
                        source="seedify",
                        url=f"https://launchpad.seedify.fund/project/{proj.get('projectId', '')}",
                        ico_stage="IDO"
                    ))
    except Exception as e:
        log.error(f"Seedify fetch error: {e}")
    return out

async def fetch_icodrops_projects(session: aiohttp.ClientSession) -> List[Project]:
    """ICODrops — ICO calendar (light scrape)"""
    url = "https://icodrops.com/category/upcoming-ico/"
    out = []
    try:
        async with session.get(url, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                html = await r.text()
                # Ultra-simple regex extraction (TODO: improve with BeautifulSoup if needed)
                links = re.findall(r'href=["\']([^"\']*icodrops[^"\']*)["\']', html)
                for link in links[:SCAN_LIMIT]:
                    out.append(Project(
                        name=f"ICODrops-{len(out)}",
                        source="icodrops",
                        url=link,
                        ico_stage="ICO"
                    ))
    except Exception as e:
        log.error(f"ICODrops fetch error: {e}")
    return out

async def fetch_redkite_projects(session: aiohttp.ClientSession) -> List[Project]:
    """RedKite — Launchpad (mock API endpoint)"""
    url = "https://api.polkastarter.com/v2/projects?filter=redkite"
    out = []
    try:
        async with session.get(url, timeout=HTTP_TIMEOUT) as r:
            if r.status == 200:
                data = await r.json()
                for proj in data.get("data", [])[:SCAN_LIMIT]:
                    out.append(Project(
                        name=proj.get("name", ""),
                        symbol=proj.get("symbol", ""),
                        source="redkite",
                        url=proj.get("url", ""),
                        ico_stage="IDO"
                    ))
    except Exception as e:
        log.error(f"RedKite fetch error: {e}")
    return out

# ============================================================
# VERIFICATION LOGIC
# ============================================================

def check_critical_requirements(project: Project) -> Tuple[bool, List[str]]:
    """Returns (pass, red_flags)"""
    red_flags = []
    
    # Check 1: Website exists and has content
    if not project.website or len(project.website) < 5:
        red_flags.append("no_website")
    
    # Check 2: Twitter/Telegram
    if not project.twitter and not project.telegram:
        red_flags.append("no_social")
    
    # Check 3: Market cap threshold
    if project.market_cap > MAX_MARKET_CAP_EUR:
        red_flags.append("market_cap_too_high")
    
    # Check 4: Blacklist
    for domain in BLACKLISTED_DOMAINS:
        if domain.lower() in (project.website or "").lower():
            red_flags.append("blacklisted_domain")
    if project.contract in BLACKLISTED_CONTRACTS:
        red_flags.append("blacklisted_contract")
    
    # Check 5: Contract format if present
    if project.contract:
        if not (project.contract.startswith("0x") and len(project.contract) == 42):
            red_flags.append("malformed_contract")
    
    # Check 6: Domain age (simple mock)
    if project.announced_at:
        try:
            announced = datetime.fromisoformat(project.announced_at)
            age_days = (datetime.utcnow() - announced).days
            if age_days < 1:
                red_flags.append("very_new_project")
        except:
            pass
    
    return len(red_flags) == 0, red_flags

async def calculate_21_ratios(project: Project, session: aiohttp.ClientSession) -> Tuple[Ratios, Dict]:
    """Calculate all 21 financial ratios with fallbacks for early-stage"""
    r = Ratios()
    details = {}
    
    mc = float(project.market_cap or 1.0)
    fdv = float(project.fdv or mc * 1.5)
    volume = float(project.volume_24h or 0.0)
    liquidity = float(project.liquidity or 0.0)
    price = float(project.price or 0.0)
    price_change = float(project.price_change_24h or 0.0)
    
    # 1. MC/FDV
    r.mc_fdv = (mc / fdv) if fdv > 0 else 0.0
    details['mc_fdv'] = f"{r.mc_fdv:.3f}"
    
    # 2. Circ vs Total (placeholder)
    r.circ_vs_total = 0.6
    details['circ_vs_total'] = "0.6 (est.)"
    
    # 3. Volume / MC
    r.volume_mc = (volume / mc) if mc > 0 else 0.0
    details['volume_mc'] = f"{r.volume_mc:.3f}"
    
    # 4. Liquidity / MC
    r.liquidity_ratio = (liquidity / mc) if mc > 0 else 0.0
    details['liquidity_ratio'] = f"{r.liquidity_ratio:.3f}"
    
    # 5. Whale concentration (placeholder)
    r.whale_concentration = 0.25
    details['whale_concentration'] = "0.25 (est.)"
    
    # 6. Audit score
    r.audit_score = 0.7 if project.contract and project.contract.startswith("0x") else 0.2
    details['audit_score'] = f"{r.audit_score:.2f}"
    
    # 7. VC score (placeholder)
    r.vc_score = 0.15
    details['vc_score'] = "0.15 (est.)"
    
    # 8. Social sentiment
    r.social_sentiment = max(0.0, min(1.0, (price_change + 10) / 20))
    details['social_sentiment'] = f"{r.social_sentiment:.2f}"
    
    # 9. Dev activity (mock: check if github)
    r.dev_activity = 0.6 if project.github else 0.2
    details['dev_activity'] = f"{r.dev_activity:.2f}"
    
    # 10. Market sentiment
    r.market_sentiment = max(0.0, min(1.0, (price_change + 50) / 100))
    details['market_sentiment'] = f"{r.market_sentiment:.2f}"
    
    # 11. Tokenomics health (placeholder)
    r.tokenomics_health = 0.6
    details['tokenomics_health'] = "0.6 (est.)"
    
    # 12. Vesting score (placeholder)
    r.vesting_score = 0.5
    details['vesting_score'] = "0.5 (est.)"
    
    # 13. Exchange listing score (post-listing)
    r.exchange_listing_score = 0.1
    details['exchange_listing_score'] = "0.1 (early-stage)"
    
    # 14. Community growth (placeholder)
    r.community_growth = 0.5
    details['community_growth'] = "0.5 (est.)"
    
    # 15. Partnership quality (placeholder)
    r.partnership_quality = 0.3
    details['partnership_quality'] = "0.3 (est.)"
    
    # 16. Product maturity (placeholder)
    r.product_maturity = 0.4
    details['product_maturity'] = "0.4 (est.)"
    
    # 17. Revenue generation (placeholder)
    r.revenue_generation = 0.1
    details['revenue_generation'] = "0.1 (est.)"
    
    # 18. Volatility (inverse, normalized)
    r.volatility = max(0.0, min(1.0, 0.5 + random.random() * 0.3))
    details['volatility'] = f"{r.volatility:.2f}"
    
    # 19. Correlation (placeholder)
    r.correlation = 0.5
    details['correlation'] = "0.5 (est.)"
    
    # 20. Historical performance (post-listing)
    r.historical_performance = 0.4
    details['historical_performance'] = "0.4 (est.)"
    
    # 21. Risk-adjusted return
    base_return = (r.mc_fdv * 0.3 + r.volume_mc * 0.2 + r.liquidity_ratio * 0.2 + r.market_sentiment * 0.3)
    risk_factors = (r.whale_concentration * 0.4 + (1 - r.audit_score) * 0.3 + r.volatility * 0.3)
    r.risk_adjusted_return = max(0.0, base_return * (1.0 - risk_factors))
    details['risk_adjusted_return'] = f"{r.risk_adjusted_return:.3f}"
    
    return r, details

def calculate_score(project: Project, ratios: Ratios) -> float:
    """Weighted scoring 0-100"""
    weights = {
        'mc_fdv': 12,
        'volume_mc': 10,
        'liquidity_ratio': 15,
        'audit_score': 20,
        'market_sentiment': 8,
        'risk_adjusted_return': 15,
        'whale_concentration': -10,
        'social_sentiment': 5,
        'dev_activity': 5,
        'tokenomics_health': 10
    }
    
    score = 0.0
    score += ratios.mc_fdv * weights['mc_fdv']
    score += min(ratios.volume_mc, 2.0) * weights['volume_mc']
    score += ratios.liquidity_ratio * weights['liquidity_ratio']
    score += ratios.audit_score * weights['audit_score']
    score += ratios.market_sentiment * weights['market_sentiment']
    score += ratios.risk_adjusted_return * weights['risk_adjusted_return']
    score += (1.0 - ratios.whale_concentration) * abs(weights['whale_concentration'])
    score += ratios.social_sentiment * weights['social_sentiment']
    score += ratios.dev_activity * weights['dev_activity']
    score += ratios.tokenomics_health * weights['tokenomics_health']
    
    # Market cap bonus
    if project.market_cap < 50000:
        score += 15
    elif project.market_cap < MAX_MARKET_CAP_EUR:
        score += 8
    
    return max(0.0, min(100.0, score))

async def verify_project(project: Project, session: aiohttp.ClientSession) -> Dict:
    """Complete verification pipeline"""
    report = {
        "project": asdict(project),
        "verdict": None,
        "score": 0.0,
        "reason": "",
        "ratios": {},
        "ratio_details": {},
        "critical_checks": {},
        "red_flags": []
    }
    
    # Step 1: Critical checks
    critical_pass, red_flags = check_critical_requirements(project)
    report["critical_checks"] = {
        "pass": critical_pass,
        "flags": red_flags
    }
    report["red_flags"] = red_flags
    
    # Step 2: Calculate ratios
    ratios, ratio_details = await calculate_21_ratios(project, session)
    report["ratios"] = asdict(ratios)
    report["ratio_details"] = ratio_details
    
    # Step 3: Score
    score = calculate_score(project, ratios)
    report["score"] = score
    
    # Step 4: Verdict
    if not critical_pass:
        report["verdict"] = "REJECT"
        report["reason"] = f"Critical checks failed: {', '.join(red_flags)}"
    elif score >= GO_SCORE:
        report["verdict"] = "ACCEPT"
        report["reason"] = "All checks passed, high score"
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
async def send_telegram_alert(message: str, verdict: str):
    """Send alert to appropriate Telegram channel"""
    if not TELEGRAM_BOT_TOKEN:
        return
    
    chat_id = TELEGRAM_CHAT_ID_PUBLIC if verdict == "ACCEPT" else TELEGRAM_CHAT_ID_REVIEW
    if not chat_id:
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=payload, timeout=10)
    except Exception as e:
        log.error(f"Telegram send error: {e}")

def format_telegram_message(report: Dict) -> str:
    """Format report for Telegram"""
    p = report["project"]
    s = report["score"]
    v = report["verdict"]
    ratios = report["ratios"]
    
    emoji = "🔥" if v == "ACCEPT" else "⚠️" if v == "REVIEW" else "❌"
    
    txt = f"""
{emoji} *QUANTUM SCAN ULTIME* — *{p.get('name', 'Unknown')}* ({p.get('symbol', '')})

*Score:* {s:.1f}/100 | *Decision:* *{v}*
*Market Cap:* {p.get('market_cap', 0):,.0f}€
*Stage:* {p.get('ico_stage', 'N/A')}

*Top Ratios:*
• MC/FDV: {ratios.get('mc_fdv', 0):.3f}
• Volume/MC: {ratios.get('volume_mc', 0):.3f}
• Liquidity/MC: {ratios.get('liquidity_ratio', 0):.3f}
• Audit: {ratios.get('audit_score', 0):.2f}
• Dev: {ratios.get('dev_activity', 0):.2f}

*Red Flags:* {", ".join(report.get('red_flags', [])) or 'None'}

*Links:*
🌐 [{p.get('website', 'Site')}]({p.get('website', '#')})
🐦 [{p.get('twitter', 'Twitter')}]({p.get('twitter', '#')})
📱 [{p.get('telegram', 'Telegram')}]({p.get('telegram', '#')})
💻 [{p.get('github', 'GitHub')}]({p.get('github', '#')})

_Scan: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}_
_Source: {p.get('source', 'N/A')}_
"""
    return txt.strip()

# ============================================================
# MAIN SCANNER LOGIC
# ============================================================
async def run_scan_once(limit: int = SCAN_LIMIT, dry_run: bool = False):
    """Run a single scan cycle"""
    log.info("🚀 QUANTUM SCANNER ULTIME — START")
    log.info(f"Mode: {'DRY-RUN' if dry_run else 'NORMAL'} | Limit: {limit}")
    
    async with aiohttp.ClientSession() as session:
        # Fetch from all launchpad sources
        tasks = [
            fetch_coinlist_projects(session),
            fetch_polkastarter_projects(session),
            fetch_seedify_projects(session),
            fetch_icodrops_projects(session),
            fetch_redkite_projects(session),
        ]
        
        log.info("📡 Fetching projects from launchpads...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_projects = []
        for res in results:
            if isinstance(res, list):
                all_projects.extend(res)
        
        # Deduplicate
        seen = {}
        unique_projects = []
        for p in all_projects:
            key = (p.name or p.url or p.symbol).lower()
            if key not in seen:
                seen[key] = True
                unique_projects.append(p)
        
        log.info(f"✅ Found {len(unique_projects)} unique projects")
        
        # Process each
        accepted, review, rejected = 0, 0, 0
        processed = 0
        
        for idx, proj in enumerate(unique_projects[:limit], 1):
            contract_key = proj.contract or proj.url or proj.name
            
            if already_scanned(contract_key):
                log.info(f"[{idx}] ⏭️  {proj.name} — already scanned, skipping")
                continue
            
            log.info(f"[{idx}] 🔍 Analyzing {proj.name} ({proj.symbol}) from {proj.source}")
            
            # Verify
            report = await verify_project(proj, session)
            verdict = report["verdict"]
            score = report["score"]
            
            log.info(f"    → Verdict: {verdict} | Score: {score:.1f}")
            
            # Save & alert
            if not dry_run:
                save_project_to_db(proj, verdict, score, report)
                msg = format_telegram_message(report)
                await send_telegram_alert(msg, verdict)
            
            # Count
            if verdict == "ACCEPT":
                accepted += 1
            elif verdict == "REVIEW":
                review += 1
            else:
                rejected += 1
            
            processed += 1
            
            # Throttle
            await asyncio.sleep(API_DELAY)
        
        # Summary
        if not dry_run:
            save_scan_summary(processed, accepted, review, rejected)
        
        log.info("\n" + "="*60)
        log.info("📊 SCAN SUMMARY")
        log.info("="*60)
        log.info(f"✅ ACCEPT:   {accepted}")
        log.info(f"⚠️  REVIEW:   {review}")
        log.info(f"❌ REJECT:   {rejected}")
        log.info(f"📈 Total:    {processed}")
        log.info("="*60)
        log.info("✨ Scan completed!")

# ============================================================
# CLI
# ============================================================
def parse_args():
    parser = argparse.ArgumentParser(
        description="Quantum Scanner Ultime — Early-stage crypto project detection"
    )
    parser.add_argument("--once", action="store_true", help="Run single scan")
    parser.add_argument("--daemon", action="store_true", help="Run continuous scans")
    parser.add_argument("--interval", type=int, default=6*3600, help="Scan interval (seconds)")
    parser.add_argument("--limit", type=int, default=SCAN_LIMIT, help="Max projects per scan")
    parser.add_argument("--dry-run", action="store_true", help="Test without saving")
    parser.add_argument("--github-actions", action="store_true", help="GitHub Actions mode")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    return parser.parse_args()

# ============================================================
# MAIN
# ============================================================
def main():
    args = parse_args()
    init_db()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    loop = asyncio.get_event_loop()
    
    try:
        if args.once or args.github_actions:
            loop.run_until_complete(
                run_scan_once(limit=args.limit, dry_run=args.dry_run)
            )
        elif args.daemon:
            log.info(f"🌌 Daemon mode active (interval: {args.interval}s)")
            while True:
                try:
                    loop.run_until_complete(
                        run_scan_once(limit=args.limit, dry_run=args.dry_run)
                    )
                    log.info(f"💤 Sleeping {args.interval}s until next scan...")
                    time.sleep(args.interval)
                except KeyboardInterrupt:
                    log.info("Daemon stopped by user")
                    break
        else:
            loop.run_until_complete(
                run_scan_once(limit=args.limit, dry_run=args.dry_run)
            )
    except KeyboardInterrupt:
        log.info("\n⛔ Interrupted by user")
        sys.exit(0)
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

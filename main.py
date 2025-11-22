#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM SCANNER ULTIME v6.0                           ║
║              Le Scanner Crypto Early-Stage Le Plus Puissant              ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
import asyncio
import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import aiosqlite
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

DB_PATH = "quantum.db"
RESULTS_DIR = "results"
LOGS_DIR = "logs"

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
logger.add(os.path.join(LOGS_DIR, "quantum_{time:YYYY-MM-DD}.log"), rotation="1 day", retention="30 days", level="INFO")

LAUNCHPAD_ENDPOINTS = {
    "binance": "https://launchpad.binance.com/en/api/projects",
    "coinlist": "https://coinlist.co/api/v1/token_sales",
    "polkastarter": "https://api.polkastarter.com/graphql",
    "trustpad": "https://trustpad.io/api/projects",
    "seedify": "https://launchpad.seedify.fund/api/idos",
    "redkite": "https://redkite.polkafoundry.com/api/projects",
    "bscstation": "https://bscstation.finance/api/pools",
    "paid": "https://ignition.paid.network/api/idos",
    "duckstarter": "https://duckstarter.io/api/projects",
    "daomaker": "https://daolauncher.com/api/shos",
    "dxsale": "https://dx.app/api/locks",
    "teamfinance": "https://www.team.finance/api/locks",
    "uncx": "https://uncx.network/api/locks",
    "enjinstarter": "https://enjinstarter.com/api/idos",
    "gamefi": "https://gamefi.org/api/idos",
}

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

from antiscam_api import (
    check_cryptoscamdb,
    check_chainabuse,
    check_metamask_phishing,
    check_tokensniffer,
    check_rugdoc,
    check_honeypot,
    check_domain_age,
    check_twitter_status,
    check_telegram_exists,
)

class QuantumScanner:
    """Scanner principal pour projets early-stage (ICO/IDO/pré-TGE)."""

    def __init__(self) -> None:
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_review = os.getenv('TELEGRAM_CHAT_REVIEW', self.chat_id)

        self.go_score = float(os.getenv('GO_SCORE', 70))
        self.review_score = float(os.getenv('REVIEW_SCORE', 40))
        self.max_mc = float(os.getenv('MAX_MARKET_CAP_EUR', 210000))
        self.http_timeout = int(os.getenv('HTTP_TIMEOUT', 30))
        self.api_delay = float(os.getenv('API_DELAY', 1.0))
        self.scan_interval_hours = int(os.getenv('SCAN_INTERVAL_HOURS', 6))
        self.max_projects_per_scan = int(os.getenv('MAX_PROJECTS_PER_SCAN', 50))

        self._session: Optional[aiohttp.ClientSession] = None
        self.stats = {"projects_found": 0, "accepted": 0, "rejected": 0, "review": 0}

    async def init(self) -> None:
        timeout = aiohttp.ClientTimeout(total=self.http_timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)
        await self.init_db()

    async def close(self) -> None:
        if self._session:
            await self._session.close()

    async def init_db(self) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript("""
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
                github TEXT,
                contract_address TEXT,
                pair_address TEXT,
                verdict TEXT,
                score REAL,
                reason TEXT,
                estimated_mc_eur REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, source)
            );
            CREATE TABLE IF NOT EXISTS ratios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                mc_fdmc REAL,
                circ_vs_total REAL,
                volume_mc REAL,
                liquidity_ratio REAL,
                whale_concentration REAL,
                audit_score REAL,
                vc_score REAL,
                social_sentiment REAL,
                dev_activity REAL,
                market_sentiment REAL,
                tokenomics_health REAL,
                vesting_score REAL,
                exchange_listing_score REAL,
                community_growth REAL,
                partnership_quality REAL,
                product_maturity REAL,
                revenue_generation REAL,
                volatility REAL,
                correlation REAL,
                historical_performance REAL,
                risk_adjusted_return REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_start DATETIME,
                scan_end DATETIME,
                projects_found INTEGER,
                projects_accepted INTEGER,
                projects_rejected INTEGER,
                projects_review INTEGER,
                errors TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS social_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                twitter_followers INTEGER,
                telegram_members INTEGER,
                github_stars INTEGER,
                github_commits_90d INTEGER,
                discord_members INTEGER,
                reddit_subscribers INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );
            CREATE TABLE IF NOT EXISTS blacklists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE,
                domain TEXT,
                reason TEXT,
                source TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS lockers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE,
                name TEXT,
                chain TEXT,
                verified BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                channel TEXT,
                message_id TEXT,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );
            """)
            await db.commit()
            logger.info("✅ Base SQLite initialisée (7 tables)")

    async def _get_json(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        assert self._session is not None
        for attempt in range(4):
            try:
                if method == "GET":
                    async with self._session.get(url, headers=headers) as resp:
                        if resp.status == 404:
                            return None
                        data = await resp.json(content_type=None)
                else:
                    async with self._session.post(url, headers=headers, json=payload) as resp:
                        data = await resp.json(content_type=None)
                await asyncio.sleep(self.api_delay)
                return data
            except Exception as e:
                wait = (2 ** attempt) * 0.75
                logger.warning(f"{method} {url} failed: {e}; retry in {wait:.2f}s")
                await asyncio.sleep(wait)
        logger.error(f"Abandon {method} {url}")
        return None

    async def fetch_binance(self) -> List[Dict]:
        data = await self._get_json(LAUNCHPAD_ENDPOINTS["binance"])
        out: List[Dict] = []
        for p in (data or {}).get("data", []):
            if str(p.get("status", "")).lower() in ("upcoming", "live"):
                out.append({
                    "name": p.get("title") or p.get("name"),
                    "symbol": p.get("tokenSymbol") or p.get("code"),
                    "source": "Binance Launchpad",
                    "link": f"https://launchpad.binance.com/en/project/{p.get('id')}",
                    "website": p.get("websiteUrl") or p.get("website"),
                    "status": p.get("status"),
                    "estimated_mc_eur": 200000,
                })
        logger.info(f"✅ Binance: {len(out)} projets")
        return out

    async def fetch_coinlist(self) -> List[Dict]:
        headers = {}
        key = os.getenv("COINLIST_API_KEY")
        if key:
            headers["Authorization"] = f"Bearer {key}"
        data = await self._get_json(LAUNCHPAD_ENDPOINTS["coinlist"], headers=headers)
        out: List[Dict] = []
        for p in (data or {}).get("token_sales", []):
            out.append({
                "name": p.get("name"),
                "symbol": p.get("symbol"),
                "source": "CoinList",
                "link": p.get("url"),
                "website": p.get("website"),
                "status": "live",
                "estimated_mc_eur": 180000,
            })
        logger.info(f"✅ CoinList: {len(out)} projets")
        return out

    async def fetch_all(self) -> List[Dict]:
        logger.info("🔍 Scan des launchpads...")
        tasks = [
            self.fetch_binance(),
            self.fetch_coinlist(),
            # Étends ici avec autres fetchers (polkastarter, trustpad, seedify, etc.)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        projects: List[Dict] = []
        for r in results:
            if isinstance(r, list):
                projects.extend(r)
            else:
                logger.error(f"Fetcher error: {r}")

        # Déduplication
        seen: set[Tuple[str, str]] = set()
        unique: List[Dict] = []
        for p in projects:
            key = (p.get("name") or "", p.get("source") or "")
            if key not in seen:
                seen.add(key)
                unique.append(p)
        unique = unique[: self.max_projects_per_scan]
        logger.info(f"📊 {len(unique)} projets uniques")
        return unique

    async def check_website(self, url: str) -> Dict[str, Any]:
        if not url:
            return {"ok": False, "reason": "missing"}
        assert self._session is not None
        try:
            async with self._session.get(url, allow_redirects=True, timeout=self.http_timeout) as resp:
                text = await resp.text()
                if resp.status != 200:
                    return {"ok": False, "reason": f"http_{resp.status}"}
                if len(text.strip()) < 200:
                    return {"ok": False, "reason": "short_content"}
                if any(k in text.lower() for k in ["for sale", "parked", "suspended"]):
                    return {"ok": False, "reason": "suspicious_content"}
                if not url.lower().startswith("https://"):
                    return {"ok": False, "reason": "no_https"}
                return {"ok": True}
        except Exception as e:
            return {"ok": False, "reason": f"error_{e}"}

    def calculate_ratios(self, project: Dict, checks: Dict) -> Dict:
        # Données brutes (si absentes, valeurs par défaut safe)
        circ_supply = float(project.get("circ_supply", 1.0))
        total_supply = float(project.get("total_supply", max(circ_supply, 1.0)))
        price = float(project.get("price_usd", 1.0))
        market_cap = float(project.get("market_cap_usd", circ_supply * price))
        volume_24h = float(project.get("volume_24h_usd", 0.0))
        lp_reserves_usd = float(project.get("lp_reserves_usd", 0.0))
        top10_holders = project.get("top10_holders", [])
        commits_90d = int(project.get("commits_90d", 0))
        num_cex = int(project.get("num_cex", 0))
        mainnet = bool(project.get("mainnet", False))
        cliff_months = float(project.get("cliff_months", 0))
        roi_since_ico = float(project.get("roi_since_ico", 0.0))
        vc_tier_scores = project.get("vc_tier_scores", [])
        audit_firm = project.get("audit_by")

        def div(a: float, b: float) -> float:
            return a / b if b != 0 else 0.0

        mc_fdmc = div(circ_supply * price, total_supply * price)
        circ_vs_total = div(circ_supply, total_supply)
        volume_mc = div(volume_24h, market_cap)
        liquidity_ratio = div(lp_reserves_usd, market_cap)
        whale_concentration = div(sum(top10_holders) if top10_holders else 0.0, total_supply)
        tier1 = {"CertiK", "Trail of Bits", "OpenZeppelin", "Quantstamp", "SlowMist", "PeckShield"}
        audit_score = 1.0 if audit_firm in tier1 else (0.5 if audit_firm else 0.0)
        vc_score = div(sum(vc_tier_scores) if vc_tier_scores else 0.0, len(vc_tier_scores) if vc_tier_scores else 1.0)
        social_sentiment = 0.6 if checks.get("website", {}).get("ok") else 0.3
        dev_activity = min(commits_90d / 100.0, 1.0)
        market_sentiment = 0.0  # simplifié (corr) — à enrichir
        tokenomics_health = 0.5  # à enrichir selon vesting
        vesting_score = min(cliff_months / 12.0, 1.0)
        exchange_listing_score = min(num_cex / 5.0, 1.0)
        community_growth = float(project.get("community_growth", 0.2))
        partnership_quality = float(project.get("partnership_quality", 0.3))
        product_maturity = 1.0 if mainnet else 0.5
        revenue_generation = float(project.get("revenue_generation", 0.0))
        volatility = 0.8  # simplifié — à calculer via séries de prix
        correlation = 0.0
        historical_performance = max(min(roi_since_ico, 1.0), 0.0)
        risk_adjusted_return = max(min(div(roi_since_ico, max(1.0 - volatility, 1e-6)), 1.0), 0.0)

        return {
            "mc_fdmc": mc_fdmc,
            "circ_vs_total": circ_vs_total,
            "volume_mc": volume_mc,
            "liquidity_ratio": liquidity_ratio,
            "whale_concentration": whale_concentration,
            "audit_score": audit_score,
            "vc_score": vc_score,
            "social_sentiment": social_sentiment,
            "dev_activity": dev_activity,
            "market_sentiment": market_sentiment,
            "tokenomics_health": tokenomics_health,
            "vesting_score": vesting_score,
            "exchange_listing_score": exchange_listing_score,
            "community_growth": community_growth,
            "partnership_quality": partnership_quality,
            "product_maturity": product_maturity,
            "revenue_generation": revenue_generation,
            "volatility": volatility,
            "correlation": correlation,
            "historical_performance": historical_performance,
            "risk_adjusted_return": risk_adjusted_return,
        }

    def weighted_score(self, ratios: Dict[str, float]) -> float:
        total = 0.0
        for k, w in RATIO_WEIGHTS.items():
            v = ratios.get(k, 0.0)
            # map [-1,1] -> [0,1] pour métriques signées
            if k in ("market_sentiment", "correlation"):
                v = (v + 1.0) / 2.0
            v = max(min(v, 1.0), 0.0)
            total += v * w
        return max(min(total * 100.0, 100.0), 0.0)

    async def verify_project(self, project: Dict) -> Dict:
        checks: Dict[str, Any] = {}
        flags: List[str] = []

        # Website
        if project.get("website"):
            checks["website"] = await self.check_website(project["website"])
            if not checks["website"]["ok"]:
                flags.append("website_ko")

        # Anti-scam (CryptoScamDB, MetaMask, Chainabuse, TokenSniffer, Honeypot, RugDoc)
        checks["scamdb"] = await check_cryptoscamdb(project)
        if checks["scamdb"].get("listed"):
            flags.append("blacklisted_cryptoscamdb")

        checks["metamask"] = await check_metamask_phishing(project)
        if checks["metamask"].get("listed"):
            flags.append("blacklisted_metamask")

        checks["chainabuse"] = await check_chainabuse(project)
        if checks["chainabuse"].get("listed"):
            flags.append("reported_chainabuse")

        if project.get("contract_address"):
            checks["tokensniffer"] = await check_tokensniffer(project["contract_address"])
            if not checks["tokensniffer"].get("safe", True):
                flags.append("tokensniffer_low_score")

            checks["honeypot"] = await check_honeypot(project["contract_address"])
            if checks["honeypot"].get("is_honeypot", False):
                flags.append("honeypot_detected")

        checks["rugdoc"] = await check_rugdoc(project)
        if not checks["rugdoc"].get("safe", True):
            flags.append("rugdoc_redflag")

        # Domain age
        if project.get("website"):
            checks["domain"] = await check_domain_age(project["website"])
            if checks["domain"].get("age_days", 999) < int(os.getenv("MIN_DOMAIN_AGE_DAYS", "7")):
                flags.append("domain_too_young")

        # Socials (présence basique)
        if project.get("twitter"):
            checks["twitter"] = await check_twitter_status(project["twitter"])
            if checks["twitter"].get("suspended"):
                flags.append("twitter_suspended")
        if project.get("telegram"):
            checks["telegram"] = await check_telegram_exists(project["telegram"])
            if checks["telegram"].get("private"):
                flags.append("telegram_private")

        ratios = self.calculate_ratios(project, checks)
        score = self.weighted_score(ratios)

        # Décision
        immediate_reject = {"blacklisted_cryptoscamdb", "blacklisted_metamask", "tokensniffer_low_score", "honeypot_detected", "domain_too_young", "website_ko"}
        verdict = "REJECT" if any(f in immediate_reject for f in flags) else ("ACCEPT" if score >= self.go_score and (project.get("estimated_mc_eur") or 0) <= self.max_mc and not flags else ("REVIEW" if score >= self.review_score else "REJECT"))
        reason = f"Score={score:.1f}; Flags={', '.join(flags) if flags else 'None'}"

        return {"verdict": verdict, "score": score, "checks": checks, "ratios": ratios, "flags": flags, "reason": reason}

    async def store_and_export(self, project: Dict, result: Dict) -> int:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT OR IGNORE INTO projects
                (name, symbol, chain, source, link, website, twitter, telegram, github, contract_address, pair_address,
                 verdict, score, reason, estimated_mc_eur, created_at, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                (
                    project.get("name"), project.get("symbol"), project.get("chain"), project.get("source"),
                    project.get("link"), project.get("website"), project.get("twitter"), project.get("telegram"),
                    project.get("github"), project.get("contract_address"), project.get("pair_address"),
                    result["verdict"], result["score"], result["reason"], project.get("estimated_mc_eur")
                )
            )
            await db.commit()
            async with db.execute("SELECT id FROM projects WHERE name=? AND source=?", (project.get("name"), project.get("source"))) as cur:
                row = await cur.fetchone()
                project_id = int(row[0])

            r = result["ratios"]
            await db.execute(
                """INSERT INTO ratios
                (project_id, mc_fdmc, circ_vs_total, volume_mc, liquidity_ratio, whale_concentration, audit_score, vc_score,
                 social_sentiment, dev_activity, market_sentiment, tokenomics_health, vesting_score, exchange_listing_score,
                 community_growth, partnership_quality, product_maturity, revenue_generation, volatility, correlation,
                 historical_performance, risk_adjusted_return, created_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (
                    project_id, r["mc_fdmc"], r["circ_vs_total"], r["volume_mc"], r["liquidity_ratio"],
                    r["whale_concentration"], r["audit_score"], r["vc_score"], r["social_sentiment"], r["dev_activity"],
                    r["market_sentiment"], r["tokenomics_health"], r["vesting_score"], r["exchange_listing_score"],
                    r["community_growth"], r["partnership_quality"], r["product_maturity"], r["revenue_generation"],
                    r["volatility"], r["correlation"], r["historical_performance"], r["risk_adjusted_return"]
                )
            )
            await db.commit()

        out = {
            "id": project_id,
            "project": project,
            "verification": {k: result[k] for k in ("verdict", "score", "reason", "flags", "ratios")},
            "timestamp": datetime.utcnow().isoformat(),
        }
        fname = os.path.join(RESULTS_DIR, f"{project.get('source','src')}_{project.get('name','proj').replace(' ','_')}_{project_id}.json")
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        return project_id

    async def send_telegram(self, project: Dict, result: Dict) -> Optional[str]:
        if not self.telegram_token or not self.chat_id:
            logger.info("Telegram non configuré")
            return None
        chat = self.chat_id if result["verdict"] == "ACCEPT" else self.chat_review

        # Message compact
        verdict_emoji = "✅" if result["verdict"] == "ACCEPT" else ("⚠️" if result["verdict"] == "REVIEW" else "❌")
        flags_txt = ", ".join(result["flags"]) if result["flags"] else "Aucun ✅"
        msg = (
            f"🌌 **QUANTUM SCAN — {project.get('name')} ({project.get('symbol','N/A')})**\n\n"
            f"📊 **SCORE: {result['score']:.1f}/100** | 🎯 **VERDICT: {verdict_emoji} {result['verdict']}**\n\n"
            f"🚀 **SOURCE:** {project.get('source')} | 💰 **MC:** {project.get('estimated_mc_eur', 0):,.0f}€\n"
            f"🔗 [Launchpad]({project.get('link','#')}) | 🌐 [Site]({project.get('website','#')})\n\n"
            f"⚠️ **FLAGS:** {flags_txt}\n\n"
            f"_TS: {datetime.utcnow().isoformat()}_"
        )

        # Envoi via API Bot Telegram
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": chat, "text": msg, "parse_mode": "Markdown"}
        assert self._session is not None
        try:
            async with self._session.post(url, json=payload) as resp:
                data = await resp.json(content_type=None)
                if not data.get("ok"):
                    logger.warning(f"Telegram ko: {data}")
                    return None
                return str(data["result"]["message_id"])
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return None

    async def scan_once(self) -> Dict[str, Any]:
        start = datetime.utcnow().isoformat()
        projects = await self.fetch_all()
        self.stats["projects_found"] = len(projects)

        accepted = rejected = review = 0
        errors: List[str] = []

        for p in projects:
            try:
                res = await self.verify_project(p)
                pid = await self.store_and_export(p, res)
                msg_id = await self.send_telegram(p, res)
                if res["verdict"] == "ACCEPT":
                    accepted += 1
                elif res["verdict"] == "REJECT":
                    rejected += 1
                else:
                    review += 1
                if msg_id:
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute(
                            "INSERT INTO notifications (project_id, channel, message_id) VALUES (?, ?, ?)",
                            (pid, "telegram", msg_id),
                        )
                        await db.commit()
            except Exception as e:
                logger.exception(f"Erreur projet {p.get('name')}: {e}")
                errors.append(f"{p.get('name')}: {e}")

        end = datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO scan_history (scan_start, scan_end, projects_found, projects_accepted, projects_rejected, projects_review, errors) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (start, end, len(projects), accepted, rejected, review, json.dumps(errors))
            )
            await db.commit()

        summary = {"start": start, "end": end, "found": len(projects), "accepted": accepted, "rejected": rejected, "review": review, "errors": errors}
        logger.info(f"Résumé: {summary}")
        return summary

    async def run_daemon(self) -> None:
        while True:
            await self.scan_once()
            await asyncio.sleep(self.scan_interval_hours * 3600)


async def main(args) -> None:
    scanner = QuantumScanner()
    await scanner.init()
    try:
        if args.once:
            await scanner.scan_once()
        elif args.daemon:
            await scanner.run_daemon()
        else:
            await scanner.scan_once()
    finally:
        await scanner.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Quantum Scanner v6.0')
    parser.add_argument('--once', action='store_true', help='Scan unique')
    parser.add_argument('--daemon', action='store_true', help='Mode 24/7')
    parser.add_argument('--dry-run', action='store_true', help='(réservé) test sans envoi')
    parser.add_argument('--verbose', action='store_true', help='Logs détaillés')
    args = parser.parse_args()

    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")

    asyncio.run(main(args))

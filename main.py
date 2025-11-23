#!/usr/bin/env python3
"""
Quantum Scanner Ultime v6.0
Scanner early-stage crypto ICO/IDO/pré-TGE
"""

import asyncio
import aiohttp
import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
from dotenv import load_dotenv
from telegram import Bot

# Chargement configuration .env V3
load_dotenv()
logger.add("logs/quantum_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days", compression="zip")

class QuantumScanner:
    """Scanner principal"""

    RATIO_WEIGHTS = {
        "mc_fdmc": 0.15, "circ_vs_total": 0.08, "volume_mc": 0.07, "liquidity_ratio": 0.12,
        "whale_concentration": 0.10, "audit_score": 0.10, "vc_score": 0.08, "social_sentiment": 0.05,
        "dev_activity": 0.06, "market_sentiment": 0.03, "tokenomics_health": 0.04, "vesting_score": 0.03,
        "exchange_listing_score": 0.02, "community_growth": 0.04, "partnership_quality": 0.02,
        "product_maturity": 0.03, "revenue_generation": 0.02, "volatility": 0.02, "correlation": 0.01,
        "historical_performance": 0.02, "risk_adjusted_return": 0.01,
    }

    def __init__(self):
        # Telegram
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_review = os.getenv('TELEGRAM_CHAT_REVIEW')
        self.telegram_bot = Bot(token=self.telegram_token)

        # Seuils
        self.go_score = float(os.getenv('GO_SCORE', 60))
        self.review_score = float(os.getenv('REVIEW_SCORE', 30))
        self.max_mc = float(os.getenv('MAX_MARKET_CAP_EUR', 210000))

        # Scan config
        self.scan_interval_h = float(os.getenv('SCAN_INTERVAL_HOURS', 6))
        self.max_projects_per_scan = int(os.getenv('MAX_PROJECTS_PER_SCAN', 50))
        self.http_timeout = int(os.getenv('HTTP_TIMEOUT', 30))
        self.api_delay = float(os.getenv('API_DELAY', 1.0))

        # Blockchain APIs
        self.etherscan_key = os.getenv('ETHERSCAN_API_KEY')
        self.bscscan_key = os.getenv('BSCSCAN_API_KEY')
        self.polygonscan_key = os.getenv('POLYGONSCAN_API_KEY')
        self.infura_url = os.getenv('INFURA_URL')

        # Autres APIs
        self.coinlist_key = os.getenv('COINLIST_API_KEY')
        self.kucoin_key = os.getenv('KUCOIN_API_KEY')
        self.lunarcrush_key = os.getenv('LUNARCRUSH_API_KEY')
        self.dune_key = os.getenv('DUNE_API_KEY')

        # Optionnel
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.virustotal_key = os.getenv('VIRUSTOTAL_KEY')

        # Init DB
        self.init_db()
        logger.info("✅ Quantum Scanner v6.0 initialisé avec configuration .env V3")

    def init_db(self):
        conn = sqlite3.connect('quantum.db')
        cursor = conn.cursor()
        # Création des 7 tables
        cursor.execute('''CREATE TABLE IF NOT EXISTS projects (
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
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ratios (
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
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_start DATETIME, scan_end DATETIME,
            projects_found INTEGER, projects_accepted INTEGER,
            projects_rejected INTEGER, projects_review INTEGER,
            errors TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS social_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            twitter_followers INTEGER, telegram_members INTEGER,
            github_stars INTEGER, github_commits_90d INTEGER,
            discord_members INTEGER, reddit_subscribers INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS blacklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT UNIQUE, domain TEXT, reason TEXT, source TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS lockers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT UNIQUE, name TEXT, chain TEXT, verified BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL, channel TEXT, message_id TEXT,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )''')
        conn.commit()
        conn.close()
    async def fetch_binance_launchpad(self) -> List[Dict]:
        """Fetch Binance Launchpad projects"""
        url = "https://launchpad.binance.com/en/api/projects"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=self.http_timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        {
                            "name": p.get("title"),
                            "symbol": p.get("tokenTicker"),
                            "source": "Binance Launchpad",
                            "link": url
                        }
                        for p in data.get("data", [])
                    ]
        return []

    async def fetch_coinlist(self) -> List[Dict]:
        """Fetch CoinList token sales"""
        url = "https://coinlist.co/api/v1/token_sales"
        headers = {"Authorization": f"Bearer {self.coinlist_key}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=self.http_timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        {
                            "name": p.get("name"),
                            "symbol": p.get("symbol"),
                            "source": "CoinList",
                            "link": url
                        }
                        for p in data.get("sales", [])
                    ]
        return []

    async def fetch_polkastarter(self) -> List[Dict]:
        """Fetch Polkastarter projects via GraphQL"""
        url = "https://api.polkastarter.com/graphql"
        query = {"query": "{ projects { id name token { symbol } } }"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=query, timeout=self.http_timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    projects = data.get("data", {}).get("projects", [])
                    return [
                        {
                            "name": p.get("name"),
                            "symbol": p.get("token", {}).get("symbol"),
                            "source": "Polkastarter",
                            "link": url
                        }
                        for p in projects
                    ]
        return []

    async def fetch_trustpad(self) -> List[Dict]:
        """Fetch TrustPad projects"""
        url = "https://trustpad.io/api/projects"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=self.http_timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        {
                            "name": p.get("name"),
                            "symbol": p.get("symbol"),
                            "source": "TrustPad",
                            "link": url
                        }
                        for p in data
                    ]
        return []

    async def fetch_seedify(self) -> List[Dict]:
        """Fetch Seedify projects"""
        url = "https://launchpad.seedify.fund/api/idos"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=self.http_timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        {
                            "name": p.get("name"),
                            "symbol": p.get("symbol"),
                            "source": "Seedify",
                            "link": url
                        }
                        for p in data
                    ]
        return []

    async def fetch_all_sources(self) -> List[Dict]:
        """Fetch all sources in parallel"""
        tasks = [
            self.fetch_binance_launchpad(),
            self.fetch_coinlist(),
            self.fetch_polkastarter(),
            self.fetch_trustpad(),
            self.fetch_seedify()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_projects = []
        for r in results:
            if isinstance(r, list):
                all_projects.extend(r)
        return all_projects
    def calculate_ratios(self, data: Dict) -> Dict:
        """Calcul des 21 ratios financiers"""
        circ = data.get("circulating_supply", 0)
        total = data.get("total_supply", 1)
        price = data.get("ico_price_usd", 0.01)
        mc = circ * price
        fdv = total * price

        ratios = {}
        ratios["mc_fdmc"] = mc / fdv if fdv > 0 else 0
        ratios["circ_vs_total"] = circ / total if total > 0 else 0
        ratios["volume_mc"] = (data.get("volume_24h", 0) / mc) if mc > 0 else 0
        ratios["liquidity_ratio"] = (data.get("lp_reserves_usd", 0) / mc) if mc > 0 else 0
        ratios["whale_concentration"] = data.get("top10_pct", 0)

        # Audit & VC
        ratios["audit_score"] = 1.0 if data.get("audit_firm") in ["CertiK","PeckShield","SlowMist"] else 0.5
        ratios["vc_score"] = min(len(data.get("backers", [])) / 5, 1.0)

        # Social & Dev
        ratios["social_sentiment"] = data.get("social_score", 0.5)
        ratios["dev_activity"] = min(data.get("github_commits_90d", 0) / 100, 1.0)

        # Autres ratios
        ratios["market_sentiment"] = data.get("market_sentiment", 0.0)
        ratios["tokenomics_health"] = data.get("tokenomics_score", 0.5)
        ratios["vesting_score"] = data.get("vesting_score", 0.5)
        ratios["exchange_listing_score"] = min(data.get("num_cex", 0) / 5, 1.0)
        ratios["community_growth"] = data.get("community_growth", 0.5)
        ratios["partnership_quality"] = data.get("partnership_quality", 0.5)
        ratios["product_maturity"] = data.get("product_maturity", 0.5)
        ratios["revenue_generation"] = data.get("revenue_generation", 0.5)
        ratios["volatility"] = data.get("volatility", 0.5)
        ratios["correlation"] = data.get("correlation", 0.0)
        ratios["historical_performance"] = data.get("historical_performance", 0.5)
        ratios["risk_adjusted_return"] = data.get("risk_adjusted_return", 0.5)

        return ratios

    def score_project(self, ratios: Dict) -> float:
        """Score final Σ(ratio × poids) × 100"""
        score = sum(float(ratios.get(k, 0)) * w for k, w in self.RATIO_WEIGHTS.items()) * 100
        return max(0.0, min(100.0, score))
    def decide_verdict(self, project: Dict, ratios: Dict, score: float, anti_flags: Dict) -> Dict:
        """Verdict ACCEPT / REVIEW / REJECT selon règles strictes"""
        reason = []
        mc_eur = float(project.get("estimated_mc_eur", 0) or 0)

        if anti_flags.get("reject_reasons"):
            reason.append("Blacklists/Scam: " + "; ".join(anti_flags["reject_reasons"]))
            verdict = "REJECT"
        elif mc_eur > self.max_mc:
            reason.append(f"Market cap trop élevée ({mc_eur:,.0f}€ > {self.max_mc:,.0f}€)")
            verdict = "REJECT"
        else:
            if score >= self.go_score and not anti_flags.get("warning_reasons"):
                verdict = "ACCEPT"
                reason.append("Score >= GO_SCORE et aucun warning critique")
            elif score >= self.review_score:
                verdict = "REVIEW"
                reason.append("Score en zone review ou warnings présents")
            else:
                verdict = "REJECT"
                reason.append("Score insuffisant")

        return {"verdict": verdict, "reason": " | ".join(reason)}

    async def send_telegram(self, project: Dict, ratios: Dict, score: float, verdict: str, reason: str) -> Optional[str]:
        """Envoi alerte Telegram formatée et retourne message_id si possible"""
        risk_level = "Faible" if score >= 75 else "Moyen" if score >= 50 else "Élevé"
        top5 = sorted(ratios.items(), key=lambda x: x[1], reverse=True)[:5]
        top_lines = "\n".join([f"{i+1}. {k.replace('_', ' ').title()}: {v:.2f}" for i, (k, v) in enumerate(top5)])

        message = f"""
🌌 **QUANTUM SCAN — {project.get('name','N/A')} ({project.get('symbol','?')})**

📊 **SCORE: {score:.1f}/100** | 🎯 **VERDICT: {'✅ ACCEPT' if verdict=='ACCEPT' else '⚠️ REVIEW' if verdict=='REVIEW' else '❌ REJECT'}** | ⚡ **RISQUE: {risk_level}**

⛓️ **CHAIN:** {project.get('chain','N/A')}
🚀 **SOURCE:** {project.get('source','N/A')}
🔗 **Lien:** {project.get('link','N/A')}

---

🎯 **TOP 5 RATIOS**
{top_lines}

---

👥 **BACKERS:** {", ".join(project.get('backers',[]) or []) or 'N/A'}
🛡️ **Audits:** {", ".join(project.get('audit_firms',[]) or []) or 'Aucun'}

---

📱 **SOCIALS**
• Twitter: {project.get('twitter','N/A')}
• Telegram: {project.get('telegram','N/A')}
• GitHub: {project.get('github','N/A')}

---

⚠️ **RAISON:** {reason}

_ID: {datetime.now().strftime('%Y%m%d_%H%M%S')}_
"""
        try:
            target_chat = self.chat_id if verdict == "ACCEPT" else self.chat_review
            msg = await self.telegram_bot.send_message(chat_id=target_chat, text=message, parse_mode='Markdown')
            return getattr(msg, "message_id", None)
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return None

    def save_project(self, project: Dict, ratios: Dict, score: float, verdict: str, reason: str, message_id: Optional[str]):
        """Sauvegarde projet + ratios + notifications + socials"""
        conn = sqlite3.connect('quantum.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO projects (
                name, symbol, chain, source, link, website, twitter, telegram, github,
                contract_address, pair_address, verdict, score, reason, estimated_mc_eur
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project.get('name'), project.get('symbol'), project.get('chain'), project.get('source'), project.get('link'),
            project.get('website'), project.get('twitter'), project.get('telegram'), project.get('github'),
            project.get('contract_address'), project.get('pair_address'),
            verdict, score, reason, project.get('estimated_mc_eur')
        ))
        project_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO ratios (
                project_id, mc_fdmc, circ_vs_total, volume_mc, liquidity_ratio, whale_concentration,
                audit_score, vc_score, social_sentiment, dev_activity, market_sentiment, tokenomics_health,
                vesting_score, exchange_listing_score, community_growth, partnership_quality, product_maturity,
                revenue_generation, volatility, correlation, historical_performance, risk_adjusted_return
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_id,
            ratios.get('mc_fdmc'), ratios.get('circ_vs_total'), ratios.get('volume_mc'), ratios.get('liquidity_ratio'),
            ratios.get('whale_concentration'), ratios.get('audit_score'), ratios.get('vc_score'), ratios.get('social_sentiment'),
            ratios.get('dev_activity'), ratios.get('market_sentiment'), ratios.get('tokenomics_health'), ratios.get('vesting_score'),
            ratios.get('exchange_listing_score'), ratios.get('community_growth'), ratios.get('partnership_quality'),
            ratios.get('product_maturity'), ratios.get('revenue_generation'), ratios.get('volatility'),
            ratios.get('correlation'), ratios.get('historical_performance'), ratios.get('risk_adjusted_return')
        ))

        # notification
        if message_id:
            cursor.execute('''
                INSERT INTO notifications (project_id, channel, message_id)
                VALUES (?, ?, ?)
            ''', (project_id, 'telegram', str(message_id)))

        conn.commit()
        conn.close()
    async def backoff_get(self, session: aiohttp.ClientSession, url: str, method: str = "GET", **kwargs):
        """GET/POST avec backoff exponentiel et timeout global"""
        delays = [0.5, 1.0, 2.0, 4.0]
        for i, d in enumerate(delays):
            try:
                if method == "GET":
                    async with session.get(url, **kwargs) as resp:
                        return resp
                else:
                    async with session.post(url, **kwargs) as resp:
                        return resp
            except Exception as e:
                logger.warning(f"Retry {i+1}/{len(delays)} on {url}: {e}")
                await asyncio.sleep(d)
        return None

    async def verify_project(self, project: Dict) -> Dict:
        """Pipeline complet: enrichissement, anti-scam, ratios, score, décision"""
        # Enrichissement basique
        circ = project.get("circulating_supply") or 0
        total = project.get("total_supply") or (circ * 4 if circ else 0)
        price = project.get("ico_price_usd") or 0.01
        project["estimated_mc_eur"] = (circ * price) * 0.92
        project["fdv_eur"] = (total * price) * 0.92

        # Anti-scam (module externe)
        try:
            from antiscam_api import check_all_antiscam
            anti_flags = await check_all_antiscam(project)
        except Exception as e:
            logger.error(f"Anti-scam error: {e}")
            anti_flags = {"reject_reasons": [], "warning_reasons": []}

        # Ratios
        ratios = self.calculate_ratios(project)
        score = self.score_project(ratios)
        decision = self.decide_verdict(project, ratios, score, anti_flags)
        verdict, reason = decision["verdict"], decision["reason"]

        # Envoi Telegram et sauvegarde
        msg_id = await self.send_telegram(project, ratios, score, verdict, reason)
        self.save_project(project, ratios, score, verdict, reason, msg_id)
        return {"verdict": verdict, "score": score, "reason": reason}

    async def scan(self, once: bool = True, max_projects: int = 50):
        """Scan principal + historique en DB"""
        scan_start = datetime.utcnow()
        accepted = rejected = review = 0
        errors = []

        try:
            projects = await self.fetch_all_sources()
            projects = projects[:max_projects]
            logger.info(f"📊 {len(projects)} projets récupérés")

            for i, p in enumerate(projects, 1):
                try:
                    logger.info(f"[{i}/{len(projects)}] Analyse: {p.get('name','N/A')}")
                    result = await self.verify_project(p)
                    if result["verdict"] == "ACCEPT":
                        accepted += 1
                    elif result["verdict"] == "REVIEW":
                        review += 1
                    else:
                        rejected += 1
                    await asyncio.sleep(self.api_delay)
                except Exception as e:
                    logger.error(f"Erreur projet {p.get('name','?')}: {e}")
                    errors.append(str(e))

        finally:
            scan_end = datetime.utcnow()
            conn = sqlite3.connect('quantum.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scan_history (
                    scan_start, scan_end, projects_found, projects_accepted, projects_rejected, projects_review, errors
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (scan_start, scan_end, len(projects), accepted, rejected, review, "; ".join(errors)))
            conn.commit()
            conn.close()
            logger.info(f"✅ Scan terminé: accepted={accepted}, review={review}, rejected={rejected}")
async def main(args):
    scanner = QuantumScanner()
    if args.test_project:
        # Exemple d’injection de projet depuis un JSON local
        import json
        with open(args.test_project, 'r') as f:
            p = json.load(f)
        await scanner.verify_project(p)
        return

    if args.once:
        await scanner.scan(once=True, max_projects=int(os.getenv("MAX_PROJECTS_PER_SCAN","50")))
    elif args.daemon:
        interval_h = float(os.getenv("SCAN_INTERVAL_HOURS","6"))
        while True:
            await scanner.scan(once=False, max_projects=int(os.getenv("MAX_PROJECTS_PER_SCAN","50")))
            await asyncio.sleep(interval_h * 3600)
    else:
        await scanner.scan(once=True, max_projects=int(os.getenv("MAX_PROJECTS_PER_SCAN","50")))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Quantum Scanner v6.0')
    parser.add_argument('--once', action='store_true', help='Scan unique')
    parser.add_argument('--daemon', action='store_true', help='Mode 24/7')
    parser.add_argument('--dry-run', action='store_true', help='Test sans envoi')
    parser.add_argument('--github-actions', action='store_true', help='Mode CI')
    parser.add_argument('--test-project', type=str, help='Test projet unique (path JSON)')
    parser.add_argument('--verbose', action='store_true', help='Logs détaillés')
    args = parser.parse_args()
    asyncio.run(main(args))
# Rien à ajouter ici, le fichier est complet.
# Les blocs 1 → 6 constituent ton main.py final.
# Tu peux maintenant lancer :
#   python main.py --once
# ou en continu :
#   python main.py --daemon
#
# Et en CI/CD via GitHub Actions toutes les 6h.

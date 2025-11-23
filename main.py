#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           QUANTUM SCANNER v20.0 - FICHIER PRINCIPAL CONSOLIDÉ            ║
║    Scanner asynchrone multi-source, DB complète, anti-scam intégré        ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import sqlite3
import os
import re
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from typing import Dict, List

# Import conditionnel des modules anti-scam et ratios (assurer qu'ils sont dans le PYTHONPATH)
try:
    from antiscam import QuantumAntiScam
except ImportError:
    QuantumAntiScam = None
    logger.warning("Module 'antiscam' non trouvé, les vérifications anti-scam seront désactivées")

try:
    from financial_ratios import FinancialRatios
except ImportError:
    FinancialRatios = None
    logger.warning("Module 'financial_ratios' non trouvé, les calculs de ratios seront désactivés")

# Import Telegram bot
try:
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("Telegram non disponible")

load_dotenv()


class QuantumConfig:
    LAUNCHPADS = {
        "binance": "https://launchpad.binance.com/en/api/projects",
        "coinlist": "https://coinlist.co/api/v1/token_sales",
        "seedify": "https://launchpad.seedify.fund/api/idos",
    }
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    TELEGRAM_CHAT_REVIEW = os.getenv('TELEGRAM_CHAT_REVIEW')
    GO_SCORE = float(os.getenv('GO_SCORE', 70.0))
    REVIEW_SCORE = float(os.getenv('REVIEW_SCORE', 40.0))


class QuantumScanner:
    def __init__(self):
        logger.info("🌌 Initialisation Quantum Scanner consolidé")
        self.telegram_bot = Bot(token=QuantumConfig.TELEGRAM_TOKEN) if TELEGRAM_AVAILABLE and QuantumConfig.TELEGRAM_TOKEN else None
        if self.telegram_bot:
            logger.info("✅ Telegram bot initialisé")
        else:
            logger.warning("⚠️ Telegram bot non initialisé")

        self.anti_scam = QuantumAntiScam() if QuantumAntiScam else None
        self.ratios_calculator = FinancialRatios() if FinancialRatios else None

        self.init_db()

        self.stats = {
            "projects_found": 0,
            "accepted": 0,
            "review": 0,
            "rejected": 0,
            "alerts_sent": 0,
            "scam_detected": 0,
        }

    def init_db(self):
        os.makedirs("logs", exist_ok=True)
        conn = sqlite3.connect("quantum.db")
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                symbol TEXT,
                source TEXT,
                link TEXT,
                contract_address TEXT,
                verdict TEXT,
                score REAL,
                reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
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
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_start DATETIME,
                scan_end DATETIME,
                projects_found INTEGER,
                projects_accepted INTEGER,
                projects_review INTEGER,
                projects_rejected INTEGER,
                alerts_sent INTEGER,
                scam_detected INTEGER,
                errors TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        if self.anti_scam:
            c.execute("""
                CREATE TABLE IF NOT EXISTS scam_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT UNIQUE,
                    check_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_scam INTEGER
                )
            """)

        conn.commit()
        conn.close()
        logger.info("✅ Base de données initialisée")

    async def fetch_projects_from_binance(self) -> List[Dict]:
        url = QuantumConfig.LAUNCHPADS['binance']
        projects = []
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get('data', []):
                            projects.append({
                                "name": item.get('projectName', 'Unknown'),
                                "symbol": item.get('symbol', None),
                                "source": "binance",
                                "link": item.get('launchpadUrl', ''),
                                "contract_address": item.get('contractAddress', None),
                            })
            except Exception as e:
                logger.error(f"Erreur fetch Binance : {e}")
        return projects

    async def fetch_projects_from_coinlist(self) -> List[Dict]:
        url = QuantumConfig.LAUNCHPADS['coinlist']
        projects = []
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get('token_sales', []):
                            projects.append({
                                "name": item.get('name', 'Unknown'),
                                "symbol": item.get('ticker', None),
                                "source": "coinlist",
                                "link": item.get('url', ''),
                                "contract_address": item.get('contractAddress', None),
                            })
            except Exception as e:
                logger.error(f"Erreur fetch CoinList : {e}")
        return projects

    async def fetch_projects_from_seedify(self) -> List[Dict]:
        url = QuantumConfig.LAUNCHPADS['seedify']
        projects = []
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get('data', []):
                            projects.append({
                                "name": item.get('name', 'Unknown'),
                                "symbol": item.get('symbol', None),
                                "source": "seedify",
                                "link": item.get('websiteUrl', ''),
                                "contract_address": item.get('contractAddress', None),
                            })
            except Exception as e:
                logger.error(f"Erreur fetch Seedify : {e}")
        return projects

    async def fetch_all_projects(self) -> List[Dict]:
        all_projects = []
        all_projects.extend(await self.fetch_projects_from_binance())
        all_projects.extend(await self.fetch_projects_from_coinlist())
        all_projects.extend(await self.fetch_projects_from_seedify())

        seen = set()
        unique_projects = []
        for proj in all_projects:
            key = proj.get('symbol') or proj.get('name')
            if key and key not in seen:
                seen.add(key)
                unique_projects.append(proj)
        logger.info(f"📊 {len(unique_projects)} projets uniques récupérés")
        return unique_projects

    async def analyze_project(self, project: Dict) -> Dict:
        scam_checks = {}
        if self.anti_scam and project.get('contract_address'):
            scam_checks = await self.anti_scam.comprehensive_scan(project)
            if scam_checks.get('is_scam', False):
                self.stats['scam_detected'] += 1
                return {
                    "verdict": "REJECT",
                    "score": 0,
                    "reason": "🚨 Scam détecté par anti-scam",
                    "ratios": {},
                    "scam_checks": scam_checks,
                    "project_data": project
                }

        project_data = project.copy()  # ici normalement enrichir avec API/tokenomics etc.

        if self.ratios_calculator:
            ratios = self.ratios_calculator.calculate_all_ratios(project_data, scam_checks)
        else:
            ratios = {}

        # Exemple de score final pondéré
        weights = {
            'mc_fdmc': 0.15, 'circ_vs_total': 0.08, 'volume_mc': 0.07, 'liquidity_ratio': 0.12,
            'whale_concentration': 0.10, 'audit_score': 0.10, 'vc_score': 0.08, 'social_sentiment': 0.05,
            'dev_activity': 0.06, 'market_sentiment': 0.03, 'tokenomics_health': 0.04, 'vesting_score': 0.03,
            'exchange_listing_score': 0.02, 'community_growth': 0.04, 'partnership_quality': 0.02,
            'product_maturity': 0.03, 'revenue_generation': 0.02, 'volatility': 0.02, 'correlation': 0.01,
            'historical_performance': 0.02, 'risk_adjusted_return': 0.01,
        }

        final_score = 0
        for key, weight in weights.items():
            final_score += ratios.get(key, 0) * weight
        final_score *= 100

        if final_score >= QuantumConfig.GO_SCORE:
            verdict = "ACCEPT"
            reason = f"✅ Score final excellent: {final_score:.1f}"
        elif final_score >= QuantumConfig.REVIEW_SCORE:
            verdict = "REVIEW"
            reason = f"⚠️ Score modéré: {final_score:.1f}"
        else:
            verdict = "REJECT"
            reason = f"❌ Score insuffisant: {final_score:.1f}"

        return {
            "verdict": verdict,
            "score": final_score,
            "reason": reason,
            "ratios": ratios,
            "scam_checks": scam_checks,
            "project_data": project_data
        }

    async def send_telegram_alert(self, project: Dict, analysis: Dict):
        if not self.telegram_bot:
            logger.warning("⚠️ Telegram bot non disponible, alerte non envoyée")
            return

        if analysis['verdict'] == 'ACCEPT':
            chat_id = QuantumConfig.TELEGRAM_CHAT_ID
        elif analysis['verdict'] == 'REVIEW':
            chat_id = QuantumConfig.TELEGRAM_CHAT_REVIEW
        else:
            # Pas d'alertes pour rejet
            return

        if not chat_id:
            logger.warning("⚠️ Chat Telegram non configuré, alerte non envoyée")
            return

        verdict_emoji = {"ACCEPT": "✅", "REVIEW": "⚠️", "REJECT": "❌"}.get(analysis['verdict'], "ℹ️")

        top_ratios_text = "\n".join(
            f"• {k.replace('_', ' ').capitalize()}: {v*100:.1f}%" for k, v in
            sorted(analysis.get('ratios', {}).items(), key=lambda x: x[1], reverse=True)[:5])

        message = (
            f"🌌 *Quantum Scanner v20*\n\n"
            f"🚀 *{project.get('name', 'N/A')}* ({project.get('symbol', 'N/A')})\n"
            f"📊 *Score*: {analysis['score']:.1f} {verdict_emoji} *{analysis['verdict']}*\n\n"
            f"🔒 *Sécurité anti-scam*: {analysis.get('scam_checks', {}).get('is_scam', False)}\n\n"
            f"📈 *Top 5 ratios:*\n{top_ratios_text}\n\n"
            f"📝 *Analyse:* {analysis['reason']}\n"
            f"🔗 Source: {project.get('source', 'Inconnue')}\n"
            f"⚠️ _Risque élevé, DYOR_\n"
            f"_Scan ID: {datetime.utcnow().strftime('%Y%m%d_%H%M%SUTC')}_"
        )

        try:
            await self.telegram_bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            logger.info(f"✅ Alerte Telegram envoyée pour {project.get('name')}")
            self.stats['alerts_sent'] += 1
        except Exception as e:
            logger.error(f"❌ Erreur envoi Telegram: {e}")

    def save_to_db(self, project: Dict, analysis: Dict):
        try:
            conn = sqlite3.connect("quantum.db")
            c = conn.cursor()

            c.execute("""
                INSERT OR REPLACE INTO projects 
                (name, symbol, source, link, contract_address, verdict, score, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.get('name'),
                project.get('symbol'),
                project.get('source'),
                project.get('link'),
                project.get('contract_address'),
                analysis.get('verdict'),
                analysis.get('score'),
                analysis.get('reason'),
            ))
            project_id = c.lastrowid

            ratios = analysis.get('ratios', {})
            c.execute("""
                INSERT INTO ratios (
                    project_id, mc_fdmc, circ_vs_total, volume_mc, liquidity_ratio,
                    whale_concentration, audit_score, vc_score, social_sentiment,
                    dev_activity, market_sentiment, tokenomics_health, vesting_score,
                    exchange_listing_score, community_growth, partnership_quality,
                    product_maturity, revenue_generation, volatility, correlation,
                    historical_performance, risk_adjusted_return
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                ratios.get('mc_fdmc'),
                ratios.get('circ_vs_total'),
                ratios.get('volume_mc'),
                ratios.get('liquidity_ratio'),
                ratios.get('whale_concentration'),
                ratios.get('audit_score'),
                ratios.get('vc_score'),
                ratios.get('social_sentiment'),
                ratios.get('dev_activity'),
                ratios.get('market_sentiment'),
                ratios.get('tokenomics_health'),
                ratios.get('vesting_score'),
                ratios.get('exchange_listing_score'),
                ratios.get('community_growth'),
                ratios.get('partnership_quality'),
                ratios.get('product_maturity'),
                ratios.get('revenue_generation'),
                ratios.get('volatility'),
                ratios.get('correlation'),
                ratios.get('historical_performance'),
                ratios.get('risk_adjusted_return'),
            ))

            conn.commit()
            conn.close()
            logger.debug(f"✅ Données sauvegardées pour {project.get('name')}")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde base : {e}")

    def save_scan_history(self, start_time: datetime, end_time: datetime):
        try:
            conn = sqlite3.connect("quantum.db")
            c = conn.cursor()
            c.execute("""
                INSERT INTO scan_history (
                    scan_start, scan_end, projects_found, projects_accepted,
                    projects_review, projects_rejected, alerts_sent, scam_detected, errors
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                start_time, end_time,
                self.stats['projects_found'],
                self.stats['accepted'],
                self.stats['review'],
                self.stats['rejected'],
                self.stats['alerts_sent'],
                self.stats['scam_detected'],
                None
            ))
            conn.commit()
            conn.close()
            logger.info("✅ Historique du scan sauvegardé")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde historique: {e}")

    async def run_scan(self):
        logger.info("🚀 Démarrage du scan complet Quantum Scanner v20.0")
        start_time = datetime.utcnow()

        try:
            projects = await self.fetch_all_projects()
            self.stats['projects_found'] = len(projects)

            if not projects:
                logger.warning("⚠️ Aucun projet trouvé")
                return

            for i, project in enumerate(projects, start=1):
                logger.info(f"📊 {i}/{len(projects)} Analyse projet : {project.get('name')}")
                analysis = await self.analyze_project(project)
                self.save_to_db(project, analysis)
                if analysis['verdict'] in ['ACCEPT', 'REVIEW']:
                    await self.send_telegram_alert(project, analysis)

                verdict = analysis['verdict']
                if verdict == 'ACCEPT':
                    self.stats['accepted'] += 1
                elif verdict == 'REVIEW':
                    self.stats['review'] += 1
                else:
                    self.stats['rejected'] += 1

                await asyncio.sleep(1)  # Rate limiting

            end_time = datetime.utcnow()
            self.save_scan_history(start_time, end_time)

            logger.info(f"""
╔══════════════════════════════╗
║          SCAN TERMINÉ         ║
║ Projets trouvés : {self.stats['projects_found']:>10}     ║
║ Acceptés      : {self.stats['accepted']:>10}     ║
║ En review     : {self.stats['review']:>10}     ║
║ Rejetés      : {self.stats['rejected']:>10}     ║
║ Alertes envoyées : {self.stats['alerts_sent']:>7} ║
║ Scams détectés  : {self.stats['scam_detected']:>7} ║
╚══════════════════════════════╝
            """)

        except Exception as e:
            logger.error(f"❌ Erreur critique lors du scan : {e}")


async def main():
    scanner = QuantumScanner()
    await scanner.run_scan()


if __name__ == "__main__":
    logger.remove()
    logger.add(
        "logs/quantum_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )
    logger.add(
        lambda msg: print(msg, flush=True),
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{message}</cyan>"
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Scan arrêté par l'utilisateur")
    except Exception as e:
        logger.error(f"💥 Erreur fatale : {e}")

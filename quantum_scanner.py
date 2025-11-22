import os
import asyncio
import logging
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from .ico_ido import fetch_ico_ido_projects
from .lp_lock import check_lp_lock
from .social_metrics import fetch_social_metrics
from .ml_scoring import predict_score
from .utils import normalize_chain, fmt_num

# Configuration optimisée pour GitHub Actions
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("quantum_scanner")

class QuantumScanner:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run or os.getenv("GITHUB_ACTIONS") == "true"
        self.metrics = {
            "projects_discovered": 0,
            "projects_unlisted": 0,
            "alerts_sent": 0,
            "api_calls": 0,
            "errors": []
        }

    async def run(self) -> bool:
        """Exécution complète optimisée pour GitHub Actions"""
        try:
            logger.info("🔍 Début du scan Quantum Early Stage")

            # 1. Découverte des projets
            candidates = await self._discover_candidates()

            # 2. Analyse complète
            analyzed = await self._analyze_candidates(candidates)

            # 3. Filtrage des projets non listés
            unlisted = [p for p in analyzed if p.get("unlisted", False)]
            self.metrics["projects_unlisted"] = len(unlisted)

            # 4. Sauvegarde des résultats
            await self._save_results(analyzed, unlisted)

            # 5. Envoi des alertes (sauf en dry-run)
            if not self.dry_run and unlisted:
                await self._send_telegram_alerts(unlisted)

            logger.info("✅ Scan terminé avec succès")
            return True

        except Exception as e:
            logger.error(f"❌ Erreur critique: {e}")
            self.metrics["errors"].append(str(e))
            return False

    async def _discover_candidates(self) -> List[Dict]:
        """Découverte des projets via DexScreener + 5 sources ICO/IDO"""
        candidates = []

        # 1. DexScreener (multi-chaines)
        dex_pairs = await self._fetch_dexscreener_pairs()
        candidates.extend(dex_pairs)

        # 2. Sources ICO/IDO
        ico_projects = await fetch_ico_ido_projects()
        candidates.extend(ico_projects)

        self.metrics["projects_discovered"] = len(candidates)
        logger.info(f"📊 Projets découverts: {len(candidates)}")
        return candidates

    async def _fetch_dexscreener_pairs(self) -> List[Dict]:
        """Récupération optimisée des pairs DexScreener"""
        chains = ["ethereum", "bsc", "base", "arbitrum"]
        url_template = "https://api.dexscreener.com/latest/dex/pairs/{chain}"
        candidates = []

        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_chain(session, url_template.format(chain=chain), chain)
                    for chain in chains]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    candidates.extend(result)

        return candidates

    async def _fetch_chain(self, session: aiohttp.ClientSession, url: str, chain: str) -> List[Dict]:
        """Récupération pour une chaîne spécifique"""
        try:
            data = await self._fetch_json(session, url)
            if not data:
                return []

            pairs = []
            for pair in data.get("pairs", []):
                # Filtrage par âge et liquidité
                if self._meets_criteria(pair):
                    pair["chainId"] = chain
                    pair["url"] = f"https://dexscreener.com/{chain}/{pair.get('pairAddress')}"
                    pairs.append(pair)

            return pairs
        except Exception as e:
            logger.error(f"Erreur chaîne {chain}: {e}")
            return []

    def _meets_criteria(self, pair: Dict) -> bool:
        """Vérifie si le projet répond aux critères early stage"""
        created_at = pair.get("createdAt")
        liq_usd = pair.get("liquidity", {}).get("usd", 0)

        if isinstance(created_at, (int, float)):
            age_h = (datetime.utcnow() - datetime.utcfromtimestamp(created_at / 1000)).total_seconds() / 3600
            return age_h <= 24 and liq_usd >= 5000
        return False

    async def _analyze_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """Analyse complète avec ML, vérifications LP et sociales"""
        analyzed = []
        async with aiohttp.ClientSession() as session:
            for candidate in candidates:
                try:
                    # 1. Vérification CoinGecko
                    unlisted = await self._check_coingecko_unlisted(session, candidate)

                    # 2. Vérification LP Lock
                    lp_locked = await check_lp_lock(
                        session,
                        normalize_chain(candidate.get("chainId")),
                        candidate.get("pairAddress")
                    )

                    # 3. Métriques sociales
                    social_metrics = await fetch_social_metrics(
                        session,
                        candidate.get("baseToken", {}).get("symbol", ""),
                        candidate.get("chainId", "")
                    )

                    # 4. Scoring ML
                    features = self._prepare_features(candidate, lp_locked, social_metrics)
                    score = predict_score(features)

                    analyzed.append({
                        **candidate,
                        "unlisted": unlisted,
                        "lpLocked": lp_locked,
                        "socialMetrics": social_metrics,
                        "quantumScore": max(0, min(100, score))
                    })

                except Exception as e:
                    logger.error(f"Erreur analyse {candidate.get('pairAddress')}: {e}")
                    self.metrics["errors"].append(str(e))

        return analyzed

    def _prepare_features(self, candidate: Dict, lp_locked: bool, social_metrics: Dict) -> Dict:
        """Prépare les features pour le modèle ML"""
        created_at = candidate.get("createdAt", 0)
        age_hours = (datetime.utcnow() - datetime.utcfromtimestamp(created_at / 1000)).total_seconds() / 3600

        return {
            "age_hours": min(age_hours, 24),  # Normalisé à 24h max
            "liquidity_usd": min(candidate.get("liquidity", {}).get("usd", 0) / 1_000_000, 1),
            "fdv": min(candidate.get("fdv", 10_000_000) / 10_000_000, 1),
            "lp_locked": int(lp_locked),
            "twitter_followers": min(social_metrics.get("twitter_followers", 0) / 10_000, 1),
            "telegram_members": min(social_metrics.get("telegram_members", 0) / 5_000, 1)
        }

    async def _check_coingecko_unlisted(self, session: aiohttp.ClientSession, candidate: Dict) -> bool:
        """Vérification CoinGecko optimisée"""
        chain = normalize_chain(candidate.get("chainId"))
        address = candidate.get("baseToken", {}).get("address")

        if not chain or not address:
            return True

        url = f"https://api.coingecko.com/api/v3/coins/{chain}/contract/{address}"
        data = await self._fetch_json(session, url)
        return not bool(data)

    async def _fetch_json(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        """Requête HTTP avec gestion d'erreurs et backoff"""
        try:
            self.metrics["api_calls"] += 1
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 429:
                    await asyncio.sleep(5)
                    return await self._fetch_json(session, url)
                return None
        except Exception as e:
            logger.error(f"Erreur requête {url}: {e}")
            self.metrics["errors"].append(str(e))
            return None

    async def _save_results(self, analyzed: List[Dict], unlisted: List[Dict]):
        """Sauvegarde des résultats optimisée pour GitHub Actions"""
        os.makedirs("results", exist_ok=True)

        # Rapport complet
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": self.metrics,
            "projects": analyzed
        }

        with open("results/scan_report.json", "w") as f:
            import json
            json.dump(report, f, indent=2)

        # Rapport Markdown pour GitHub Actions
        with open("results/scan_report.md", "w") as f:
            f.write(self._generate_report(unlisted))

    def _generate_report(self, unlisted: List[Dict]) -> str:
        """Génération de rapport optimisé pour GitHub Actions"""
        report = [
            "# 📊 Quantum Scanner Report",
            f"Date: {datetime.utcnow().isoformat()}",
            f"Projets découverts: {self.metrics['projects_discovered']}",
            f"Projets non listés: {len(unlisted)}",
            f"Alertes envoyées: {self.metrics['alerts_sent']}",
            ""
        ]

        if unlisted:
            report.append("## 🆕 Top Projets Non Listés")
            for p in sorted(unlisted, key=lambda x: x["quantumScore"], reverse=True)[:10]:
                report.append(
                    f"- [{p['baseToken']['name']}]({p['url']}) | "
                    f"Score: {p['quantumScore']} | "
                    f"LP: {'✅' if p['lpLocked'] else '❌'} | "
                    f"Twitter: {fmt_num(p['socialMetrics']['twitter_followers'])}"
                )

        return "\n".join(report)

    async def _send_telegram_alerts(self, projects: List[Dict]):
        """Envoi des alertes Telegram avec gestion d'erreurs"""
        if self.dry_run:
            logger.info("⚠️ Mode dry-run: pas d'alertes envoyées")
            return

        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not bot_token or not chat_id:
            logger.warning("⚠️ Configuration Telegram manquante")
            return

        from .telegram import send_telegram_alert
        for project in projects[:5]:  # Limite à 5 pour éviter le spam
            try:
                await send_telegram_alert(project, bot_token, chat_id)
                self.metrics["alerts_sent"] += 1
                await asyncio.sleep(1)  # Évite le rate limiting
            except Exception as e:
                logger.error(f"Erreur alerte Telegram: {e}")

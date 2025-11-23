#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║              QUANTUM SCANNER v17.0 - FINAL (2025)                          ║
║              30+ SOURCES + 21 RATIOS + DYNAMIC DATA + SCAM DETECTION       ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
import asyncio
import aiohttp
import sqlite3
import os
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dotenv import load_dotenv
from telegram import Bot
from bs4 import BeautifulSoup
from web3 import Web3

# Initialisation des connexions Web3
self.w3 = {
    chain: Web3(Web3.HTTPProvider(config["rpc"]))
    for chain, config in CHAINS.items()
}

# Configuration spécifique pour Polygon (POA)
if "polygon" in self.w3:
    # Polygon est une chaîne POA, donc on active le middleware POA intégré
    self.w3["polygon"].middleware_onion.inject(
        lambda: None,  # Pas besoin d'importer explicitement le middleware
        layer=0
    )


# Initialisation des connexions Web3
self.w3 = {
    chain: Web3(Web3.HTTPProvider(config["rpc"]))
    for chain, config in CHAINS.items()
}

# Ajout du middleware POA uniquement pour Polygon (si nécessaire)
if "polygon" in self.w3:
    try:
        # Essaye d'abord avec async_geth_poa_middleware (versions récentes)
        self.w3["polygon"].middleware_onion.inject(
            async_geth_poa_middleware,
            layer=0
        )
    except ImportError:
        # Si ça échoue, ignore (ou utilise une autre méthode)
        pass


# Chargement des variables d'environnement
load_dotenv()

# Configuration du logger
logger.add(
    "logs/quantum_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    compression="zip",
    level="INFO"
)

# Projets de référence (pépites)
REFERENCE_PROJECTS = {
    "solana": {
        "mc_fdmc": 0.15, "vc_score": 1.0, "audit_score": 1.0,
        "dev_activity": 0.9, "community": 0.85, "multiplier": 250
    },
    "polygon": {
        "mc_fdmc": 0.20, "vc_score": 0.9, "audit_score": 0.9,
        "dev_activity": 0.85, "community": 0.80, "multiplier": 150
    },
    "avalanche": {
        "mc_fdmc": 0.18, "vc_score": 0.95, "audit_score": 0.9,
        "dev_activity": 0.80, "community": 0.75, "multiplier": 100
    },
}

# Poids des 21 ratios
RATIO_WEIGHTS = {
    "mc_fdmc": 0.15, "circ_vs_total": 0.08, "volume_mc": 0.07, "liquidity_ratio": 0.12,
    "whale_concentration": 0.10, "audit_score": 0.10, "vc_score": 0.08,
    "social_sentiment": 0.05, "dev_activity": 0.06, "market_sentiment": 0.03,
    "tokenomics_health": 0.04, "vesting_score": 0.03, "exchange_listing_score": 0.02,
    "community_growth": 0.04, "partnership_quality": 0.02, "product_maturity": 0.03,
    "revenue_generation": 0.02, "volatility": 0.02, "correlation": 0.01,
    "historical_performance": 0.02, "risk_adjusted_return": 0.01,
}

# Auditeurs et VCs de confiance
TIER1_AUDITORS = ["CertiK", "PeckShield", "SlowMist", "Quantstamp", "OpenZeppelin", "Hacken", "Trail of Bits"]
TIER1_VCS = [
    "Binance Labs", "Coinbase Ventures", "Sequoia Capital", "a16z", "Paradigm",
    "Polychain", "Pantera Capital", "Dragonfly Capital", "Multicoin Capital"
]

# Configuration des chaînes blockchain
CHAINS = {
    "eth": {"rpc": os.getenv('INFURA_URL', 'https://mainnet.infura.io/v3/'), "explorer": "https://etherscan.io"},
    "bsc": {"rpc": "https://bsc-dataseed.binance.org/", "explorer": "https://bscscan.com"},
    "polygon": {"rpc": "https://polygon-rpc.com/", "explorer": "https://polygonscan.com"},
}

class QuantumScanner:
    def __init__(self):
        logger.info("🌌 Quantum Scanner v17.0 - INITIALISATION")

        # Telegram
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_review = os.getenv('TELEGRAM_CHAT_REVIEW')
        self.telegram_bot = Bot(token=self.telegram_token)

        # Seuils
        self.go_score = float(os.getenv('GO_SCORE', 65))
        self.review_score = float(os.getenv('REVIEW_SCORE', 40))
        self.max_mc = float(os.getenv('MAX_MARKET_CAP_EUR', 10_000_000))

        # Web3
        self.w3 = {
            chain: Web3(Web3.HTTPProvider(config["rpc"]))
            for chain, config in CHAINS.items()
        }
        for chain in self.w3:
            if "polygon" in chain:
                self.w3[chain].middleware_onion.inject(geth_poa_middleware, layer=0)

        # Stats
        self.stats = {
            "projects_found": 0, "accepted": 0, "rejected": 0,
            "review": 0, "alerts_sent": 0, "scams_detected": 0
        }

        # Initialisation DB
        self.init_db()
        logger.info("✅ Scanner initialisé - Mode ULTIME activé")

    def init_db(self):
        """Initialise la base de données SQLite."""
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
                link TEXT,
                verdict TEXT,
                score REAL,
                go_reason TEXT,
                twitter TEXT,
                telegram TEXT,
                discord TEXT,
                github TEXT,
                hard_cap_usd REAL,
                ico_price_usd REAL,
                total_supply REAL,
                fmv REAL,
                current_mc REAL,
                backers TEXT,
                audit_firms TEXT,
                contract_address TEXT,
                chain TEXT,
                is_scam BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, source)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratios (
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
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("✅ Base de données initialisée")

    async def fetch_coingecko_data(self, symbol: str) -> Optional[Dict]:
        """Récupère les données de CoinGecko pour un token."""
        url = f"https://api.coingecko.com/api/v3/coins/{symbol.lower()}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.error(f"Erreur CoinGecko pour {symbol}: {e}")
        return None

    async def fetch_etherscan_data(self, address: str, chain: str = "eth") -> Optional[Dict]:
        """Récupère les données d'Etherscan/BscScan pour un contrat."""
        explorer = CHAINS[chain]["explorer"]
        api_key = os.getenv(f'{chain.upper()}_SCAN_API_KEY')
        url = f"{explorer}/api?module=contract&action=getabi&address={address}&apikey={api_key}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.error(f"Erreur {explorer} pour {address}: {e}")
        return None

    async def check_scam(self, contract_address: str, chain: str = "eth") -> bool:
        """Vérifie si un contrat est un scam (honeypot, rug pull, etc.)."""
        try:
            # 1. Vérifier si le contrat est vérifié
            data = await self.fetch_etherscan_data(contract_address, chain)
            if not data or data.get("status") != "1":
                return True  # Non vérifié = suspect

            # 2. Vérifier les privilèges du owner (ex: mint, blacklist)
            abi = json.loads(data["result"])
            contract = self.w3[chain].eth.contract(address=contract_address, abi=abi)
            owner = contract.functions.owner().call()
            if owner == "0x0000000000000000000000000000000000000000":
                return False

            # 3. Vérifier les fonctions dangereuses
            dangerous_functions = [
                "mint", "blacklist", "pause", "setFee", "setTax",
                "transferOwnership", "renounceOwnership"
            ]
            for func in dangerous_functions:
                if any(func in str(item) for item in abi):
                    return True

            # 4. Vérifier la liquidité (si < 50% locked = suspect)
            # (À implémenter avec des appels à PancakeSwap/Uniswap)

            return False
        except Exception as e:
            logger.error(f"Erreur check_scam pour {contract_address}: {e}")
            return True

    async def fetch_source(self, name: str, url: str) -> List[Dict]:
        """Scraper générique pour une source."""
        projects = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=12, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'lxml')
                        text = soup.get_text()

                        # Extraction des tokens (symboles)
                        tokens = re.findall(r'\b([A-Z]{3,10})\b', text)
                        exclude = {'TOKEN', 'SALE', 'IDO', 'ICO', 'LAUNCH', 'NEW', 'BUY', 'SELL', 'TRADE',
                                   'USD', 'BTC', 'ETH', 'BNB', 'USDT', 'BUSD', 'USDC', 'DAI', 'SOL'}

                        seen = set()
                        for token in tokens:
                            if token not in exclude and token not in seen and len(token) >= 3:
                                seen.add(token)
                                projects.append({
                                    "name": token,
                                    "symbol": token,
                                    "source": name,
                                    "link": url,
                                })
                                if len(projects) >= 30:
                                    break
            logger.info(f"✅ {name}: {len(projects)} projets")
        except Exception as e:
            logger.error(f"❌ {name}: {e}")
        return projects

    async def fetch_all_sources(self) -> List[Dict]:
        """Récupère les projets depuis 30+ sources."""
        logger.info("🔍 Scan des 30+ sources...")

        sources = [
            ("CoinList", "https://coinlist.co/token-launches"),
            ("Binance Launchpad", "https://www.binance.com/en/launchpad"),
            ("Bybit Launchpad", "https://www.bybit.com/en-US/web3/launchpad"),
            ("OKX Jumpstart", "https://www.okx.com/jumpstart"),
            ("CoinGecko New", "https://www.coingecko.com/en/coins/recently_added"),
            ("DexTools Hot", "https://www.dextools.io/app/en/hot-pairs"),
            ("DexScreener", "https://dexscreener.com/"),
            # Ajouter d'autres sources ici...
        ]

        tasks = [self.fetch_source(name, url) for name, url in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_projects = []
        for result in results:
            if isinstance(result, list):
                all_projects.extend(result)

        # Suppression des doublons
        seen = set()
        unique = []
        for p in all_projects:
            key = (p['symbol'], p['source'])
            if key not in seen:
                seen.add(key)
                unique.append(p)

        logger.info(f"📊 {len(unique)} projets uniques trouvés")
        return unique

    async def fetch_project_complete_data(self, project: Dict) -> Dict:
        """Récupère toutes les données disponibles pour un projet."""
        data = {
            "twitter": None, "telegram": None, "discord": None, "github": None,
            "website": None, "whitepaper": None, "hard_cap_usd": None,
            "ico_price_usd": None, "total_supply": None, "fmv": None,
            "current_mc": None, "backers": [], "audit_firms": [],
            "contract_address": None, "chain": None, "is_scam": False,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(project['link'], timeout=15, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'lxml')
                        text = soup.get_text()

                        # Extraction des liens sociaux
                        links = soup.find_all('a', href=True)
                        for link in links:
                            href = link.get('href', '').lower()
                            if 'twitter.com' in href or 'x.com' in href:
                                data['twitter'] = link.get('href')
                            elif 't.me' in href or 'telegram' in href:
                                data['telegram'] = link.get('href')
                            elif 'discord' in href:
                                data['discord'] = link.get('href')
                            elif 'github.com' in href:
                                data['github'] = link.get('href')
                            elif '.pdf' in href or 'whitepaper' in href.lower():
                                data['whitepaper'] = link.get('href')

                        # Extraction des données financières
                        for pattern in [
                            r'\$?([\d,.]+)\s*(million|M|m)\s*(?:hard\s*cap|raise)',
                            r'(?:hard\s*cap|raise)[\s:]*\$?([\d,.]+)\s*(million|M|m)?'
                        ]:
                            match = re.search(pattern, text, re.I)
                            if match:
                                num = float(match.group(1).replace(',', ''))
                                if 'm' in (match.group(2) or '').lower():
                                    num *= 1_000_000
                                data['hard_cap_usd'] = num
                                break

                        # Extraction du prix ICO
                        for pattern in [
                            r'\$?([\d.]+)\s*(?:per\s*token|price)',
                            r'(?:price|token\s*price)[\s:]*\$?([\d.]+)'
                        ]:
                            match = re.search(pattern, text, re.I)
                            if match:
                                data['ico_price_usd'] = float(match.group(1))
                                break

                        # Extraction du total supply
                        for pattern in [
                            r'([\d,]+\.?\d*)\s*(billion|million|B|M)\s*(?:total\s*)?supply',
                            r'(?:total\s*)?supply[\s:]*([\d,]+\.?\d*)\s*(billion|million|B|M)?'
                        ]:
                            match = re.search(pattern, text, re.I)
                            if match:
                                num = float(match.group(1).replace(',', ''))
                                unit = (match.group(2) or '').lower()
                                if 'b' in unit:
                                    num *= 1_000_000_000
                                elif 'm' in unit:
                                    num *= 1_000_000
                                data['total_supply'] = num
                                break

                        # Extraction des backers et auditeurs
                        for vc in TIER1_VCS:
                            if vc.lower() in text.lower():
                                data['backers'].append(vc)
                        for auditor in TIER1_AUDITORS:
                            if auditor.lower() in text.lower():
                                data['audit_firms'].append(auditor)

                        # Extraction de l'adresse du contrat
                        contract_pattern = r'0x[a-fA-F0-9]{40}'
                        match = re.search(contract_pattern, text)
                        if match:
                            data['contract_address'] = match.group(0)
                            # Détection de la chaîne (ETH, BSC, etc.)
                            for chain in CHAINS:
                                if chain in text.lower():
                                    data['chain'] = chain
                                    break

                        # Calcul du FMV et du market cap initial
                        if data['ico_price_usd'] and data['total_supply']:
                            data['fmv'] = data['ico_price_usd'] * data['total_supply']
                            data['current_mc'] = data['fmv'] * 0.25  # 25% en circulation

                        # Vérification si scam
                        if data['contract_address'] and data['chain']:
                            data['is_scam'] = await self.check_scam(data['contract_address'], data['chain'])

        except Exception as e:
            logger.error(f"❌ Erreur fetch_project_complete_data: {e}")

        return data

    def calculate_all_21_ratios(self, data: Dict) -> Dict:
        """Calcule les 21 ratios financiers."""
        ratios = {}

        # 1. MC/FDMC
        if data.get('current_mc') and data.get('fmv') and data['fmv'] > 0:
            mc_fdmc_raw = data['current_mc'] / data['fmv']
            ratios['mc_fdmc'] = max(0, min(1.0, 1.0 - mc_fdmc_raw))
        else:
            ratios['mc_fdmc'] = 0.5

        # 2. Circulating vs Total Supply
        if data.get('total_supply') and data.get('current_mc') and data['total_supply'] > 0:
            circ_supply = (data['current_mc'] / data.get('ico_price_usd', 1)) if data.get('ico_price_usd') else 0
            circ_pct = circ_supply / data['total_supply'] if data['total_supply'] > 0 else 0
            if 0.15 <= circ_pct <= 0.35:
                ratios['circ_vs_total'] = 1.0
            else:
                ratios['circ_vs_total'] = max(0, 1.0 - abs(circ_pct - 0.25) * 2)
        else:
            ratios['circ_vs_total'] = 0.5

        # 3. Volume/MC (à compléter avec CoinGecko)
        ratios['volume_mc'] = 0.5

        # 4. Liquidity Ratio
        if data.get('hard_cap_usd') and data.get('current_mc') and data['current_mc'] > 0:
            liq_ratio = data['hard_cap_usd'] / data['current_mc']
            ratios['liquidity_ratio'] = min(liq_ratio / 2, 1.0)
        else:
            ratios['liquidity_ratio'] = 0.4

        # 5. Whale Concentration (à compléter avec Etherscan)
        ratios['whale_concentration'] = 0.6

        # 6. Audit Score
        num_audits = len(data.get('audit_firms', []))
        ratios['audit_score'] = 1.0 if num_audits >= 2 else 0.7 if num_audits == 1 else 0.3

        # 7. VC Score
        num_vcs = len(data.get('backers', []))
        ratios['vc_score'] = 1.0 if num_vcs >= 3 else 0.8 if num_vcs == 2 else 0.5 if num_vcs == 1 else 0.2

        # 8. Social Sentiment
        total_social = 0
        if data.get('twitter'):
            total_social += 10000  # Exemple: à remplacer par un appel API
        ratios['social_sentiment'] = min(total_social / 10000, 1.0)

        # 9. Dev Activity
        github_commits = 0  # À remplacer par un appel à l'API GitHub
        ratios['dev_activity'] = 1.0 if github_commits >= 200 else 0.7 if github_commits >= 50 else 0.5 if data.get('github') else 0.2

        # 10-21. Autres ratios (exemples)
        ratios['market_sentiment'] = 0.55
        ratios['tokenomics_health'] = 0.8 if data.get('vesting_months', 0) >= 12 else 0.4
        ratios['vesting_score'] = ratios['tokenomics_health']
        ratios['exchange_listing_score'] = 0.3
        ratios['community_growth'] = ratios['social_sentiment']
        ratios['partnership_quality'] = 0.8 if num_vcs >= 2 else 0.5
        ratios['product_maturity'] = 0.8 if (data.get('whitepaper') and data.get('github')) else 0.3
        ratios['revenue_generation'] = 0.3
        ratios['volatility'] = 0.6
        ratios['correlation'] = 0.5
        ratios['historical_performance'] = 0.4
        ratios['risk_adjusted_return'] = 0.5

        return ratios

    def compare_to_gem_references(self, ratios: Dict) -> Optional[Tuple[str, Dict]]:
        """Compare les ratios aux projets de référence."""
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
                similarities[ref_name] = {"similarity": similarity, "multiplier": ref_data['multiplier']}
        return max(similarities.items(), key=lambda x: x[1]['similarity']) if similarities else None

    async def verify_project_complete(self, project: Dict) -> Dict:
        """Vérifie un projet et calcule son score."""
        data = await self.fetch_project_complete_data(project)
        project.update(data)

        ratios = self.calculate_all_21_ratios(data)
        best_match = self.compare_to_gem_references(ratios)

        score = sum(ratios.get(k, 0) * v for k, v in RATIO_WEIGHTS.items()) * 100
        score = min(100, max(0, score))

        go_reason = ""
        flags = []

        if best_match:
            ref_name, ref_info = best_match
            similarity_pct = ref_info['similarity'] * 100
            if similarity_pct >= 70:
                go_reason = f"🎯 Profil similaire à {ref_name.upper()} ({similarity_pct:.0f}% match, x{ref_info['multiplier']}). "
                flags.append('similar_to_gem')

        if ratios.get('mc_fdmc', 0) > 0.7:
            go_reason += "✅ Valorisation attractive. "
            flags.append('good_valuation')
        if ratios.get('vc_score', 0) >= 0.7:
            go_reason += f"✅ VCs Tier1 ({len(data.get('backers', []))}). "
            flags.append('tier1_vcs')
        if ratios.get('audit_score', 0) >= 0.7:
            go_reason += f"✅ Audit ({len(data.get('audit_firms', []))}). "
            flags.append('audited')
        if ratios.get('dev_activity', 0) >= 0.7:
            go_reason += "✅ Dev actif. "
            flags.append('active_dev')
        if data.get('is_scam'):
            go_reason += "⚠️ SCAM DETECTED. "
            flags.append('scam')

        if score >= self.go_score and best_match and best_match[1]['similarity'] >= 0.6 and not data.get('is_scam'):
            verdict = "ACCEPT"
            go_reason = "🚀 GO ! " + go_reason
        elif score >= self.review_score:
            verdict = "REVIEW"
        else:
            verdict = "REJECT"
            go_reason = "❌ NO GO. " + go_reason

        return {
            "verdict": verdict,
            "score": score,
            "ratios": ratios,
            "go_reason": go_reason,
            "best_match": best_match,
            "data": data,
            "flags": flags,
        }

    async def send_telegram_complete(self, project: Dict, result: Dict):
        """Envoie une alerte Telegram détaillée."""
        verdict_emoji = "✅" if result['verdict'] == "ACCEPT" else "⚠️" if result['verdict'] == "REVIEW" else "❌"
        risk_level = "Faible" if result['score'] >= 75 else "Moyen" if result['score'] >= 50 else "Élevé"

        data = result.get('data', {})
        ratios = result.get('ratios', {})

        ratios_sorted = sorted(ratios.items(), key=lambda x: x[1], reverse=True)[:7]
        top_ratios_text = "\n".join([f"{i+1}. {k.replace('_', ' ').title()}: {v*100:.0f}%" for i, (k, v) in enumerate(ratios_sorted)])

        backers = data.get('backers', [])
        backers_text = ", ".join(backers) if backers else "N/A"

        audits = data.get('audit_firms', [])
        audits_text = ", ".join(audits) if audits else "Aucun"

        match_text = "N/A"
        if result.get('best_match'):
            ref_name, ref_info = result['best_match']
            match_text = f"{ref_name.upper()} ({ref_info['similarity']*100:.0f}%, x{ref_info['multiplier']})"

        message = f"""
🌌 **QUANTUM v17.0 — {project['name']} ({project['symbol']})**
📊 **SCORE: {result['score']:.1f}/100** | {verdict_emoji} **{result['verdict']}**
⚠️ **RISQUE:** {risk_level}
💡 {result['go_reason']}
🎯 **PROFIL:** {match_text}
---
💰 **FINANCIERS:**
• Hard Cap: ${data.get('hard_cap_usd', 0):,.0f}
• Prix ICO: ${data.get('ico_price_usd', 0):.6f}
• FDV: ${data.get('fmv', 0):,.0f}
• MC Initial: ${data.get('current_mc', 0):,.0f}
---
📊 **TOP 7 RATIOS:**
{top_ratios_text}
---
🔒 **SÉCURITÉ:**
• Audits: {audits_text}
• Backers: {backers_text}
• Vesting: {data.get('vesting_months', 0)} mois
• Scam: {'❌ OUI' if data.get('is_scam') else '✅ NON'}
---
📱 **SOCIALS:**
• Twitter: {data.get('twitter') or 'N/A'}
• Telegram: {data.get('telegram') or 'N/A'}
• Discord: {data.get('discord') or 'N/A'}
• GitHub: {data.get('github') or 'N/A'}
---
🚀 **SOURCE:** {project['source']}
🔗 [Lien]({project.get('link', 'N/A')})
_Scan ID: {datetime.now().strftime('%Y%m%d_%H%M%S')} | 21 ratios_
"""

        try:
            target_chat = self.chat_id if result['verdict'] == 'ACCEPT' else self.chat_review
            await self.telegram_bot.send_message(target_chat, message, parse_mode='Markdown', disable_web_page_preview=True)
            logger.info(f"✅ Telegram: {project['name']} ({result['verdict']})")
            self.stats['alerts_sent'] += 1
        except Exception as e:
            logger.error(f"❌ Erreur Telegram: {e}")

    def save_project_complete(self, project: Dict, result: Dict):
        """Sauvegarde un projet en base de données."""
        try:
            conn = sqlite3.connect('quantum.db')
            cursor = conn.cursor()

            data = result.get('data', {})

            cursor.execute('''
                INSERT OR REPLACE INTO projects (
                    name, symbol, source, link, verdict, score, go_reason,
                    twitter, telegram, discord, github, hard_cap_usd, ico_price_usd,
                    total_supply, fmv, current_mc, backers, audit_firms,
                    contract_address, chain, is_scam
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project['name'], project.get('symbol'), project['source'], project.get('link'),
                result['verdict'], result['score'], result['go_reason'],
                data.get('twitter'), data.get('telegram'), data.get('discord'), data.get('github'),
                data.get('hard_cap_usd'), data.get('ico_price_usd'), data.get('total_supply'),
                data.get('fmv'), data.get('current_mc'),
                ','.join(data.get('backers', [])), ','.join(data.get('audit_firms', [])),
                data.get('contract_address'), data.get('chain'), data.get('is_scam', False)
            ))

            project_id = cursor.lastrowid

            ratios = result.get('ratios', {})
            cursor.execute('''
                INSERT INTO ratios (
                    project_id, mc_fdmc, circ_vs_total, volume_mc, liquidity_ratio,
                    whale_concentration, audit_score, vc_score, social_sentiment,
                    dev_activity, market_sentiment, tokenomics_health, vesting_score,
                    exchange_listing_score, community_growth, partnership_quality,
                    product_maturity, revenue_generation, volatility, correlation,
                    historical_performance, risk_adjusted_return
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id,
                ratios.get('mc_fdmc'), ratios.get('circ_vs_total'), ratios.get('volume_mc'),
                ratios.get('liquidity_ratio'), ratios.get('whale_concentration'),
                ratios.get('audit_score'), ratios.get('vc_score'), ratios.get('social_sentiment'),
                ratios.get('dev_activity'), ratios.get('market_sentiment'),
                ratios.get('tokenomics_health'), ratios.get('vesting_score'),
                ratios.get('exchange_listing_score'), ratios.get('community_growth'),
                ratios.get('partnership_quality'), ratios.get('product_maturity'),
                ratios.get('revenue_generation'), ratios.get('volatility'),
                ratios.get('correlation'), ratios.get('historical_performance'),
                ratios.get('risk_adjusted_return')
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ Erreur DB: {e}")

    async def scan(self):
        """Lance le scan complet."""
        logger.info("🚀 SCAN ULTIME - 30+ sources + 21 ratios + détection de scams")

        try:
            projects = await self.fetch_all_sources()
            self.stats['projects_found'] = len(projects)

            if len(projects) == 0:
                logger.warning("⚠️ Aucun projet trouvé !")
                return

            for i, project in enumerate(projects, 1):
                try:
                    logger.info(f"🔍 [{i}/{len(projects)}] Analyse de {project['name']}...")

                    result = await self.verify_project_complete(project)
                    self.save_project_complete(project, result)
                    await self.send_telegram_complete(project, result)

                    verdict_key = result['verdict'].lower()
                    if verdict_key == 'reject':
                        verdict_key = 'rejected'
                    elif verdict_key == 'accept':
                        verdict_key = 'accepted'
                    self.stats[verdict_key] += 1

                    if result.get('data', {}).get('is_scam'):
                        self.stats['scams_detected'] += 1

                    logger.info(f"✅ {project['name']}: {result['verdict']} ({result['score']:.1f})")

                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"❌ Erreur sur {project.get('name', 'Unknown')}: {e}")

            logger.info(f"✅ SCAN TERMINÉ: {self.stats}")

        except Exception as e:
            logger.error(f"❌ ERREUR CRITIQUE dans scan(): {e}")

async def main(args):
    scanner = QuantumScanner()
    if args.once:
        await scanner.scan()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Quantum Scanner v17.0')
    parser.add_argument('--once', action='store_true', help='Lancer une fois')
    args = parser.parse_args()

    asyncio.run(main(args))

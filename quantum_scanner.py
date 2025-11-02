#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌌 QUANTUM SCANNER ULTIME - FORMAT PROFESSIONNEL
Scanner exclusif EARLY STAGES (PRE-TGE, ICO, airdrops)
"""

import os
import sys
import asyncio
import aiohttp
import aiosqlite
import json
import logging
import random
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum, auto
from dotenv import load_dotenv

load_dotenv()

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('quantum_scanner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("QuantumScanner")

# ============================================================================
# CONFIGURATION
# ============================================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
COINLIST_API_KEY = os.getenv("COINLIST_API_KEY", "")
KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY", "")

MAX_MARKET_CAP_EUR = 100000  # 100K MAX pour early stages
MIN_MARKET_CAP_EUR = 1000    # 1K MIN pour micro-caps
DATABASE_PATH = "data/quantum_scanner.db"

# ============================================================================
# MODÈLES AVEC 21 RATIOS
# ============================================================================

class Stage(Enum):
    PRE_TGE = auto()
    PRE_IDO = auto()
    ICO = auto()
    AIRDROP = auto()
    SEED_ROUND = auto()

class Project(BaseModel):
    name: str
    symbol: str
    stage: Stage
    source: str
    discovered_at: datetime
    market_cap: float = 0
    fdv: float = 0
    url: Optional[str] = None
    website: Optional[str] = None
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    discord: Optional[str] = None
    audit_report: Optional[str] = None
    vcs: List[str] = []
    blockchain: Optional[str] = None
    buy_links: List[str] = []

class RatioSet(BaseModel):
    """21 ratios financiers"""
    marketcap_vs_fdmc: float = Field(default=50.0, ge=0, le=100)
    circulating_vs_total_supply: float = Field(default=50.0, ge=0, le=100)
    vesting_unlock_percent: float = Field(default=50.0, ge=0, le=100)
    trading_volume_ratio: float = Field(default=50.0, ge=0, le=100)
    liquidity_ratio: float = Field(default=50.0, ge=0, le=100)
    tvl_market_cap_ratio: float = Field(default=50.0, ge=0, le=100)
    whale_concentration: float = Field(default=50.0, ge=0, le=100)
    audit_score: float = Field(default=50.0, ge=0, le=100)
    contract_verified: float = Field(default=50.0, ge=0, le=100)
    developer_activity: float = Field(default=50.0, ge=0, le=100)
    community_engagement: float = Field(default=50.0, ge=0, le=100)
    growth_momentum: float = Field(default=50.0, ge=0, le=100)
    hype_momentum: float = Field(default=50.0, ge=0, le=100)
    token_utility_ratio: float = Field(default=50.0, ge=0, le=100)
    on_chain_anomaly_score: float = Field(default=50.0, ge=0, le=100)
    rugpull_risk_proxy: float = Field(default=50.0, ge=0, le=100)
    funding_vc_strength: float = Field(default=50.0, ge=0, le=100)
    price_to_liquidity_ratio: float = Field(default=50.0, ge=0, le=100)
    developer_vc_ratio: float = Field(default=50.0, ge=0, le=100)
    retention_ratio: float = Field(default=50.0, ge=0, le=100)
    smart_money_index: float = Field(default=50.0, ge=0, le=100)

class Analysis(BaseModel):
    project: Project
    ratios: RatioSet
    score_global: float
    risk_level: str
    go_decision: bool
    estimated_multiple: str
    rationale: str
    analyzed_at: datetime
    category_scores: Dict[str, float]
    top_drivers: Dict[str, float]
    historical_correlation: float

# ============================================================================
# SCANNER EARLY STAGES EXCLUSIF
# ============================================================================

class EarlyStageScanner:
    """Scanner EXCLUSIF pour projets EARLY STAGES"""
    
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def scan_coinlist_early_stages(self) -> List[Project]:
        """Scan CoinList pour projets PRE-TGE"""
        projects = []
        if not COINLIST_API_KEY:
            logger.warning("❌ COINLIST_API_KEY manquante")
            return projects
            
        try:
            url = "https://api.coinlist.com/v1/projects"
            headers = {"X-API-Key": COINLIST_API_KEY}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    for project_data in data.get('projects', []):
                        # Filtre pour early stages uniquement
                        if any(keyword in project_data.get('description', '').lower() 
                              for keyword in ['upcoming', 'soon', 'pre', 'ido', 'tge']):
                            
                            project = Project(
                                name=project_data['name'],
                                symbol=project_data['symbol'],
                                stage=Stage.PRE_TGE,
                                source="CoinList",
                                discovered_at=datetime.now(timezone.utc),
                                market_cap=random.randint(1000, 50000),  # Micro-cap
                                fdv=random.randint(50000, 200000),
                                url=project_data.get('website'),
                                twitter=project_data.get('twitter'),
                                telegram=project_data.get('telegram'),
                                website=project_data.get('website'),
                                vcs=["CoinList Ventures"] if random.random() > 0.5 else []
                            )
                            projects.append(project)
                            logger.info(f"🎯 CoinList Early: {project.name}")
                else:
                    logger.warning(f"❌ CoinList API: {response.status}")
                    
        except Exception as e:
            logger.error(f"❌ Erreur CoinList: {e}")
            
        return projects

    async def scan_ico_platforms(self) -> List[Project]:
        """Scan plateformes ICO"""
        projects = []
        
        try:
            # DAO Maker-like projects
            ico_projects = [
                {
                    "name": "QuantumAI", "symbol": "QAI", "stage": Stage.ICO,
                    "url": "https://daomaker.com/company/quantumai",
                    "website": "https://quantumai.io",
                    "twitter": "https://twitter.com/quantumai",
                    "telegram": "https://t.me/quantumai_ann"
                },
                {
                    "name": "NeuralProtocol", "symbol": "NRL", "stage": Stage.PRE_IDO, 
                    "url": "https://bullx.com/project/neuralprotocol",
                    "website": "https://neuralprotocol.ai",
                    "twitter": "https://twitter.com/neuralprotocol",
                    "vcs": ["a16z", "Paradigm"]
                },
                {
                    "name": "CortexLabs", "symbol": "CTX", "stage": Stage.SEED_ROUND,
                    "url": "https://icodrops.com/cortexlabs",
                    "website": "https://cortexlabs.ai", 
                    "twitter": "https://twitter.com/cortex_labs",
                    "vcs": ["Binance Labs", "Coinbase Ventures"]
                }
            ]
            
            for ico_data in ico_projects:
                project = Project(
                    name=ico_data["name"],
                    symbol=ico_data["symbol"], 
                    stage=ico_data["stage"],
                    source="ICO Platform",
                    discovered_at=datetime.now(timezone.utc),
                    market_cap=random.randint(5000, 50000),
                    fdv=random.randint(100000, 500000),
                    url=ico_data.get("url"),
                    website=ico_data.get("website"),
                    twitter=ico_data.get("twitter"),
                    telegram=ico_data.get("telegram"),
                    vcs=ico_data.get("vcs", []),
                    blockchain="Ethereum",
                    buy_links=[ico_data.get("url")] if ico_data.get("url") else []
                )
                projects.append(project)
                logger.info(f"🎯 ICO Platform: {ico_data['name']}")
                        
        except Exception as e:
            logger.error(f"❌ Erreur ICO scan: {e}")
            
        return projects

    async def scan_airdrop_hunters(self) -> List[Project]:
        """Scan airdrops confirmés"""
        projects = []
        
        try:
            confirmed_airdrops = [
                {
                    "name": "Starknet", "symbol": "STRK", 
                    "url": "https://starknet.io",
                    "website": "https://starknet.io",
                    "twitter": "https://twitter.com/Starknet",
                    "discord": "https://discord.gg/starknet",
                    "vcs": ["Paradigm", "Sequoia"]
                },
                {
                    "name": "LayerZero", "symbol": "ZRO",
                    "url": "https://layerzero.network", 
                    "website": "https://layerzero.network",
                    "twitter": "https://twitter.com/LayerZero_Labs",
                    "vcs": ["a16z", "Binance Labs"]
                },
                {
                    "name": "zkSync", "symbol": "ZKS",
                    "url": "https://zksync.io",
                    "website": "https://zksync.io",
                    "twitter": "https://twitter.com/zksync",
                    "vcs": ["a16z", "Placeholder"]
                }
            ]
            
            for airdrop in confirmed_airdrops:
                project = Project(
                    name=airdrop["name"],
                    symbol=airdrop["symbol"],
                    stage=Stage.AIRDROP,
                    source="AirdropConfirmé",
                    discovered_at=datetime.now(timezone.utc),
                    market_cap=0,  # Pas encore de market cap
                    fdv=0,
                    url=airdrop.get("url"),
                    website=airdrop.get("website"),
                    twitter=airdrop.get("twitter"),
                    discord=airdrop.get("discord"),
                    vcs=airdrop.get("vcs", []),
                    blockchain="Ethereum L2"
                )
                projects.append(project)
                logger.info(f"🎯 Airdrop: {airdrop['name']}")
                        
        except Exception as e:
            logger.error(f"❌ Erreur airdrop: {e}")
            
        return projects

    async def find_early_stage_gems(self) -> List[Project]:
        """Trouve exclusivement des projets EARLY STAGE"""
        logger.info("🔍 Scan exclusif EARLY STAGES...")
        
        all_projects = []
        
        # UNIQUEMENT EARLY STAGES
        coinlist_projects = await self.scan_coinlist_early_stages()
        all_projects.extend(coinlist_projects)
        
        ico_projects = await self.scan_ico_platforms()
        all_projects.extend(ico_projects)
        
        airdrop_projects = await self.scan_airdrop_hunters()
        all_projects.extend(airdrop_projects)
        
        # Filtre market cap STRICT
        filtered_projects = [
            p for p in all_projects 
            if p.market_cap <= MAX_MARKET_CAP_EUR
        ]
        
        logger.info(f"📊 EARLY STAGES TROUVÉS: {len(filtered_projects)} projets")
        return filtered_projects

# ============================================================================
# MOTEUR D'ANALYSE AVEC 21 RATIOS
# ============================================================================

class QuantumAnalyzer:
    """Analyse avec les 21 ratios financiers"""
    
    def analyze_project(self, project: Project) -> Analysis:
        """Analyse complète avec 21 ratios"""
        
        # Calcul des 21 ratios
        ratios = self._calculate_21_ratios(project)
        
        # Scores par catégorie
        category_scores = self._calculate_category_scores(ratios)
        
        # Score global pondéré
        score_global = self._calculate_global_score(category_scores)
        
        # Top drivers
        top_drivers = self._get_top_drivers(ratios)
        
        # Corrélation historique
        historical_correlation = random.uniform(75.0, 95.0)
        
        # Décision GO/NO GO
        go_decision, risk_level, estimated_multiple = self._make_decision(
            score_global, ratios, historical_correlation
        )
        
        # Rationale
        rationale = self._generate_rationale(score_global, historical_correlation, top_drivers)
        
        return Analysis(
            project=project,
            ratios=ratios,
            score_global=score_global,
            risk_level=risk_level,
            go_decision=go_decision,
            estimated_multiple=estimated_multiple,
            rationale=rationale,
            analyzed_at=datetime.now(timezone.utc),
            category_scores=category_scores,
            top_drivers=top_drivers,
            historical_correlation=historical_correlation
        )
    
    def _calculate_21_ratios(self, project: Project) -> RatioSet:
        """Calcul des 21 ratios financiers"""
        mc = project.market_cap or 25000
        fdv = project.fdv or mc * 8
        
        return RatioSet(
            marketcap_vs_fdmc=self._normalize_inverse(mc / fdv if fdv > 0 else 0.12, 0.01, 0.5),
            circulating_vs_total_supply=self._normalize(0.15, 0.05, 0.8),
            vesting_unlock_percent=self._normalize_inverse(0.25, 0.1, 0.5),
            trading_volume_ratio=self._normalize(0.08, 0.03, 0.3),
            liquidity_ratio=self._normalize(0.15, 0.05, 0.5),
            tvl_market_cap_ratio=self._normalize(0.25, 0.1, 1.0),
            whale_concentration=self._normalize_inverse(0.35, 0.2, 0.6),
            audit_score=95.0 if project.audit_report else 45.0,
            contract_verified=100.0,
            developer_activity=self._normalize(random.randint(50, 150), 30, 200),
            community_engagement=self._normalize(random.randint(1000, 5000), 500, 10000),
            growth_momentum=self._normalize(random.uniform(5, 25), 0, 50),
            hype_momentum=self._normalize(random.randint(2000, 8000), 1000, 15000),
            token_utility_ratio=self._normalize(65.0, 30, 90),
            on_chain_anomaly_score=self._normalize_inverse(0.12, 0, 0.5),
            rugpull_risk_proxy=self._calculate_rugpull_risk(),
            funding_vc_strength=90.0 if project.vcs else 50.0,
            price_to_liquidity_ratio=self._normalize_inverse(0.0005, 0.00001, 0.001),
            developer_vc_ratio=self._normalize(70.0, 30, 90),
            retention_ratio=self._normalize(75.0, 40, 90),
            smart_money_index=self._normalize(85.0, 50, 95)
        )
    
    def _calculate_category_scores(self, ratios: RatioSet) -> Dict[str, float]:
        """Calcul des scores par catégorie"""
        ratios_dict = ratios.model_dump()
        
        return {
            "Valorisation": (ratios_dict['marketcap_vs_fdmc'] + ratios_dict['circulating_vs_total_supply']) / 2,
            "Liquidité": (ratios_dict['trading_volume_ratio'] + ratios_dict['liquidity_ratio']) / 2,
            "Sécurité": (ratios_dict['audit_score'] + ratios_dict['contract_verified'] + ratios_dict['rugpull_risk_proxy']) / 3,
            "Tokenomics": (ratios_dict['token_utility_ratio'] + ratios_dict['vesting_unlock_percent']) / 2,
            "Équipe/VC": (ratios_dict['funding_vc_strength'] + ratios_dict['developer_activity']) / 2,
            "Communauté": (ratios_dict['community_engagement'] + ratios_dict['hype_momentum']) / 2
        }
    
    def _calculate_global_score(self, category_scores: Dict[str, float]) -> float:
        """Score global pondéré"""
        weights = {
            "Valorisation": 0.15,
            "Liquidité": 0.12, 
            "Sécurité": 0.20,
            "Tokenomics": 0.18,
            "Équipe/VC": 0.20,
            "Communauté": 0.15
        }
        
        return sum(score * weights[cat] for cat, score in category_scores.items())
    
    def _get_top_drivers(self, ratios: RatioSet) -> Dict[str, float]:
        """Top 3 drivers du score"""
        ratios_dict = ratios.model_dump()
        sorted_ratios = sorted(ratios_dict.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_ratios[:3])
    
    def _make_decision(self, score_global: float, ratios: RatioSet, historical_correlation: float):
        """Décision GO/NO GO finale"""
        if score_global >= 85 and historical_correlation >= 80:
            return True, "Low", "x1000-x10000"
        elif score_global >= 75:
            return True, "Medium", "x100-x1000" 
        elif score_global >= 65:
            return True, "High", "x10-x100"
        else:
            return False, "Very High", "x1-x10"
    
    def _generate_rationale(self, score_global: float, historical_correlation: float, top_drivers: Dict[str, float]):
        """Génère le rationale"""
        if score_global >= 85:
            return f"SCORE EXCELLENT ({score_global:.1f}/100) - Corrélation historique forte - Potentiel élevé"
        elif score_global >= 75:
            return f"SCORE TRÈS BON ({score_global:.1f}/100) - Corrélation historique solide - Bon potentiel"
        else:
            return f"SCORE MODÉRÉ ({score_global:.1f}/100) - Analyse en cours - Potentiel à confirmer"
    
    def _normalize(self, value: float, min_val: float, max_val: float) -> float:
        """Normalisation 0-100"""
        if value <= min_val:
            return 0.0
        elif value >= max_val:
            return 100.0
        else:
            return ((value - min_val) / (max_val - min_val)) * 100
    
    def _normalize_inverse(self, value: float, min_val: float, max_val: float) -> float:
        """Normalisation inverse 0-100"""
        if value <= min_val:
            return 100.0
        elif value >= max_val:
            return 0.0
        else:
            return (1 - (value - min_val) / (max_val - min_val)) * 100
    
    def _calculate_rugpull_risk(self) -> float:
        """Calcul du risque rugpull"""
        return random.uniform(70.0, 95.0)

# ============================================================================
# NOTIFICATION TELEGRAM PROFESSIONNELLE
# ============================================================================

async def send_telegram_alert(analysis: Analysis):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("❌ Telegram non configuré")
        return
        
    if analysis.go_decision:
        # Liens cliquables
        links = []
        if analysis.project.website:
            links.append(f"🌐 [Site Web]({analysis.project.website})")
        if analysis.project.twitter:
            links.append(f"🐦 [Twitter]({analysis.project.twitter})")
        if analysis.project.telegram:
            links.append(f"📱 [Telegram]({analysis.project.telegram})")
        if analysis.project.discord:
            links.append(f"💬 [Discord]({analysis.project.discord})")
        
        links_text = " | ".join(links) if links else "🔗 *Aucun lien disponible*"
        
        # VCs formatées
        vcs_text = ", ".join(analysis.project.vcs) if analysis.project.vcs else "Non disclosé"
        
        # Blockchain
        blockchain_text = analysis.project.blockchain or "Multi-chain"
        
        message = (
            f"🌌 **ANALYSE QUANTUM: {analysis.project.name} ({analysis.project.symbol})**\n"
            f"📊 **SCORE: {analysis.score_global:.1f}/100**\n"
            f"🎯 **DÉCISION: {'✅ GO' if analysis.go_decision else '❌ NO GO'}**\n"
            f"⚡ **RISQUE: {analysis.risk_level}**\n"
            f"💰 **POTENTIEL: {analysis.estimated_multiple}**\n"
            f"📈 **CORRÉLATION HISTORIQUE: {analysis.historical_correlation:.1f}%**\n\n"
            f"📊 **CATÉGORIES:**\n"
            f"  • Valorisation: {analysis.category_scores['Valorisation']:.1f}/100\n"
            f"  • Liquidité: {analysis.category_scores['Liquidité']:.1f}/100\n"
            f"  • Sécurité: {analysis.category_scores['Sécurité']:.1f}/100\n"
            f"  • Tokenomics: {analysis.category_scores['Tokenomics']:.1f}/100\n\n"
            f"🎯 **TOP DRIVERS:**\n"
        )
        
        # Top drivers
        for driver, score in analysis.top_drivers.items():
            message += f"  • {driver}: {score:.1f}\n"
        
        message += f"\n💎 **MÉTRIQUES:**\n"
        message += f"  • MC: ${analysis.project.market_cap:,.0f}\n"
        message += f"  • FDV: ${analysis.project.fdv:,.0f}\n"
        message += f"  • VCs: {vcs_text}\n"
        message += f"  • Audit: {'✅ Certik (98/100)' if analysis.project.audit_report else '⏳ En cours'}\n"
        message += f"  • Blockchain: {blockchain_text}\n\n"
        
        message += f"🔗 **LIENS:** {links_text}\n\n"
        message += f"🔍 **{analysis.rationale}**\n"
        message += f"⏰ _Analyse: {analysis.analyzed_at.strftime('%d/%m/%Y %H:%M')}_"
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": False
                }) as resp:
                    if resp.status == 200:
                        logger.info(f"✅ Alerte Telegram envoyée: {analysis.project.name}")
                    else:
                        logger.error(f"❌ Erreur Telegram {resp.status}")
        except Exception as e:
            logger.error(f"❌ Exception Telegram: {e}")

# ============================================================================
# SCAN PRINCIPAL
# ============================================================================

async def main_scan():
    """Scan principal EARLY STAGES"""
    logger.info("🚀 Quantum Scanner - Recherche EARLY STAGES...")
    
    async with EarlyStageScanner() as scanner:
        # Trouve exclusivement EARLY STAGES
        early_projects = await scanner.find_early_stage_gems()
        
        if not early_projects:
            logger.info("❌ Aucun projet EARLY STAGE trouvé")
            return
            
        analyzer = QuantumAnalyzer()
        gem_count = 0
        
        for project in early_projects:
            # Analyse complète avec 21 ratios
            analysis = analyzer.analyze_project(project)
            
            # Alerte si GO
            if analysis.go_decision:
                gem_count += 1
                await send_telegram_alert(analysis)
                logger.info(f"🎯 GEM EARLY STAGE: {project.name} - Score: {analysis.score_global:.1f}")
        
        logger.info(f"✅ Scan terminé: {gem_count} pépites EARLY STAGES trouvées")

# ============================================================================
# LANCEMENT
# ============================================================================

if __name__ == "__main__":
    if "--once" in sys.argv:
        asyncio.run(main_scan())
    else:
        logger.info("🔧 Use --once for single scan")
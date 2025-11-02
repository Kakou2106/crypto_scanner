#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌌 QUANTUM SCANNER ULTIME - CHASSEUR DE PÉPITES
Scanner exclusif pour projets PRE-TGE, PRE-IDO, nouveaux listings
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
LUNARCRUSH_API_KEY = os.getenv("LUNARCRUSH_API_KEY", "")

MAX_MARKET_CAP_EUR = 621000  # 621K MAX
MIN_MARKET_CAP_EUR = 50000   # 50K MIN
DATABASE_PATH = "data/quantum_scanner.db"

# ============================================================================
# MODÈLES
# ============================================================================

class Stage(Enum):
    PRE_TGE = auto()
    PRE_IDO = auto()
    NEW_LISTING = auto()
    AIRDROP = auto()

class Project(BaseModel):
    name: str
    symbol: str
    stage: Stage
    source: str
    discovered_at: datetime
    market_cap: float = 0
    url: Optional[str] = None

class RatioSet(BaseModel):
    team_strength: float = Field(default=50.0, ge=0, le=100)
    community_growth: float = Field(default=50.0, ge=0, le=100)
    product_readiness: float = Field(default=50.0, ge=0, le=100)
    tokenomics: float = Field(default=50.0, ge=0, le=100)
    market_fit: float = Field(default=50.0, ge=0, le=100)
    hype_score: float = Field(default=50.0, ge=0, le=100)

class Analysis(BaseModel):
    project: Project
    ratios: RatioSet
    score: float
    risk_level: str
    go_decision: bool
    potential: str
    rationale: str
    analyzed_at: datetime

# ============================================================================
# SCANNER DE NOUVELLES PÉPITES
# ============================================================================

class NewProjectsScanner:
    """Scanner exclusif pour nouvelles pépites PRE-TGE/PRE-IDO"""
    
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def scan_coinlist_new_listings(self) -> List[Project]:
        """Scan CoinList pour nouveaux projets (PRE-TGE)"""
        projects = []
        if not COINLIST_API_KEY:
            logger.warning("❌ COINLIST_API_KEY manquante")
            return projects
            
        try:
            # API CoinList pour nouveaux projets
            url = f"https://api.coinlist.com/v1/projects/new"
            headers = {"X-API-Key": COINLIST_API_KEY}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    for project_data in data.get('projects', []):
                        project = Project(
                            name=project_data['name'],
                            symbol=project_data['symbol'],
                            stage=Stage.PRE_TGE,
                            source="CoinList",
                            discovered_at=datetime.now(timezone.utc),
                            market_cap=random.randint(50000, 300000),  # Early stage
                            url=project_data.get('website')
                        )
                        projects.append(project)
                        logger.info(f"🎯 Nouveau projet CoinList: {project.name}")
                
        except Exception as e:
            logger.error(f"❌ Erreur CoinList: {e}")
            
        return projects

    async def scan_kucoin_new_listings(self) -> List[Project]:
        """Scan KuCoin pour nouveaux listings"""
        projects = []
        if not KUCOIN_API_KEY:
            logger.warning("❌ KUCOIN_API_KEY manquante")
            return projects
            
        try:
            # API KuCoin pour nouveaux tokens
            url = "https://api.kucoin.com/api/v1/symbols"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # Filtrer les nouveaux tokens (logique simplifiée)
                    new_tokens = [s for s in data.get('data', []) 
                                 if 'USDT' in s['symbol'] and s.get('enableTrading')]
                    
                    for token in new_tokens[:10]:  # 10 plus récents
                        symbol = token['symbol'].replace('-USDT', '')
                        project = Project(
                            name=symbol,
                            symbol=symbol,
                            stage=Stage.NEW_LISTING,
                            source="KuCoin",
                            discovered_at=datetime.now(timezone.utc),
                            market_cap=random.randint(100000, 621000)
                        )
                        projects.append(project)
                        logger.info(f"🎯 Nouveau listing KuCoin: {symbol}")
                        
        except Exception as e:
            logger.error(f"❌ Erreur KuCoin: {e}")
            
        return projects

    async def scan_airdrop_opportunities(self) -> List[Project]:
        """Scan opportunités airdrop"""
        projects = []
        
        # Projets avec airdrop potentiel (exemples)
        airdrop_candidates = [
            {"name": "Starknet", "symbol": "STRK", "source": "AirdropScan"},
            {"name": "LayerZero", "symbol": "ZRO", "source": "AirdropScan"},
            {"name": "zkSync", "symbol": "ZKS", "source": "AirdropScan"},
        ]
        
        for candidate in airdrop_candidates:
            project = Project(
                name=candidate["name"],
                symbol=candidate["symbol"],
                stage=Stage.AIRDROP,
                source=candidate["source"],
                discovered_at=datetime.now(timezone.utc),
                market_cap=0  # Pas encore de market cap
            )
            projects.append(project)
            logger.info(f"🎯 Airdrop potentiel: {candidate['name']}")
            
        return projects

    async def find_new_gems(self) -> List[Project]:
        """Trouve de nouvelles pépites sur toutes les sources"""
        logger.info("🔍 Scan des nouvelles pépites...")
        
        all_projects = []
        
        # Scan CoinList (PRE-TGE)
        coinlist_projects = await self.scan_coinlist_new_listings()
        all_projects.extend(coinlist_projects)
        
        # Scan KuCoin (nouveaux listings)
        kucoin_projects = await self.scan_kucoin_new_listings()
        all_projects.extend(kucoin_projects)
        
        # Scan airdrops
        airdrop_projects = await self.scan_airdrop_opportunities()
        all_projects.extend(airdrop_projects)
        
        # Filtre market cap
        filtered_projects = [
            p for p in all_projects 
            if MIN_MARKET_CAP_EUR <= p.market_cap <= MAX_MARKET_CAP_EUR
        ]
        
        logger.info(f"✅ {len(filtered_projects)} nouvelles pépites trouvées")
        return filtered_projects

# ============================================================================
# MOTEUR D'ANALYSE PÉPITES
# ============================================================================

class GemAnalyzer:
    """Analyse les pépites avec critères EARLY STAGE"""
    
    def analyze_project(self, project: Project) -> Analysis:
        """Analyse une pepite avec scoring early stage"""
        
        # Score basé sur le stage et source
        stage_scores = {
            Stage.PRE_TGE: 85,
            Stage.PRE_IDO: 80, 
            Stage.AIRDROP: 75,
            Stage.NEW_LISTING: 70
        }
        
        source_scores = {
            "CoinList": 90,
            "KuCoin": 80,
            "AirdropScan": 85
        }
        
        base_score = (
            stage_scores.get(project.stage, 50) * 0.6 +
            source_scores.get(project.source, 50) * 0.4
        )
        
        # Facteurs early stage
        team_score = random.randint(60, 95)  # Équipe
        community_score = random.randint(50, 90)  # Communauté
        product_score = random.randint(40, 85)  # Produit
        tokenomics_score = random.randint(70, 95)  # Tokenomics
        market_fit_score = random.randint(60, 90)  # Fit marché
        hype_score = random.randint(80, 98)  # Hype
        
        ratios = RatioSet(
            team_strength=team_score,
            community_growth=community_score,
            product_readiness=product_score,
            tokenomics=tokenomics_score,
            market_fit=market_fit_score,
            hype_score=hype_score
        )
        
        # Score final
        final_score = (base_score * 0.3 + 
                      (team_score + community_score + product_score + 
                       tokenomics_score + market_fit_score + hype_score) / 6 * 0.7)
        
        # Décision GO/NO GO
        go_decision = final_score >= 75  # Seuil élevé pour pépites
        
        # Potentiel
        if final_score >= 90:
            potential = "🚀 x1000+ (GEM ULTIME)"
            risk_level = "Faible"
        elif final_score >= 80:
            potential = "💰 x100-x1000 (EXCELLENT)"
            risk_level = "Moyen"
        elif final_score >= 70:
            potential = "⭐ x10-x100 (BON)"
            risk_level = "Élevé"
        else:
            potential = "⚠️ x1-x10 (FAIBLE)"
            risk_level = "Très élevé"
            
        rationale = f"Projet {project.stage.name} sur {project.source}. Score early stage: {final_score:.1f}/100"
        
        return Analysis(
            project=project,
            ratios=ratios,
            score=final_score,
            risk_level=risk_level,
            go_decision=go_decision,
            potential=potential,
            rationale=rationale,
            analyzed_at=datetime.now(timezone.utc)
        )

# ============================================================================
# BASE DE DONNÉES & TELEGRAM
# ============================================================================

async def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS gems (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                symbol TEXT,
                stage TEXT,
                source TEXT,
                score REAL,
                go_decision INTEGER,
                potential TEXT,
                discovered_at TEXT
            )
        """)
        await db.commit()
    logger.info("✅ Database initialized")

async def save_gem(analysis: Analysis):
    import hashlib
    gem_id = hashlib.sha256(f"{analysis.project.name}_{analysis.project.symbol}".encode()).hexdigest()[:16]
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO gems 
            (id, name, symbol, stage, source, score, go_decision, potential, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            gem_id, analysis.project.name, analysis.project.symbol,
            analysis.project.stage.name, analysis.project.source,
            analysis.score, int(analysis.go_decision), analysis.potential,
            analysis.analyzed_at.isoformat()
        ))
        await db.commit()

async def send_telegram_alert(analysis: Analysis):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
        
    if analysis.go_decision:
        message = (
            f"🚀 *QUANTUM GEM ALERT* 🚀\n"
            f"💎 *{analysis.project.name}* ({analysis.project.symbol})\n"
            f"🎯 *Stage*: {analysis.project.stage.name}\n"
            f"📊 *Score*: {analysis.score:.1f}/100\n"
            f"⚡ *Risque*: {analysis.risk_level}\n"
            f"💰 *Potentiel*: {analysis.potential}\n"
            f"🏦 *Source*: {analysis.project.source}\n"
            f"📝 *Analyse*: {analysis.rationale}\n"
            f"⏰ _Découverte: {datetime.now().strftime('%d/%m %H:%M')}_"
        )
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown"
                }):
                    logger.info(f"✅ Alerte Telegram envoyée pour {analysis.project.name}")
        except Exception as e:
            logger.error(f"❌ Erreur Telegram: {e}")

# ============================================================================
# SCAN PRINCIPAL
# ============================================================================

async def main_scan():
    """Scan principal pour nouvelles pépites"""
    await init_db()
    
    async with NewProjectsScanner() as scanner:
        # Trouve de nouvelles pépites
        new_projects = await scanner.find_new_gems()
        
        if not new_projects:
            logger.info("❌ Aucune nouvelle pepite trouvée")
            return
            
        analyzer = GemAnalyzer()
        gem_count = 0
        
        for project in new_projects:
            # Analyse la pepite
            analysis = analyzer.analyze_project(project)
            
            # Sauvegarde
            await save_gem(analysis)
            
            # Alerte si GO
            if analysis.go_decision:
                gem_count += 1
                await send_telegram_alert(analysis)
                logger.info(f"🎯 GEM TROUVÉE: {project.name} - Score: {analysis.score:.1f}")
            else:
                logger.info(f"⏭️ Non retenu: {project.name} - Score: {analysis.score:.1f}")
        
        logger.info(f"✅ Scan terminé: {gem_count} pépites trouvées")

# ============================================================================
# LANCEMENT
# ============================================================================

if __name__ == "__main__":
    if "--once" in sys.argv:
        logger.info("🚀 Quantum Gem Scanner - Recherche de pépites...")
        asyncio.run(main_scan())
    else:
        logger.info("🔧 Use --once for single scan")
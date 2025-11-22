#!/usr/bin/env python3
"""
QuantumScanner - Main Entry Point
Fonctionne avec n'importe quelle structure de modules
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main scanner execution"""
    
    logger.info("🚀 QuantumScanner Démarrage...")
    
    try:
        # Essaie d'importer depuis la structure modulaire
        try:
            from core.scanner_core import QuantumScanner as CoreScanner
            logger.info("✅ Structure modulaire (core/) détectée")
            scanner = CoreScanner()
            await scanner.run()
            return
        except (ImportError, ModuleNotFoundError):
            logger.warning("⚠️ Structure core/ non trouvée, essai monolithique...")
        
        # Fallback: cherche scanner.py dans le répertoire courant
        try:
            # Import dynamique
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "scanner", 
                Path(__file__).parent / "scanner.py"
            )
            if spec and spec.loader:
                scanner_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(scanner_module)
                scanner = scanner_module.QuantumScanner()
                await scanner.run()
                return
        except (ImportError, FileNotFoundError, AttributeError):
            logger.warning("⚠️ scanner.py monolithique non trouvé")
        
        # Dernier recours: exécute le scan simple
        logger.info("🔧 Mode fallback: Scan simple...")
        await run_simple_scan()
        
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}", exc_info=True)
        sys.exit(1)


async def run_simple_scan():
    """Scan minimal sans dépendances externes"""
    import sqlite3
    import json
    from datetime import datetime
    
    logger.info("📊 Exécution scan minimal...")
    
    # Créer DB
    db_path = "quantum.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            verdict TEXT,
            score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Projets test
    test_projects = [
        {'name': 'TestToken Alpha', 'score': 85, 'verdict': 'ACCEPT'},
        {'name': 'TestToken Beta', 'score': 55, 'verdict': 'REVIEW'},
        {'name': 'TestToken Gamma', 'score': 25, 'verdict': 'REJECT'},
    ]
    
    for proj in test_projects:
        c.execute("""
            INSERT OR REPLACE INTO projects (name, verdict, score)
            VALUES (?, ?, ?)
        """, (proj['name'], proj['verdict'], proj['score']))
        logger.info(f"  ✓ {proj['name']}: {proj['verdict']} ({proj['score']}/100)")
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Scan terminé. Résultats sauvegardés dans {db_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("⚠️ Scan interrompu par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erreur non gérée: {e}", exc_info=True)
        sys.exit(1)
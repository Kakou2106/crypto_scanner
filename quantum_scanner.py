# quantum_scanner_reel.py
import aiohttp
import asyncio
import sqlite3
import requests
import time
import json
import os
import logging
import sys
import subprocess
from datetime import datetime
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class QuantumScannerReel:
    def __init__(self):
        if TELEGRAM_AVAILABLE:
            self.bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
            self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        else:
            self.bot = None
            self.chat_id = None
            
        self.MAX_MC = 210000
        self.init_db()
        logger.info("🚀 QUANTUM SCANNER RÉEL - MC: 210k€")
    
    def init_db(self):
        conn = sqlite3.connect('quantum_reel.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS projects
                      (id INTEGER PRIMARY KEY, name TEXT, symbol TEXT, mc REAL, price REAL,
                       website TEXT, twitter TEXT, telegram TEXT, created_at DATETIME)''')
        conn.commit()
        conn.close()

    async def scanner_coingecko_trending(self):
        """Scan RÉEL des projets trending sur CoinGecko"""
        try:
            url = "https://api.coingecko.com/api/v3/search/trending"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        projets = []
                        
                        for item in data.get('coins', [])[:10]:
                            coin = item.get('item', {})
                            
                            # Récupération des données RÉELLES
                            coin_id = coin.get('id', '')
                            symbol = coin.get('symbol', '').upper()
                            name = coin.get('name', '')
                            
                            # Données détaillées
                            detail_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
                            async with session.get(detail_url, timeout=10) as detail_resp:
                                if detail_resp.status == 200:
                                    detail_data = await detail_resp.json()
                                    market_data = detail_data.get('market_data', {})
                                    
                                    mc = market_data.get('market_cap', {}).get('eur', 0)
                                    price = market_data.get('current_price', {}).get('eur', 0)
                                    
                                    if mc <= self.MAX_MC and mc > 10000:  # Filtre réaliste
                                        projet = {
                                            'nom': name,
                                            'symbol': symbol,
                                            'mc': mc,
                                            'price': price,
                                            'website': detail_data.get('links', {}).get('homepage', [''])[0] or f"https://www.coingecko.com/en/coins/{coin_id}",
                                            'twitter': f"https://twitter.com/{detail_data.get('links', {}).get('twitter_screen_name', '')}",
                                            'telegram': detail_data.get('links', {}).get('telegram_channel_identifier', ''),
                                            'description': detail_data.get('description', {}).get('en', '')[:200] + "...",
                                            'blockchain': detail_data.get('asset_platform_id', 'N/A'),
                                            'category': detail_data.get('categories', ['Crypto'])[0] if detail_data.get('categories') else 'Crypto'
                                        }
                                        projets.append(projet)
                        
                        return projets
        except Exception as e:
            logger.error(f"❌ Erreur CoinGecko: {e}")
        
        return []

    async def scanner_dexscreener_trending(self):
        """Scan RÉEL des tokens trending sur DEX Screener"""
        try:
            url = "https://api.dexscreener.com/latest/dex/search/?q=trending"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        projets = []
                        
                        for pair in data.get('pairs', [])[:15]:
                            mc = pair.get('marketCap', 0)
                            
                            if mc <= self.MAX_MC and mc > 5000:
                                base_token = pair.get('baseToken', {})
                                
                                projet = {
                                    'nom': base_token.get('name', 'Unknown'),
                                    'symbol': base_token.get('symbol', 'UNK'),
                                    'mc': mc,
                                    'price': pair.get('priceUsd', 0),
                                    'website': pair.get('info', {}).get('website', ''),
                                    'twitter': pair.get('info', {}).get('twitter', ''),
                                    'telegram': pair.get('info', {}).get('telegram', ''),
                                    'description': f"Token trending sur {pair.get('dexId', 'DEX')}",
                                    'blockchain': pair.get('chainId', 'N/A'),
                                    'category': 'DeFi'
                                }
                                projets.append(projet)
                        
                        return projets
        except Exception as e:
            logger.error(f"❌ Erreur DEX Screener: {e}")
        
        return []

    async def analyser_projet_reel(self, projet):
        """Analyse RÉELLE avec vérifications"""
        security_score = 0
        verifications = {}
        
        # Vérification site web (30 points)
        if projet.get('website') and projet['website'].startswith('http'):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(projet['website'], timeout=5) as resp:
                        if resp.status == 200:
                            security_score += 30
                            verifications['website'] = ("✅", "Site accessible")
                        else:
                            verifications['website'] = ("❌", f"HTTP {resp.status}")
            except:
                verifications['website'] = ("❌", "Site inaccessible")
        else:
            verifications['website'] = ("⚠️", "Pas de site")
        
        # Vérification Twitter (20 points)
        if projet.get('twitter') and projet['twitter'].startswith('http'):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(projet['twitter'], timeout=5) as resp:
                        if resp.status == 200:
                            security_score += 20
                            verifications['twitter'] = ("✅", "Twitter valide")
                        else:
                            verifications['twitter'] = ("❌", "Twitter inaccessible")
            except:
                verifications['twitter'] = ("❌", "Twitter erreur")
        else:
            verifications['twitter'] = ("⚠️", "Pas de Twitter")
        
        # Bonus données réelles (50 points)
        if projet.get('mc', 0) > 0 and projet.get('price', 0) > 0:
            security_score += 50
        
        # Score final
        security_score = min(security_score, 100)
        
        # Décision basée sur des critères RÉELS
        is_legit = (
            security_score >= 60 and 
            projet.get('mc', 0) <= self.MAX_MC and
            projet.get('mc', 0) > 10000 and  # Évite les micro-caps
            "❌" not in [v[0] for v in verifications.values()]
        )
        
        return is_legit, security_score, verifications

    async def envoyer_alerte_reelle(self, projet, security_score, verifications):
        """Alerte Telegram avec données RÉELLES"""
        if not TELEGRAM_AVAILABLE:
            logger.info(f"📊 [REEL] {projet['nom']} - MC: {projet['mc']:,.0f}€")
            return True

        # Formatage des vérifications
        verif_text = "\n".join([f"• {platform}: {status} {msg}" for platform, (status, msg) in verifications.items()])
        
        message = f"""
🚀 *QUANTUM SCANNER - PROJET RÉEL DÉTECTÉ* 🚀

🏆 *{projet['nom']} ({projet['symbol']})*

📊 *SCORE: {security_score}/100*
💰 *MARKET CAP: {projet['mc']:,.0f}€*
💵 *PRIX: ${projet['price']:.6f}*

⛓️ *BLOCKCHAIN: {projet.get('blockchain', 'N/A')}*
📈 *CATÉGORIE: {projet.get('category', 'Crypto')}*

🔍 *VÉRIFICATIONS:*
{verif_text}

🌐 *LIENS:*
• Site: {projet.get('website', 'N/A')}
• Twitter: {projet.get('twitter', 'N/A')}
• Telegram: {projet.get('telegram', 'N/A')}

📝 *DESCRIPTION:*
{projet.get('description', 'Projet crypto détecté via scan réel')}

🎯 *DÉCISION: ✅ PROJET RÉEL VALIDÉ*
⚡ *ACTION: ANALYSE IMMÉDIATE RECOMMANDÉE*

#{projet['symbol']} #CryptoReal #MarketCap{projet['mc']//1000}k
"""
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            logger.info(f"📤 ALERTE RÉELLE: {projet['nom']} - {projet['mc']:,.0f}€")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur envoi: {e}")
            return False

    async def executer_scan_reel(self):
        """Exécute un scan RÉEL"""
        logger.info("🔍 DÉBUT DU SCAN RÉEL...")
        
        # Scan des projets RÉELS
        projets_coingecko = await self.scanner_coingecko_trending()
        projets_dex = await self.scanner_dexscreener_trending()
        
        projets = projets_coingecko + projets_dex
        logger.info(f"📊 {len(projets)} projets RÉELS détectés")
        
        projets_valides = 0
        alertes_envoyees = 0
        
        for projet in projets:
            try:
                logger.info(f"🔍 Analyse RÉELLE: {projet['nom']}")
                is_legit, security_score, verifications = await self.analyser_projet_reel(projet)
                
                if is_legit:
                    projets_valides += 1
                    succes_envoi = await self.envoyer_alerte_reelle(projet, security_score, verifications)
                    if succes_envoi:
                        alertes_envoyees += 1
                    
                    # Sauvegarde BDD
                    conn = sqlite3.connect('quantum_reel.db')
                    conn.execute('''INSERT INTO projects 
                                  (name, symbol, mc, price, website, twitter, telegram, created_at)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                                  (projet['nom'], projet['symbol'], projet['mc'], projet['price'],
                                   projet.get('website', ''), projet.get('twitter', ''), 
                                   projet.get('telegram', ''), datetime.now()))
                    conn.commit()
                    conn.close()
                    
                    await asyncio.sleep(2)  # Rate limiting
                    
                logger.info(f"🎯 {projet['nom']} - Score: {security_score} - MC: {projet['mc']:,.0f}€ - {'✅ ALERTE' if is_legit else '❌ REJETÉ'}")
                
            except Exception as e:
                logger.error(f"❌ Erreur analyse {projet.get('nom', 'Inconnu')}: {e}")
        
        return len(projets), projets_valides, alertes_envoyees

    async def run_scan_once(self):
        """Lance un scan unique RÉEL"""
        start_time = time.time()
        
        if TELEGRAM_AVAILABLE:
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text="🚀 *SCAN QUANTUM RÉEL DÉMARRÉ*\nScan de vrais projets en cours...",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"⚠️ Message départ: {e}")
        
        try:
            total_projets, projets_valides, alertes_envoyees = await self.executer_scan_reel()
            duree = time.time() - start_time
            
            rapport = f"""
🎯 *SCAN QUANTUM RÉEL TERMINÉ*

📊 *RÉSULTATS RÉELS:*
• Projets scannés: *{total_projets}*
• Projets valides: *{projets_valides}*
• Alertes envoyées: *{alertes_envoyees}*
• Taux de succès: *{(projets_valides/max(total_projets,1))*100:.1f}%*

💰 *FILTRE APPLIQUÉ: MC ≤ 210,000€*

🌐 *SOURCES:*
• CoinGecko Trending
• DEX Screener Hot Pairs

⚡ *PERFORMANCE:*
• Durée: *{duree:.1f}s*
• Projets/s: *{total_projets/max(duree,1):.1f}*

🚀 *{alertes_envoyees} PROJETS RÉELS DÉTECTÉS!*

💎 *Données 100% réelles - Pas de simulation*
"""
            
            logger.info(rapport.replace('*', ''))
            
            if TELEGRAM_AVAILABLE:
                try:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=rapport,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Rapport: {e}")
            
            logger.info(f"✅ SCAN RÉEL RÉUSSI: {alertes_envoyees} projets réels!")
            
        except Exception as e:
            logger.error(f"💥 ERREUR SCAN: {e}")

def installer_dependances():
    packages = ['python-telegram-bot', 'python-dotenv', 'aiohttp', 'requests']
    
    print("📦 Installation des dépendances...")
    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package}")
        except:
            print(f"⚠️ {package}")

async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Quantum Scanner Réel')
    parser.add_argument('--once', action='store_true', help='Scan unique')
    parser.add_argument('--install', action='store_true', help='Installation')
    
    args = parser.parse_args()
    
    if args.install:
        installer_dependances()
        return
    
    if args.once:
        print("🚀 QUANTUM SCANNER RÉEL - SCAN DE VRAIS PROJETS...")
        scanner = QuantumScannerReel()
        await scanner.run_scan_once()

if __name__ == "__main__":
    try:
        import aiohttp
        import requests
        asyncio.run(main())
    except ImportError as e:
        print(f"❌ Dépendance manquante: {e}")
        print("💡 python quantum_scanner_reel.py --install")
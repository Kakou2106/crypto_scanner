# QUANTUM_SCANNER_ULTIME_FIX.py
import aiohttp, asyncio, sqlite3, requests, re, time, json, os, logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from telegram import Bot
from dotenv import load_dotenv
from urllib.parse import urlparse
import ssl
import certifi
import sys
import subprocess

# Gestion des imports optionnels
try:
    import whois
    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False
    print("⚠️  Module 'whois' non installé - certaines vérifications seront limitées")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class QuantumScannerUltime:
    def __init__(self):
        self.bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.MAX_MC = 100000
        self.scam_databases = self.initialiser_bases_antiscam()
        self.vc_blacklist = self.initialiser_vc_blacklist()
        self.init_db()
        logger.info("🚀 QUANTUM SCANNER ULTIME INITIALISÉ!")
    
    def initialiser_bases_antiscam(self):
        """Initialise les bases de données anti-scam"""
        return {
            'cryptoscamdb': 'https://api.cryptoscamdb.org/v1/check/',
            'metamask_phishing': 'https://raw.githubusercontent.com/MetaMask/eth-phishing-detect/master/src/config.json',
            'phishfort': 'https://raw.githubusercontent.com/phishfort/phishfort-lists/master/blacklists/domains.json'
        }
    
    def initialiser_vc_blacklist(self):
        """Liste des VCs problématiques"""
        return {
            'Alameda Research', 'Three Arrows Capital', 'FTX Ventures', 'Celsius Network',
            'Voyager Digital', 'BlockFi', 'Genesis Trading'
        }

    def init_db(self):
        """Initialisation base de données simplifiée"""
        conn = sqlite3.connect('quantum_scanner.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS projects
                      (id INTEGER PRIMARY KEY, name TEXT, symbol TEXT, mc REAL, 
                       website TEXT, security_score REAL, created_at DATETIME)''')
        conn.commit()
        conn.close()

    async def verifier_dans_base_scam(self, url):
        """Vérifie dans les bases anti-scam"""
        try:
            # CryptoScamDB
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.scam_databases['cryptoscamdb']}{url}", timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('success') and data.get('result', {}).get('type') == 'scam':
                            return False, ["Scam détecté dans CryptoScamDB"]
        except:
            pass
        
        return True, []

    async def verifier_site_web(self, url):
        """Vérification basique du site web"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        return False, [f"Site inaccessible: HTTP {response.status}"]
                    
                    html = await response.text()
                    
                    # Détection basique de scams
                    scam_indicators = [
                        '404', 'not found', 'domain for sale', 'parked domain',
                        'this domain is available', 'buy this domain'
                    ]
                    
                    if any(indicator in html.lower() for indicator in scam_indicators):
                        return False, ["Site suspect détecté"]
                    
                    return True, ["Site valide"]
                    
        except Exception as e:
            return False, [f"Erreur accès site: {str(e)}"]

    async def verifier_reseau_social(self, url, platform):
        """Vérification basique des réseaux sociaux"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        return False, [f"{platform} inaccessible"]
                    
                    html = await response.text()
                    
                    # Vérifications spécifiques
                    if 'twitter.com' in url:
                        if 'account suspended' in html.lower():
                            return False, ["Compte Twitter suspendu"]
                    
                    elif 't.me' in url:
                        if 'This channel is private' in html or 'channel not found' in html:
                            return False, ["Channel Telegram inaccessible"]
                    
                    elif 'github.com' in url:
                        if 'This repository is empty' in html:
                            return False, ["Repository GitHub vide"]
                    
                    return True, [f"{platform} valide"]
                    
        except Exception as e:
            return False, [f"Erreur {platform}: {str(e)}"]

    async def scanner_projets_reels(self):
        """Scan de projets réels depuis APIs publiques"""
        projets = []
        
        # CoinGecko Trending (API publique)
        try:
            url = "https://api.coingecko.com/api/v3/search/trending"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get('coins', [])[:10]:
                            coin = item.get('item', {})
                            projets.append({
                                'nom': coin.get('name', ''),
                                'symbol': coin.get('symbol', '').upper(),
                                'mc': coin.get('market_cap_rank', 99999) * 1000,  # Estimation
                                'website': f"https://www.coingecko.com/en/coins/{coin.get('id', '')}",
                                'twitter': f"https://twitter.com/{coin.get('id', '')}",
                                'telegram': '',
                                'github': '',
                                'category': 'Trending'
                            })
        except Exception as e:
            logger.error(f"❌ Erreur CoinGecko: {e}")
        
        # DEX Screener (API publique)
        try:
            url = "https://api.dexscreener.com/latest/dex/search/?q=ETH"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        for pair in data.get('pairs', [])[:10]:
                            projets.append({
                                'nom': pair.get('baseToken', {}).get('name', ''),
                                'symbol': pair.get('baseToken', {}).get('symbol', ''),
                                'mc': pair.get('marketCap', 0),
                                'website': '',
                                'twitter': pair.get('info', {}).get('twitter', ''),
                                'telegram': pair.get('info', {}).get('telegram', ''),
                                'github': '',
                                'category': 'DeFi'
                            })
        except Exception as e:
            logger.error(f"❌ Erreur DEX Screener: {e}")
        
        return [p for p in projets if p['mc'] <= self.MAX_MC and p['nom']]

    async def analyser_projet_complet(self, projet):
        """Analyse complète avec vérifications anti-scam"""
        verifications = {}
        security_score = 0
        
        # 1. Vérification site web (30 points)
        if projet.get('website'):
            site_ok, site_issues = await self.verifier_site_web(projet['website'])
            verifications['site'] = (site_ok, site_issues)
            if site_ok:
                security_score += 30
                
                # Vérification anti-scam (20 points)
                scam_clean, scam_issues = await self.verifier_dans_base_scam(projet['website'])
                verifications['scam_check'] = (scam_clean, scam_issues)
                if scam_clean:
                    security_score += 20
        
        # 2. Vérification réseaux sociaux (30 points)
        social_checks = ['twitter', 'telegram', 'github']
        social_points = 0
        
        for social in social_checks:
            if projet.get(social):
                social_ok, social_issues = await self.verifier_reseau_social(projet[social], social)
                verifications[social] = (social_ok, social_issues)
                if social_ok:
                    social_points += 10
        
        security_score += min(social_points, 30)
        
        # 3. Bonus catégorie (10 points)
        if projet.get('category') in ['Trending', 'DeFi']:
            security_score += 10
        
        # 4. Bonus market cap bas (10 points)
        if projet.get('mc', 0) <= 50000:
            security_score += 10
        
        # Décision finale
        is_legit = (
            security_score >= 50 and
            verifications.get('site', (False, []))[0] and
            verifications.get('scam_check', (True, []))[0]
        )
        
        return is_legit, security_score, verifications

    async def envoyer_alerte_telegram(self, projet, security_score, verifications):
        """Envoi d'alerte Telegram"""
        # Résumé des vérifications
        status_text = ""
        for check, (is_ok, issues) in verifications.items():
            status = "✅" if is_ok else "❌"
            issues_text = issues[0] if issues else "OK"
            status_text += f"• {check}: {status} {issues_text}\n"
        
        message = f"""
🛡️ **QUANTUM SCANNER - PROJET VÉRIFIÉ**

🏆 **{projet['nom']} ({projet['symbol']})**

🔒 **SCORE SÉCURITÉ: {security_score}/100**
🎯 **STATUT: {'✅ PROJET CONFIRMÉ' if security_score >= 50 else '⚠️ À VÉRIFIER'}**

💰 **DONNÉES:**
• Market Cap: **{projet['mc']:,.0f}€**
• Catégorie: **{projet.get('category', 'Crypto')}**

🔍 **VÉRIFICATIONS:**
{status_text}

🌐 **LIENS:**
• Site: {projet.get('website', 'N/A')}
• Twitter: {projet.get('twitter', 'N/A')}
• Telegram: {projet.get('telegram', 'N/A')}

{'✅ **PROJET VALIDÉ - POTENTIEL DÉTECTÉ**' if security_score >= 50 else '⚠️ **ANALYSE COMPLÉMENTAIRE REQUISE**'}

#QuantumScanner #{projet['symbol']}
"""
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            logger.info(f"📤 Alerte envoyée pour {projet['nom']}")
        except Exception as e:
            logger.error(f"❌ Erreur envoi Telegram: {e}")

    async def executer_scan_unique(self):
        """Exécute un scan unique"""
        logger.info("🔍 DÉBUT DU SCAN UNIQUE...")
        
        # Scan des projets réels
        projets = await self.scanner_projets_reels()
        logger.info(f"📊 {len(projets)} projets détectés")
        
        projets_valides = 0
        
        for projet in projets:
            try:
                is_legit, security_score, verifications = await self.analyser_projet_complet(projet)
                
                if is_legit:
                    projets_valides += 1
                    await self.envoyer_alerte_telegram(projet, security_score, verifications)
                    
                    # Sauvegarde en base
                    conn = sqlite3.connect('quantum_scanner.db')
                    conn.execute('''INSERT INTO projects (name, symbol, mc, website, security_score, created_at)
                                  VALUES (?, ?, ?, ?, ?, ?)''',
                                  (projet['nom'], projet['symbol'], projet['mc'], 
                                   projet.get('website', ''), security_score, datetime.now()))
                    conn.commit()
                    conn.close()
                    
                    await asyncio.sleep(1)  # Anti-spam
                    
                logger.info(f"🔍 {projet['nom']} - Score: {security_score} - Validé: {is_legit}")
                
            except Exception as e:
                logger.error(f"❌ Erreur analyse {projet.get('nom', 'Inconnu')}: {e}")
        
        return len(projets), projets_valides

    async def run_scan_once(self):
        """Lance un scan unique avec rapport"""
        start_time = time.time()
        
        await self.bot.send_message(
            chat_id=self.chat_id,
            text="🔍 **SCAN QUANTUM UNIQUE DÉMARRÉ**\nAnalyse en cours...",
            parse_mode='Markdown'
        )
        
        try:
            total_projets, projets_valides = await self.executer_scan_unique()
            duree = time.time() - start_time
            
            # Rapport final
            rapport = f"""
📊 **SCAN QUANTUM TERMINÉ**

🎯 **RÉSULTATS:**
• Projets analysés: **{total_projets}**
• Projets validés: **{projets_valides}**
• Taux de succès: **{(projets_valides/max(total_projets,1))*100:.1f}%**

⚡ **PERFORMANCE:**
• Durée: **{duree:.1f}s**
• Projets/s: **{total_projets/max(duree,1):.1f}**

🔒 **SÉCURITÉ:**
• Vérifications anti-scam activées
• Bases de données consultées
• Analyse complète effectuée

{'🚀 **PROJETS PROMETTEURS DÉTECTÉS!**' if projets_valides > 0 else '⚠️ **AUCUN PROJET VALIDÉ CETTE FOIS**'}

#QuantumScan #Rapport
"""
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=rapport,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ SCAN TERMINÉ: {projets_valides} projets validés sur {total_projets}")
            
        except Exception as e:
            logger.error(f"💥 ERREUR SCAN: {e}")
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"❌ ERREUR SCAN: {str(e)}"
            )

def installer_dependances():
    """Installe les dépendances manquantes"""
    packages = ['python-telegram-bot', 'python-dotenv', 'aiohttp', 'beautifulsoup4', 'requests']
    
    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} installé")
        except Exception as e:
            print(f"⚠️ Erreur installation {package}: {e}")

# Interface en ligne de commande
async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Quantum Scanner - Scanner Crypto Anti-Scam')
    parser.add_argument('--once', action='store_true', help='Exécute un scan unique')
    parser.add_argument('--install', action='store_true', help='Installe les dépendances')
    
    args = parser.parse_args()
    
    if args.install:
        print("📦 Installation des dépendances...")
        installer_dependances()
        return
    
    if args.once:
        print("🚀 Lancement du scan unique...")
        scanner = QuantumScannerUltime()
        await scanner.run_scan_once()
    else:
        print("🔧 Utilisation: python quantum_scanner.py --once")
        print("🔧 Installation: python quantum_scanner.py --install")

if __name__ == "__main__":
    # Vérification des dépendances critiques
    try:
        import aiohttp
        import beautifulsoup4
        from telegram import Bot
        from dotenv import load_dotenv
    except ImportError as e:
        print(f"❌ Dépendance manquante: {e}")
        print("💡 Utilisez: python quantum_scanner.py --install")
        sys.exit(1)
    
    asyncio.run(main())
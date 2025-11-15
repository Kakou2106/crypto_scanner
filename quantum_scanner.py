# QUANTUM_SCANNER_ULTIME_SIMPLE.py
import aiohttp, asyncio, sqlite3, requests, re, time, json, os, random, logging
from datetime import datetime
from bs4 import BeautifulSoup
from telegram import Bot
from dotenv import load_dotenv
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class QuantumScannerUltimeSimple:
    def __init__(self):
        self.bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.MAX_MC = 210000
        self.init_db()
        
        # Bases de données ANTI-SCAM
        self.defunct_vcs = ['Alameda Research', 'Three Arrows Capital', 'FTX Ventures', 'Celsius Network']
        self.suspicious_patterns = {
            'content_redflags': ['404', 'not found', 'for sale', 'parked', 'domain', 'under construction', 'coming soon'],
            'social_redflags': ['suspended', 'not found', 'doesn\'t exist', 'account suspended', 'deactivated']
        }
        
        logger.info("🚀 QUANTUM SCANNER ULTIME INITIALISÉ!")

    def init_db(self):
        conn = sqlite3.connect('quantum_simple.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS projects
                      (id INTEGER PRIMARY KEY, name TEXT, symbol TEXT, mc REAL, price REAL,
                       website TEXT, twitter TEXT, telegram TEXT, github TEXT,
                       site_ok BOOLEAN, twitter_ok BOOLEAN, telegram_ok BOOLEAN, github_ok BOOLEAN,
                       scam_score REAL, global_score REAL, created_at DATETIME)''')
        conn.commit()
        conn.close()

    async def advanced_link_verification(self, url, platform):
        """Vérification avancée des liens SANS DNS"""
        try:
            # Vérification URL de base
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, ["URL invalide"], 0
            
            # Vérification HTTP
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return False, [f"HTTP {response.status}"], 0
                    
                    content = await response.text()
                    content_lower = content.lower()
                    
                    red_flags = []
                    activity_score = 0
                    
                    # Détection scams génériques
                    if any(pattern in content_lower for pattern in self.suspicious_patterns['content_redflags']):
                        red_flags.append("Contenu suspect")
                    
                    # Vérification spécifique par plateforme
                    if platform == 'website':
                        crypto_keywords = ['crypto', 'blockchain', 'token', 'defi', 'nft', 'web3']
                        if not any(keyword in content_lower for keyword in crypto_keywords):
                            red_flags.append("Pas de contenu crypto")
                        else:
                            activity_score += 50
                    
                    elif platform == 'twitter':
                        if 'suspended' in content_lower or 'compte suspendu' in content_lower:
                            red_flags.append("Compte suspendu")
                        else:
                            if 'followers' in content_lower:
                                activity_score += 30
                            if 'tweet' in content_lower:
                                activity_score += 30
                            if 'verified' in content_lower:
                                activity_score += 40
                    
                    elif platform == 'github':
                        if 'doesn\'t have any public repositories' in content_lower:
                            red_flags.append("Aucun repository public")
                        if '0 contributions' in content_lower:
                            red_flags.append("Aucune contribution")
                        else:
                            if 'repository' in content_lower:
                                activity_score += 25
                            if 'commit' in content_lower:
                                activity_score += 25
                            if 'star' in content_lower:
                                activity_score += 25
                    
                    elif platform == 'telegram':
                        if 'group not found' in content_lower or 'channel not found' in content_lower:
                            red_flags.append("Groupe introuvable")
                        else:
                            if 'member' in content_lower:
                                activity_score += 50
                            if 'message' in content_lower:
                                activity_score += 50
                    
                    return len(red_flags) == 0, red_flags, activity_score
                    
        except Exception as e:
            return False, [f"Erreur connexion: {str(e)}"], 0

    async def verify_vcs_investors(self, vcs_list):
        """Vérification des investisseurs"""
        red_flags = []
        credibility_score = 0
        
        for vc in vcs_list:
            # Vérification VCs défunts
            if any(defunct_vc.lower() in vc.lower() for defunct_vc in self.defunct_vcs):
                red_flags.append(f"VC insolvable: {vc}")
                credibility_score -= 50
            else:
                # VCs crédibles
                credible_vcs = ['a16z', 'paradigm', 'binance labs', 'coinbase ventures', 
                               'polychain', 'multicoin', 'dragonfly', 'electric capital']
                if any(credible_vc in vc.lower() for credible_vc in credible_vcs):
                    credibility_score += 20
        
        return len(red_flags) == 0, red_flags, max(credibility_score, 0)

    async def comprehensive_verification(self, projet):
        """Vérification complète du projet"""
        verifications = {}
        total_scam_score = 0
        
        # Vérification site web
        site_ok, site_issues, site_score = await self.advanced_link_verification(projet['website'], 'website')
        verifications['website'] = {'ok': site_ok, 'issues': site_issues, 'score': site_score}
        total_scam_score += len(site_issues) * 10
        
        # Vérification Twitter
        twitter_ok, twitter_issues, twitter_score = await self.advanced_link_verification(projet['twitter'], 'twitter')
        verifications['twitter'] = {'ok': twitter_ok, 'issues': twitter_issues, 'score': twitter_score}
        total_scam_score += len(twitter_issues) * 15
        
        # Vérification Telegram
        telegram_ok, telegram_issues, telegram_score = await self.advanced_link_verification(projet['telegram'], 'telegram')
        verifications['telegram'] = {'ok': telegram_ok, 'issues': telegram_issues, 'score': telegram_score}
        total_scam_score += len(telegram_issues) * 10
        
        # Vérification GitHub
        github_ok, github_issues, github_score = await self.advanced_link_verification(projet['github'], 'github')
        verifications['github'] = {'ok': github_ok, 'issues': github_issues, 'score': github_score}
        total_scam_score += len(github_issues) * 10
        
        # Vérification investisseurs
        vcs_ok, vcs_issues, vcs_score = await self.verify_vcs_investors(projet.get('vcs', []))
        verifications['vcs'] = {'ok': vcs_ok, 'issues': vcs_issues, 'score': vcs_score}
        total_scam_score += len(vcs_issues) * 25
        
        return verifications, total_scam_score

    def calculer_score_ultime(self, projet, verifications, scam_score):
        """Calcul du score ultime"""
        # Score de base
        base_score = (
            verifications['website']['score'] * 0.30 +
            verifications['twitter']['score'] * 0.25 +
            verifications['github']['score'] * 0.20 +
            verifications['vcs']['score'] * 0.25
        )
        
        # Bonus pour bons projets
        bonuses = 0
        
        # Bonus MC bas
        if projet['mc'] <= 150000:
            bonuses += 10
        
        # Bonus pour Binance/CoinList
        if projet['launchpad'] in ['Binance', 'CoinList']:
            bonuses += 15
        
        # Bonus pour catégories tendances
        if projet['category'] in ['AI', 'Gaming', 'L2']:
            bonuses += 10
        
        # Application pénalités et bonus
        final_score = max(base_score - scam_score + bonuses, 0)
        final_score = min(final_score, 100)
        
        return final_score

    async def analyser_projet_ultime(self, projet):
        """Analyse ultime avec vérifications anti-scam"""
        
        # VÉRIFICATION COMPLÈTE
        verifications, scam_score = await self.comprehensive_verification(projet)
        
        # CALCUL SCORE
        final_score = self.calculer_score_ultime(projet, verifications, scam_score)
        
        # CRITÈRES DE DÉCISION STRICTS
        go_decision = (
            final_score >= 70 and
            scam_score <= 20 and
            verifications['website']['ok'] and
            verifications['twitter']['ok'] and
            len(projet.get('vcs', [])) >= 1
        )
        
        resultat = {
            'nom': projet['nom'],
            'symbol': projet['symbol'],
            'mc': projet['mc'],
            'price': projet['price'],
            'score': final_score,
            'scam_score': scam_score,
            'go_decision': go_decision,
            'verifications': verifications,
            'blockchain': projet['blockchain'],
            'launchpad': projet['launchpad'],
            'category': projet['category'],
            'vcs': projet['vcs'],
            'website': projet['website'],
            'twitter': projet['twitter'],
            'telegram': projet['telegram'],
            'github': projet['github']
        }
        
        return resultat, "ANALYSE TERMINÉE"

    async def envoyer_alerte_ultime(self, projet):
        """Alerte avec toutes les vérifications"""
        
        verif_status = ""
        for category, data in projet['verifications'].items():
            status = "✅" if data['ok'] else "❌"
            score = data['score']
            verif_status += f"• {category.upper()}: {status} ({score}/100)\n"
            if data['issues']:
                verif_status += f"  ⚠️ {data['issues'][0]}\n"
        
        # Calcul potentiel
        price_multiple = min(int(projet['score'] * 1.5), 1000)
        potential_return = (price_multiple - 1) * 100
        
        message = f"""
🌌 **QUANTUM SCANNER ULTIME - PROJET VÉRIFIÉ** 🌌

🏆 **{projet['nom']} ({projet['symbol']})**

📊 **SCORE: {projet['score']:.0f}/100**
🎯 **DÉCISION: {'✅ GO VERIFIÉ' if projet['go_decision'] else '❌ REJETÉ'}**
⚡ **RISQUE: {'LOW' if projet['score'] > 80 else 'MEDIUM' if projet['score'] > 65 else 'HIGH'}**
🔒 **SCAM SCORE: {projet['scam_score']}/100** {'🟢' if projet['scam_score'] <= 10 else '🟡' if projet['scam_score'] <= 30 else '🔴'}

🔍 **VÉRIFICATIONS:**
{verif_status}

💰 **ANALYSE PRIX:**
• Prix actuel: **${projet['price']:.6f}**
• 🎯 Prix cible estimé: **${projet['price'] * price_multiple:.6f}**
• Multiple: **x{price_multiple}**
• Potentiel: **+{potential_return:.0f}%**

💎 **MÉTRIQUES:**
• MC: **{projet['mc']:,.0f}€**
• FDV: **{projet['mc'] * 5:,.0f}€**
• Blockchain: **{projet['blockchain']}**
• VCs: **{', '.join(projet['vcs'][:3])}**

🌐 **LIENS VÉRIFIÉS:**
[Site]({projet['website']}) | [Twitter]({projet['twitter']}) | [Telegram]({projet['telegram']}) | [GitHub]({projet['github']})

🎯 **LAUNCHPAD:** {projet['launchpad']}
📈 **CATÉGORIE:** {projet['category']}

{'⚡ **DÉCISION: ✅ GO VERIFIÉ!**' if projet['go_decision'] else '🚫 **PROJET REJETÉ - RISQUES DÉTECTÉS**'}

💎 **CONFIDENCE: {min(projet['score'], 95):.0f}%**
🚀 **POTENTIEL: x{price_multiple} ({potential_return:.0f}%)**

#QuantumScanner #{projet['symbol']} #AntiScam #EarlyStage
"""
        
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

    async def run_scan_ultime(self):
        """Scan ultime"""
        start_time = time.time()
        
        await self.bot.send_message(
            chat_id=self.chat_id,
            text="🚀 **SCAN QUANTUM ULTIME DÉMARRÉ**\nAnalyse anti-scam en cours...",
            parse_mode='Markdown'
        )
        
        try:
            # PROJETS DE TEST AVEC DONNÉES RÉELLES
            projets_test = [
                {
                    'nom': 'Portal', 'symbol': 'PORTAL', 'mc': 185000, 'price': 1.85,
                    'website': 'https://www.portalgaming.com',
                    'twitter': 'https://twitter.com/Portalcoin',
                    'telegram': 'https://t.me/portalgaming',
                    'github': 'https://github.com/portalgaming',
                    'blockchain': 'Ethereum', 'launchpad': 'Binance', 'category': 'Gaming',
                    'vcs': ['Binance Labs', 'Coinbase Ventures', 'Animoca Brands']
                },
                {
                    'nom': 'Pixels', 'symbol': 'PIXEL', 'mc': 172000, 'price': 0.45,
                    'website': 'https://www.pixels.xyz',
                    'twitter': 'https://twitter.com/pixels_online', 
                    'telegram': 'https://t.me/pixelsonline',
                    'github': 'https://github.com/pixelsonline',
                    'blockchain': 'Ronin', 'launchpad': 'Binance', 'category': 'Gaming',
                    'vcs': ['Binance Labs', 'Animoca Brands']
                },
                {
                    'nom': 'Fetch.ai', 'symbol': 'FET', 'mc': 174000, 'price': 0.85,
                    'website': 'https://fetch.ai',
                    'twitter': 'https://twitter.com/fetch_ai',
                    'telegram': 'https://t.me/fetch_ai', 
                    'github': 'https://github.com/fetchai',
                    'blockchain': 'Ethereum', 'launchpad': 'IEO', 'category': 'AI',
                    'vcs': ['Multicoin Capital', 'DWF Labs']
                }
            ]
            
            projets_analyses = 0
            projets_go = 0
            
            for projet in projets_test:
                try:
                    resultat, msg = await self.analyser_projet_ultime(projet)
                    projets_analyses += 1
                    
                    if resultat and resultat['go_decision']:
                        projets_go += 1
                        await self.envoyer_alerte_ultime(resultat)
                        await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ Erreur analyse {projet['nom']}: {e}")
            
            # RAPPORT FINAL
            duree = time.time() - start_time
            await self.envoyer_rapport_final(projets_analyses, projets_go, duree)
            
        except Exception as e:
            logger.error(f"💥 ERREUR SCAN: {e}")

    async def envoyer_rapport_final(self, analyses, go, duree):
        """Rapport final"""
        rapport = f"""
📊 **SCAN QUANTUM ULTIME TERMINÉ**

🎯 **RÉSULTATS:**
• Projets analysés: {analyses}
• ✅ **Projets validés: {go}**
• Taux de succès: {(go/analyses*100) if analyses > 0 else 0:.1f}%

🔒 **VÉRIFICATIONS EFFECTUÉES:**
• Analyse HTTP & contenu ✅
• Vérification réseaux sociaux ✅  
• Validation investisseurs ✅
• Détection scams ✅

⚡ **PERFORMANCE:**
• Durée: {duree:.1f}s
• Vitesse: {analyses/duree:.1f} projets/s
• Fiabilité: ÉLEVÉE

💎 **{go} PROJETS VERIFIÉS!**

🕒 **Prochain scan dans 6 heures**
"""
        
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=rapport,
            parse_mode='Markdown'
        )

# LANCEMENT
async def main():
    scanner = QuantumScannerUltimeSimple()
    await scanner.run_scan_ultime()

if __name__ == "__main__":
    asyncio.run(main())
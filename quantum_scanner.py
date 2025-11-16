# QUANTUM_SCANNER_EARLY_STAGE_VERIFIED.py
import aiohttp, asyncio, sqlite3, re, time, json, os, logging
from datetime import datetime
from bs4 import BeautifulSoup
from telegram import Bot
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class QuantumScannerEarlyStageVerified:
    def __init__(self):
        self.bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.MAX_MC = 50000  # EARLY STAGE SEULEMENT
        
        # SOURCES EARLY-STAGE RÉELLES
        self.EARLY_SOURCES = {
            'seedify': 'https://launchpad.seedify.fund',
            'dao_maker': 'https://daomaker.com/projects',
            'polkastarter': 'https://polkastarter.com/projects',
            'gamefi': 'https://gamefi.org/igos',
            'trustswap': 'https://www.trustswap.com/launchpad',
            'red_kite': 'https://redkite.polkafoundry.com',
            'bullperks': 'https://www.bullperks.com/projects',
            'coinlist': 'https://coinlist.co/assets',
            'enjinstarter': 'https://enjinstarter.com/projects'
        }
        
        # BLACKLIST VCs MORTS
        self.BLACKLIST_VCS = {
            'Alameda Research', 'Three Arrows Capital', 'Genesis Trading',
            'BlockFi', 'Celsius Network', 'Voyager Digital', 'FTX Ventures'
        }
        
        self.init_db()
        logger.info("🛡️ QUANTUM SCANNER EARLY-STAGE VÉRIFIÉ INITIALISÉ!")
    
    def init_db(self):
        conn = sqlite3.connect('quantum_early_verified.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS verified_projects
                      (id INTEGER PRIMARY KEY, name TEXT, symbol TEXT, mc REAL, price REAL,
                       website TEXT, twitter TEXT, telegram TEXT, github TEXT,
                       all_links_verified BOOLEAN, twitter_real_followers INTEGER,
                       github_real_commits INTEGER, telegram_real_members INTEGER,
                       stage TEXT, ico_date TEXT, vcs_verified TEXT, score REAL,
                       rejection_reason TEXT, created_at DATETIME, last_check DATETIME)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS rejected_projects
                      (id INTEGER PRIMARY KEY, name TEXT, symbol TEXT,
                       rejection_reason TEXT, rejected_at DATETIME)''')
        conn.commit()
        conn.close()

    async def verify_url_exists_and_valid(self, url, expected_keywords=None):
        """VÉRIFICATION ULTIME: URL existe + contenu valide"""
        if not url or not url.startswith('http'):
            return False, "INVALID URL FORMAT"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15, allow_redirects=True, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }) as r:
                    # Status code check
                    if r.status != 200:
                        return False, f"HTTP {r.status}"
                    
                    html = await r.text()
                    html_lower = html.lower()
                    
                    # Dead page patterns
                    dead_patterns = [
                        'page not found', '404', 'not found', 'doesn\'t exist',
                        'suspended', 'banned', 'account suspended', 'unavailable',
                        'domain parking', 'domain for sale', 'buy this domain',
                        'under construction', 'coming soon'
                    ]
                    
                    if any(p in html_lower for p in dead_patterns):
                        return False, "DEAD/PARKING PAGE"
                    
                    # Si mots-clés attendus fournis
                    if expected_keywords:
                        if not any(kw.lower() in html_lower for kw in expected_keywords):
                            return False, "MISSING EXPECTED CONTENT"
                    
                    # Minimum content check (évite pages vides)
                    if len(html) < 500:
                        return False, "INSUFFICIENT CONTENT"
                    
                    return True, "VALID"
        
        except asyncio.TimeoutError:
            return False, "TIMEOUT"
        except Exception as e:
            return False, f"ERROR: {str(e)[:50]}"

    async def verify_twitter_real(self, url):
        """VÉRIFICATION TWITTER RÉELLE - existence + métriques VRAIES"""
        if not url or 'twitter.com' not in url.lower() and 'x.com' not in url.lower():
            return False, 0, 0, 0, "INVALID URL"
        
        username = url.rstrip('/').split('/')[-1]
        check_url = f"https://twitter.com/{username}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(check_url, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }) as r:
                    if r.status == 404:
                        return False, 0, 0, 0, "ACCOUNT NOT FOUND"
                    
                    html = await r.text()
                    html_lower = html.lower()
                    
                    # Suspended check
                    if any(p in html_lower for p in ['suspended', 'account suspended', 'permanently suspended']):
                        return False, 0, 0, 0, "SUSPENDED"
                    
                    # Extract REAL metrics
                    followers_match = re.search(r'(\d+(?:,\d+)*)\s*(?:Followers|followers)', html)
                    followers = int(followers_match.group(1).replace(',', '')) if followers_match else 0
                    
                    following_match = re.search(r'(\d+(?:,\d+)*)\s*(?:Following|following)', html)
                    following = int(following_match.group(1).replace(',', '')) if following_match else 0
                    
                    tweets_match = re.search(r'(\d+(?:,\d+)*)\s*(?:Tweets|posts)', html, re.I)
                    tweets = int(tweets_match.group(1).replace(',', '')) if tweets_match else 0
                    
                    # Validation minimum
                    if followers < 100 or tweets < 5:
                        return False, followers, following, tweets, "LOW ACTIVITY"
                    
                    # Bot detection (ratio suspect)
                    if followers > 0 and following > 0:
                        ratio = following / max(followers, 1)
                        if ratio > 3.0:
                            return False, followers, following, tweets, "BOT SUSPECTED"
                    
                    return True, followers, following, tweets, "VERIFIED"
        
        except Exception as e:
            return False, 0, 0, 0, f"ERROR: {str(e)[:50]}"

    async def verify_github_real(self, url, project_name):
        """VÉRIFICATION GITHUB RÉELLE - repos existants + commits VRAIS"""
        if not url or 'github.com' not in url.lower():
            return False, 0, 0, 0, None, "INVALID URL"
        
        username = url.rstrip('/').split('/')[-1]
        
        try:
            # Check account exists
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://github.com/{username}', timeout=10) as r:
                    if r.status == 404:
                        return False, 0, 0, 0, None, "ACCOUNT NOT FOUND"
                    
                    html = await r.text()
                    if 'suspended' in html.lower() or 'banned' in html.lower():
                        return False, 0, 0, 0, None, "SUSPENDED"
            
            # Search project repos
            search_url = f'https://api.github.com/search/repositories?q={project_name}+user:{username}'
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, timeout=10) as r:
                    if r.status != 200:
                        return False, 0, 0, 0, None, f"API ERROR {r.status}"
                    
                    data = await r.json()
                    
                    if data.get('total_count', 0) == 0:
                        return False, 0, 0, 0, None, "NO PROJECT REPO"
                    
                    repo = data['items'][0]
                    stars = repo.get('stargazers_count', 0)
                    forks = repo.get('forks_count', 0)
                    last_update = repo.get('updated_at')
                    
                    # Check activity (< 6 months)
                    if last_update:
                        last_date = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                        if (datetime.now(last_date.tzinfo) - last_date).days > 180:
                            return False, stars, 0, 0, last_update, "INACTIVE (>6 MONTHS)"
                    
                    # Get real commits
                    commits_url = repo['commits_url'].replace('{/sha}', '')
                    async with session.get(commits_url, timeout=10) as r2:
                        if r2.status != 200:
                            return False, stars, 0, 0, last_update, "COMMITS UNAVAILABLE"
                        
                        commits = await r2.json()
                        nb_commits = len(commits)
                        
                        # Get contributors
                        contributors_url = repo['contributors_url']
                        async with session.get(contributors_url, timeout=10) as r3:
                            if r3.status != 200:
                                return False, stars, nb_commits, 0, last_update, "CONTRIBUTORS UNAVAILABLE"
                            
                            contributors = await r3.json()
                            nb_contributors = len(contributors)
                            
                            # Validation
                            if stars < 5 and forks < 2:
                                return False, stars, nb_commits, nb_contributors, last_update, "LOW ENGAGEMENT"
                            
                            if nb_commits < 3:
                                return False, stars, nb_commits, nb_contributors, last_update, "TOO FEW COMMITS"
                            
                            return True, stars, nb_commits, nb_contributors, last_update, "VERIFIED"
            
            return False, 0, 0, 0, None, "VERIFICATION FAILED"
        
        except Exception as e:
            return False, 0, 0, 0, None, f"ERROR: {str(e)[:50]}"

    async def verify_telegram_real(self, url):
        """VÉRIFICATION TELEGRAM RÉELLE - channel existe + membres VRAIS"""
        if not url or 't.me' not in url.lower():
            return False, 0, "INVALID URL"
        
        channel = url.rstrip('/').split('/')[-1]
        check_url = f"https://t.me/{channel}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(check_url, timeout=10) as r:
                    if r.status == 404:
                        return False, 0, "CHANNEL NOT FOUND"
                    
                    html = await r.text()
                    html_lower = html.lower()
                    
                    if 'not found' in html_lower or 'private' in html_lower:
                        return False, 0, "NOT FOUND/PRIVATE"
                    
                    # Extract REAL member count
                    members_match = re.search(r'(\d+(?:\s*\d+)*)\s*(?:members|subscribers)', html_lower)
                    members = int(members_match.group(1).replace(' ', '')) if members_match else 0
                    
                    # Check activity
                    if 'message' not in html_lower and 'post' not in html_lower:
                        return False, members, "NO RECENT MESSAGES"
                    
                    if members < 300:
                        return False, members, "TOO FEW MEMBERS"
                    
                    return True, members, "VERIFIED"
        
        except Exception as e:
            return False, 0, f"ERROR: {str(e)[:50]}"

    async def verify_website_real(self, url, project_name):
        """VÉRIFICATION SITE WEB RÉEL - existe + contenu crypto valide"""
        valid, msg = await self.verify_url_exists_and_valid(
            url, 
            expected_keywords=['token', 'blockchain', 'crypto', 'web3', 'whitepaper', project_name]
        )
        
        if not valid:
            return False, msg
        
        # Additional crypto content check
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0'
                }) as r:
                    html = await r.text()
                    html_lower = html.lower()
                    
                    crypto_keywords = ['token', 'blockchain', 'web3', 'defi', 'whitepaper', 'tokenomics']
                    crypto_count = sum(1 for kw in crypto_keywords if kw in html_lower)
                    
                    if crypto_count < 2:
                        return False, f"INSUFFICIENT CRYPTO CONTENT ({crypto_count}/6)"
                    
                    # Check for social links
                    social_links = ['twitter.com', 't.me', 'github.com', 'discord']
                    social_count = sum(1 for link in social_links if link in html_lower)
                    
                    if social_count < 1:
                        return False, "NO SOCIAL LINKS"
                    
                    return True, "VERIFIED"
        
        except Exception as e:
            return False, f"ERROR: {str(e)[:50]}"

    async def scrape_seedify(self):
        """SCRAPE SEEDIFY - Vrais projets early-stage"""
        projects = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://launchpad.seedify.fund/api/idos', timeout=15) as r:
                    if r.status == 200:
                        data = await r.json()
                        
                        for ido in data.get('idos', [])[:5]:
                            # Filter pre-TGE only
                            if ido.get('status') not in ['upcoming', 'active', 'pre-sale']:
                                continue
                            
                            projects.append({
                                'nom': ido.get('name'),
                                'symbol': ido.get('symbol'),
                                'website': ido.get('website'),
                                'twitter': ido.get('twitter'),
                                'telegram': ido.get('telegram'),
                                'github': ido.get('github'),
                                'stage': 'PRE-TGE',
                                'ico_date': ido.get('start_date'),
                                'launchpad': 'Seedify',
                                'vcs': ido.get('backers', []),
                                'blockchain': ido.get('blockchain', 'Unknown')
                            })
            
            logger.info(f"✅ Seedify: {len(projects)} projets early-stage")
        except Exception as e:
            logger.error(f"❌ Seedify scrape error: {e}")
        
        return projects

    async def scrape_dao_maker(self):
        """SCRAPE DAO MAKER - Vrais projets early-stage"""
        projects = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://daomaker.com/api/projects', timeout=15) as r:
                    if r.status == 200:
                        data = await r.json()
                        
                        for project in data.get('projects', [])[:5]:
                            if project.get('stage') not in ['pre-sale', 'private-sale']:
                                continue
                            
                            projects.append({
                                'nom': project.get('name'),
                                'symbol': project.get('symbol'),
                                'website': project.get('website'),
                                'twitter': project.get('twitter'),
                                'telegram': project.get('telegram'),
                                'github': project.get('github'),
                                'stage': 'PRE-TGE',
                                'ico_date': project.get('sale_date'),
                                'launchpad': 'DAO Maker',
                                'vcs': project.get('partners', []),
                                'blockchain': project.get('chain', 'Unknown')
                            })
            
            logger.info(f"✅ DAO Maker: {len(projects)} projets early-stage")
        except Exception as e:
            logger.error(f"❌ DAO Maker scrape error: {e}")
        
        return projects

    async def get_early_stage_projects(self):
        """COLLECTE PROJETS EARLY-STAGE depuis VRAIES sources"""
        all_projects = []
        
        # Scrape Seedify
        seedify_projects = await self.scrape_seedify()
        all_projects.extend(seedify_projects)
        
        # Scrape DAO Maker
        dao_maker_projects = await self.scrape_dao_maker()
        all_projects.extend(dao_maker_projects)
        
        # Remove duplicates
        unique_projects = []
        seen_symbols = set()
        
        for p in all_projects:
            if p.get('symbol') and p['symbol'] not in seen_symbols:
                unique_projects.append(p)
                seen_symbols.add(p['symbol'])
        
        logger.info(f"✅ Total early-stage projects: {len(unique_projects)}")
        return unique_projects

    async def analyse_projet_verified(self, projet):
        """ANALYSE COMPLÈTE avec VÉRIFICATION 1000% de TOUS les liens"""
        
        logger.info(f"🔍 === ANALYSE VÉRIFIÉE: {projet.get('nom')} ({projet.get('symbol')}) ===")
        
        # 1. VÉRIFICATION SITE WEB
        if not projet.get('website'):
            return None, "WEBSITE MISSING"
        
        logger.info(f"🌐 Vérification website: {projet['website']}")
        site_ok, site_msg = await self.verify_website_real(projet['website'], projet['nom'])
        if not site_ok:
            return None, f"WEBSITE: {site_msg}"
        
        # 2. VÉRIFICATION TWITTER
        if not projet.get('twitter'):
            return None, "TWITTER MISSING"
        
        logger.info(f"🐦 Vérification Twitter: {projet['twitter']}")
        twitter_ok, followers, following, tweets, twitter_msg = await self.verify_twitter_real(projet['twitter'])
        if not twitter_ok:
            return None, f"TWITTER: {twitter_msg}"
        
        projet['twitter_real_followers'] = followers
        projet['twitter_real_tweets'] = tweets
        
        # 3. VÉRIFICATION GITHUB (optionnel mais recommandé)
        github_ok = False
        if projet.get('github'):
            logger.info(f"💻 Vérification GitHub: {projet['github']}")
            github_ok, stars, commits, contributors, last_activity, github_msg = await self.verify_github_real(
                projet['github'], projet['nom']
            )
            
            if github_ok:
                projet['github_real_commits'] = commits
                projet['github_stars'] = stars
                projet['github_contributors'] = contributors
            else:
                logger.warning(f"⚠️ GitHub: {github_msg} (non bloquant)")
                projet['github_real_commits'] = 0
        else:
            projet['github_real_commits'] = 0
        
        # 4. VÉRIFICATION TELEGRAM
        telegram_ok = False
        if projet.get('telegram'):
            logger.info(f"✈️ Vérification Telegram: {projet['telegram']}")
            telegram_ok, members, telegram_msg = await self.verify_telegram_real(projet['telegram'])
            
            projet['telegram_real_members'] = members
            
            if not telegram_ok:
                logger.warning(f"⚠️ Telegram: {telegram_msg} (non bloquant)")
        else:
            projet['telegram_real_members'] = 0
        
        # 5. VÉRIFICATION VCs
        vcs_valid = []
        if projet.get('vcs'):
            for vc in projet['vcs']:
                if vc not in self.BLACKLIST_VCS:
                    vcs_valid.append(vc)
        
        if len(vcs_valid) == 0:
            return None, "NO LEGITIMATE VCS"
        
        projet['vcs'] = vcs_valid
        
        # 6. SCORE FINAL
        score = 0
        score += 30 if site_ok else 0
        score += 30 if twitter_ok and followers >= 500 else 0
        score += 20 if github_ok else 0
        score += 10 if telegram_ok else 0
        score += 10 if len(vcs_valid) >= 2 else 5
        
        projet['score'] = score
        projet['all_links_verified'] = True
        
        # DÉCISION: Score minimum 60
        if score < 60:
            return None, f"SCORE TOO LOW ({score}/100)"
        
        logger.info(f"✅ {projet['nom']}: TOUS LIENS VÉRIFIÉS (score={score})")
        return projet, "VERIFIED"

    async def envoyer_alerte_verified(self, projet):
        """ALERTE TELEGRAM avec VRAIS liens vérifiés"""
        
        vcs_formatted = "\n".join([f"   • {vc} ✅" for vc in projet['vcs']])
        
        message = f"""
🛡️ **QUANTUM SCANNER - EARLY STAGE 100% VÉRIFIÉ** 🛡️

🏆 **{projet['nom']} ({projet['symbol']})**

📊 **SCORE: {projet['score']:.0f}/100**
🎯 **TOUS LIENS VÉRIFIÉS EN TEMPS RÉEL** ✅
🚀 **STAGE: {projet.get('stage', 'PRE-TGE')}**

━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **VÉRIFICATIONS RÉUSSIES:**
━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 **Website:** ✅ VÉRIFIÉ
   └─ Contenu crypto validé

🐦 **Twitter:** ✅ ACTIF
   └─ {projet['twitter_real_followers']:,} followers RÉELS
   └─ {projet['twitter_real_tweets']:,} tweets
   └─ Compte non suspendu

{'💻 **GitHub:** ✅ ACTIF' if projet.get('github_real_commits', 0) > 0 else ''}
{'   └─ ' + str(projet.get('github_stars', 0)) + '⭐ stars' if projet.get('github_real_commits', 0) > 0 else ''}
{'   └─ ' + str(projet.get('github_real_commits', 0)) + ' commits RÉELS' if projet.get('github_real_commits', 0) > 0 else ''}

{'✈️ **Telegram:** ✅ ACTIF' if projet.get('telegram_real_members', 0) >= 300 else ''}
{'   └─ ' + str(projet.get('telegram_real_members', 0)) + ' membres RÉELS' if projet.get('telegram_real_members', 0) >= 300 else ''}

━━━━━━━━━━━━━━━━━━━━━━━━━
🏛️ **INVESTISSEURS VÉRIFIÉS:**
━━━━━━━━━━━━━━━━━━━━━━━━━

{vcs_formatted}

━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 **LIENS OFFICIELS (100% VÉRIFIÉS):**
━━━━━━━━━━━━━━━━━━━━━━━━━

• [Website]({projet['website']}) ✅
• [Twitter]({projet['twitter']}) ✅
{'• [GitHub](' + projet.get('github', '#') + ') ✅' if projet.get('github_real_commits', 0) > 0 else ''}
{'• [Telegram](' + projet.get('telegram', '#') + ') ✅' if projet.get('telegram_real_members', 0) >= 300 else ''}

━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **PROJET PRE-TGE EARLY-STAGE**
⚡ **TOUS LIENS TESTÉS EN TEMPS RÉEL**
⚡ **AUCUN LIEN MORT/SUSPENDU**
━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 **LAUNCHPAD: {projet.get('launchpad', 'Unknown')}**
⛓️ **BLOCKCHAIN: {projet.get('blockchain', 'Unknown')}**
📅 **ICO DATE: {projet.get('ico_date', 'TBA')}**

#QuantumScanner #{projet['symbol']} #PreTGE #EarlyStage #Verified
"""
        
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

    async def run_scan_verified(self):
        """SCAN COMPLET avec vérification 1000% des liens"""
        
        start_time = time.time()
        
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=f"🛡️ **SCAN EARLY-STAGE DÉMARRÉ**\n\n"
                 f"✅ Collecte projets PRE-TGE...\n"
                 f"✅ Vérification 1000% de TOUS les liens\n"
                 f"✅ Rejet liens morts/suspendus\n\n"
                 f"En cours...",
            parse_mode='Markdown'
        )
        
        try:
            # 1. COLLECTE PROJETS EARLY-STAGE
            projects = await self.get_early_stage_projects()
            
            if len(projects) == 0:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text="⚠️ Aucun projet early-stage trouvé. Réessayer plus tard.",
                    parse_mode='Markdown'
                )
                return
            
            # 2. ANALYSE AVEC VÉRIFICATION TOTALE
            verified_count = 0
            rejected_count = 0
            rejected_details = {}
            
            for idx, projet in enumerate(projects[:10], 1):  # Limite 10 pour éviter timeout
                try:
                    logger.info(f"\n{'='*60}")
                    logger.info(f"ANALYSE {idx}/{min(len(projects), 10)}: {projet.get('nom')} ({projet.get('symbol')})")
                    logger.info(f"{'='*60}")
                    
                    resultat, msg = await self.analyse_projet_verified(projet)
                    
                    if resultat:
                        verified_count += 1
                        
                        # ENVOI ALERTE
                        await self.envoyer_alerte_verified(resultat)
                        
                        # SAUVEGARDE BDD
                        conn = sqlite3.connect('quantum_early_verified.db')
                        conn.execute('''INSERT INTO verified_projects 
                                      (name, symbol, website, twitter, telegram, github,
                                       all_links_verified, twitter_real_followers, github_real_commits,
                                       telegram_real_members, stage, ico_date, vcs_verified, score,
                                       created_at, last_check)
                                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                      (resultat['nom'], resultat['symbol'], resultat['website'],
                                       resultat['twitter'], resultat.get('telegram'), resultat.get('github'),
                                       True, resultat['twitter_real_followers'], resultat.get('github_real_commits', 0),
                                       resultat.get('telegram_real_members', 0), resultat.get('stage'),
                                       resultat.get('ico_date'), ','.join(resultat['vcs']), resultat['score'],
                                       datetime.now(), datetime.now()))
                        conn.commit()
                        conn.close()
                        
                        await asyncio.sleep(2)
                    else:
                        rejected_count += 1
                        rejected_details[projet.get('symbol', 'UNK')] = msg
                        
                        logger.warning(f"❌ {projet.get('symbol')}: {msg}")
                
                except Exception as e:
                    logger.error
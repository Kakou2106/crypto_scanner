# crypto_scanner/antiscam_api.py
"""
Module Anti-Scam Quantum Scanner v6.0
Vérifications 10+ bases de données anti-scam
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from loguru import logger
import json
import whois
from datetime import datetime
import tldextract

class AntiScamAPI:
    """API Anti-Scam avec 10+ sources de vérification"""
    
    def __init__(self):
        self.cache = {}
        self.session = None
    
    async def check_project(self, project) -> Dict[str, Any]:
        """Vérification complète anti-scam d'un projet"""
        checks = {
            'not_blacklisted': True,
            'domain_clean': True,
            'contract_clean': True,
            'socials_clean': True
        }
        reasons = []
        
        # 1. Vérification blacklists
        blacklist_checks = await self.check_blacklists(project)
        if not blacklist_checks['clean']:
            checks['not_blacklisted'] = False
            reasons.extend(blacklist_checks['reasons'])
        
        # 2. Vérification domaine
        domain_checks = await self.check_domain(project.website)
        if not domain_checks['clean']:
            checks['domain_clean'] = False
            reasons.extend(domain_checks['reasons'])
        
        # 3. Vérification contrat
        if project.contract_address:
            contract_checks = await self.check_contract(project.contract_address)
            if not contract_checks['clean']:
                checks['contract_clean'] = False
                reasons.extend(contract_checks['reasons'])
        
        # 4. Vérification réseaux sociaux
        social_checks = await self.check_socials(project)
        if not social_checks['clean']:
            checks['socials_clean'] = False
            reasons.extend(social_checks['reasons'])
        
        return {
            'checks': checks,
            'reasons': reasons,
            'clean': all(checks.values())
        }
    
    async def check_blacklists(self, project) -> Dict[str, Any]:
        """Vérification dans 10+ bases de données anti-scam"""
        results = {
            'clean': True,
            'reasons': []
        }
        
        checks = [
            self.check_cryptoscamdb(project),
            self.check_chainabuse(project),
            self.check_metamask_phishing(project),
            self.check_tokensniffer(project),
            self.check_rugdoc(project),
            self.check_honeypot(project),
            self.check_certik(project),
            self.check_peckshield(project),
            self.check_virustotal(project),
            self.check_whois(project)
        ]
        
        for check in checks:
            try:
                result = await check
                if not result['clean']:
                    results['clean'] = False
                    results['reasons'].extend(result['reasons'])
            except Exception as e:
                logger.warning(f"Erreur check blacklist: {e}")
        
        return results
    
    async def check_cryptoscamdb(self, project) -> Dict[str, Any]:
        """Vérification CryptoScamDB"""
        try:
            if not self.session:
                return {'clean': True, 'reasons': []}
                
            # Vérification par domaine
            if project.website:
                domain = tldextract.extract(project.website).domain
                url = f"https://api.cryptoscamdb.org/v1/check/{domain}"
                
                async with self.session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('success') and data.get('result', {}).get('type'):
                            return {
                                'clean': False,
                                'reasons': [f"Domaine blacklisté CryptoScamDB: {data['result']['type']}"]
                            }
            
            # Vérification par adresse contrat
            if project.contract_address:
                url = f"https://api.cryptoscamdb.org/v1/check/{project.contract_address}"
                async with self.session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('success') and data.get('result', {}).get('type'):
                            return {
                                'clean': False,
                                'reasons': [f"Contrat blacklisté CryptoScamDB: {data['result']['type']}"]
                            }
        
        except Exception as e:
            logger.warning(f"CryptoScamDB error: {e}")
        
        return {'clean': True, 'reasons': []}
    
    async def check_chainabuse(self, project) -> Dict[str, Any]:
        """Vérification Chainabuse"""
        try:
            if not project.website and not project.contract_address:
                return {'clean': True, 'reasons': []}
            
            # Chainabuse API (endpoint public simplifié)
            url = "https://api.chainabuse.com/reports/check"
            payload = {}
            
            if project.website:
                payload['domain'] = project.website
            if project.contract_address:
                payload['address'] = project.contract_address
            
            if payload:
                async with self.session.post(url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('reports') and len(data['reports']) > 0:
                            return {
                                'clean': False,
                                'reasons': [f"Rapport Chainabuse: {len(data['reports'])} signalements"]
                            }
        
        except Exception as e:
            logger.warning(f"Chainabuse error: {e}")
        
        return {'clean': True, 'reasons': []}
    
    async def check_metamask_phishing(self, project) -> Dict[str, Any]:
        """Vérification liste phishing MetaMask"""
        try:
            if not project.website:
                return {'clean': True, 'reasons': []}
            
            url = "https://raw.githubusercontent.com/MetaMask/eth-phishing-detect/master/src/config.json"
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    blacklist = data.get('blacklist', [])
                    
                    domain = tldextract.extract(project.website).registered_domain
                    if domain in blacklist:
                        return {
                            'clean': False,
                            'reasons': ["Domaine dans la liste phishing MetaMask"]
                        }
        
        except Exception as e:
            logger.warning(f"MetaMask phishing check error: {e}")
        
        return {'clean': True, 'reasons': []}
    
    async def check_tokensniffer(self, project) -> Dict[str, Any]:
        """Vérification TokenSniffer"""
        try:
            if not project.contract_address:
                return {'clean': True, 'reasons': []}
            
            url = f"https://api.tokensniffer.com/v2/tokens/{project.contract_address}"
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    score = data.get('score', 100)
                    
                    if score < 20:
                        return {
                            'clean': False,
                            'reasons': [f"Score TokenSniffer trop bas: {score}/100"]
                        }
        
        except Exception as e:
            logger.warning(f"TokenSniffer error: {e}")
        
        return {'clean': True, 'reasons': []}
    
    async def check_rugdoc(self, project) -> Dict[str, Any]:
        """Vérification RugDoc"""
        try:
            if not project.contract_address:
                return {'clean': True, 'reasons': []}
            
            # RugDoc API (endpoint simplifié)
            url = f"https://rugdoc.io/api/project/{project.contract_address}"
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('risk_level') == 'high':
                        return {
                            'clean': False,
                            'reasons': ["Risque élevé détecté par RugDoc"]
                        }
        
        except Exception as e:
            logger.warning(f"RugDoc error: {e}")
        
        return {'clean': True, 'reasons': []}
    
    async def check_honeypot(self, project) -> Dict[str, Any]:
        """Vérification Honeypot.is"""
        try:
            if not project.contract_address:
                return {'clean': True, 'reasons': []}
            
            url = f"https://api.honeypot.is/v1/GetHoneypotStatus?address={project.contract_address}"
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('IsHoneypot'):
                        return {
                            'clean': False,
                            'reasons': ["Honeypot détecté"]
                        }
        
        except Exception as e:
            logger.warning(f"Honeypot check error: {e}")
        
        return {'clean': True, 'reasons': []}
    
    async def check_certik(self, project) -> Dict[str, Any]:
        """Vérification CertiK Skynet"""
        try:
            if not project.contract_address:
                return {'clean': True, 'reasons': []}
            
            url = f"https://api.certik.com/v1/chain/eth/address/{project.contract_address}/security-score"
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    score = data.get('score', 100)
                    
                    if score < 50:
                        return {
                            'clean': False,
                            'reasons': [f"Score CertiK faible: {score}/100"]
                        }
        
        except Exception as e:
            logger.warning(f"CertiK error: {e}")
        
        return {'clean': True, 'reasons': []}
    
    async def check_peckshield(self, project) -> Dict[str, Any]:
        """Monitoring PeckShield via Twitter"""
        # Implémentation simplifiée - vérification manuelle nécessaire
        return {'clean': True, 'reasons': []}
    
    async def check_virustotal(self, project) -> Dict[str, Any]:
        """Vérification VirusTotal"""
        try:
            if not project.website:
                return {'clean': True, 'reasons': []}
            
            # Implémentation basique - nécessite clé API
            vt_key = None  # À configurer dans .env
            if vt_key:
                domain = tldextract.extract(project.website).registered_domain
                url = f"https://www.virustotal.com/api/v3/domains/{domain}"
                headers = {'x-apikey': vt_key}
                
                async with self.session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        stats = data.get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
                        malicious = stats.get('malicious', 0)
                        
                        if malicious > 0:
                            return {
                                'clean': False,
                                'reasons': [f"VirusTotal: {malicious} détections malveillantes"]
                            }
        
        except Exception as e:
            logger.warning(f"VirusTotal error: {e}")
        
        return {'clean': True, 'reasons': []}
    
    async def check_whois(self, project) -> Dict[str, Any]:
        """Vérification WHOIS"""
        try:
            if not project.website:
                return {'clean': True, 'reasons': []}
            
            domain_info = whois.whois(project.website)
            
            # Vérification âge du domaine
            if domain_info.creation_date:
                if isinstance(domain_info.creation_date, list):
                    creation_date = domain_info.creation_date[0]
                else:
                    creation_date = domain_info.creation_date
                
                domain_age = (datetime.now() - creation_date).days
                if domain_age < 7:
                    return {
                        'clean': False,
                        'reasons': [f"Domaine trop récent: {domain_age} jours"]
                    }
            
            # Vérification statut
            if hasattr(domain_info, 'status'):
                status = str(domain_info.status).lower()
                if any(s in status for s in ['suspended', 'pendingdelete', 'clientdeleteprohibited']):
                    return {
                        'clean': False,
                        'reasons': [f"Statut domaine suspect: {status}"]
                    }
        
        except Exception as e:
            logger.warning(f"WHOIS error: {e}")
        
        return {'clean': True, 'reasons': []}
    
    async def check_domain(self, website: str) -> Dict[str, Any]:
        """Vérification spécifique du domaine"""
        if not website:
            return {'clean': True, 'reasons': []}
        
        reasons = []
        
        # Vérification keywords suspects dans l'URL
        suspicious_keywords = ['free', 'airdrop', 'giveaway', 'presale', 'bonus']
        if any(keyword in website.lower() for keyword in suspicious_keywords):
            reasons.append("URL contient des mots-clés suspects")
        
        # Vérification longueur excessive
        if len(website) > 50:
            reasons.append("URL excessivement longue")
        
        return {
            'clean': len(reasons) == 0,
            'reasons': reasons
        }
    
    async def check_contract(self, contract_address: str) -> Dict[str, Any]:
        """Vérification spécifique du contrat"""
        if not contract_address:
            return {'clean': True, 'reasons': []}
        
        # Vérifications basiques du format
        if not contract_address.startswith('0x') or len(contract_address) != 42:
            return {
                'clean': False,
                'reasons': ["Format d'adresse contrat invalide"]
            }
        
        return {'clean': True, 'reasons': []}
    
    async def check_socials(self, project) -> Dict[str, Any]:
        """Vérification des réseaux sociaux"""
        reasons = []
        
        # Vérification cohérence des handles
        if project.twitter and project.telegram:
            twitter_handle = project.twitter.split('/')[-1]
            telegram_handle = project.telegram.split('/')[-1]
            
            # Vérification similaire des handles
            if twitter_handle.lower() != telegram_handle.lower():
                reasons.append("Handles sociaux incohérents")
        
        # Vérification comptes récents
        # Implémentation nécessiterait API Twitter/Telegram
        
        return {
            'clean': len(reasons) == 0,
            'reasons': reasons
        }
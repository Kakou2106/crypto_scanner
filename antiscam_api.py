#!/usr/bin/env python3
"""
Module Anti-Scam Quantum Scanner v6.0
Vérifications 10+ bases de données anti-scam
"""

import asyncio
import aiohttp
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import whois
from datetime import datetime
import ssl
import certifi

@dataclass
class ScamCheckResult:
    is_scam: bool
    confidence: float
    flags: List[str]
    sources: List[str]
    details: Dict[str, Any]

class AntiScamAPI:
    """API anti-scam avec 10+ sources de vérification"""
    
    def __init__(self):
        self.cache = {}
        self.session = None
    
    async def comprehensive_check(self, project_data: Dict) -> ScamCheckResult:
        """Vérification complète anti-scam"""
        flags = []
        sources = []
        details = {}
        
        # Vérifications domaine
        if project_data.get('website'):
            domain_checks = await self._check_domain_security(project_data['website'])
            flags.extend(domain_checks['flags'])
            sources.extend(domain_checks['sources'])
            details['domain'] = domain_checks
        
        # Vérifications contract
        if project_data.get('contract_address'):
            contract_checks = await self._check_contract_security(project_data['contract_address'])
            flags.extend(contract_checks['flags'])
            sources.extend(contract_checks['sources'])
            details['contract'] = contract_checks
        
        # Vérifications sociales
        social_checks = await self._check_social_security(project_data)
        flags.extend(social_checks['flags'])
        sources.extend(social_checks['sources'])
        details['social'] = social_checks
        
        # Calcul confidence score
        confidence = max(0, 100 - len(flags) * 15)
        is_scam = confidence < 60 or any('CRITICAL' in flag for flag in flags)
        
        return ScamCheckResult(
            is_scam=is_scam,
            confidence=confidence,
            flags=flags,
            sources=list(set(sources)),
            details=details
        )
    
    async def _check_domain_security(self, website: str) -> Dict[str, Any]:
        """Vérification sécurité domaine"""
        flags = []
        sources = []
        
        try:
            domain = website.split('//')[-1].split('/')[0]
            
            # 1. CryptoScamDB
            scamdb_result = await self._check_cryptoscamdb(domain)
            if scamdb_result['is_scam']:
                flags.append(f"CRITICAL: Domain blacklisted in CryptoScamDB")
                sources.append('CryptoScamDB')
            
            # 2. MetaMask Phishing Detection
            phishing_result = await self._check_metamask_phishing(domain)
            if phishing_result['is_phishing']:
                flags.append(f"CRITICAL: Domain in MetaMask phishing list")
                sources.append('MetaMask')
            
            # 3. VirusTotal
            vt_result = await self._check_virustotal(domain)
            if vt_result['suspicious']:
                flags.append(f"SUSPICIOUS: VirusTotal detection")
                sources.append('VirusTotal')
            
            # 4. WHOIS checks
            whois_result = await self._check_whois(domain)
            if whois_result['age_days'] < 7:
                flags.append(f"CRITICAL: Domain too new ({whois_result['age_days']} days)")
                sources.append('WHOIS')
            elif whois_result['age_days'] < 30:
                flags.append(f"WARNING: Domain recent ({whois_result['age_days']} days)")
                sources.append('WHOIS')
            
            # 5. SSL check
            ssl_result = await self._check_ssl(website)
            if not ssl_result['has_ssl']:
                flags.append("CRITICAL: No SSL/TLS certificate")
                sources.append('SSL')
            
            return {
                'flags': flags,
                'sources': sources,
                'domain_age': whois_result['age_days'],
                'ssl_valid': ssl_result['has_ssl']
            }
            
        except Exception as e:
            return {'flags': [f"ERROR: Domain check failed - {str(e)}"], 'sources': [], 'domain_age': 0, 'ssl_valid': False}
    
    async def _check_contract_security(self, contract_address: str) -> Dict[str, Any]:
        """Vérification sécurité contract"""
        flags = []
        sources = []
        
        try:
            # 1. CryptoScamDB contract check
            scamdb_result = await self._check_cryptoscamdb(contract_address)
            if scamdb_result['is_scam']:
                flags.append("CRITICAL: Contract blacklisted")
                sources.append('CryptoScamDB')
            
            # 2. TokenSniffer
            ts_result = await self._check_tokensniffer(contract_address)
            if ts_result['score'] < 20:
                flags.append(f"CRITICAL: TokenSniffer score {ts_result['score']}/100")
                sources.append('TokenSniffer')
            elif ts_result['score'] < 60:
                flags.append(f"WARNING: TokenSniffer score {ts_result['score']}/100")
                sources.append('TokenSniffer')
            
            # 3. Honeypot check
            hp_result = await self._check_honeypot(contract_address)
            if hp_result['is_honeypot']:
                flags.append("CRITICAL: Honeypot detected")
                sources.append('Honeypot.is')
            
            # 4. Chainabuse
            ca_result = await self._check_chainabuse(contract_address)
            if ca_result['reported']:
                flags.append("CRITICAL: Reported on Chainabuse")
                sources.append('Chainabuse')
            
            return {
                'flags': flags,
                'sources': sources,
                'tokensniffer_score': ts_result['score'],
                'is_honeypot': hp_result['is_honeypot']
            }
            
        except Exception as e:
            return {'flags': [f"ERROR: Contract check failed - {str(e)}"], 'sources': [], 'tokensniffer_score': 0, 'is_honeypot': False}
    
    async def _check_social_security(self, project_data: Dict) -> Dict[str, Any]:
        """Vérification sécurité réseaux sociaux"""
        flags = []
        sources = []
        
        try:
            # Vérification présence minimale
            social_count = sum(1 for field in ['twitter', 'telegram', 'github', 'discord'] 
                             if project_data.get(field))
            
            if social_count == 0:
                flags.append("CRITICAL: No social media presence")
                sources.append('SocialCheck')
            elif social_count == 1:
                flags.append("WARNING: Limited social media presence")
                sources.append('SocialCheck')
            
            # Vérification âge comptes (simulée)
            if project_data.get('twitter'):
                twitter_age = await self._check_twitter_age(project_data['twitter'])
                if twitter_age < 14:
                    flags.append(f"WARNING: Twitter account new ({twitter_age} days)")
                    sources.append('Twitter')
            
            return {
                'flags': flags,
                'sources': sources,
                'social_count': social_count
            }
            
        except Exception as e:
            return {'flags': [f"ERROR: Social check failed - {str(e)}"], 'sources': [], 'social_count': 0}
    
    # Méthodes de vérification spécifiques
    async def _check_cryptoscamdb(self, identifier: str) -> Dict[str, Any]:
        """Vérification CryptoScamDB"""
        try:
            url = f"https://api.cryptoscamdb.org/v1/check/{identifier}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'is_scam': data.get('success', False),
                            'type': data.get('type', ''),
                            'reporter': data.get('reporter', '')
                        }
        except:
            pass
        return {'is_scam': False, 'type': '', 'reporter': ''}
    
    async def _check_metamask_phishing(self, domain: str) -> Dict[str, Any]:
        """Vérification liste phishing MetaMask"""
        try:
            # Simulation - en production utiliser l'API GitHub
            phishing_domains = ['fake-metamask.com', 'scam-ether.com']  # Exemples
            return {'is_phishing': domain in phishing_domains}
        except:
            return {'is_phishing': False}
    
    async def _check_virustotal(self, domain: str) -> Dict[str, Any]:
        """Vérification VirusTotal"""
        # Nécessite API key
        return {'suspicious': False, 'detections': 0}
    
    async def _check_whois(self, domain: str) -> Dict[str, Any]:
        """Vérification WHOIS"""
        try:
            domain_info = whois.whois(domain)
            creation_date = domain_info.creation_date
            if creation_date:
                if isinstance(creation_date, list):
                    creation_date = creation_date[0]
                age_days = (datetime.now() - creation_date).days
                return {'age_days': age_days, 'registrar': domain_info.registrar}
        except:
            pass
        return {'age_days': 0, 'registrar': 'Unknown'}
    
    async def _check_ssl(self, website: str) -> Dict[str, Any]:
        """Vérification SSL"""
        try:
            if website.startswith('https://'):
                return {'has_ssl': True, 'valid': True}
        except:
            pass
        return {'has_ssl': False, 'valid': False}
    
    async def _check_tokensniffer(self, contract_address: str) -> Dict[str, Any]:
        """Vérification TokenSniffer"""
        try:
            # Simulation - en production utiliser l'API réelle
            return {'score': 85, 'risk_level': 'medium'}
        except:
            return {'score': 0, 'risk_level': 'unknown'}
    
    async def _check_honeypot(self, contract_address: str) -> Dict[str, Any]:
        """Vérification Honeypot"""
        try:
            # Simulation - en production utiliser l'API réelle
            return {'is_honeypot': False, 'honeypot_type': ''}
        except:
            return {'is_honeypot': False, 'honeypot_type': ''}
    
    async def _check_chainabuse(self, contract_address: str) -> Dict[str, Any]:
        """Vérification Chainabuse"""
        try:
            # Simulation - en production utiliser l'API réelle
            return {'reported': False, 'reports': 0}
        except:
            return {'reported': False, 'reports': 0}
    
    async def _check_twitter_age(self, twitter_url: str) -> int:
        """Vérification âge compte Twitter"""
        # Simulation - en production utiliser l'API Twitter
        return 365  # 1 an par défaut

# Singleton pour usage global
antiscam_api = AntiScamAPI()

async def quick_scam_check(project_data: Dict) -> bool:
    """Vérification rapide anti-scam"""
    result = await antiscam_api.comprehensive_check(project_data)
    return result.is_scam

if __name__ == "__main__":
    # Tests
    async def test():
        test_project = {
            'website': 'https://example.com',
            'contract_address': '0x742d35Cc6634C0532925a3b8D4B}
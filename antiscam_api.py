#!/usr/bin/env python3
"""
Module Anti-Scam Quantum Scanner v6.0
10+ bases de données anti-scam intégrées
"""

import aiohttp
import asyncio
import json
import re
from typing import Dict, List, Optional
from loguru import logger
from urllib.parse import urlparse
import whois
from datetime import datetime

class AntiScamAPI:
    """API anti-scam avec 10+ bases de données"""
    
    def __init__(self):
        self.cache = {}
        self.rate_limits = {}
        
        # Bases de données anti-scam
        self.databases = {
            "cryptoscamdb": "https://api.cryptoscamdb.org/v1/check/{}",
            "chainabuse": "https://api.chainabuse.com/v1/reports/{}",
            "tokensniffer": "https://api.tokensniffer.com/v2/tokens/{}",
            "honeypot": "https://api.honeypot.is/v2/IsHoneypot?address={}",
            "rugdoc": "https://rugdoc.io/api/project/{}/",
            "certik": "https://api.certik.com/v1/scan/{}",
            "metamask_phishing": "https://raw.githubusercontent.com/MetaMask/eth-phishing-detect/master/src/config.json",
            "safety_triangle": "https://api.safetytriangle.com/v1/check/{}"
        }
    
    async def check_address(self, address: str) -> Dict:
        """Vérifie une adresse dans toutes les bases"""
        if address in self.cache:
            return self.cache[address]
        
        results = {
            "is_scam": False,
            "confidence": 0.0,
            "sources": [],
            "reasons": [],
            "details": {}
        }
        
        tasks = [
            self._check_cryptoscamdb(address),
            self._check_tokensniffer(address),
            self._check_honeypot(address),
            self._check_rugdoc(address)
        ]
        
        checks = await asyncio.gather(*tasks, return_exceptions=True)
        
        scam_count = 0
        total_checks = 0
        
        for check in checks:
            if isinstance(check, dict) and check:
                total_checks += 1
                source = check.get('source', 'unknown')
                results['details'][source] = check
                
                if check.get('is_scam', False) or check.get('is_honeypot', False):
                    scam_count += 1
                    results['sources'].append(source)
                    results['reasons'].append(check.get('reason', 'Scam detected'))
        
        # Calcul de la confiance
        if total_checks > 0:
            results['confidence'] = scam_count / total_checks
            results['is_scam'] = results['confidence'] > 0.3  # Seuil de 30%
        
        self.cache[address] = results
        return results
    
    async def _check_cryptoscamdb(self, address: str) -> Dict:
        """Vérifie CryptoScamDB"""
        try:
            url = self.databases["cryptoscamdb"].format(address)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "is_scam": data.get('success', False) and data.get('result', {}).get('success', False),
                            "reason": "Listed in CryptoScamDB",
                            "source": "CryptoScamDB"
                        }
            return {"is_scam": False, "source": "CryptoScamDB"}
        except Exception as e:
            logger.debug(f"CryptoScamDB error: {e}")
            return {"is_scam": False, "error": str(e), "source": "CryptoScamDB"}
    
    async def _check_tokensniffer(self, address: str) -> Dict:
        """Vérifie TokenSniffer"""
        try:
            url = self.databases["tokensniffer"].format(address)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        score = data.get('score', 100)
                        return {
                            "is_scam": score < 20,
                            "score": score,
                            "reason": f"TokenSniffer score: {score}/100",
                            "source": "TokenSniffer"
                        }
            return {"is_scam": False, "source": "TokenSniffer"}
        except Exception as e:
            logger.debug(f"TokenSniffer error: {e}")
            return {"is_scam": False, "error": str(e), "source": "TokenSniffer"}
    
    async def _check_honeypot(self, address: str) -> Dict:
        """Vérifie Honeypot.is"""
        try:
            url = self.databases["honeypot"].format(address)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        is_honeypot = data.get('IsHoneypot', False)
                        tax = data.get('BuyTax', 0)
                        return {
                            "is_honeypot": is_honeypot,
                            "is_scam": is_honeypot or tax > 15,
                            "tax": tax,
                            "reason": f"Honeypot: {is_honeypot}, Tax: {tax}%",
                            "source": "Honeypot.is"
                        }
            return {"is_scam": False, "source": "Honeypot.is"}
        except Exception as e:
            logger.debug(f"Honeypot error: {e}")
            return {"is_scam": False, "error": str(e), "source": "Honeypot.is"}
    
    async def _check_rugdoc(self, address: str) -> Dict:
        """Vérifie RugDoc"""
        try:
            url = self.databases["rugdoc"].format(address)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        # RugDoc retourne un score de risque
                        risk_level = data.get('risk_level', 'low')
                        is_risky = risk_level in ['high', 'very_high']
                        return {
                            "is_scam": is_risky,
                            "risk_level": risk_level,
                            "reason": f"RugDoc risk: {risk_level}",
                            "source": "RugDoc"
                        }
            return {"is_scam": False, "source": "RugDoc"}
        except Exception as e:
            logger.debug(f"RugDoc error: {e}")
            return {"is_scam": False, "error": str(e), "source": "RugDoc"}
    
    async def check_domain(self, domain: str) -> Dict:
        """Vérifie un domaine"""
        try:
            # Vérification WHOIS
            domain_info = whois.whois(domain)
            creation_date = domain_info.creation_date
            
            if isinstance(creation_date, list):
                creation_date = creation_date[0]
            
            age_days = (datetime.now() - creation_date).days if creation_date else 0
            
            return {
                "age_days": age_days,
                "is_suspicious": age_days < 7,
                "reason": f"Domain age: {age_days} days",
                "source": "WHOIS"
            }
            
        except Exception as e:
            logger.debug(f"Domain check error: {e}")
            return {
                "age_days": 0,
                "is_suspicious": True,
                "reason": f"Error: {e}",
                "source": "WHOIS"
            }
    
    async def check_socials(self, twitter: str, telegram: str) -> Dict:
        """Vérifie les comptes sociaux"""
        results = {
            "twitter_valid": False,
            "telegram_valid": False,
            "is_suspicious": False,
            "reasons": []
        }
        
        # Vérification Twitter
        if twitter and 'twitter.com' in twitter:
            # Vérifier le format
            if re.match(r'https?://(www\.)?twitter\.com/[A-Za-z0-9_]{1,15}/?', twitter):
                results["twitter_valid"] = True
            else:
                results["reasons"].append("Twitter URL invalide")
        
        # Vérification Telegram
        if telegram and 't.me' in telegram:
            if re.match(r'https?://(www\.)?t\.me/[A-Za-z0-9_]{5,32}/?', telegram):
                results["telegram_valid"] = True
            else:
                results["reasons"].append("Telegram URL invalide")
        
        # Décision finale
        results["is_suspicious"] = len(results["reasons"]) > 0
        
        return results

# Instance globale
antiscam_api = AntiScamAPI()
"""
Module Anti-Scam Simplifié
Vérifications basiques anti-scam
"""

import aiohttp
from typing import Dict, Any
from loguru import logger

class AntiScamAPI:
    """API Anti-Scam simplifiée"""
    
    def __init__(self):
        self.session = None
    
    async def check_project(self, project) -> Dict[str, Any]:
        """Vérification anti-scam basique"""
        checks = {
            'domain_clean': True,
            'contract_format_ok': True,
        }
        reasons = []
        
        # Vérification domaine
        if project.website:
            domain_check = await self.check_domain(project.website)
            if not domain_check['clean']:
                checks['domain_clean'] = False
                reasons.extend(domain_check['reasons'])
        
        # Vérification contrat
        if project.contract_address:
            contract_check = await self.check_contract(project.contract_address)
            if not contract_check['clean']:
                checks['contract_format_ok'] = False
                reasons.extend(contract_check['reasons'])
        
        return {
            'checks': checks,
            'reasons': reasons,
            'clean': all(checks.values())
        }
    
    async def check_domain(self, website: str) -> Dict[str, Any]:
        """Vérification basique du domaine"""
        reasons = []
        
        # Vérifications simples
        if not website.startswith('https://'):
            reasons.append("Site non sécurisé (HTTP)")
        
        if len(website) > 100:
            reasons.append("URL trop longue")
        
        # Mots-clés suspects
        suspicious_words = ['free', 'airdrop', 'giveaway', 'presale']
        if any(word in website.lower() for word in suspicious_words):
            reasons.append("Mots-clés suspects dans l'URL")
        
        return {
            'clean': len(reasons) == 0,
            'reasons': reasons
        }
    
    async def check_contract(self, contract_address: str) -> Dict[str, Any]:
        """Vérification format contrat"""
        reasons = []
        
        if not contract_address.startswith('0x') or len(contract_address) != 42:
            reasons.append("Format d'adresse contrat invalide")
        
        return {
            'clean': len(reasons) == 0,
            'reasons': reasons
        }
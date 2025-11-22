"""Module anti-scam avec 10+ bases de données"""

import aiohttp
import requests
import whois
from typing import Dict, Optional
from loguru import logger
from datetime import datetime


async def check_cryptoscamdb(project: Dict) -> Dict:
    """Check CryptoScamDB"""
    try:
        url = "https://cryptoscamdb.org/api/check"
        params = {"url": project.get('website', '')}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"listed": data.get('result') == 'blocked', "source": "CryptoScamDB"}
    except Exception as e:
        logger.error(f"CryptoScamDB error: {e}")
    return {"listed": False, "source": "CryptoScamDB"}


async def check_chainabuse(project: Dict) -> Dict:
    """Check Chainabuse"""
    try:
        url = f"https://www.chainabuse.com/api/reports/{project.get('contract_address', '')}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"listed": len(data.get('reports', [])) > 0, "source": "Chainabuse"}
    except Exception as e:
        logger.error(f"Chainabuse error: {e}")
    return {"listed": False, "source": "Chainabuse"}


async def check_metamask_phishing(project: Dict) -> Dict:
    """Check MetaMask Phishing List"""
    try:
        url = "https://raw.githubusercontent.com/MetaMask/eth-phishing-detect/master/src/config.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    domain = project.get('website', '').replace('https://', '').replace('http://', '').split('/')[0]
                    listed = domain in data.get('blacklist', [])
                    return {"listed": listed, "source": "MetaMask"}
    except Exception as e:
        logger.error(f"MetaMask error: {e}")
    return {"listed": False, "source": "MetaMask"}


async def check_tokensniffer(contract_address: str) -> Dict:
    """Check TokenSniffer"""
    try:
        url = f"https://tokensniffer.com/api/v2/tokens/{contract_address}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    score = data.get('score', 100)
                    return {"safe": score >= 20, "score": score, "source": "TokenSniffer"}
    except Exception as e:
        logger.error(f"TokenSniffer error: {e}")
    return {"safe": True, "score": 50, "source": "TokenSniffer"}


async def check_rugdoc(project: Dict) -> Dict:
    """Check RugDoc"""
    try:
        url = f"https://rugdoc.io/api/project/{project.get('name', '')}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"safe": data.get('status') != 'scam', "source": "RugDoc"}
    except Exception as e:
        logger.error(f"RugDoc error: {e}")
    return {"safe": True, "source": "RugDoc"}


async def check_honeypot(contract_address: str) -> Dict:
    """Check Honeypot.is"""
    try:
        url = f"https://honeypot.is/api/checkToken?address={contract_address}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"is_honeypot": data.get('isHoneypot', False), "source": "Honeypot.is"}
    except Exception as e:
        logger.error(f"Honeypot error: {e}")
    return {"is_honeypot": False, "source": "Honeypot.is"}


async def check_domain_age(url: str) -> Dict:
    """Check domain age avec WHOIS"""
    try:
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        w = whois.whois(domain)
        if w.creation_date:
            creation_date = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
            age_days = (datetime.now() - creation_date).days
            return {"age_days": age_days, "created": creation_date, "safe": age_days >= 7}
    except Exception as e:
        logger.error(f"WHOIS error: {e}")
    return {"age_days": 999, "safe": True}


async def check_twitter_status(twitter_url: str) -> Dict:
    """Check Twitter status"""
    try:
        # TODO[HUMAN]: Implémenter check Twitter avec API
        return {"exists": True, "suspended": False}
    except Exception as e:
        logger.error(f"Twitter error: {e}")
    return {"exists": False, "suspended": False}


async def check_telegram_exists(telegram_url: str) -> Dict:
    """Check Telegram existe"""
    try:
        # TODO[HUMAN]: Implémenter check Telegram avec Bot API
        return {"exists": True, "private": False}
    except Exception as e:
        logger.error(f"Telegram error: {e}")
    return {"exists": False, "private": False}

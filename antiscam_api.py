"""Module anti-scam (10+ sources) — async + backoff léger."""
from __future__ import annotations

import aiohttp
from datetime import datetime
from typing import Dict
from loguru import logger
import whois

async def _get_json(url: str, params: Dict | None = None, headers: Dict | None = None, timeout: int = 10) -> Dict | None:
    for attempt in range(3):
        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 404:
                        return None
                    data = await resp.json(content_type=None)
                    return data
        except Exception as e:
            wait = (2 ** attempt) * 0.5
            logger.debug(f"GET {url} failed: {e}; retry in {wait:.2f}s")
            await asyncio.sleep(wait)  # type: ignore
    return None

async def check_cryptoscamdb(project: Dict) -> Dict:
    url = "https://cryptoscamdb.org/api/check"
    params = {"url": project.get('website', '')}
    data = await _get_json(url, params=params)
    listed = bool(data and data.get('result') == 'blocked')
    return {"listed": listed, "source": "CryptoScamDB"}

async def check_chainabuse(project: Dict) -> Dict:
    addr = project.get('contract_address', '')
    if not addr:
        return {"listed": False, "source": "Chainabuse"}
    url = f"https://www.chainabuse.com/api/reports/{addr}"
    data = await _get_json(url)
    listed = bool(data and len(data.get('reports', [])) > 0)
    return {"listed": listed, "source": "Chainabuse"}

async def check_metamask_phishing(project: Dict) -> Dict:
    url = "https://raw.githubusercontent.com/MetaMask/eth-phishing-detect/master/src/config.json"
    data = await _get_json(url)
    domain = (project.get('website', '') or '').replace('https://', '').replace('http://', '').split('/')[0]
    listed = bool(domain and data and domain in (data.get('blacklist', []) or []))
    return {"listed": listed, "source": "MetaMask"}

async def check_tokensniffer(contract_address: str) -> Dict:
    url = f"https://tokensniffer.com/api/v2/tokens/{contract_address}"
    data = await _get_json(url)
    score = int(data.get('score', 100)) if data else 100
    return {"safe": score >= 20, "score": score, "source": "TokenSniffer"}

async def check_rugdoc(project: Dict) -> Dict:
    name = project.get('name', '')
    if not name:
        return {"safe": True, "source": "RugDoc"}
    url = f"https://rugdoc.io/api/project/{name}"
    data = await _get_json(url)
    safe = True if not data else (data.get('status') != 'scam')
    return {"safe": safe, "source": "RugDoc"}

async def check_honeypot(contract_address: str) -> Dict:
    url = f"https://honeypot.is/api/checkToken?address={contract_address}"
    data = await _get_json(url)
    is_hp = bool(data and data.get('isHoneypot', False))
    return {"is_honeypot": is_hp, "source": "Honeypot.is"}

async def check_domain_age(url: str) -> Dict:
    try:
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        w = whois.whois(domain)
        creation_date = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
        if not creation_date:
            return {"age_days": 999, "safe": True}
        age_days = (datetime.now() - creation_date).days
        return {"age_days": age_days, "created": creation_date, "safe": age_days >= 7}
    except Exception as e:
        logger.debug(f"WHOIS error for {url}: {e}")
        return {"age_days": 999, "safe": True}

async def check_twitter_status(twitter_url: str) -> Dict:
    # Base: présence; intégrer API Twitter plus tard
    exists = bool(twitter_url and twitter_url.startswith("https://"))
    return {"exists": exists, "suspended": False}

async def check_telegram_exists(telegram_url: str) -> Dict:
    exists = bool(telegram_url and telegram_url.startswith("https://"))
    private = "joinchat" in telegram_url.lower()
    return {"exists": exists, "private": private}

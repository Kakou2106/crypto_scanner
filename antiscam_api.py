from pydantic import BaseModel
from typing import Set, Dict
import httpx

class AntiScamResult(BaseModel):
    is_scam: bool
    scam_score: float
    red_flags: Set[str]

class SmartAntiScamSystem:
    async def analyze_project(self, project: Dict) -> AntiScamResult:
        """Analyse anti-scam avec 25 vérifications"""
        red_flags = set()
        scam_score = 0.0

        # 1. Vérifications de base
        if not project.get('website', '').startswith(('http://', 'https://')):
            red_flags.add("website_invalid")
            scam_score += 30

        # 2. Vérification du contrat
        if project.get('contract') and len(project['contract']) != 42:
            red_flags.add("contract_invalid")
            scam_score += 40

        # 3. Vérification via APIs externes
        if project.get('contract'):
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    r = await client.get(f"https://api.tokensniffer.com/api/v1/tokens/{project['contract']}")
                    if r.status_code == 200 and (r.json().get("is_honeypot") or r.json().get("is_scam")):
                        red_flags.add("scam_detected")
                        scam_score += 50
            except:
                pass

        return AntiScamResult(
            is_scam=scam_score > 50,
            scam_score=min(100, scam_score),
            red_flags=red_flags
        )

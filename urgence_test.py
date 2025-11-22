#!/usr/bin/env python3
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

async def diagnostic_telegram():
    """Diagnostic complet de votre configuration Telegram"""
    
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    print("🔍 DIAGNOSTIC COMPLET TELEGRAM:")
    print(f"   BOT_TOKEN: {BOT_TOKEN}")
    print(f"   CHAT_ID: {CHAT_ID}")
    print(f"   Token length: {len(BOT_TOKEN) if BOT_TOKEN else 0}")
    print(f"   Chat ID type: {type(CHAT_ID)}")
    
    # Vérification du format
    if BOT_TOKEN and ":" not in BOT_TOKEN:
        print("❌ MAUVAIS FORMAT: Le token doit contenir ':'")
        return False
    
    if CHAT_ID and not CHAT_ID.lstrip('-').isdigit():
        print("❌ MAUVAIS FORMAT: Chat ID doit être numérique")
        return False
    
    # Test d'envoi
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": "🚀 TEST URGENT: Quantum Scanner - Si vous voyez ceci, ça marche!",
        "parse_mode": "Markdown"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                print(f"📡 Statut HTTP: {response.status}")
                
                if response.status == 200:
                    print("✅ TELEGRAM FONCTIONNE!")
                    return True
                elif response.status == 400:
                    print("❌ ERREUR 400: Mauvais Chat ID - Vérifiez votre CHAT_ID!")
                    error = await response.json()
                    print(f"   Détail: {error}")
                elif response.status == 401:
                    print("❌ ERREUR 401: Token invalide - Vérifiez BOT_TOKEN!")
                else:
                    error = await response.text()
                    print(f"❌ Erreur {response.status}: {error}")
                return False
                
    except Exception as e:
        print(f"💥 Erreur réseau: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(diagnostic_telegram())
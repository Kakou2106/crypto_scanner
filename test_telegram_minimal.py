#!/usr/bin/env python3
"""
Test Telegram - Version MINIMALE sans dépendances externes
Utilise uniquement urllib (built-in)
"""

import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# CONFIG
# ============================================================================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

print("=" * 70)
print("🧪 TELEGRAM TEST - MINIMAL VERSION")
print("=" * 70)

# ============================================================================
# CHECK ENV
# ============================================================================
print("\n📋 Configuration Check:")
if TELEGRAM_BOT_TOKEN:
    masked = TELEGRAM_BOT_TOKEN[:15] + "***"
    print(f"  ✅ TELEGRAM_BOT_TOKEN: {masked}")
else:
    print(f"  ❌ TELEGRAM_BOT_TOKEN: MISSING")
    exit(1)

if TELEGRAM_CHAT_ID:
    print(f"  ✅ TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")
else:
    print(f"  ❌ TELEGRAM_CHAT_ID: MISSING")
    exit(1)

# ============================================================================
# TEST 1: Get Bot Info
# ============================================================================
print("\n🤖 Test 1: Get Bot Info")
try:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        
        if data.get('ok'):
            bot_info = data['result']
            print(f"  ✅ Bot Name: {bot_info.get('first_name')}")
            print(f"  ✅ Bot Username: @{bot_info.get('username')}")
            print(f"  ✅ Bot ID: {bot_info.get('id')}")
        else:
            print(f"  ❌ Error: {data.get('description')}")
            exit(1)
except urllib.error.URLError as e:
    print(f"  ❌ Connection error: {e}")
    exit(1)
except Exception as e:
    print(f"  ❌ Error: {e}")
    exit(1)

# ============================================================================
# TEST 2: Send Test Message
# ============================================================================
print("\n📨 Test 2: Send Test Message")

message_text = """🔧 **QUANTUM SCANNER - CONFIGURATION TEST**

✅ Bot is working correctly!

If you see this message, Telegram alerts are enabled.

**Your Chat ID:** `{}`

Ready to receive crypto alerts! 🚀
""".format(TELEGRAM_CHAT_ID)

try:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message_text,
        'parse_mode': 'Markdown'
    }
    
    data = json.dumps(payload).encode('utf-8')
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        
        if result.get('ok'):
            msg_id = result['result']['message_id']
            print(f"  ✅ Message sent successfully!")
            print(f"  ✅ Message ID: {msg_id}")
            print(f"  ✅ Chat ID: {TELEGRAM_CHAT_ID}")
        else:
            print(f"  ❌ Error: {result.get('description')}")
            exit(1)
            
except urllib.error.URLError as e:
    print(f"  ❌ Connection error: {e}")
    exit(1)
except Exception as e:
    print(f"  ❌ Error: {e}")
    exit(1)

# ============================================================================
# SUCCESS
# ============================================================================
print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED - TELEGRAM IS WORKING!")
print("=" * 70)
print("\n📝 Next steps:")
print("  1. Check your Telegram chat for the test message")
print("  2. Run: python main.py")
print("  3. You should receive alerts for early stage projects")
print("\n" + "=" * 70)
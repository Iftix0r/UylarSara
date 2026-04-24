import os
import sys

# Loyiha papkasining to'liq yo'lini ko'rsatish
sys.path.insert(0, os.path.dirname(__file__))

# .env faylini yuklash (cPanel da environment variables ishlamasligi mumkin)
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    load_dotenv(env_path)
    print(f"[WSGI] .env loaded from {env_path}, TOKEN_LEN={len(os.getenv('TELEGRAM_BOT_TOKEN',''))}")
except Exception as e:
    print(f"[WSGI] dotenv error: {e}")

# Django sozlamalari joylashuvini ko'rsatamiz
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sarauylar.settings")

# Django WSGI ilovasini import qilamiz
from sarauylar.wsgi import application

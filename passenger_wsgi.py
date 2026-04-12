import os
import sys

# Loyiha papkasining to'liq yo'lini ko'rsatish
sys.path.insert(0, os.path.dirname(__file__))

# .env faylini yuklash (cPanel da environment variables ishlamasligi mumkin)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except Exception:
    pass

# Django sozlamalari joylashuvini ko'rsatamiz
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sarauylar.settings")

# Django WSGI ilovasini import qilamiz
from sarauylar.wsgi import application

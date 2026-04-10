import os
import sys

# Loyiha papkasining to'liq yo'lini ko'rsatish
# Odatda bu cPanel dagi papkangiz nomi bo'ladi
# sys.path.insert orqali uni birinchi bo'lib qidirishni buyuramiz
sys.path.insert(0, os.path.dirname(__file__))

# Django sozlamalari joylashuvini ko'rsatamiz
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sarauylar.settings")

# Django WSGI ilovasini import qilamiz
# application o'zgaruvchisi cPanel uchun kerak
from sarauylar.wsgi import application

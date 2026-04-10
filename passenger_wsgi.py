import os
import sys

# Joriy katalogni (loyiha papkasini) sys.path ga qo'shamiz
project_dir = os.path.dirname(os.path.realpath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Django sozlamalari faylining joylashuvini muhit o'zgaruvchisi orqali beramiz
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sarauylar.settings')

# Django loyihasining WSGI ilovasini import qilamiz
# "sarauylar" bu sizning Django loyihangiz papkasi hisoblanadi
from sarauylar.wsgi import application

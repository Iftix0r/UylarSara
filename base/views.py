from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Category, Property, Favorite
from .forms import PropertyForm
import os
import json
import hmac
import hashlib
import logging
import tempfile
from urllib.parse import parse_qsl, unquote
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

try:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    _openai_available = True
except ImportError:
    _openai_available = False


def verify_telegram_init_data(init_data: str) -> dict | None:
    """Telegram WebApp initData ni HMAC-SHA256 bilan tekshiradi."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or not init_data:
        return None
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=False))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash):
            return None
        user_str = parsed.get("user", "")
        return json.loads(user_str) if user_str else None
    except Exception as e:
        logger.warning("[TG] verify error: %s", e)
        return None


@csrf_exempt
def telegram_auth(request):
    """Telegram WebApp initData yoki Login Widget orqali login/register."""
    import time

    # ── Telegram Login Widget (GET) ──────────────────────────────────────────
    if request.method == "GET":
        params = request.GET.dict()
        received_hash = params.pop("hash", None)
        if not received_hash or not params.get("id"):
            return redirect("/")
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        token_hash = hashlib.sha256(token.encode()).digest()
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        expected_hash = hmac.new(token_hash, data_check_string.encode(), hashlib.sha256).hexdigest()
        auth_date = int(params.get("auth_date", 0))
        if not hmac.compare_digest(expected_hash, received_hash) or (time.time() - auth_date) > 86400:
            return redirect("/")
        _create_or_login_tg_user(
            request, int(params["id"]),
            params.get("first_name", ""), params.get("last_name", ""), params.get("username", "")
        )
        return redirect("/")

    # ── Telegram Web App (POST) ──────────────────────────────────────────────
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        body = json.loads(request.body)
        init_data = body.get("initData", "")
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_data = verify_telegram_init_data(init_data)
    if not user_data or not user_data.get("id"):
        return JsonResponse({"error": "Invalid initData"}, status=403)

    _create_or_login_tg_user(
        request, int(user_data["id"]),
        user_data.get("first_name", ""), user_data.get("last_name", ""),
        user_data.get("username", ""), user_data.get("photo_url", "")
    )
    return JsonResponse({"ok": True})


def _get_demo_properties():
    """DB bo'sh bo'lganda ko'rsatiladigan 10 ta demo e'lon (fake obyektlar)."""
    from types import SimpleNamespace
    DEMOS = [
        dict(pk=None, title="Yangi 3 xonali kvartira", price="85000", location="Toshkent, Yunusobod",
             rooms=3, area="90", property_type="APARTMENT", is_premium=True,
             image=None, views_count=142, description="Zamonaviy ta'mirli, mebelli."),
        dict(pk=None, title="2 xonali kvartira, metro yaqin", price="55000", location="Toshkent, Chilonzor",
             rooms=2, area="65", property_type="APARTMENT", is_premium=False,
             image=None, views_count=98, description="Qulay joylashuv, barcha kommunal."),
        dict(pk=None, title="Hashamatli villa, hovlili", price="320000", location="Toshkent, Mirzo Ulug'bek",
             rooms=6, area="350", property_type="VILLA", is_premium=True,
             image=None, views_count=310, description="Yashil bog', basseyn, garaj."),
        dict(pk=None, title="1 xonali kvartira, yangi bino", price="38000", location="Samarqand, Markaz",
             rooms=1, area="42", property_type="APARTMENT", is_premium=False,
             image=None, views_count=55, description="Birinchi qavat, ta'mirli."),
        dict(pk=None, title="Tijorat binosi, ofis uchun", price="150000", location="Toshkent, Shayxontohur",
             rooms=8, area="200", property_type="COMMERCIAL", is_premium=True,
             image=None, views_count=201, description="Markaziy ko'chada, 2-qavat."),
        dict(pk=None, title="4 xonali uy, yangi qurilish", price="120000", location="Andijon, Asaka",
             rooms=4, area="160", property_type="HOUSE", is_premium=False,
             image=None, views_count=77, description="Hovli, garaj, barcha qulayliklar."),
        dict(pk=None, title="Yangi qurilish, 2 xona", price="72000", location="Buxoro, Markaz",
             rooms=2, area="75", property_type="NEW_CONSTRUCTION", is_premium=False,
             image=None, views_count=44, description="Qurilish 90% tayyor, ipoteka mumkin."),
        dict(pk=None, title="3 xonali penthouse", price="210000", location="Toshkent, Yakkasaroy",
             rooms=3, area="130", property_type="APARTMENT", is_premium=True,
             image=None, views_count=189, description="Tepa qavat, panorama ko'rinish."),
        dict(pk=None, title="Arzon 1 xonali kvartira", price="28000", location="Namangan, Markaz",
             rooms=1, area="38", property_type="APARTMENT", is_premium=False,
             image=None, views_count=33, description="Tez sotiladi, hujjatlar tayyor."),
        dict(pk=None, title="Zamonaviy 5 xonali uy", price="195000", location="Farg'ona, Fergana",
             rooms=5, area="280", property_type="HOUSE", is_premium=True,
             image=None, views_count=256, description="Ikki qavatli, katta hovli."),
    ]

    result = []
    for i, d in enumerate(DEMOS):
        obj = SimpleNamespace(**d)
        obj.pk = f"demo_{i}"
        obj.get_property_type_display = lambda t=d["property_type"]: {
            "APARTMENT": "Kvartira", "HOUSE": "Uy", "VILLA": "Villa",
            "COMMERCIAL": "Tijorat", "NEW_CONSTRUCTION": "Yangi qurilish"
        }.get(t, t)
        obj.images = SimpleNamespace(count=lambda: 0)
        obj.created_at = None
        result.append(obj)
    return result


def _fetch_telegram_photo(telegram_id: int) -> str:
    """Bot API orqali foydalanuvchi profil rasmini oladi."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return ""
    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/getUserProfilePhotos?user_id={telegram_id}&limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())

        if not data.get("ok") or not data["result"]["total_count"]:
            return ""

        photos = data["result"]["photos"][0]
        best = max(photos, key=lambda p: p.get("file_size", 0))
        file_id = best["file_id"]

        url2 = f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
        req2 = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req2, timeout=8) as resp:
            data2 = json.loads(resp.read())

        file_path = data2["result"]["file_path"]
        return f"https://api.telegram.org/file/bot{token}/{file_path}"
    except Exception as e:
        logger.warning("[TG PHOTO] error for %s: %s", telegram_id, e)
        return ""


def _create_or_login_tg_user(request, telegram_id, first_name, last_name, tg_username, init_photo_url=""):
    from django.contrib.auth.models import User
    from .models import UserProfile

    def get_best_photo():
        if init_photo_url:
            return init_photo_url
        return _fetch_telegram_photo(telegram_id)

    profile = UserProfile.objects.filter(telegram_id=telegram_id).select_related("user").first()
    if profile:
        user = profile.user
        update_fields = []
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            update_fields.append("first_name")
        if last_name != user.last_name:
            user.last_name = last_name
            update_fields.append("last_name")
        if update_fields:
            user.save(update_fields=update_fields)

        profile_fields = []
        if tg_username and profile.telegram_username != tg_username:
            profile.telegram_username = tg_username
            profile_fields.append("telegram_username")
        photo = get_best_photo()
        if photo and profile.telegram_photo_url != photo:
            profile.telegram_photo_url = photo
            profile_fields.append("telegram_photo_url")
        if profile_fields:
            profile.save(update_fields=profile_fields)
    else:
        if tg_username:
            candidate = tg_username.lower()
            username = candidate if not User.objects.filter(username=candidate).exists() else f"tg_{telegram_id}"
        else:
            username = f"tg_{telegram_id}"

        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        photo = get_best_photo()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.telegram_id = telegram_id
        profile.telegram_username = tg_username
        profile.telegram_photo_url = photo
        profile.save()

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")


def set_language(request, lang):
    if lang in ['uz', 'ru']:
        request.session['lang'] = lang
    return redirect(request.META.get('HTTP_REFERER', '/'))

def set_city(request, city):
    request.session['city'] = city
    return JsonResponse({'status': 'ok'})

def seller_profile(request, username):
    from django.contrib.auth.models import User
    from django.db.models import Sum
    seller = get_object_or_404(User, username=username)
    properties = (
        Property.objects
        .filter(owner=seller, status='active')
        .select_related('category')
        .prefetch_related('images')
        .order_by('-created_at')
    )

    total_views = properties.aggregate(Sum('views_count'))['views_count__sum'] or 0

    favorited_ids = set()
    if request.user.is_authenticated:
        favorited_ids = set(Favorite.objects.filter(user=request.user).values_list('property_id', flat=True))

    context = {
        'seller': seller,
        'properties': properties,
        'favorited_ids': favorited_ids,
        'total_views': total_views,
    }
    return render(request, 'seller_profile.html', context)

def about(request):
    return render(request, 'about.html')

def help_page(request):
    return render(request, 'help.html')

def home(request):
    lang = request.session.get('lang', 'uz')
    hero_title = None
    hero_subtitle = None

    if _openai_available:
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=4.5)
            sys_prompt = "You are an expert real estate copywriter. Respond with exactly ONE line of text in the format TITLE|SUBTITLE and NOTHING else. No markdown, no quotes."
            if lang == 'ru':
                prompt = "Напишите короткий креативный заголовок из 3-5 слов (1 ключевое слово строго оберните в <span>...</span>) и описание из 1 короткого привлекательного предложения для платформы недвижимости в Узбекистане (SaraUylar)."
            else:
                prompt = "O'zbekistondagi premium uylar platformasi (SaraUylar) uchun qisqa 3-5 so'zli jozibador sarlavha (1 ta asosiy so'zi albatta <span>...</span> qavsida bo'lsin) va 1 ta qisqa gapdan iborat ta'rif yozing."

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=60,
                temperature=0.8,
            )
            content = response.choices[0].message.content.strip().replace('\n', ' ')
            if '|' in content:
                hero_title, hero_subtitle = content.split('|', 1)
                hero_title = hero_title.strip()
                hero_subtitle = hero_subtitle.strip()
        except Exception as e:
            logger.warning("OpenAI Hero Error: %s", e)

    category_slug = request.GET.get('category')
    query = request.GET.get('q', '').strip()
    rooms = request.GET.get('rooms', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()

    categories = Category.objects.all()
    properties = (
        Property.objects
        .filter(status='active')
        .select_related('category')
        .prefetch_related('images')
        .order_by('-created_at')
    )

    if category_slug:
        properties = properties.filter(category__slug=category_slug)

    if query:
        from django.db.models import Q
        properties = properties.filter(
            Q(title__icontains=query) |
            Q(location__icontains=query) |
            Q(description__icontains=query)
        )

    if rooms:
        if rooms == '5+':
            properties = properties.filter(rooms__gte=5)
        elif rooms.isdigit():
            properties = properties.filter(rooms=int(rooms))

    if min_price and min_price.isdigit():
        properties = properties.filter(price__gte=int(min_price))

    if max_price and max_price.isdigit():
        properties = properties.filter(price__lte=int(max_price))

    favorited_ids = set()
    if request.user.is_authenticated:
        favorited_ids = set(Favorite.objects.filter(user=request.user).values_list('property_id', flat=True))

    is_filtered = any([category_slug, query, rooms, min_price, max_price])
    demo_properties = []
    if not is_filtered and not properties.exists():
        demo_properties = _get_demo_properties()

    # Pagination — 20 ta e'lon per sahifa
    from django.core.paginator import Paginator
    if demo_properties:
        page_obj = demo_properties
        is_paginated = False
    else:
        paginator = Paginator(properties, 20)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        is_paginated = paginator.num_pages > 1

    context = {
        'categories': categories,
        'properties': page_obj,
        'favorited_ids': favorited_ids,
        'hero_title': hero_title,
        'hero_subtitle': hero_subtitle,
        'is_demo': bool(demo_properties),
        'is_paginated': is_paginated,
        'page_obj': page_obj if not demo_properties else None,
    }

    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    if lat and lng:
        try:
            from math import radians, cos, sin, asin, sqrt
            def haversine(lon1, lat1, lon2, lat2):
                lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                return 2 * asin(sqrt(a)) * 6371

            user_lat = float(lat)
            user_lng = float(lng)
            props_with_coords = properties.filter(latitude__isnull=False, longitude__isnull=False)
            prop_list = list(props_with_coords)
            for p in prop_list:
                p.distance = haversine(user_lng, user_lat, p.longitude, p.latitude)
            prop_list.sort(key=lambda x: x.distance)
            context['properties'] = prop_list[:20]
            context['nearby_active'] = True
        except (ValueError, TypeError):
            pass

    return render(request, 'index.html', context)

def property_detail(request, pk):
    property = get_object_or_404(
        Property.objects.select_related('owner__profile', 'category'),
        pk=pk, status='active'
    )

    viewed_properties = request.session.get('viewed_properties', [])
    if pk not in viewed_properties:
        property.views_count += 1
        property.save(update_fields=['views_count'])
        viewed_properties.append(pk)
        request.session['viewed_properties'] = viewed_properties

    similar_properties = (
        Property.objects
        .filter(category=property.category, status='active')
        .exclude(pk=pk)
        .select_related('category')
        [:4]
    )

    favorited_ids = set()
    is_favorited = False
    if request.user.is_authenticated:
        favorited_ids = set(Favorite.objects.filter(user=request.user).values_list('property_id', flat=True))
        is_favorited = property.pk in favorited_ids

    context = {
        'property': property,
        'similar_properties': similar_properties,
        'is_favorited': is_favorited,
        'favorited_ids': favorited_ids,
    }
    return render(request, 'property_detail.html', context)

def _save_gallery_images(prop, files):
    """gallery_images fayllarini PropertyImage sifatida saqlaydi."""
    from .models import PropertyImage
    order_start = prop.images.count()
    for i, f in enumerate(files):
        if f.size > 8 * 1024 * 1024:
            continue  # 8MB dan katta rasmni o'tkazib yuborish
        PropertyImage.objects.create(property=prop, image=f, order=order_start + i)


@login_required
def add_property(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES)
        if form.is_valid():
            prop = form.save(commit=False)
            prop.owner = request.user
            prop.status = 'pending'
            prop.save()
            gallery_files = request.FILES.getlist('gallery_images')
            if gallery_files:
                _save_gallery_images(prop, gallery_files)
            return redirect('profile')
    else:
        form = PropertyForm()
    return render(request, 'add_property.html', {'form': form})


@login_required
def edit_property(request, pk):
    from .models import PropertyImage
    prop = get_object_or_404(Property, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=prop)
        if form.is_valid():
            p = form.save(commit=False)
            p.status = 'pending'
            p.save()
            gallery_files = request.FILES.getlist('gallery_images')
            if gallery_files:
                _save_gallery_images(p, gallery_files)
            return redirect('profile')
    else:
        form = PropertyForm(instance=prop)
    existing_images = prop.images.all().order_by('order', 'id')
    return render(request, 'add_property.html', {
        'form': form, 'edit': True, 'prop': prop,
        'existing_images': existing_images,
    })


@login_required
def delete_property_image(request, pk):
    from .models import PropertyImage
    img = get_object_or_404(PropertyImage, pk=pk, property__owner=request.user)
    if request.method == 'POST':
        img.delete()
        return JsonResponse({'ok': True})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def delete_property(request, pk):
    prop = get_object_or_404(Property, pk=pk, owner=request.user)
    if request.method == 'POST':
        prop.delete()
    return redirect('profile')

@login_required
def profile(request):
    user_properties = Property.objects.filter(owner=request.user).order_by('-created_at')
    context = {
        'user_properties': user_properties,
        'total_ads': user_properties.count(),
        'favorites_count': Favorite.objects.filter(user=request.user).count(),
    }
    return render(request, 'profile.html', context)

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def favorites(request):
    user_favorites = (
        Favorite.objects
        .filter(user=request.user)
        .select_related('property', 'property__category')
        .prefetch_related('property__images')
    )
    categories = Category.objects.all()
    context = {
        'favorites': user_favorites,
        'properties': [f.property for f in user_favorites],
        'categories': categories,
    }
    return render(request, 'favorites.html', context)

@login_required
def toggle_favorite(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    property = get_object_or_404(Property, pk=pk)
    favorite, created = Favorite.objects.get_or_create(user=request.user, property=property)

    if not created:
        favorite.delete()
        is_favorite = False
    else:
        is_favorite = True

    return JsonResponse({'is_favorite': is_favorite})

def ai_chat(request):
    if not _openai_available:
        return JsonResponse({'message': "AI xizmati mavjud emas."}, status=503)
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_message = data.get('message', '').strip()
    if not user_message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    import re
    id_match = re.search(r'#?(\d{4,})', user_message)
    specific_context = ""
    if id_match:
        try:
            target_id = int(id_match.group(1)) - 1024
            p = Property.objects.select_related('category').get(pk=target_id, status='active')
            img_url = request.build_absolute_uri(p.image.url) if p.image else ""
            detail_url = request.build_absolute_uri(f"/property/{p.pk}/")
            specific_context = (
                f"SPECIFIC PROPERTY (ID #{target_id + 1024}):\n"
                f"Title: {p.title}\nLocation: {p.location}\nPrice: ${p.price}\n"
                f"Rooms: {p.rooms}\nArea: {p.area}m2\nDescription: {p.description}\n"
                f"Image: {img_url}\nDetail URL: {detail_url}\n"
            )
        except Property.DoesNotExist:
            pass

    top_properties = Property.objects.filter(status='active').order_by('-created_at')[:5]
    context_str = "Recent properties:\n" + "".join(
        f"- {p.title} in {p.location} (${p.price})\n" for p in top_properties
    )

    lang = request.session.get('lang', 'uz')
    lang_name = "Russian" if lang == 'ru' else "Uzbek"

    system_prompt = (
        f"You are a professional real estate assistant for 'SaraUylar' platform.\n"
        f"Speak in {lang_name}. Be persuasive and helpful.\n\n"
        f"{specific_context}\n"
        f"General listings:\n{context_str}\n\n"
        "CRITICAL: If Image URL is empty, DO NOT include an <img> tag.\n"
        "Output format: simple HTML. Use <br> for new lines."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for h in data.get('history', [])[-10:]:
        messages.append({"role": "assistant" if h.get('isAi') else "user", "content": h.get('text', '')})
    messages.append({"role": "user", "content": user_message})

    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=600
        )
        ai_message = response.choices[0].message.content
        return JsonResponse({'message': ai_message})
    except Exception as e:
        logger.error("AI chat error: %s", e)
        return JsonResponse({'message': "Kechirasiz, hozirda bog'lanishda muammo bo'ldi."}, status=500)


@csrf_exempt
def ai_whisper(request):
    if not _openai_available:
        return JsonResponse({'error': 'AI service unavailable'}, status=503)
    if request.method != 'POST' or not request.FILES.get('audio'):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    audio_file = request.FILES['audio']
    # 10 MB limit
    if audio_file.size > 10 * 1024 * 1024:
        return JsonResponse({'error': 'File too large (max 10MB)'}, status=413)

    tmp = tempfile.NamedTemporaryFile(suffix='.webm', delete=False)
    try:
        for chunk in audio_file.chunks():
            tmp.write(chunk)
        tmp.close()

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        with open(tmp.name, 'rb') as f:
            transcription = client.audio.transcriptions.create(model="whisper-1", file=f)
        return JsonResponse({'text': transcription.text})
    except Exception as e:
        logger.error("Whisper error: %s", e)
        return JsonResponse({'error': 'Transcription failed'}, status=500)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


@csrf_exempt
def ai_tts(request):
    if not _openai_available:
        return JsonResponse({'error': 'AI service unavailable'}, status=503)
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    text = data.get('text', '').strip()
    if not text:
        return JsonResponse({'error': 'No text'}, status=400)

    import re
    clean_text = re.sub(r'<[^<]+?>', '', text)[:4000]

    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.audio.speech.create(model="tts-1", voice="nova", input=clean_text)
        from django.http import HttpResponse
        return HttpResponse(response.content, content_type="audio/mpeg")
    except Exception as e:
        logger.error("TTS error: %s", e)
        return JsonResponse({'error': 'TTS failed'}, status=500)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Category, Property, Favorite
from .forms import PropertyForm
import openai
import os
import json
import hmac
import hashlib
from urllib.parse import parse_qsl, unquote
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


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
            print(f"[TG] Hash mismatch. expected={expected_hash[:16]} got={received_hash[:16]}")
            return None
        user_str = parsed.get("user", "")
        return json.loads(user_str) if user_str else None
    except Exception as e:
        print(f"[TG] verify error: {e}")
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
        user_data.get("first_name", ""), user_data.get("last_name", ""), user_data.get("username", "")
    )
    return JsonResponse({"ok": True})


def _fetch_telegram_photo(telegram_id: int) -> str:
    """Bot API orqali foydalanuvchi profil rasmini oladi."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return ""
    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/getUserProfilePhotos?user_id={telegram_id}&limit=1"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        if not data.get("ok") or not data["result"]["total_count"]:
            return ""
        file_id = data["result"]["photos"][0][-1]["file_id"]

        url2 = f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
        with urllib.request.urlopen(url2, timeout=5) as resp:
            data2 = json.loads(resp.read())
        file_path = data2["result"]["file_path"]
        return f"https://api.telegram.org/file/bot{token}/{file_path}"
    except Exception as e:
        print(f"[TG PHOTO] error: {e}")
        return ""


def _create_or_login_tg_user(request, telegram_id, first_name, last_name, tg_username):
    from django.contrib.auth.models import User
    from .models import UserProfile

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
        # Rasm yo'q bo'lsa yangilaymiz
        if not profile.telegram_photo_url:
            photo = _fetch_telegram_photo(telegram_id)
            if photo:
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
        photo = _fetch_telegram_photo(telegram_id)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.telegram_id = telegram_id
        profile.telegram_username = tg_username
        profile.telegram_photo_url = photo
        profile.save()
        print(f"[TG AUTH] New user: {username} ({first_name}) photo={'yes' if photo else 'no'}")

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
    from django.shortcuts import get_object_or_404
    from django.db.models import Sum
    seller = get_object_or_404(User, username=username)
    properties = Property.objects.filter(owner=seller).prefetch_related('images').order_by('-created_at')
    
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
    
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=4.5)
        sys_prompt = "You are an expert real estate copywriter. Respond with exactly ONE line of text in the format TITLE|SUBTITLE and NOTHING else. No markdown, no quotes."
        prompt = "O'zbekistondagi premium uylar platformasi (SaraUylar) uchun qisqa 3-5 so'zli jozibador sarlavha (1 ta asosiy so'zi albatta <span>...</span> qavsida bo'lsin) va 1 ta qisqa gapdan iborat ta'rif yozing."
        if lang == 'ru':
            prompt = "Напишите короткий креативный заголовок из 3-5 слов (1 ключевое слово строго оберните в <span>...</span>) и описание из 1 короткого привлекательного предложения для платформы недвижимости в Узбекистане (SaraUylar)."
            
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
        print(f"OpenAI Hero Error: {e}")

    category_slug = request.GET.get('category')
    query = request.GET.get('q')
    rooms = request.GET.get('rooms')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    categories = Category.objects.all()
    properties = Property.objects.all().prefetch_related('images').order_by('-created_at')
    
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
        else:
            properties = properties.filter(rooms=rooms)
            
    if min_price:
        properties = properties.filter(price__gte=min_price)
    
    if max_price:
        properties = properties.filter(price__lte=max_price)
    
    favorited_ids = set()
    if request.user.is_authenticated:
        favorited_ids = set(Favorite.objects.filter(user=request.user).values_list('property_id', flat=True))
    
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    
    context = {
        'categories': categories,
        'properties': properties,
        'favorited_ids': favorited_ids,
        'hero_title': hero_title,
        'hero_subtitle': hero_subtitle,
    }

    if lat and lng:
        try:
            from math import radians, cos, sin, asin, sqrt
            def haversine(lon1, lat1, lon2, lat2):
                lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                r = 6371 # Radius of earth in kilometers
                return c * r

            user_lat = float(lat)
            user_lng = float(lng)
            
            # Filter properties with coordinates and calculate distance
            props_with_coords = properties.filter(latitude__isnull=False, longitude__isnull=False)
            
            # In a real app with many properties, we'd use GeoDjango.
            # For this MVP, we'll do it in Python.
            prop_list = list(props_with_coords)
            for p in prop_list:
                p.distance = haversine(user_lng, user_lat, p.longitude, p.latitude)
            
            # Sort by distance
            prop_list.sort(key=lambda x: x.distance)
            context['properties'] = prop_list[:20]
            context['nearby_active'] = True
        except (ValueError, TypeError):
            pass

    return render(request, 'index.html', context)

def property_detail(request, pk):
    property = get_object_or_404(Property, pk=pk)
    
    # Increment views (once per session)
    viewed_properties = request.session.get('viewed_properties', [])
    if pk not in viewed_properties:
        property.views_count += 1
        property.save(update_fields=['views_count'])
        viewed_properties.append(pk)
        request.session['viewed_properties'] = viewed_properties
    
    similar_properties = Property.objects.filter(category=property.category).exclude(pk=pk)[:4]
    
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

def add_property(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES)
        if form.is_valid():
            property = form.save(commit=False)
            if request.user.is_authenticated:
                property.owner = request.user
            property.save()
            return redirect('property_detail', pk=property.pk)
    else:
        form = PropertyForm()
    return render(request, 'add_property.html', {'form': form})

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
    user_favorites = Favorite.objects.filter(user=request.user).select_related('property').prefetch_related('property__images')
    categories = Category.objects.all()
    context = {
        'favorites': user_favorites,
        'properties': [f.property for f in user_favorites],
        'categories': categories,
    }
    return render(request, 'favorites.html', context)

@login_required
def toggle_favorite(request, pk):
    property = get_object_or_404(Property, pk=pk)
    favorite, created = Favorite.objects.get_or_create(user=request.user, property=property)
    
    if not created:
        favorite.delete()
        is_favorite = False
    else:
        is_favorite = True
        
    return JsonResponse({'is_favorite': is_favorite})

def ai_chat(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        user_message = data.get('message', '')
        
        # Get host for absolute URLs
        host = request.get_host()
        proto = 'https' if request.is_secure() else 'http'
        base_url = f"{proto}://{host}"
        
        # 1. Detect potential Listing IDs (e.g., #1024 or 1024)
        import re
        id_match = re.search(r'#?(\d{4,})', user_message)
        specific_context = ""
        if id_match:
            try:
                # Listing ID = PK + 1024
                target_id = int(id_match.group(1)) - 1024
                p = Property.objects.get(pk=target_id)
                img_url = request.build_absolute_uri(p.image.url) if p.image else ""
                detail_url = request.build_absolute_uri(f"/property/{p.pk}/")
                specific_context = f"""
                SPECIFIC PROPERTY ANALYZED (ID #{target_id + 1024}):
                Title: {p.title}
                Location: {p.location}
                Price: ${p.price}
                Rooms: {p.rooms}
                Area: {p.area}m2
                Description: {p.description}
                Image: {img_url}
                Detail URL: {detail_url}
                """
            except Property.DoesNotExist:
                pass

        # 2. Get general context (top 5 for relevance)
        top_properties = Property.objects.all().order_by('-created_at')[:5]
        context_str = "Recent properties:\n"
        for p in top_properties:
            img_url = request.build_absolute_uri(p.image.url) if p.image else ""
            detail_url = request.build_absolute_uri(f"/property/{p.pk}/")
            context_str += f"- {p.title} in {p.location} (${p.price})\n"
        
        # 3. Handle History
        history_data = data.get('history', [])
        messages = []
        
        # Get language from session
        lang = request.session.get('lang', 'uz')
        lang_name = "Russian" if lang == 'ru' else "Uzbek"
        
        system_prompt = f"""
        You are a professional real estate assistant for 'SaraUylar' platform.
        Speak in {lang_name}. Be persuasive and helpful.
        
        {specific_context}
        
        General listings for reference:
        {context_str}
        
        If the user provides a listing ID (like #1024), focus YOUR ANALYSIS on that specific property.
        If the user asks follow-up questions about a property (like 'how many rooms?'), use the context of the property we are discussing.
        
        CRITICAL: If the 'Image' URL in the context is empty or missing, DO NOT include an <img> tag in your response.
        
        Output format: Use simple HTML for formatting. 
        - For property images use: <img src='URL' style='width:100%; border-radius:12px; margin:12px 0; box-shadow:0 4px 12px rgba(0,0,0,0.1);'>
        - For property links use: <a href='URL' style='display:inline-block; background:#2563eb; color:white; padding:8px 20px; border-radius:8px; text-decoration:none; font-weight:bold; margin-top:8px;'>Batafsil ko'rish</a>
        - Use <br> for new lines.
        """
        
        messages.append({"role": "system", "content": system_prompt})
        
        # Add last 10 messages from history for context
        for h in history_data[-10:]:
            messages.append({"role": "assistant" if h.get('isAi') else "user", "content": h.get('text', '')})
            
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=800
            )
            ai_message = response.choices[0].message.content
            return JsonResponse({'message': ai_message})
        except Exception as e:
            print(f"AI Error: {e}")
            return JsonResponse({'message': "Kechirasiz, hozirda bog'lanishda muammo bo'ldi."}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def ai_whisper(request):
    if request.method == 'POST' and request.FILES.get('audio'):
        audio_file = request.FILES['audio']
        
        # Save temp file with proper extension
        temp_path = f"temp_audio_{request.user.id or 'anon'}.webm"
        with open(temp_path, 'wb+') as destination:
            for chunk in audio_file.chunks():
                destination.write(chunk)
        
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            with open(temp_path, 'rb') as f:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=f
                )
            if os.path.exists(temp_path): os.remove(temp_path)
            return JsonResponse({'text': transcription.text})
        except Exception as e:
            print(f"Whisper Error: {e}")
            if os.path.exists(temp_path): os.remove(temp_path)
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def ai_tts(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        text = data.get('text', '')
        if not text:
            return JsonResponse({'error': 'No text'}, status=400)
        
        # Strip HTML for TTS
        import re
        clean_text = re.sub('<[^<]+?>', '', text)
        
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=clean_text[:4000]
            )
            
            from django.http import HttpResponse
            return HttpResponse(response.content, content_type="audio/mpeg")
        except Exception as e:
            print(f"TTS Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)

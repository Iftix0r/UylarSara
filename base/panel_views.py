import json
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.utils.timezone import now
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Property, Category, Favorite, UserProfile, PropertyImage

staff_required = user_passes_test(lambda u: u.is_staff, login_url='/accounts/login/')


def staff_only(view_func):
    return login_required(staff_required(view_func))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@staff_only
def panel_home(request):
    week_ago = now() - timedelta(days=7)
    month_ago = now() - timedelta(days=30)

    # Chart: so'nggi 7 kun e'lonlar
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        day = now() - timedelta(days=i)
        label = day.strftime('%d %b')
        count = Property.objects.filter(
            created_at__date=day.date()
        ).count()
        chart_labels.append(label)
        chart_data.append(count)

    ctx = {
        'page': 'dashboard',
        'total_properties':   Property.objects.count(),
        'total_users':        User.objects.count(),
        'total_favorites':    Favorite.objects.count(),
        'total_views':        Property.objects.aggregate(t=Sum('views_count'))['t'] or 0,
        'total_categories':   Category.objects.count(),
        'new_props_week':     Property.objects.filter(created_at__gte=week_ago).count(),
        'new_users_week':     User.objects.filter(date_joined__gte=week_ago).count(),
        'premium_count':      Property.objects.filter(is_premium=True).count(),
        'recent_properties':  Property.objects.select_related('owner', 'category').order_by('-created_at')[:8],
        'recent_users':       User.objects.order_by('-date_joined')[:6],
        'top_properties':     Property.objects.order_by('-views_count')[:5],
        'chart_labels':       json.dumps(chart_labels),
        'chart_data':         json.dumps(chart_data),
    }
    return render(request, 'panel/dashboard.html', ctx)


# ── Properties ────────────────────────────────────────────────────────────────

@staff_only
def panel_properties(request):
    qs = Property.objects.select_related('owner', 'category').prefetch_related('images').order_by('-created_at')
    q = request.GET.get('q', '')
    cat = request.GET.get('cat', '')
    ptype = request.GET.get('type', '')
    premium = request.GET.get('premium', '')
    if q:
        qs = qs.filter(title__icontains=q) | qs.filter(location__icontains=q)
    if cat:
        qs = qs.filter(category__slug=cat)
    if ptype:
        qs = qs.filter(property_type=ptype)
    if premium == '1':
        qs = qs.filter(is_premium=True)

    ctx = {
        'page': 'properties',
        'properties': qs,
        'categories': Category.objects.all(),
        'property_types': Property.PROPERTY_TYPES,
        'q': q, 'cat': cat, 'ptype': ptype, 'premium': premium,
    }
    return render(request, 'panel/properties.html', ctx)


@staff_only
def panel_property_delete(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        prop.delete()
        messages.success(request, f"'{prop.title}' o'chirildi.")
    return redirect('panel_properties')


@staff_only
def panel_property_toggle_premium(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    prop.is_premium = not prop.is_premium
    prop.save(update_fields=['is_premium'])
    return JsonResponse({'is_premium': prop.is_premium})


# ── Users ─────────────────────────────────────────────────────────────────────

@staff_only
def panel_users(request):
    qs = User.objects.prefetch_related('properties', 'favorites').select_related('profile').order_by('-date_joined')
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    if q:
        qs = qs.filter(username__icontains=q) | qs.filter(email__icontains=q)
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'blocked':
        qs = qs.filter(is_active=False)
    elif status == 'staff':
        qs = qs.filter(is_staff=True)

    ctx = {
        'page': 'users',
        'users': qs,
        'q': q,
        'status': status,
    }
    return render(request, 'panel/users.html', ctx)


@staff_only
def panel_user_toggle_block(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        return JsonResponse({'error': "O'zingizni bloklayolmaysiz"}, status=400)
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    return JsonResponse({'is_active': user.is_active})


@staff_only
def panel_user_toggle_staff(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        return JsonResponse({'error': "O'zingizni o'zgartira olmaysiz"}, status=400)
    user.is_staff = not user.is_staff
    user.save(update_fields=['is_staff'])
    return JsonResponse({'is_staff': user.is_staff})


@staff_only
def panel_user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if user == request.user:
            messages.error(request, "O'zingizni o'chira olmaysiz.")
        else:
            user.delete()
            messages.success(request, f"'{user.username}' o'chirildi.")
    return redirect('panel_users')


# ── Categories ────────────────────────────────────────────────────────────────

@staff_only
def panel_categories(request):
    cats = Category.objects.annotate(prop_count=Count('properties')).order_by('name')
    ctx = {'page': 'categories', 'categories': cats}
    return render(request, 'panel/categories.html', ctx)


@staff_only
def panel_category_save(request):
    if request.method == 'POST':
        pk = request.POST.get('pk')
        name = request.POST.get('name', '').strip()
        icon = request.POST.get('icon', '').strip()
        if not name:
            messages.error(request, "Nom kiritilmadi.")
            return redirect('panel_categories')
        if pk:
            cat = get_object_or_404(Category, pk=pk)
            cat.name = name
            cat.icon = icon
            cat.save()
            messages.success(request, "Kategoriya yangilandi.")
        else:
            Category.objects.create(name=name, icon=icon)
            messages.success(request, "Kategoriya qo'shildi.")
    return redirect('panel_categories')


@staff_only
def panel_category_delete(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        cat.delete()
        messages.success(request, f"'{cat.name}' o'chirildi.")
    return redirect('panel_categories')


# ── Property Edit ─────────────────────────────────────────────────────────────

@staff_only
def panel_property_edit(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        prop.title       = request.POST.get('title', prop.title).strip()
        prop.description = request.POST.get('description', prop.description).strip()
        prop.price       = request.POST.get('price', prop.price)
        prop.location    = request.POST.get('location', prop.location).strip()
        prop.rooms       = request.POST.get('rooms', prop.rooms)
        prop.area        = request.POST.get('area', prop.area)
        prop.is_premium  = request.POST.get('is_premium') == 'on'
        prop.latitude    = request.POST.get('latitude') or None
        prop.longitude   = request.POST.get('longitude') or None
        cat_id = request.POST.get('category')
        if cat_id:
            prop.category_id = cat_id
        ptype = request.POST.get('property_type')
        if ptype:
            prop.property_type = ptype
        if request.FILES.get('image'):
            prop.image = request.FILES['image']
        prop.save()
        messages.success(request, "E'lon yangilandi.")
        return redirect('panel_property_edit', pk=pk)

    ctx = {
        'page': 'properties',
        'prop': prop,
        'categories': Category.objects.all(),
        'property_types': Property.PROPERTY_TYPES,
        'images': prop.images.all(),
    }
    return render(request, 'panel/property_edit.html', ctx)


@staff_only
def panel_property_image_delete(request, pk):
    img = get_object_or_404(PropertyImage, pk=pk)
    prop_pk = img.property.pk
    img.delete()
    return JsonResponse({'ok': True})


# ── User Detail ───────────────────────────────────────────────────────────────

@staff_only
def panel_user_detail(request, pk):
    u = get_object_or_404(User, pk=pk)
    props = Property.objects.filter(owner=u).order_by('-created_at')
    favs  = Favorite.objects.filter(user=u).select_related('property').order_by('-created_at')
    ctx = {
        'page': 'users',
        'u': u,
        'props': props,
        'favs': favs,
        'total_views': props.aggregate(t=Sum('views_count'))['t'] or 0,
    }
    return render(request, 'panel/user_detail.html', ctx)


# ── Favorites ─────────────────────────────────────────────────────────────────

@staff_only
def panel_favorites(request):
    qs = Favorite.objects.select_related('user', 'property', 'property__category').order_by('-created_at')
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(user__username__icontains=q) | qs.filter(property__title__icontains=q)
    ctx = {
        'page': 'favorites',
        'favorites': qs,
        'q': q,
        'total': qs.count(),
    }
    return render(request, 'panel/favorites.html', ctx)


# ── Statistics ────────────────────────────────────────────────────────────────

@staff_only
def panel_stats(request):
    # 30 kunlik e'lonlar grafigi
    labels_30, data_30 = [], []
    for i in range(29, -1, -1):
        day = now() - timedelta(days=i)
        labels_30.append(day.strftime('%d %b'))
        data_30.append(Property.objects.filter(created_at__date=day.date()).count())

    # 30 kunlik userlar
    user_labels, user_data = [], []
    for i in range(29, -1, -1):
        day = now() - timedelta(days=i)
        user_labels.append(day.strftime('%d %b'))
        user_data.append(User.objects.filter(date_joined__date=day.date()).count())

    # Kategoriya bo'yicha taqsimot
    cat_stats = Category.objects.annotate(cnt=Count('properties')).order_by('-cnt')
    cat_labels = json.dumps([c.name for c in cat_stats])
    cat_data   = json.dumps([c.cnt for c in cat_stats])

    # Tur bo'yicha
    type_stats = Property.objects.values('property_type').annotate(cnt=Count('id')).order_by('-cnt')
    type_labels = json.dumps([t['property_type'] for t in type_stats])
    type_data   = json.dumps([t['cnt'] for t in type_stats])

    ctx = {
        'page': 'stats',
        'labels_30':   json.dumps(labels_30),
        'data_30':     json.dumps(data_30),
        'user_labels': json.dumps(user_labels),
        'user_data':   json.dumps(user_data),
        'cat_labels':  cat_labels,
        'cat_data':    cat_data,
        'type_labels': type_labels,
        'type_data':   type_data,
        'top10':       Property.objects.order_by('-views_count')[:10],
        'total_views': Property.objects.aggregate(t=Sum('views_count'))['t'] or 0,
        'avg_price':   Property.objects.aggregate(a=Sum('price'))['a'] or 0,
        'premium_pct': round(Property.objects.filter(is_premium=True).count() / max(Property.objects.count(), 1) * 100),
    }
    return render(request, 'panel/stats.html', ctx)


# ── CSV exports ───────────────────────────────────────────────────────────────

import csv
from django.http import HttpResponse
from django.utils import timezone as tz

@staff_only
def panel_export_properties(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="properties_{tz.now().strftime("%Y%m%d")}.csv"'
    response.write('\ufeff')
    w = csv.writer(response)
    w.writerow(['ID','Sarlavha','Egasi','Kategoriya','Tur','Narx','Xona','Maydon','Joylashuv','Premium',"Ko'rishlar",'Sana'])
    for p in Property.objects.select_related('owner','category').order_by('-created_at'):
        w.writerow([p.pk, p.title, p.owner.username if p.owner else '',
                    p.category.name, p.get_property_type_display(),
                    p.price, p.rooms, p.area, p.location,
                    'Ha' if p.is_premium else "Yo'q", p.views_count,
                    p.created_at.strftime('%Y-%m-%d')])
    return response


@staff_only
def panel_export_users(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="users_{tz.now().strftime("%Y%m%d")}.csv"'
    response.write('\ufeff')
    w = csv.writer(response)
    w.writerow(['ID','Username','Email','Ism','Familiya','Staff','Faol',"E'lonlar",'Sana'])
    for u in User.objects.prefetch_related('properties').order_by('-date_joined'):
        w.writerow([u.pk, u.username, u.email, u.first_name, u.last_name,
                    u.is_staff, u.is_active, u.properties.count(),
                    u.date_joined.strftime('%Y-%m-%d')])
    return response


# ── Sidebar counts (context processor alternative — inject via each view) ─────

def _sidebar_counts():
    return {
        'cnt_properties': Property.objects.count(),
        'cnt_users':      User.objects.count(),
        'cnt_favorites':  Favorite.objects.count(),
        'cnt_categories': Category.objects.count(),
    }

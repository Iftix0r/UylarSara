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

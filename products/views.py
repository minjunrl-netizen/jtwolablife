from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count
import json
from .models import Product, PricePolicy, Category
from .forms import ProductForm, PricePolicyForm, CategoryForm
from accounts.models import User


@login_required
def product_list(request):
    if not request.user.is_admin:
        return redirect('dashboard:index')
    products = Product.objects.select_related('category').all()
    return render(request, 'products/product_list.html', {'products': products})


@login_required
def product_create(request):
    if not request.user.is_admin:
        return redirect('dashboard:index')
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '?곹뭹???앹꽦?섏뿀?듬땲??')
            return redirect('products:product_list')
    else:
        form = ProductForm()
    return render(request, 'products/product_form.html', {'form': form, 'title': '?곹뭹 ?깅줉'})


@login_required
def product_edit(request, pk):
    if not request.user.is_admin:
        return redirect('dashboard:index')
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, '?곹뭹???섏젙?섏뿀?듬땲??')
            return redirect('products:product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'products/product_form.html', {'form': form, 'title': '?곹뭹 ?섏젙'})


@login_required
def price_policy_list(request):
    if not request.user.is_admin:
        return redirect('dashboard:index')
    policies = PricePolicy.objects.select_related('product', 'user').all()
    return render(request, 'products/price_policy_list.html', {'policies': policies})


@login_required
def price_matrix(request):
    """?곹뭹 x ?낆껜 ?④? 留ㅽ듃由?뒪"""
    if not request.user.is_admin:
        return redirect('dashboard:index')
    products = Product.objects.filter(is_active=True)
    users = User.objects.filter(role__in=['agency', 'seller'], is_active=True).order_by('role', 'company_name')
    policies = {
        (p.product_id, p.user_id): p
        for p in PricePolicy.objects.all()
    }

    matrix = []
    for u in users:
        row = {
            'user': u,
            'prices': []
        }
        for p in products:
            policy = policies.get((p.id, u.id))
            row['prices'].append({
                'product': p,
                'policy': policy,
                'price': int(policy.price) if policy else None,
            })
        matrix.append(row)

    return render(request, 'products/price_matrix.html', {
        'products': products,
        'matrix': matrix,
    })


@login_required
@require_POST
def api_price_save(request):
    """AJAX로 단가 저장"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'forbidden'}, status=403)

    try:
        body = json.loads(request.body)
    except (TypeError, json.JSONDecodeError):
        return JsonResponse({'error': 'invalid_json'}, status=400)

    product_id = body.get('product_id')
    user_id = body.get('user_id')
    price = body.get('price')

    product = get_object_or_404(Product, pk=product_id)
    user = get_object_or_404(User, pk=user_id)

    if price is None or price == '':
        PricePolicy.objects.filter(product=product, user=user).delete()
        return JsonResponse({'status': 'deleted'})

    try:
        parsed_price = int(price)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'invalid_price'}, status=400)

    if parsed_price < 0:
        return JsonResponse({'error': 'invalid_price'}, status=400)

    policy, created = PricePolicy.objects.update_or_create(
        product=product, user=user,
        defaults={'price': parsed_price},
    )
    return JsonResponse({
        'status': 'saved',
        'price': int(policy.price),
    })


@login_required
def price_policy_create(request):
    if not request.user.is_admin:
        return redirect('dashboard:index')
    if request.method == 'POST':
        form = PricePolicyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '?④? ?뺤콉???앹꽦?섏뿀?듬땲??')
            return redirect('products:price_policy_list')
    else:
        form = PricePolicyForm()
    return render(request, 'products/price_policy_form.html', {'form': form, 'title': '?④? ?ㅼ젙'})


@login_required
def price_policy_edit(request, pk):
    if not request.user.is_admin:
        return redirect('dashboard:index')
    policy = get_object_or_404(PricePolicy, pk=pk)
    if request.method == 'POST':
        form = PricePolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, '?④? ?뺤콉???섏젙?섏뿀?듬땲??')
            return redirect('products:price_policy_list')
    else:
        form = PricePolicyForm(instance=policy)
    return render(request, 'products/price_policy_form.html', {'form': form, 'title': '?④? ?섏젙'})


@login_required
def price_policy_delete(request, pk):
    if not request.user.is_admin:
        return redirect('dashboard:index')
    policy = get_object_or_404(PricePolicy, pk=pk)
    if request.method == 'POST':
        policy.delete()
        messages.success(request, '?④? ?뺤콉????젣?섏뿀?듬땲??')
    return redirect('products:price_policy_list')


@login_required
def api_product_schema(request, pk):
    product = get_object_or_404(Product, pk=pk)
    user = request.user
    # ?대떦 ?좎????④? 議고쉶
    try:
        policy = PricePolicy.objects.get(product=product, user=user)
        price = int(policy.price)
    except PricePolicy.DoesNotExist:
        price = int(product.base_price)
    return JsonResponse({
        'schema': product.schema,
        'price': price,
        'name': product.name,
        'description': product.description or '',
        'min_work_days': product.min_work_days,
        'max_work_days': product.max_work_days,
    })


# ?? 移댄뀒怨좊━ 愿由???????????????????????????????????

@login_required
def category_list(request):
    if not request.user.is_admin:
        return redirect('dashboard:index')
    categories = Category.objects.annotate(
        product_count=Count('products')
    ).all()
    return render(request, 'products/category_list.html', {'categories': categories})


@login_required
def category_create(request):
    if not request.user.is_admin:
        return redirect('dashboard:index')
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '移댄뀒怨좊━媛 ?앹꽦?섏뿀?듬땲??')
            return redirect('products:category_list')
    else:
        form = CategoryForm()
    return render(request, 'products/category_form.html', {'form': form, 'title': '移댄뀒怨좊━ ?깅줉'})


@login_required
def category_edit(request, pk):
    if not request.user.is_admin:
        return redirect('dashboard:index')
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, '移댄뀒怨좊━媛 ?섏젙?섏뿀?듬땲??')
            return redirect('products:category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'products/category_form.html', {'form': form, 'title': '移댄뀒怨좊━ ?섏젙'})


@login_required
def category_delete(request, pk):
    if not request.user.is_admin:
        return redirect('dashboard:index')
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, '移댄뀒怨좊━媛 ??젣?섏뿀?듬땲??')
    return redirect('products:category_list')


@login_required
def api_category_products(request, pk):
    """移댄뀒怨좊━???쒖꽦 ?곹뭹 紐⑸줉 JSON 諛섑솚"""
    category = get_object_or_404(Category, pk=pk, is_active=True)
    products = category.products.filter(is_active=True).order_by('name')
    data = []
    for p in products:
        # ?ъ슜?먮퀎 ?④? 議고쉶
        try:
            policy = PricePolicy.objects.get(product=p, user=request.user)
            price = int(policy.price)
        except PricePolicy.DoesNotExist:
            price = int(p.base_price)
        data.append({
            'id': p.id,
            'name': p.name,
            'description': p.description or '',
            'price': price,
        })
    return JsonResponse({'products': data})


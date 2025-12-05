from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from .models import Product, Category, Brand, Wishlist
from .forms import ProductForm, ProductImageFormSet, ProductVariantFormSet

def is_staff_or_superuser(user):
    return user.is_staff or user.is_superuser

@user_passes_test(is_staff_or_superuser)
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        image_formset = ProductImageFormSet(request.POST, request.FILES)
        variant_formset = ProductVariantFormSet(request.POST)
        
        if form.is_valid() and image_formset.is_valid() and variant_formset.is_valid():
            with transaction.atomic():
                product = form.save()
                
                images = image_formset.save(commit=False)
                for image in images:
                    image.product = product
                    image.save()
                image_formset.save_m2m()
                
                variants = variant_formset.save(commit=False)
                for variant in variants:
                    variant.product = product
                    variant.save()
                variant_formset.save_m2m()
                
                return redirect('catalog:detail', slug=product.slug)
    else:
        form = ProductForm()
        image_formset = ProductImageFormSet()
        variant_formset = ProductVariantFormSet()
    
    return render(request, 'catalog/product_form.html', {
        'form': form,
        'image_formset': image_formset,
        'variant_formset': variant_formset
    })

class ProductListView(ListView):
    model = Product
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).prefetch_related("images", "brand", "categories")
        
        # Filtering
        category_slug = self.request.GET.get("category")
        brand_slug = self.request.GET.get("brand")
        search_query = self.request.GET.get("q")

        if category_slug:
            qs = qs.filter(categories__slug=category_slug)
        
        if brand_slug:
            qs = qs.filter(brand__slug=brand_slug)

        if search_query:
            qs = qs.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(sku__icontains=search_query)
            )

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.filter(is_active=True)
        context["brands"] = Brand.objects.filter(is_active=True)
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = "catalog/product_detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Product.objects.filter(is_active=True).prefetch_related("images", "variants", "brand", "categories")


class WishlistListView(LoginRequiredMixin, ListView):
    model = Wishlist
    template_name = "catalog/wishlist.html"
    context_object_name = "wishlist_items"

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related("product").prefetch_related("product__images")


@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)

    if not created:
        wishlist_item.delete()
        added = False
    else:
        added = True

    return JsonResponse({
        "added": added,
        "count": Wishlist.objects.filter(user=request.user).count()
    })


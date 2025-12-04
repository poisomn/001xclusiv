from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import Product, Category, Brand

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


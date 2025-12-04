from django.shortcuts import render
from apps.catalog.models import Product   # 👈 importa el modelo

def home(request):
    featured = (
        Product.objects
        .filter(is_active=True, is_featured=True)  # activos + destacados
        .prefetch_related("images")               # para las fotos
    )[:4]  # máximo 4 en el home (cámbialo si quieres)

    context = {
        "title": "001xclusiv",
        "featured_products": featured,
    }
    return render(request, "core/home.html", context)

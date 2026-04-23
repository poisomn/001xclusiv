from django.http import Http404
from django.db.models import Count, Prefetch, Q
from django.shortcuts import render

from apps.catalog.models import Category, Product, ProductVariant, Wishlist


CATEGORY_VISUALS = {
    "hombre": {
        "image": "home/hombreCate.jpg",
        "eyebrow": "Para los sangres",
    },
    "mujer": {
        "image": "home/mujerCate.jpg",
        "eyebrow": "Para las reinas",
    },
    "ninos": {
        "image": "home/airforcelv8blackbrown.jpg",
        "eyebrow": "Para los mini sangres",
    },
    "calzado": {
        "image": "home/airmutblackhome2.png",
        "eyebrow": "Pedales",
    },
    "ropa": {
        "image": "home/ropa.jpg",
        "eyebrow": "Prenditas del corte pa' todos",
    },
    "accesorios": {
        "image": "home/airmutblackhome.jpg",
        "eyebrow": "Los detallitos que marcan la diferencia en el outfit",
    },
}

HOME_TESTIMONIALS = [
    {
        "quote": "No se siente como comprar algo al azar. Se siente como elegir una pieza que si va conmigo.",
        "author": "Camila R.",
        "role": "Compra verificada",
    },
    {
        "quote": "Entre por unas sneakers y termine armando presencia completa. Eso es lo que hace distinta a la marca.",
        "author": "Matias G.",
        "role": "Cliente frecuente",
    },
    {
        "quote": "001xclusiv no se ve como una tienda generica. Se siente como una identidad con criterio propio.",
        "author": "Valentina S.",
        "role": "Amante del streetwear",
    },
]

HOME_IMMERSIVE_METRICS = [
    {
        "value": "001",
        "label": "the only one",
        "description": "Exclusivity, Originality, Distinctiveness, Uniqueness, Authenticity.",
    },
    {
        "value": "100%",
        "label": "único",
        "description": "Sé quien quieras ser, pero sé único.",
    },
    {
        "value": "360",
        "label": "vístete entero xclusiv",
        "description": "Aquí te armas de pies a cabeza, échale un ojito a las categorías👀.",
    },
]

HOME_EDITORIAL_PANELS = [
    {
        "image": "home/airmutblackhome1.jpg",
        "eyebrow": "Presencia real",
        "title": "No vendemos solo producto, vendemos como entras al espacio.",
        "copy": "Sombras, textura y silueta. Todo esta pensado para que la prenda te sume presencia antes de hablar.",
        "query": "category=calzado",
    },
    {
        "image": "home/retro4bcathome.jpg",
        "eyebrow": "Street code",
        "title": "Cada drop tiene que sostenerse con actitud, no con relleno.",
        "copy": "Si no transmite algo al verlo, no entra. Asi de simple. Queremos piezas que te hagan ver xclusiv.",
        "query": "sort=newest",
    },
]

HOME_JOURNEY_STEPS = [
    {
        "step": "01",
        "title": "Entras y ya se siente",
        "text": "El home tiene que atraparte al primer segundo. No para que mires, para que quieras quedarte un rato mas.",
    },
    {
        "step": "02",
        "title": "Encuentras tu energia",
        "text": "Hay quien viene por unas sneakers, hay quien quiere outfit completo. El scroll acompana ambos caminos sin perder identidad.",
    },
    {
        "step": "03",
        "title": "Sales con algo tuyo",
        "text": "Cada bloque tiene que dejarte una salida natural: guardar, explorar, elegir talla o entrar directo al carrito.",
    },
]

HOME_BRAND_PROMISES = [
    {
        "title": "Menos ruido, mas identidad",
        "text": "No todo merece entrar. Solo lo que de verdad sostiene el universo 001xclusiv.",
    },
    {
        "title": "Vestirte tambien es decir algo",
        "text": "La seleccion no busca llenar catalogo. Busca ayudarte a construir presencia con criterio.",
    },
    {
        "title": "No parecer una tienda mas",
        "text": "La experiencia tiene que sentirse propia, con tono, con presencia y con una forma distinta de mostrar producto.",
    },
]

INFO_PAGES = {
    "about": {
        "title": "Sobre 001xclusiv",
        "meta_description": "Conoce la vision de 001xclusiv, una tienda enfocada en streetwear curado, drops con criterio y una experiencia premium.",
        "hero_kicker": "Nuestra vision",
        "hero_title": "001xclusiv nace para que vestir distinto se sienta natural.",
        "hero_copy": "No buscamos llenar un catalogo por llenar. Buscamos construir una seleccion con presencia, criterio visual y una forma mas cuidada de presentar streetwear, sneakers y accesorios.",
        "sections": [
            {
                "title": "Curaduria antes que ruido",
                "body": "Cada producto deberia tener una razon para estar aqui. Por eso pensamos el catalogo como una seleccion con identidad, no como un listado generico.",
            },
            {
                "title": "Una experiencia mas editorial",
                "body": "Queremos que entrar a la tienda se parezca mas a entrar a una marca con universo propio que a navegar una plantilla comun de e-commerce.",
            },
            {
                "title": "Streetwear con intencion",
                "body": "La idea es que puedas armar un look completo y encontrar piezas que dialoguen entre si, desde el primer scroll hasta el checkout.",
            },
        ],
        "highlights": [
            "Seleccion enfocada en sneakers, ropa y accesorios con personalidad.",
            "Visual premium alineado con la identidad de la marca.",
            "Compra mas clara, mas confiable y con mejor lectura de producto.",
        ],
    },
    "shipping": {
        "title": "Envios y entregas",
        "meta_description": "Informacion de envios, tiempos de entrega y alcance de despacho en 001xclusiv.",
        "hero_kicker": "Informacion de compra",
        "hero_title": "Envios claros para que compres con menos friccion.",
        "hero_copy": "Queremos que el proceso sea simple: confirmar tu pedido, prepararlo con cuidado y mantener una expectativa realista sobre despacho y tiempos.",
        "sections": [
            {
                "title": "Preparacion del pedido",
                "body": "Una vez confirmado el pedido, nuestro objetivo es prepararlo lo antes posible. Los tiempos pueden variar segun volumen, disponibilidad y direccion de despacho.",
            },
            {
                "title": "Cobertura",
                "body": "Trabajamos para despachar dentro de Chile y priorizar entregas seguras. Si una direccion requiere coordinacion especial, te contactaremos antes de cerrar el envio.",
            },
            {
                "title": "Seguimiento",
                "body": "A medida que el MVP siga creciendo, iremos incorporando mas automatizaciones para el tracking. Mientras tanto, el estado del pedido en tu cuenta ya entrega contexto de avance.",
            },
        ],
        "highlights": [
            "Procesamiento claro del pedido.",
            "Estados visibles desde tu cuenta.",
            "Base preparada para sumar tracking mas adelante.",
        ],
    },
    "returns": {
        "title": "Cambios y devoluciones",
        "meta_description": "Politica base de cambios y devoluciones de 001xclusiv para dar mas confianza al momento de comprar.",
        "hero_kicker": "Compra con confianza",
        "hero_title": "Una politica clara mejora la confianza incluso antes del checkout.",
        "hero_copy": "En esta etapa MVP, lo importante es dejar expectativas transparentes: si hay un problema con el pedido, deberia existir un camino claro para resolverlo.",
        "sections": [
            {
                "title": "Productos en buen estado",
                "body": "Para evaluar un cambio o devolucion, el producto debe conservar su estado original, sin uso indebido y con todos sus elementos asociados.",
            },
            {
                "title": "Revision del caso",
                "body": "Cada solicitud se revisa considerando el estado del producto, el motivo del requerimiento y la informacion entregada por el cliente.",
            },
            {
                "title": "Resolucion",
                "body": "Dependiendo del caso, podremos orientar un cambio, devolucion o solucion alternativa. La meta es resolver sin ambiguedad y con comunicacion clara.",
            },
        ],
        "highlights": [
            "Evaluacion caso a caso con criterio claro.",
            "Compra mas segura gracias a reglas visibles.",
            "Espacio preparado para sumar politica legal completa mas adelante.",
        ],
    },
    "faq": {
        "title": "Preguntas frecuentes",
        "meta_description": "Resuelve dudas frecuentes sobre pedidos, stock, tallas, envios y funcionamiento general de 001xclusiv.",
        "hero_kicker": "FAQ",
        "hero_title": "Las preguntas mas comunes tambien son parte de la experiencia.",
        "hero_copy": "Una buena tienda responde dudas antes de que se conviertan en friccion. Esta base de FAQ ayuda a dar claridad desde el primer contacto.",
        "faq_items": [
            {
                "question": "Como se si un producto sigue disponible?",
                "answer": "Cada detalle de producto muestra disponibilidad y tallas activas. Si un producto deja de estar publicado o sin stock, el catalogo se actualiza en consecuencia.",
            },
            {
                "question": "Puedo guardar productos para revisarlos despues?",
                "answer": "Si. La wishlist te permite marcar favoritos y volver a ellos cuando quieras desde tu cuenta.",
            },
            {
                "question": "Donde veo el estado de mi compra?",
                "answer": "Dentro de tu perfil puedes revisar tu historial de pedidos, entrar al detalle de cada orden y descargar el comprobante de pedido.",
            },
            {
                "question": "Ya existe comprobante de pago?",
                "answer": "Por ahora la app genera comprobante de pedido. El comprobante de pago quedara para una siguiente etapa del proyecto.",
            },
        ],
        "highlights": [
            "Dudas frecuentes resueltas en un solo lugar.",
            "Menos friccion antes y despues de comprar.",
            "Base preparada para crecer con nuevas respuestas.",
        ],
    },
    "contact": {
        "title": "Contacto",
        "meta_description": "Canales de contacto y atencion de 001xclusiv para resolver dudas sobre pedidos, productos y la marca.",
        "hero_kicker": "Conversemos",
        "hero_title": "Cuando la tienda responde bien, la confianza sube sola.",
        "hero_copy": "Si tienes dudas sobre un producto, un pedido o simplemente quieres saber mas de la marca, dejamos un punto de contacto claro dentro del MVP.",
        "sections": [
            {
                "title": "Correo principal",
                "body": "001xclusiv@gmail.com",
            },
            {
                "title": "Horario referencial",
                "body": "Respuesta prioritaria durante horario comercial, con seguimiento progresivo para consultas de post-venta.",
            },
            {
                "title": "Instagram / comunidad",
                "body": "La marca puede apoyarse tambien en redes para contenido, novedades y cercania con la comunidad.",
            },
        ],
        "highlights": [
            "Canal claro para dudas de compra.",
            "Mejor percepcion de soporte y legitimidad.",
            "Preparado para sumar WhatsApp o formulario mas adelante.",
        ],
    },
}


def _home_product_queryset():
    variant_qs = ProductVariant.objects.filter(is_active=True).order_by("size")
    return (
        Product.objects.filter(is_active=True)
        .select_related("brand")
        .prefetch_related(
            "images",
            "categories",
            Prefetch("variants", queryset=variant_qs),
        )
    )


def home(request):
    product_qs = _home_product_queryset()

    featured_products = list(
        product_qs.filter(is_featured=True).order_by("-created_at", "-updated_at")[:8]
    )
    featured_ids = [product.id for product in featured_products]

    if len(featured_products) < 4:
        fallback_products = list(
            product_qs.exclude(id__in=featured_ids).order_by("-created_at")[: 4 - len(featured_products)]
        )
        featured_products.extend(fallback_products)
        featured_ids.extend(product.id for product in fallback_products)

    new_arrivals = list(
        product_qs.exclude(id__in=featured_ids).order_by("-created_at")[:4]
    )

    category_qs = (
        Category.objects.filter(is_active=True)
        .annotate(
            active_products=Count(
                "products",
                filter=Q(products__is_active=True),
                distinct=True,
            )
        )
        .filter(active_products__gt=0)
        .order_by("-active_products", "name")[:6]
    )
    featured_categories = [
        {
            "category": category,
            "image": CATEGORY_VISUALS.get(category.slug, {}).get(
                "image",
                "home/airforcelv8blackbrown.jpg",
            ),
            "eyebrow": CATEGORY_VISUALS.get(category.slug, {}).get(
                "eyebrow",
                "Curado para ti",
            ),
        }
        for category in category_qs
    ]

    wishlist_product_ids = set()
    if request.user.is_authenticated:
        wishlist_product_ids = set(
            Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True)
        )

    context = {
        "title": "001xclusiv",
        "seo_title": "001xclusiv - Streetwear y sneakers curados",
        "seo_description": "Explora 001xclusiv, una experiencia editorial de streetwear, sneakers y accesorios con seleccion premium y compra mas clara.",
        "featured_products": featured_products,
        "new_arrivals": new_arrivals,
        "featured_categories": featured_categories,
        "testimonials": HOME_TESTIMONIALS,
        "immersive_metrics": HOME_IMMERSIVE_METRICS,
        "editorial_panels": HOME_EDITORIAL_PANELS,
        "journey_steps": HOME_JOURNEY_STEPS,
        "brand_promises": HOME_BRAND_PROMISES,
        "wishlist_product_ids": wishlist_product_ids,
    }
    return render(request, "core/home.html", context)


def info_page(request, slug):
    page = INFO_PAGES.get(slug)
    if not page:
        raise Http404("Pagina no encontrada.")
    return render(
        request,
        "core/info_page.html",
        {
            "page": page,
            "slug": slug,
            "seo_title": f"{page['title']} - 001xclusiv",
            "seo_description": page["meta_description"],
        },
    )

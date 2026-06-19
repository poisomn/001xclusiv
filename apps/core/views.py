from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.http import Http404, JsonResponse
from django.db.models import Count, Prefetch, Q
from django.shortcuts import render
from django.contrib.staticfiles import finders
from django.conf import settings
from django.views.decorators.http import require_POST

from apps.catalog.models import Category, Product, ProductVariant, Wishlist
from apps.core.models import CommunityImage, NewsletterSubscriber
from apps.notifications.services import send_newsletter_discount_email


CATEGORY_VISUALS = {
    "accesories-xclusiv": {
        "image": "home/airmutblackhome.jpg",
        "eyebrow": "Detalles xclusiv",
    },
    "bags-001xclusiv": {
        "image": "home/20251204_072107000_iOS.jpg",
        "eyebrow": "Carry pieces",
    },
    "clothing-001xclusiv": {
        "image": "home/ropa.jpg",
        "eyebrow": "Clothing edit",
    },
    "hoodies--001xclusiv": {
        "image": "home/hombreCate.jpg",
        "eyebrow": "Hoodies",
    },
    "hoodies-001xclusiv": {
        "image": "home/hombreCate.jpg",
        "eyebrow": "Hoodies",
    },
    "jackets-001xclusiv": {
        "image": "home/retro4bcathome.jpg",
        "eyebrow": "Outer layers",
    },
    "outerwear-001xclusiv": {
        "image": "home/airforcehome.jpg",
        "eyebrow": "Outerwear",
    },
    "pants-001xclusiv": {
        "image": "home/mujerCate.jpg",
        "eyebrow": "Pants",
    },
    "sneakers-xclusiv": {
        "image": "home/airmutblackhome2.png",
        "eyebrow": "Sneakers",
    },
    "t-shirts-001xclusiv": {
        "image": "home/airforcelv8black.jpg",
        "eyebrow": "T-Shirts",
    },
    "hombre": {
        "image": "home/hombreCate.jpg",
        "eyebrow": "Para los sangres",
    },
    "mujer": {
        "image": "home/mujerCate.jpg",
        "eyebrow": "Para las reinas",
    },
    "niños": {
        "image": "home/airforcelv8blackbrown.jpg",
        "eyebrow": "Para los mini sangres",
    },
    "calzado": {
        "image": "home/airmutblackhome2.png",
        "eyebrow": "Pedales",
    },
    "ninos": {
        "image": "home/airforcelv8blackbrown.jpg",
        "eyebrow": "Para los mini sangres",
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

HOME_CATEGORY_FALLBACK = "home/airforcelv8blackbrown.jpg"
CATEGORY_VISUALS["ni\u00f1os"] = CATEGORY_VISUALS["ninos"]

HOME_CATEGORY_SLUGS = [
    "sneakers-xclusiv",
    "clothing-001xclusiv",
    "hoodies--001xclusiv",
    "jackets-001xclusiv",
    "pants-001xclusiv",
    "t-shirts-001xclusiv",
    "bags-001xclusiv",
    "accesories-xclusiv",
]

HOME_TESTIMONIALS = [
    {
        "quote": "Buenas, por aquí el Admin, les doy las gracias por su compra, espero disfruten su pedido cabros (obvio que me quedé con unas black cat fichitas 😼).",
        "author": "Christopher Araya",
        "role": "Compra verificada",
    },
    {
        "quote": "Entré a comprar unas zapatillas y me quedé viendo la página por más de una hora jkajskaja, me encantó todo, bacán como evolucionó la página compañero.",
        "author": "Alonso M.",
        "role": "Cliente frecuente",
    },
    {
        "quote": "001xclusiv🔥🔥, gracias cabros, está muy bueno todo.",
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
        "title": "Entra, encuentra tu estilo, encuentrate tú",
        "text": "La idea es que si no venías con algo en mente, salgas con una idea clara de lo que quieres y con algo que refleje tu personalidad.",
    },
    {
        "step": "02",
        "title": "Favoritos, wishlist, carrito y listo",
        "text": "Explora el catálogo, ve lo que te gusta, añádelo a tu wishlist, o directito al carrito.",
    },
    {
        "step": "03",
        "title": "Post-pago nosotros nos encargamos de todo",
        "text": "Seleccionaste, hiciste el pago, ahora nosotros nos encargamos de todo lo demás. Lo que más nos importa es fortalecer la confianza y brindarte una experiencia 5 estrellas.",
    },
]

HOME_BRAND_PROMISES = [
    {
        "title": "Más exclusivo, menos relleno",
        "text": "No vendemos por vender, vendemos porque nos aburrimos de las típicas tiendas de SNKRS que no ofrecen nada nuevo.",
    },
    {
        "title": "Selección con intención",
        "text": "No tenemos stock por tenerlo, nuestro stock es único, para ti.",
    },
    {
        "title": "No parecer una tienda más",
        "text": "Queremos que entres a la tienda y sepas que estás en 001xclusiv y no en cualquier tienda de Streetwear / SNKRS.",
    },
]

INFO_PAGES = {
    "about": {
        "title": "Sobre 001xclusiv",
        "meta_description": "Conoce la visión de 001xclusiv, una tienda enfocada en streetwear curado, drops con criterio y una experiencia premium.",
        "hero_kicker": "Nuestra visión",
        "hero_title": "001xclusiv nace para brindar la experiencia que otros no dan.",
        "hero_copy": "Nuestro catálogo está pensado con una selección hecha por nosotros mismos, con intención, criterio visual y una forma diferente de presentar streetwear, sneakers y accesorios.",
        "sections": [
            {
                "title": "El sueño siempre fue 001",
                "body": "Todos los productos tienen una razón para estar aquí. Por eso pensamos el catálogo como una selección con identidad, no como un listado generico.",
            },
            {
                "title": "Una experiencia premium",
                "body": "Queremos que comprar sea claro, visual y confiable. Desde el primer scroll hasta el checkout, 001xclusiv busca transmitir seguridad, estética y una experiencia más cuidada para quienes valoran lo exclusivo.",
            },
            {
                "title": "La cultura nos mueve",
                "body": "Nos mueve la cultura urbana, las zapatillas, los drops, los detalles y esa sensación de encontrar una pieza que calza con tu estilo. La tienda está pensada para sentirse como una marca, no como una plantilla más de internet.",
            },
        ],
        "highlights": [
            "👟 Sneakers, ropa y accesorios seleccionados con criterio.",
            "🖤 Identidad visual premium, deluxe y callejera.",
            "🛒 Compra clara, segura y pensada para productos exclusivos.",
        ],
    },
    "shipping": {
        "title": "Envíos y entregas",
        "meta_description": "Información sobre envíos, tiempos de entrega y despacho de productos físicos en 001xclusiv.",
        "hero_kicker": "📦 Envíos",
        "hero_title": "Tu pedido merece llegar bien, claro y sin vueltas.",
        "hero_copy": "Sabemos que cuando compras una pieza exclusiva, quieres claridad. Por eso buscamos que cada pedido tenga un proceso simple: confirmación, preparación y entrega con comunicación transparente.",
        "sections": [
            {
                "title": "Preparación del pedido",
                "body": "Una vez confirmado el pago, preparamos tu pedido con cuidado. Revisamos producto, talla y datos de entrega antes de avanzar al despacho.",
            },
            {
                "title": "Cobertura",
                "body": "Inicialmente trabajamos con despachos dentro de Chile. Si la dirección necesita coordinación especial, te contactaremos para confirmar los detalles antes del envío.",
            },
            {
                "title": "Seguimiento",
                "body": "Desde tu cuenta puedes revisar el estado de tus pedidos. A medida que la tienda crezca, se integrarán opciones de tracking más automatizadas.",
            },
        ],
        "highlights": [
            "📍 Despacho orientado a Chile.",
            "🧾 Estado del pedido visible desde tu cuenta.",
            "📦 Preparación cuidadosa antes del envío.",
        ],
    },
    "returns": {
        "title": "Cambios y devoluciones",
        "meta_description": "Política base de cambios y devoluciones de 001xclusiv para comprar con mayor seguridad y claridad.",
        "hero_kicker": "🔁 Cambios",
        "hero_title": "Comprar exclusivo también debe sentirse seguro.",
        "hero_copy": "Queremos que cada compra tenga reglas claras. Si existe un problema con tu pedido, la idea es resolverlo con comunicación directa, criterio y transparencia.",
        "sections": [
            {
                "title": "Estado del producto",
                "body": "Para evaluar un cambio o devolución, el producto debe conservar su estado original, sin uso, sin daños y con sus elementos asociados cuando corresponda.",
            },
            {
                "title": "Revisión caso a caso",
                "body": "Cada solicitud será revisada considerando el motivo, el estado del producto y la información entregada por el cliente.",
            },
            {
                "title": "Resolución clara",
                "body": "Dependiendo del caso, se podrá orientar un cambio, devolución o solución alternativa. Lo importante es evitar ambigüedades y mantener comunicación clara.",
            },
        ],
        "highlights": [
            "✅ Revisión transparente del caso.",
            "🧼 Productos deben mantener su estado original.",
            "🤝 Comunicación directa para resolver problemas.",
        ],
    },
    "faq": {
        "title": "Preguntas frecuentes",
        "meta_description": "Resuelve dudas frecuentes sobre pedidos, stock, tallas, pagos, envíos y funcionamiento general de 001xclusiv.",
        "hero_kicker": "❓ FAQ",
        "hero_title": "Preguntas claras para comprar sin dudas.",
        "hero_copy": "Una buena experiencia también significa responder antes de que exista la fricción. Aquí reunimos dudas importantes sobre productos, pedidos y pagos.",
        "faq_items": [
            {
                "question": "¿Cómo sé si un producto sigue disponible?",
                "answer": "Cada producto muestra disponibilidad según sus tallas activas. Si una talla se queda sin stock o el producto deja de estar publicado, el catálogo se actualiza según la gestión del backoffice.",
            },
            {
                "question": "¿Puedo guardar productos para revisarlos después?",
                "answer": "Sí. Puedes usar la wishlist para guardar tus favoritos y volver a ellos desde tu cuenta cuando quieras.",
            },
            {
                "question": "¿Dónde veo el estado de mi compra?",
                "answer": "Desde tu perfil puedes revisar tus pedidos, entrar al detalle de cada orden y ver su estado actual.",
            },
            {
                "question": "¿El pago es seguro?",
                "answer": "Sí. El checkout está integrado con Flow, una pasarela de pago que permite procesar transacciones de forma segura mediante Webpay y otros medios disponibles.",
            },
            {
                "question": "¿Recibo comprobante de mi compra?",
                "answer": "Sí. Al crear un pedido y al confirmar un pago, el sistema puede generar comprobantes y enviar notificaciones al correo registrado.",
            },
        ],
        "highlights": [
            "🧠 Dudas importantes en un solo lugar.",
            "💳 Información clara sobre pago y pedidos.",
            "🛍️ Menos trámites antes y después de comprar.",
        ],
    },
    "contact": {
        "title": "Contacto",
        "meta_description": "Contacta a 001xclusiv para resolver dudas sobre productos, pedidos, pagos, envíos y novedades de la marca.",
        "hero_kicker": "📲 Contacto",
        "hero_title": "Si tienes dudas, hablemos directo.",
        "hero_copy": "Ya sea por un producto, una talla, un pedido o simplemente porque quieres saber más de la marca, aquí tienes nuestros canales de contacto.",
        "sections": [
            {
                "title": "📧 Correo principal",
                "body": "001xclusiv@gmail.com",
            },
            {
                "title": "📸 Instagram",
                "body": "@001xclusiv",
            },
            {
                "title": "🕒 Horario referencial",
                "body": "Respondemos prioritariamente durante horario comercial. Las consultas de pedidos y post-venta tendrán seguimiento según el caso.",
            },
        ],
        "highlights": [
            "📩 Canal claro para dudas de compra.",
            "📸 Instagram para novedades, drops y comunidad.",
            "🤝 Atención directa para pedidos y post-venta.",
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


def _static_asset_exists(path):
    return bool(finders.find(path))


def _home_static_asset(*candidates):
    for candidate in candidates:
        if candidate and _static_asset_exists(candidate):
            return candidate
    return ""


def _home_static_url(path):
    if not path:
        return ""
    return f"{settings.STATIC_URL}{path}"


def _category_visual(category):
    visual = (
        CATEGORY_VISUALS.get(category.slug)
        or CATEGORY_VISUALS.get(category.slug.replace("-", "_"))
        or CATEGORY_VISUALS.get(category.name.strip().lower())
        or {}
    )
    image_url = category.image_url.strip() if category.image_url else ""
    image_path = category.image_path.strip() if category.image_path else ""
    if not image_url and image_path and _static_asset_exists(image_path):
        image_url = _home_static_url(image_path)
    if not image_url:
        image = visual.get("image", HOME_CATEGORY_FALLBACK)
        if not _static_asset_exists(image):
            image = HOME_CATEGORY_FALLBACK
        image_url = _home_static_url(image)
    return {
        "category": category,
        "image_url": image_url,
        "eyebrow": category.visual_eyebrow or visual.get("eyebrow", "Curado para ti"),
    }


def _home_featured_categories():
    categories = (
        Category.objects.filter(is_active=True)
        .annotate(
            active_products=Count(
                "products",
                filter=Q(products__is_active=True),
                distinct=True,
            )
        )
    )
    priority = {slug: index for index, slug in enumerate(HOME_CATEGORY_SLUGS)}
    selected = list(categories.filter(slug__in=HOME_CATEGORY_SLUGS))
    selected.sort(key=lambda category: priority.get(category.slug, 999))

    if len(selected) < 8:
        selected_ids = [category.id for category in selected]
        selected.extend(
            categories.exclude(id__in=selected_ids).order_by("-active_products", "name")[: 8 - len(selected)]
        )

    return [_category_visual(category) for category in selected[:8]]


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
        product_qs.filter(show_in_new_arrivals=True).order_by("new_arrival_order", "-created_at")[:6]
    )
    if not new_arrivals:
        new_arrivals = list(product_qs.order_by("-created_at")[:6])

    featured_categories = _home_featured_categories()
    community_images = list(
        CommunityImage.objects.filter(is_active=True).order_by("ordering", "-created_at")[:12]
    )

    wishlist_product_ids = set()
    if request.user.is_authenticated:
        wishlist_product_ids = set(
            Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True)
        )

    context = {
        "title": "001xclusiv",
        "seo_title": "001xclusiv - SNKRS & Streetwear, Accesories & More...",
        "seo_description": "Explora 001xclusiv, una experiencia editorial de streetwear, sneakers y accesorios con selección premium y compra más clara.",
        "featured_products": featured_products,
        "new_arrivals": new_arrivals,
        "featured_categories": featured_categories,
        "testimonials": HOME_TESTIMONIALS,
        "immersive_metrics": HOME_IMMERSIVE_METRICS,
        "editorial_panels": HOME_EDITORIAL_PANELS,
        "journey_steps": HOME_JOURNEY_STEPS,
        "brand_promises": HOME_BRAND_PROMISES,
        "community_images": community_images,
        "community_marquee_images": community_images + community_images,
        "home_experience_video_url": _home_static_url(
            _home_static_asset("home/001experience.mp4", "home/blackcat2.mp4")
        ),
        "home_experience_poster_url": _home_static_url(
            _home_static_asset("home/videoPoster.jpg", "home/retro4bcathome.jpg")
        ),
        "wishlist_product_ids": wishlist_product_ids,
    }
    return render(request, "core/home.html", context)


@require_POST
def newsletter_subscribe(request):
    email = (request.POST.get("email") or "").strip().lower()
    validator = EmailValidator()

    try:
        validator(email)
    except ValidationError:
        return JsonResponse(
            {
                "success": False,
                "message": "Ingresa un correo valido para recibir novedades.",
            },
            status=400,
        )

    subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)

    if not created and subscriber.welcome_email_sent:
        return JsonResponse(
            {
                "success": True,
                "message": "Ya estabas registrado. Revisa tu correo para encontrar tu codigo 15% OFF.",
            }
        )

    email_sent = send_newsletter_discount_email(subscriber)
    if email_sent:
        message = "Listo. Te enviamos tu 15% OFF y quedaste registrado para nuevos drops."
    else:
        message = "Te registramos correctamente. Si el correo no llega, revisa promociones o intenta mas tarde."

    return JsonResponse({"success": True, "message": message})


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

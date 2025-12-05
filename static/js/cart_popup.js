document.addEventListener('DOMContentLoaded', function () {
    const addToCartForm = document.querySelector('form[action*="cart/add"]');

    if (addToCartForm) {
        addToCartForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const formData = new FormData(addToCartForm);
            const actionUrl = addToCartForm.action;

            // Convert FormData to JSON
            const data = {};
            formData.forEach((value, key) => data[key] = value);

            fetch(actionUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(data)
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showCartPopup(data);
                        updateCartCount(data.cart_count);
                    } else {
                        console.error('Error adding to cart');
                    }
                })
                .catch(error => console.error('Error:', error));
        });
    }
});

function showCartPopup(data) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('cart-popup-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'cart-popup-modal';
        modal.className = 'cart-popup-overlay';
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <div class="cart-popup-content">
            <div class="cart-popup-header">
                <div class="d-flex align-items-center gap-2">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2">
                        <path d="M20 6L9 17l-5-5"/>
                    </svg>
                    <span class="fw-bold">Agregado al carrito</span>
                </div>
                <button onclick="closeCartPopup()" class="btn-close-custom">&times;</button>
            </div>
            
            <div class="cart-popup-body">
                <div class="d-flex gap-3">
                    <img src="${data.product_image}" alt="${data.product_name}" class="cart-popup-img">
                    <div>
                        <h6 class="fw-bold mb-1">${data.product_name}</h6>
                        <p class="text-muted small mb-1">Talla: ${data.variant || 'Única'}</p>
                        <p class="fw-bold">$${data.price.toLocaleString('es-CL')}</p>
                    </div>
                </div>
            </div>
            
            <div class="cart-popup-footer">
                <a href="/cart/" class="btn btn-outline-dark w-100 mb-2">Ver Carrito (${data.cart_count})</a>
                <a href="/checkout/" class="btn btn-dark w-100">Pagar</a>
            </div>
        </div>
    `;

    // Show modal
    setTimeout(() => modal.classList.add('show'), 10);
}

function closeCartPopup() {
    const modal = document.getElementById('cart-popup-modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    }
}

function updateCartCount(count) {
    const badge = document.querySelector('.nav-link .badge');
    if (badge) {
        badge.textContent = count;
    } else {
        // If badge doesn't exist, create it (optional, depends on navbar structure)
        const cartLink = document.querySelector('a[href*="cart"]');
        if (cartLink) {
            const newBadge = document.createElement('span');
            newBadge.className = 'badge bg-black text-white rounded-pill ms-1';
            newBadge.textContent = count;
            cartLink.appendChild(newBadge);
        }
    }
}

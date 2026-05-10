# 001xclusiv

001xclusiv is a premium e-commerce platform for exclusive sneakers, built with Django.

## Features

- **Catalog**: Browse products with filtering by category and brand.
- **Cart**: Session-based shopping cart.
- **Checkout**: Simple checkout flow with order creation.
- **Accounts**: User registration, login, and order history.
- **Design**: Minimalist, responsive design using Bootstrap 5 and custom CSS.

## Tech Stack

- **Backend**: Python 3.13, Django 5.2.9
- **Frontend**: HTML5, CSS3, Bootstrap 5, GSAP
- **Database**: SQLite (Development)

## Setup

1. **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd 001xclusiv
    ```

2. **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Run migrations**:
    ```bash
    python manage.py migrate
    ```

5. **Create a superuser** (optional, for admin access):
    ```bash
    python manage.py createsuperuser
    ```

6. **Run the server**:
    ```bash
    python manage.py runserver
    ```

7. **Access the site**:
    Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## Project Structure

- `apps/`: Django apps (core, catalog, cart, checkout, orders, accounts, notifications).
- `config/`: Project configuration (settings, urls).
- `static/`: Static files (CSS, images).
- `templates/`: HTML templates.

## Gmail API para correos de ordenes

El proyecto envia comprobantes de orden con Gmail API usando OAuth refresh token. Si Gmail no esta configurado, el checkout y Flow continuan funcionando y el sistema solo registra un warning.

Variables de entorno:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`
- `GMAIL_SENDER_EMAIL`
- `GMAIL_SENDER_NAME`
- `ADMIN_NOTIFICATION_EMAIL`
- `SITE_URL`

Para obtener el refresh token en local:

```bash
python scripts/get_gmail_refresh_token.py
```

El script lee `credentials.json`, abre el navegador con el scope:

- `https://www.googleapis.com/auth/gmail.send`

Luego imprime los valores que deben copiarse a Render. No subas `credentials.json`, `token.json` ni `gmail_token.json` al repositorio.

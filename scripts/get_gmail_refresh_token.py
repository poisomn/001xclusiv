import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "gmail_token.json"


def load_oauth_client_config():
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"No se encontro {CREDENTIALS_FILE}. Copia ahi el JSON OAuth descargado de Google Cloud."
        )

    try:
        credentials_data = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{CREDENTIALS_FILE} no es un JSON valido: {error}") from error

    client_config = credentials_data.get("installed") or credentials_data.get("web")
    if not client_config:
        raise ValueError(
            "credentials.json debe contener una seccion 'installed' o 'web' descargada desde Google Cloud."
        )

    client_id = client_config.get("client_id")
    client_secret = client_config.get("client_secret")
    missing = [
        name
        for name, value in (
            ("client_id", client_id),
            ("client_secret", client_secret),
        )
        if not value
    ]
    if missing:
        raise ValueError(
            f"credentials.json no contiene {', '.join(missing)} en la seccion OAuth."
        )

    return client_id, client_secret


def main():
    client_id, client_secret = load_oauth_client_config()

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    credentials = flow.run_local_server(port=0, prompt="consent")

    TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")

    print("\nCopiar estos valores a las variables de entorno de Render:\n")
    print(f"GOOGLE_CLIENT_ID={client_id}")
    print(f"GOOGLE_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={credentials.refresh_token or ''}")
    print("\nTambien configura GMAIL_SENDER_EMAIL, GMAIL_SENDER_NAME, ADMIN_NOTIFICATION_EMAIL y SITE_URL.")
    print(f"\nToken local generado en: {TOKEN_FILE}")
    print("No subas credentials.json ni gmail_token.json al repositorio.")


if __name__ == "__main__":
    main()

import os
from dotenv import load_dotenv

# Em local lê o ficheiro .env. No Render não existe .env: as variáveis são
# definidas no painel (Environment) ou no render.yaml.
load_dotenv()


def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(
            f"Variável de ambiente obrigatória em falta: {key}. "
            f"Confirma o teu .env (local) ou o Environment do serviço no Render."
        )
    return value


class Config:
    # --- Segurança base ---
    SECRET_KEY = _require_env('SECRET_KEY')

    # --- Sessões ---
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 1800

    # --- Base de dados (PostgreSQL) ---
    # Lida em utils/call_conn.py. Falha cedo se faltar.
    DATABASE_URL = _require_env('DATABASE_URL')

    # --- Mail ---
    # Opcionais: se não estiverem definidos o envio falha, mas o código já
    # trata a exceção e a app arranca na mesma.
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 25))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'surveybw@borgwarner.com')
    MAIL_DEBUG = 0

    # --- Rate limiting ---
    # Em memória: usa só 1 worker do gunicorn (cada worker teria o seu contador)
    # e os contadores zeram quando o Render reinicia ou adormece o serviço.
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')

    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True
    # Só em local sem HTTPS. Em qualquer ambiente exposto isto TEM de ser True.
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False


def get_config():
    env = os.environ.get('FLASK_ENV', 'production').lower()
    return DevelopmentConfig if env == 'development' else ProductionConfig
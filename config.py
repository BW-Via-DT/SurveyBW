import os
from dotenv import load_dotenv

# Em desenvolvimento lê o .env local. Em produção, define as variáveis
# de ambiente reais no IIS
load_dotenv()


def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(
            f"Variável de ambiente obrigatória em falta: {key}. "
            f"Confirma o teu .env (dev) ou a configuração do servidor (prod)."
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

    # --- Base de dados (SQL Server via pyodbc) ---
    DB_SERVER = _require_env('DB_SERVER')
    DB_NAME = _require_env('DB_NAME')
    DB_USER = os.environ.get('DB_USER')       
    DB_PASSWORD = os.environ.get('DB_PASSWORD')  
    DB_TRUSTED_CONNECTION = os.environ.get('DB_TRUSTED_CONNECTION', 'no')  

    # --- Mail ---
    MAIL_SERVER = _require_env('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 25))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_DEFAULT_SENDER = _require_env('MAIL_DEFAULT_SENDER')
    MAIL_DEBUG = 0

    # --- Rate limiting ---
    # Em produção com mais de 1 worker/processo, troca 'memory://' por Redis
    # (RATELIMIT_STORAGE_URI=redis://...), senão cada worker tem o seu próprio contador.
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')

    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True
    # Só em dev local sem HTTPS. Em qualquer ambiente exposto, isto TEM de ser True.
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False


def get_config():
    env = os.environ.get('FLASK_ENV', 'production').lower()
    return DevelopmentConfig if env == 'development' else ProductionConfig
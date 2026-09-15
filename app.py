import logging
import logging.handlers
from datetime import datetime

from flask import redirect, render_template, session, url_for
from flask_mail import Mail

from api import create_app
from config import get_config
from extensions import limiter, csrf, talisman

app = create_app()
app.config.from_object(get_config())

mail = Mail(app)
limiter.init_app(app)
csrf.init_app(app)

# Headers de segurança + força HTTPS (exceto em debug local)
talisman.init_app(
    app,
    force_https=not app.debug,
    strict_transport_security=True,
    session_cookie_secure=not app.debug,
    content_security_policy_nonce_in=['script-src'],
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", 'cdnjs.cloudflare.com', 'cdn.jsdelivr.net', 'code.jquery.com'],
        'style-src': ["'self'", "'unsafe-inline'", 'cdnjs.cloudflare.com',
                       'cdn.jsdelivr.net', 'fonts.googleapis.com'],
        'font-src': ["'self'", 'fonts.gstatic.com', 'cdnjs.cloudflare.com', 'data:'],
        'img-src': ["'self'", 'data:'],
    },
)


def configure_logging():
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = logging.handlers.RotatingFileHandler(
        'app.log', maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.propagate = False


configure_logging()

year = datetime.now().year


@app.context_processor
def inject_template_vars():
    return {
        'current_year': year,
        'user_name': session.get('name', 'User'),
        'user_role': session.get('role', ''),
        'is_logged_in': 'local_user_id' in session,
        'page_title': "SurveyBW Application",
    }


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route('/')
def index():
    if 'local_user_id' in session:
        return redirect(url_for('surveys_routes.surveys_page'))
    return render_template('index.html', year=year)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=app.debug)
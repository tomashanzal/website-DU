# app/__init__.py
from flask import Flask, request
from dotenv import load_dotenv
import os
from flask_mail import Mail # <-- Ujisti se, že je tu tento import!

# Definujeme základní adresář projektu
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Inicializace Flask-Mail instance na globální úrovni
mail = Mail() # <-- Ujisti se, že je tu tento řádek!


def create_app():
    load_dotenv()

    app = Flask(__name__)

    app.secret_key = os.getenv("FLASK_SECRET_KEY")

    if not app.secret_key:
        print("VAROVÁNÍ: 'FLASK_SECRET_KEY' není nastaven v .env souboru! "
              "Flash zprávy a relace nebudou fungovat bezpečně.")
        app.secret_key = 'vychozi_tajny_klic_pro_vyvoj_POUZE'

    app.jinja_env.globals['request'] = request


    # --- KONFIGURACE FLASK-MAIL ZDE ---
    # Ujisti se, že celá tato sekce je zde a je správně napsaná
    print(os.getenv('MAIL_PASSWORD'))
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME') # Může být stejné jako USERNAME

    # Inicializace Flask-Mail s aplikací - TOTO JE KLÍČOVÝ ŘÁDEK!
    mail.init_app(app) # <-- Ujisti se, že je tu tento řádek!
    # --- KONEC KONFIGURACE FLASK-MAILU ---

    # --- DŮLEŽITÉ: Import Blueprintu ZDE ---
    from .routes import main
    app.register_blueprint(main)
    # --- KONEC DŮLEŽITÉHO KÓDU ---

    return app
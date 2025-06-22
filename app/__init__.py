
from flask import Flask
from flask import request
from dotenv import load_dotenv
import os
def create_app():
    # Načti proměnné z .env souboru (ujisti se, že .env existuje v kořenovém adresáři projektu)
    load_dotenv()

    app = Flask(__name__)

    # --- DŮLEŽITÉ: NASTAVENÍ SECRET_KEY PRO FLASK RELACE ---
    # Tento klíč je nezbytný pro bezpečné fungování flash zpráv a dalších relací.
    # Měl by být načten z proměnné prostředí pro produkční nasazení.
    app.secret_key = os.getenv("FLASK_SECRET_KEY")

    # Kontrola pro vývojové prostředí - upozorní, pokud klíč není nastaven
    if not app.secret_key:
        print("VAROVÁNÍ: 'FLASK_SECRET_KEY' není nastaven v .env souboru! "
              "Flash zprávy a relace nebudou fungovat bezpečně.")
        # Pro VÝVOJ můžeš nastavit dočasný klíč, ale NIKDY v PRODUKCI!
        app.secret_key = 'vychozi_tajny_klic_pro_vyvoj_POUZE'


    app.jinja_env.globals['request'] = request
    
    # Registrace Blueprintu
    from .routes import main
    app.register_blueprint(main)

    return app


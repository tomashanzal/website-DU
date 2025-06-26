from flask import Blueprint, render_template, request, redirect, url_for, flash
import qrcode
import io
import base64
import stripe
import os
from dotenv import load_dotenv


# Načti proměnné z .env souboru
load_dotenv()

# Inicializace Stripe API s tvým Secret klíčem
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

main = Blueprint('main', __name__)

@main.route("/")
def home():
    return render_template("home.html")

@main.route("/projekt")
def projekt():
    return render_template("projekt.html")

@main.route("/about")
def about():
    return render_template("about.html")

@main.route("/kontakt")
def kontakt():
    return render_template("kontakt.html")

@main.route("/payment")
def payment():
    # Zde bys mohl/a načíst a předat public key do payment.html,
    # i když pro Stripe Checkout to není nutné, je to dobrá praxe.
    # stripe_public_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
    return render_template("payment.html")

@main.route("/lektori")
def lektori():
    return render_template("lektori.html")

@main.route("/seznam-wmt-FxvluknOGKyiY9qEmSibGmmmmeAiIkhu.txt")
def random_text():
    return render_template("random_text.html")

# Platba přes Stripe (tlačítko pro vytvoření session)
@main.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        # Získání dat z formuláře
        course_name = request.form.get('course_name')
        # Zajištění, že cena je integer a v haléřích/centech
        course_price_str = request.form.get('course_price')
        if not course_price_str:
            raise ValueError("Cena kurzu nebyla zadána.")
        
        # Převod ceny z float (např. "99.00") na integer (9900)
        # Zkontroluj, zda vstup z formuláře je opravdu číslo
        try:
            # Pokud přijímáš např. "100.00", převedeme na float a pak vynásobíme 100
            # Pokud by vstup byl int (např. "100"), také to funguje
            course_price_float = float(course_price_str)
            course_price = int(course_price_float * 100)
        except ValueError:
            raise ValueError("Neplatný formát ceny kurzu. Zadejte prosím číslo.")

        child_name = request.form.get('child_name')
        parent_email = request.form.get('parent_email')

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'czk',
                    'product_data': {
                        'name': f"Kurz doučování: {course_name}",
                        'description': f"Příprava na Cermat přijímačky pro {child_name}",
                    },
                    'unit_amount': course_price, # Cena v haléřích/centech
                },
                'quantity': 1,
            }],
            mode='payment',
            # Důležité: Přidáme {CHECKOUT_SESSION_ID} pro získání session ID na success stránce
            success_url=url_for('main.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('main.cancel', _external=True),
            metadata={ # Volitelné: metadata pro Stripe session
                'course_name': course_name,
                'child_name': child_name,
                'parent_email': parent_email
            }
        )
        return redirect(session.url, code=303)
    except stripe.error.StripeError as e:
        # Chyby specifické pro Stripe
        flash(f"Chyba platby: {e}", "danger")
        print(f"Stripe Error: {e}")
        return redirect(url_for('main.payment')) # Přesměrování zpět na platební stránku
    except ValueError as e:
        # Chyby z validace dat formuláře
        flash(f"Chyba ve formuláři: {e}", "danger")
        print(f"Validation Error: {e}")
        return redirect(url_for('main.payment'))
    except Exception as e:
        # Obecné neočekávané chyby
        flash("Došlo k neočekávané chybě. Zkuste to prosím znovu.", "danger")
        print(f"Unexpected Error: {e}")
        return redirect(url_for('main.payment'))

# Route pro úspěšnou platbu s ověřením
@main.route('/success')
def success():
    session_id = request.args.get('session_id')
    if not session_id:
        # Pokud chybí session_id, něco je špatně, přesměruj nebo zobraz chybu
        flash("Chyba: Chybí ID platební relace.", "danger")
        return redirect(url_for('main.payment'))

    try:
        # Načti Stripe Checkout Session podle ID
        session = stripe.checkout.Session.retrieve(session_id)

        # Zkontroluj stav platby
        if session.payment_status == "paid":
            # Platba byla ÚSPĚŠNÁ!
            # Zde implementuj logiku pro splnění objednávky:
            # - Uložení dat do databáze (získat je můžeš ze session.metadata nebo předávat v URL)
            # - Poslání potvrzovacího e-mailu
            # - Odemknutí přístupu ke kurzu
            
            # Získání dat z metadata, pokud jsou dostupná
            course_name = session.metadata.get('course_name', 'neznámý kurz')
            child_name = session.metadata.get('child_name', 'žák')
            parent_email = session.metadata.get('parent_email', 'neznámý email')

            print(f"Platba úspěšná! Session ID: {session_id}")
            print(f"Kurz: {course_name}, Žák: {child_name}, E-mail rodiče: {parent_email}")
            
            # Doporučení: Zabraň vícenásobnému zpracování stejné platby!
            # Před dokončením objednávky zkontroluj, zda už tato session_id nebyla zpracována.
            # Např. SELECT * FROM objednavky WHERE stripe_session_id = '...'

            flash("Platba proběhla úspěšně! Děkujeme za nákup.", "success")
            return render_template("success.html", course_name=course_name, child_name=child_name)
        elif session.payment_status == "unpaid":
            flash("Platba nebyla dokončena. Zkuste to prosím znovu.", "warning")
            print(f"Platba nebyla dokončena. Session ID: {session_id}, Status: {session.payment_status}")
            return render_template("cancel.html") # Nebo specializovaná stránka pro nedokončenou platbu
        else:
            # Zde by mohly být jiné statusy jako 'no_payment_required'
            flash("Stav platby je nejednoznačný. Kontaktujte podporu.", "info")
            print(f"Stav platby nejednoznačný. Session ID: {session_id}, Status: {session.payment_status}")
            return render_template("cancel.html") # Můžete vytvořit speciální stránku
            
    except stripe.error.StripeError as e:
        flash(f"Chyba při ověřování platby u Stripe: {e}", "danger")
        print(f"Stripe Error on success page: {e}")
        return redirect(url_for('main.payment')) # Přesměrování zpět na platební stránku
    except Exception as e:
        flash("Došlo k neočekávané chybě při ověřování platby.", "danger")
        print(f"Unexpected Error on success page: {e}")
        return redirect(url_for('main.payment'))

# Route pro zrušenou platbu
@main.route('/cancel')
def cancel():
    flash("Platba byla zrušena nebo nedokončena.", "info")
    return render_template("cancel.html")







@main.route("/generate-qr", methods=["POST"])
def generate_qr():
    child_name = request.form["name_zak"]
    parent_email = request.form["parent_email"]
    course_name = request.form["course_name"]

    # Cena v haléřích
    course_price_str = request.form["course_price"]
    try:
        course_price_float = float(course_price_str)
        course_price = int(course_price_float * 100)  # v haléřích
    except ValueError:
        flash("Neplatný formát ceny kurzu pro QR platbu. Zadejte prosím číslo.", "danger")
        return redirect(url_for('main.payment'))

    amount = course_price

    # Načtení čísla účtu z .env
    account_full = os.getenv("BANK_ACCOUNT_NUMBER")
    bank_code = os.getenv("BANK_CODE")

    if account_full:
        if "/" in account_full:
            account_number, bank_code = account_full.split("/")
            account_number = account_number.strip()
            bank_code = bank_code.strip()
        else:
            account_number = account_full.strip()
            bank_code = os.getenv("BANK_CODE", "").strip()
    else:
        account_number = ""
        bank_code = os.getenv("BANK_CODE", "").strip()

    import uuid
    variable_symbol = str(uuid.uuid4().int % (10**10))  # 10místné číslo

    # Výběr QR obrázku podle ceny (haléře)
    print(course_price)
    if course_price == 200000:
        qr_filename = "ctvrtinovy.jpg"
    elif course_price == 400000:
        qr_filename = "polovicni.jpg"
    elif course_price == 750000:
        qr_filename = "komplet.jpg"
    else:
        qr_filename = "qr_default.png"  # fallback obrázek, pokud chceš

    return render_template(
        "qr_result.html",
        qr_filename=qr_filename,
        amount=amount / 100,
        account_number=account_number,
        bank_code=bank_code,
        child_name=child_name,
        parent_email=parent_email,
        course_name=course_name,
        variable_symbol=variable_symbol,
    )
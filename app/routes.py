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
            course_price = int(course_price_float /1000)
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

# Nová route pro generování QR kódu bankovního převodu
@main.route("/generate-qr", methods=["POST"])
def generate_qr():
    child_name = request.form["child_name"]
    parent_email = request.form["parent_email"]
    parent_account = request.form["parent_account"]
    course_name = request.form["course_name"]
    
    # --- ZDE DOPORUČUJI PŘESUNOUT DO .ENV SOUBORU ---
    # Cena v haléřích. Ověř, že vstup je číslo a správně se převede
    course_price_str = request.form["course_price"]
    try:
        course_price_float = float(course_price_str)
        course_price = int(course_price_float * 100) # Cena v haléřích/centech
    except ValueError:
        flash("Neplatný formát ceny kurzu pro QR platbu. Zadejte prosím číslo.", "danger")
        return redirect(url_for('main.payment')) # Nebo jiná stránka s formulářem

    # Cíl platby - DŮLEŽITÉ: NAČÍTAT Z .ENV, NE ZDE TVRDOZAKÓDOVANĚ!
    amount = course_price  # v haléřích
    account_number = os.getenv("BANK_ACCOUNT_NUMBER", "123456789/0100") # Příklad, načti z .env
    bank_code = os.getenv("BANK_CODE", "0100") # Příklad, načti z .env
    specific_symbol = os.getenv("SPECIFIC_SYMBOL", "2025") # Příklad, načti z .env
    
    # Lepší variabilní symbol - unikátní pro každou objednávku
    # Může to být např. ID z databáze nebo UUID
    import uuid
    variable_symbol = str(uuid.uuid4().int % (10**10)) # Generuje 10místné číslo

    # Zpráva pro příjemce
    message = f"Doucovani {course_name} pro {child_name}"

    # QR kód podle standardu SPD pro bankovní platbu
    qr_data = (
        f"SPD*1.0*ACC:CZ{account_number.replace('/', '')}*AM:{amount / 100:.2f}*CC:CZK*"
        f"MSG:{message}*X-VS:{variable_symbol}*X-SS:{specific_symbol}"
    )

    # Vygenerování QR kódu
    qr_img = qrcode.make(qr_data)
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return render_template(
        "qr_result.html",
        qr_code=qr_code_base64,
        amount=amount / 100,
        account_number=account_number,
        bank_code=bank_code,
        message=message,
        child_name=child_name,
        parent_email=parent_email,
        course_name=course_name,
        variable_symbol=variable_symbol,
        specific_symbol=specific_symbol
    )
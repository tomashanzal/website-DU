from flask import Blueprint, render_template, request, redirect, url_for
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
    return render_template("payment.html")

@main.route("/lektori")
def lektori():
    return render_template("lektori.html")

# Platba přes Stripe (tlačítko pro vytvoření session)
@main.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    # Získání dat z formuláře
    course_name = request.form.get('course_name')
    course_price = int(request.form.get('course_price')) # Cena je v haléřích
    child_name = request.form.get('child_name')
    parent_email = request.form.get('parent_email')

    # Můžeš si zde uložit informace o nákupu do databáze nebo je poslat e-mailem
    # například: print(f"Nákup: {course_name}, Žák: {child_name}, Rodič: {parent_email}")

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'czk',
                'product_data': {
                    'name': f"Kurz doučování: {course_name}",
                    'description': f"Příprava na Cermat přijímačky pro {child_name}",
                },
                'unit_amount': course_price,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('main.success', _external=True, course_name=course_name, child_name=child_name),
        cancel_url=url_for('main.cancel', _external=True),
        metadata={ # Volitelné: metadata pro Stripe session
            'course_name': course_name,
            'child_name': child_name,
            'parent_email': parent_email
        }
    )
    return redirect(session.url, code=303)

# Route pro úspěšnou platbu
@main.route('/success')
def success():
    course_name = request.args.get('course_name', 'neznámý kurz')
    child_name = request.args.get('child_name', 'žák')
    return render_template("success.html", course_name=course_name, child_name=child_name)

# Route pro zrušenou platbu
@main.route('/cancel')
def cancel():
    return render_template("cancel.html")

# Nová route pro generování QR kódu bankovního převodu
@main.route("/generate-qr", methods=["POST"])
def generate_qr():
    child_name = request.form["child_name"]
    parent_email = request.form["parent_email"]
    parent_account = request.form["parent_account"]
    course_name = request.form["course_name"]
    course_price = int(request.form["course_price"]) # Cena v haléřích

    # Cíl platby - doplňte vaše skutečné bankovní údaje!
    amount = course_price  # v haléřích
    account_number = "123456789/0100"  # <--- ZDE ZADEJTE SVŮJ SKUTEČNÝ ÚČET
    bank_code = "0100" # <--- ZDE ZADEJTE SVŮJ SKUTEČNÝ KÓD BANKY (např. 0100 pro Komerční banku)
    specific_symbol = "2025" # <--- Specifický symbol pro identifikaci ročníku doučování
    variable_symbol = f"9{len(child_name) % 10}{len(parent_email) % 10}{len(course_name) % 10}" # Jednoduchý variabilní symbol na základě délky jmen
    
    # Zpráva pro příjemce
    message = f"Doucovani {course_name} pro {child_name}"

    # QR kód podle standardu SPD pro bankovní platbu
    # Formát: SPD*1.0*ACC:CZ<ČísloÚčtuBezLomítka>CC:CZK*AM:<Částka>
    # Dále můžete přidat: *MSG:<Zpráva>*X-VS:<VariabilníSymbol>*X-SS:<SpecifickýSymbol>*X-KS:<KonstantníSymbol>
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
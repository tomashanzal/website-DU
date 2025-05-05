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

@main.route("/about")
def about():
    return render_template("about.html")

@main.route("/kontakt")
def kontakt():
    return render_template("kontakt.html")

@main.route("/payment")
def payment():
    return render_template("payment.html")

# Stránka pro bankovní převod
@main.route("/prevod")
def prevod():
    return render_template("prevod.html")

@main.route("/lektori")
def lektori():
    return render_template("lektori.html")

# Platba přes Stripe (tlačítko pro vytvoření session)
@main.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'czk',
                'product_data': {
                    'name': 'Kurz přijímaček – balíček',
                },
                'unit_amount': 7900,  # Cena v haléřích (79 Kč)
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('main.success', _external=True),
        cancel_url=url_for('main.cancel', _external=True),
    )
    return redirect(session.url, code=303)

# Route pro úspěšnou platbu
@main.route('/success')
def success():
    return "Děkujeme, platba probíhla úspěšně!"

# Route pro zrušenou platbu
@main.route('/cancel')
def cancel():
    return "Platba byla zrušena."

# Formulář pro bankovní QR kód
@main.route("/submit", methods=["POST"])
def submit():
    child_name = request.form["childName"]
    parent_email = request.form["parentEmail"]
    parent_account = request.form["parentAccount"]

    # Cíl platby
    amount = 7900  # v haléřích (tzn. 79 Kč)
    account_number = "123456789/0100"
    message = f"{child_name}"

    # QR kód podle standardu SPD pro bankovní platbu
    qr_data = f"SPD*1.0*ACC:CZ{account_number.replace('/', '')}*AM:{amount / 100:.2f}*CC:CZK*MSG:{message}"

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
        message=message,
        child_name=child_name,
        parent_email=parent_email
    )

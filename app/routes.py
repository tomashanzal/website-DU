from flask import Blueprint, render_template, request, redirect, url_for
import qrcode
import io
import base64

main = Blueprint('main', __name__)

@main.route("/")
def home():
    return render_template("home.html")

@main.route("/about")
def about():
    return render_template("about.html")

@main.route("/payment")
def payment():
    return render_template("payment.html")  # název šablony změněn z payment.html

@main.route("/submit", methods=["POST"])
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


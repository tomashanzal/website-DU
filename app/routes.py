
# app/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import stripe
import os
import json # <-- NOVÝ IMPORT
from datetime import datetime # <-- NOVÝ IMPORT
import uuid # Pro generování ID objednávky, pokud nebudeš používat db ID
import qrcode # Pokud generuješ QR kódy
import io # Pro práci s byty (pro QR kódy)
import base64 # Pro práci s base64 kódováním (pro QR kódy)
from flask_mail import Message, Mail # <-- NOVÝ IMPORT PRO EMAILY

# Inicicializace Stripe API
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Cesta k JSON souboru pro ukládání objednávek
# Používáme current_app.instance_path pro bezpečné umístění
# To vyžaduje, aby 'current_app' byl dostupný, což je v kontextu aplikace.
# Pokud byste chtěli cestu definovat globálně bez current_app,
# museli byste použít os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'instance', 'orders.json')
ORDERS_FILE = None # Inicializujeme na None, nastavíme v create_app nebo v routách přes current_app

main = Blueprint('main', __name__)

# Pomocná funkce pro získání cesty k JSON souboru
def get_orders_file_path():
    # Zajišťuje, že 'instance' složka existuje
    instance_path = current_app.instance_path
    os.makedirs(instance_path, exist_ok=True)
    return os.path.join(instance_path, 'orders.json')

# Pomocné funkce pro práci s JSON souborem
def load_orders():
    orders_file_path = get_orders_file_path()
    if not os.path.exists(orders_file_path):
        return []
    try:
        with open(orders_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Soubor je prázdný nebo poškozený, vrátíme prázdný seznam
        return []

def save_orders(orders):
    orders_file_path = get_orders_file_path()
    with open(orders_file_path, 'w', encoding='utf-8') as f:
        json.dump(orders, f, indent=4, ensure_ascii=False)

# Pomocná funkce pro odesílání e-mailů (vyžaduje konfiguraci Flask-Mail v __init__.py)
def send_order_email(recipient_email, subject, body_html):
    mail = current_app.extensions.get('mail') # Získáme instanci Flask-Mail
    if mail:
        msg = Message(subject,
                      sender=current_app.config.get('MAIL_USERNAME'), # Nebo konkrétní adresa odesílatele
                      recipients=[recipient_email])
        msg.html = body_html
        try:
            mail.send(msg)
            print(f"E-mail odeslán na: {recipient_email}")
        except Exception as e:
            print(f"Chyba při odesílání e-mailu na {recipient_email}: {e}")
    else:
        print("Flask-Mail není nakonfigurován nebo dostupný.")

# Standardní routy
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

@main.route("/seznam-wmt-FxvluknOGKyiY9qEmSibGmmmmeAiIkhu.txt")
def random_text():
    return render_template("random_text.html")

# MODIFIKOVANÁ ROUTA: create-checkout-session (Stripe)
@main.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        course_name = request.form.get('course_name')
        course_price_str = request.form.get('course_price')
        
        student_name = request.form.get('name_zak')
        student_phone = request.form.get('telefon_zak')
        parent_name = request.form.get('name_rodic')
        parent_email = request.form.get('parent_email')
        bank_account_input = request.form.get('cislo_uctu')
        address = request.form.get('misto_bydliste')
        zip_code = request.form.get('psc')

        if not course_price_str:
            raise ValueError("Cena kurzu nebyla zadána.")
        
        try:
            course_price_float = float(course_price_str)
            course_price = int(course_price_float * 100) # Cena v centech/halířích pro Stripe
        except ValueError:
            raise ValueError("Neplatný formát ceny kurzu. Zadejte prosím číslo.")

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'czk',
                    'product_data': {
                        'name': f"Kurz doučování: {course_name}",
                        'description': f"Příprava na Cermat přijímačky pro {student_name}",
                    },
                    'unit_amount': course_price,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('main.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('main.cancel', _external=True),
            metadata={
                'course_name': course_name,
                'child_name': student_name,
                'child_phone': student_phone,
                'parent_name': parent_name,
                'parent_email': parent_email,
                'address': address,
                'zip_code': zip_code,
                'bank_account_input': bank_account_input, 
                'payment_method': 'stripe'
            }
        )

        # Uložení objednávky do JSON souboru (status 'pending')
        orders = load_orders()
        new_order_id = str(uuid.uuid4()) # Generujeme unikátní ID pro objednávku
        new_order_data = {
            'id': new_order_id,
            'course_name': course_name,
            'course_price': course_price, # V centech/halířích
            'student_name': student_name,
            'student_phone': student_phone,
            'parent_name': parent_name,
            'parent_email': parent_email,
            'bank_account': bank_account_input,
            'address': address,
            'zip_code': zip_code,
            'payment_method': 'stripe',
            'stripe_session_id': session.id,
            'status': 'pending',
            'timestamp': datetime.now().isoformat() # ISO formát pro snadné ukládání a čtení
        }
        orders.append(new_order_data)
        save_orders(orders)
        
        # Odeslání e-mailu o nové objednávce (status pending)
        email_subject = f"Nová objednávka kurzu ({course_name}) - Čekající platba Stripe"
        email_body = f"""
        <p>Ahoj,</p>
        <p>Byla vytvořena nová objednávka kurzu.</p>
        <ul>
            <li><strong>Kurz:</strong> {course_name}</li>
            <li><strong>Cena:</strong> {course_price / 100:.2f} CZK</li>
            <li><strong>Jméno žáka:</strong> {student_name}</li>
            <li><strong>Telefon žáka:</strong> {student_phone}</li>
            <li><strong>Jméno rodiče:</strong> {parent_name}</li>
            <li><strong>E-mail rodiče:</strong> {parent_email}</li>
            <li><strong>Platební metoda:</strong> Stripe</li>
            <li><strong>Stav:</strong> Čeká na platbu</li>
            <li><strong>ID objednávky:</strong> {new_order_id}</li>
            <li><strong>Stripe Session ID:</strong> {session.id}</li>
        </ul>
        <p>Objednávka byla uložena do JSON souboru.</p>
        """
        send_order_email(os.getenv("ADMIN_EMAIL"), email_subject, email_body) # Pošli na admin email

        return redirect(session.url, code=303)
    except stripe.error.StripeError as e:
        flash(f"Chyba platby: {e}", "danger")
        print(f"Stripe Error: {e}")
        return redirect(url_for('main.payment'))
    except ValueError as e:
        flash(f"Chyba ve formuláři: {e}", "danger")
        print(f"Validation Error: {e}")
        return redirect(url_for('main.payment'))
    except Exception as e:
        flash("Došlo k neočekávané chybě. Zkuste to prosím znovu.", "danger")
        print(f"Unexpected Error: {e}")
        return redirect(url_for('main.payment'))

# MODIFIKOVANÁ ROUTA: success (Stripe)
@main.route('/success')
def success():
    session_id = request.args.get('session_id')
    if not session_id:
        flash("Chyba: Chybí ID platební relace.", "danger")
        return redirect(url_for('main.payment'))

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        orders = load_orders()
        order_to_update = next((order for order in orders if order.get('stripe_session_id') == session_id), None)

        if session.payment_status == "paid":
            if order_to_update:
                if order_to_update['status'] != 'paid':
                    order_to_update['status'] = 'paid'
                    save_orders(orders) # Uložíme aktualizovaný seznam objednávek
                    flash("Platba proběhla úspěšně! Děkujeme za nákup.", "success")

                    # Odeslání e-mailu o úspěšné platbě
                    email_subject = f"Platba za kurz {order_to_update['course_name']} úspěšná!"
                    email_body = f"""
                    <p>Ahoj,</p>
                    <p>Platba za objednávku kurzu <strong>{order_to_update['course_name']}</strong> byla úspěšně zpracována.</p>
                    <ul>
                        <li><strong>Jméno žáka:</strong> {order_to_update['student_name']}</li>
                        <li><strong>E-mail rodiče:</strong> {order_to_update['parent_email']}</li>
                        <li><strong>Stav:</strong> Zaplaceno</li>
                        <li><strong>ID objednávky:</strong> {order_to_update['id']}</li>
                    </ul>
                    <p>Objednávka byla aktualizována v JSON souboru.</p>
                    """
                    send_order_email(os.getenv("ADMIN_EMAIL"), email_subject, email_body) # Pošli na admin email
                    send_order_email(order_to_update['parent_email'], email_subject, email_body) # Pošli i rodiči

                else:
                    flash("Tato platba již byla zpracována. Děkujeme!", "info")
            else:
                flash("Platba proběhla úspěšně, ale odpovídající objednávka nebyla nalezena. Kontaktujte podporu.", "warning")
                # Zde bys mohl/a zvážit ruční záznam nebo odeslání e-mailu s neznámou platbou
                email_subject = f"Neznámá úspěšná platba Stripe - ID: {session_id}"
                email_body = f"""
                <p>Upozornění: Přišla platba Stripe s ID {session_id}, ale odpovídající objednávka nebyla nalezena v JSON souboru.</p>
                <p>Zkontrolujte prosím ručně Stripe dashboard.</p>
                """
                send_order_email(os.getenv("ADMIN_EMAIL"), email_subject, email_body)

            course_name = session.metadata.get('course_name', 'neznámý kurz')
            child_name = session.metadata.get('child_name', 'žák')
            return render_template("success.html", course_name=course_name, child_name=child_name)
            
        elif session.payment_status == "unpaid":
            if order_to_update:
                order_to_update['status'] = 'cancelled'
                save_orders(orders) # Uložíme aktualizovaný seznam objednávek
                flash("Platba nebyla dokončena. Zkuste to prosím znovu.", "warning")
                # Odeslání e-mailu o zrušené platbě
                email_subject = f"Platba za kurz {order_to_update['course_name']} zrušena/nedokončena"
                email_body = f"""
                <p>Ahoj,</p>
                <p>Platba za objednávku kurzu <strong>{order_to_update['course_name']}</strong> byla zrušena nebo nedokončena.</p>
                <ul>
                    <li><strong>Jméno žáka:</strong> {order_to_update['student_name']}</li>
                    <li><strong>E-mail rodiče:</strong> {order_to_update['parent_email']}</li>
                    <li><strong>Stav:</strong> Zrušeno</li>
                    <li><strong>ID objednávky:</strong> {order_to_update['id']}</li>
                </ul>
                <p>Objednávka byla aktualizována v JSON souboru.</p>
                """
                send_order_email(os.getenv("ADMIN_EMAIL"), email_subject, email_body)
            else:
                 flash("Platba nebyla dokončena. Zkuste to prosím znovu.", "warning")
            return render_template("cancel.html")
        else:
            flash("Stav platby je nejednoznačný. Kontaktujte podporu.", "info")
            return render_template("cancel.html")
            
    except stripe.error.StripeError as e:
        flash(f"Chyba při ověřování platby u Stripe: {e}", "danger")
        print(f"Stripe Error on success page: {e}")
        return redirect(url_for('main.payment'))
    except Exception as e:
        flash("Došlo k neočekávané chybě při ověřování platby.", "danger")
        print(f"Unexpected Error on success page: {e}")
        return redirect(url_for('main.app')) # Změněno z main.payment na main.app, předpokládám, že payment je pod main blueprintem


# Route pro zrušenou platbu
@main.route('/cancel')
def cancel():
    flash("Platba byla zrušena nebo nedokončena.", "info")
    return render_template("cancel.html")

# MODIFIKOVANÁ ROUTA: generate-qr (Bankovní převod)
@main.route("/generate-qr", methods=["POST"])
def generate_qr():
    student_name = request.form["name_zak"]
    student_phone = request.form["telefon_zak"]
    parent_name = request.form["name_rodic"]
    parent_email = request.form["parent_email"]
    bank_account_input = request.form["cislo_uctu"]
    address = request.form["misto_bydliste"]
    zip_code = request.form["psc"]
    course_name = request.form["course_name"]
    course_price_str = request.form["course_price"]

    try:
        course_price_float = float(course_price_str)
        course_price = int(course_price_float * 100)
    except ValueError:
        flash("Neplatný formát ceny kurzu pro QR platbu. Zadejte prosím číslo.", "danger")
        return redirect(url_for('main.payment'))

    amount = course_price

    # Uložení objednávky do JSON souboru (status 'pending' pro bankovní převod)
    orders = load_orders()
    new_order_id = str(uuid.uuid4()) # Generujeme unikátní ID
    new_order_data = {
        'id': new_order_id,
        'course_name': course_name,
        'course_price': course_price, # V centech/halířích
        'student_name': student_name,
        'student_phone': student_phone,
        'parent_name': parent_name,
        'parent_email': parent_email,
        'bank_account': bank_account_input,
        'address': address,
        'zip_code': zip_code,
        'payment_method': 'bank_transfer',
        'status': 'pending',
        'timestamp': datetime.now().isoformat()
    }
    orders.append(new_order_data)
    save_orders(orders)

    variable_symbol = new_order_id[:10] # Použijeme část UUID jako variabilní symbol

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

    print(course_price)
    if course_price == 200000:
        qr_filename = "ctvrtinovy.jpg"
    elif course_price == 400000:
        qr_filename = "polovicni.jpg"
    elif course_price == 800000:
        qr_filename = "komplet.jpg"
    else:
        # Generování dynamického QR kódu
        # Zde potřebuješ knihovnu qrcode
        qr_data = f"SPD*1.0*ACC:{account_number}+{bank_code}*AM:{amount/100:.2f}*CC:CZK*MSG:Platba za kurz*X-VS:{variable_symbol}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Uložení QR kódu do paměti a předání do šablony jako base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        qr_filename = "data:image/png;base64," + qr_base64


    # Odeslání e-mailu s instrukcemi pro bankovní převod
    email_subject = f"Potvrzení objednávky kurzu ({course_name}) - Bankovní převod"
    email_body = f"""
    <p>Ahoj,</p>
    <p>Děkujeme za objednávku kurzu <strong>{course_name}</strong>.</p>
    <p>Pro dokončení objednávky prosím proveďte platbu na následující údaje:</p>
    <ul>
        <li><strong>Částka:</strong> {amount / 100:.2f} CZK</li>
        <li><strong>Číslo účtu:</strong> {account_number}/{bank_code}</li>
        <li><strong>Variabilní symbol:</strong> {variable_symbol}</li>
        <li><strong>Popis platby:</strong> Platba za kurz - {student_name}</li>
    </ul>
    <p>QR kód pro platbu naleznete také na stránce potvrzení.</p>
    <p>Jakmile obdržíme platbu, potvrdíme vaši objednávku e-mailem.</p>
    <ul>
        <li><strong>ID objednávky:</strong> {new_order_id}</li>
        <li><strong>Jméno žáka:</strong> {student_name}</li>
        <li><strong>E-mail rodiče:</strong> {parent_email}</li>
        <li><strong>Stav:</strong> Čeká na bankovní převod</li>
    </ul>
    <p>Objednávka byla uložena do JSON souboru.</p>
    """
    send_order_email(os.getenv("ADMIN_EMAIL"), email_subject, email_body) # Pošli na admin email
    send_order_email(parent_email, email_subject, email_body) # Pošli i rodiči

    return render_template(
        "qr_result.html",
        qr_filename=qr_filename,
        amount=amount / 100,
        account_number=account_number,
        bank_code=bank_code,
        child_name=student_name,
        parent_email=parent_email,
        course_name=course_name,
        variable_symbol=variable_symbol,
    )

# NOVÁ SEKCE: ADMIN PANEL
@main.route("/admin/orders")
def admin_orders():
    orders = load_orders()
    # Zde můžete případně filtrovat, řadit nebo zpracovat objednávky před zobrazením
    return render_template("admin_orders.html", orders=orders)
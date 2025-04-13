
from app import create_app  # název složky s __init__.py

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)


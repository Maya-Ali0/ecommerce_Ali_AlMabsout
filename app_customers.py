from flask import Flask
from services.customers import customers_bp

app = Flask(__name__)
app.register_blueprint(customers_bp, url_prefix="/customers")

if __name__ == "__main__":
    app.run(port=5001, debug=True)

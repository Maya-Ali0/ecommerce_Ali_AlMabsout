from flask import Flask
from services.customers import customers_bp
from services.inventory import inventory_bp

app = Flask(__name__)

# Register Blueprints (Modular Services)
app.register_blueprint(customers_bp, url_prefix="/customers")
app.register_blueprint(inventory_bp, url_prefix="/inventory")

if __name__ == "__main__":
    app.run(debug=True)

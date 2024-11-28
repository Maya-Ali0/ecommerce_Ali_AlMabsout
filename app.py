from flask import Flask
from services.customers import customers_bp
from services.inventory import inventory_bp
from services.sales import sales_bp
from services.reviews import reviews_bp
app = Flask(__name__)

app.register_blueprint(customers_bp, url_prefix="/customers")
app.register_blueprint(inventory_bp, url_prefix="/inventory")
app.register_blueprint(sales_bp, url_prefix="/sales")
app.register_blueprint(reviews_bp, url_prefix="/reviews")

if __name__ == "__main__":
    app.run(debug=True)

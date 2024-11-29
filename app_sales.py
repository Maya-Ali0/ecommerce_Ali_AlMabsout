from flask import Flask
from services.sales import sales_bp

app = Flask(__name__)
app.register_blueprint(sales_bp, url_prefix="/sales")

if __name__ == "__main__":
    app.run(port=5003, debug=True)

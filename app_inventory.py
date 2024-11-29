from flask import Flask
from services.inventory import inventory_bp

app = Flask(__name__)
app.register_blueprint(inventory_bp, url_prefix="/inventory")

if __name__ == "__main__":
    app.run(port=5002, debug=True)

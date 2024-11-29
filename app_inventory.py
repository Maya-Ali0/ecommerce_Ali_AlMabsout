from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from services.inventory import inventory_bp

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour"]  
)

@app.errorhandler(429)
def ratelimit_exceeded(e):
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

app.register_blueprint(inventory_bp, url_prefix="/inventory")

if __name__ == "__main__":
    app.run(port=5002, debug=True)

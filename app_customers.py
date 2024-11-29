from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from services.customers import customers_bp

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["10 per hour"]  
)

@app.errorhandler(429)
def ratelimit_exceeded(e):
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

app.register_blueprint(customers_bp, url_prefix="/customers")

if __name__ == "__main__":
    app.run(port=5001, debug=True)

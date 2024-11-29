from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from services.sales import sales_bp

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per hour"] 
)

@app.errorhandler(429)
def ratelimit_exceeded(e):
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

app.register_blueprint(sales_bp, url_prefix="/sales")

if __name__ == "__main__":
    app.run(port=5003, debug=True)

from flask import Flask, jsonify, Response, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from services.customers import customers_bp
from prometheus_client import Counter, Histogram, generate_latest
import time

app = Flask(__name__)

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP Requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_latency_seconds", "Latency of HTTP requests", ["method", "endpoint"])

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour"]
)

@app.errorhandler(429)
def ratelimit_exceeded(e):
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def record_metrics(response):
    latency = time.time() - request.start_time
    endpoint = request.path
    method = request.method
    status = response.status_code
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()

    return response

@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype="text/plain")

app.register_blueprint(customers_bp, url_prefix="/customers")

if __name__ == "__main__":
    app.run(debug=True, port=5001)

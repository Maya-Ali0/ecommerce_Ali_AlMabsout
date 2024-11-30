from flask import Flask, jsonify, Response, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from services.inventory import inventory_bp
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
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.path).observe(latency)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.path, status=response.status_code).inc()
    return response

@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype="text/plain")

app.register_blueprint(inventory_bp, url_prefix="/inventory")

if __name__ == "__main__":
    app.run(port=5002, debug=True)

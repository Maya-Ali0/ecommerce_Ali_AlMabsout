from flask import Flask, jsonify, Response, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prometheus_client import Counter, Histogram, generate_latest, CollectorRegistry, REGISTRY
from services.reviews import reviews_bp
import time
from memory_profiler import profile
import pytest


app = Flask(__name__)

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP Requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_latency_seconds", "Latency of HTTP requests", ["method", "endpoint"])

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["50 per hour"]
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

@pytest.fixture(autouse=True)
def clear_registry():
    REGISTRY._names_to_collectors.clear()

app.register_blueprint(reviews_bp, url_prefix="/reviews")


@profile
def start_app():
    app.run(debug=True, port=5004)

if __name__ == "__main__":
    start_app()
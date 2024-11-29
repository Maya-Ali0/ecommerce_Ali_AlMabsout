from flask import Flask
from services.reviews import reviews_bp

app = Flask(__name__)
app.register_blueprint(reviews_bp, url_prefix="/reviews")

if __name__ == "__main__":
    app.run(port=5004, debug=True)

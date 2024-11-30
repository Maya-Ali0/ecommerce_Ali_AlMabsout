import pytest
import sqlite3
from flask import Flask
from services.reviews import reviews_bp, execute_query

DB_PATH = "./eCommerce.db"

@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(reviews_bp, url_prefix="/reviews")
    app.config["TESTING"] = True
    client = app.test_client()

    # Mock token validation
    app.view_functions['reviews.submit_review'].__globals__['decode_jwt'] = lambda x: "user1"
    app.view_functions['reviews.update_review'].__globals__['decode_jwt'] = lambda x: "user1"
    app.view_functions['reviews.delete_review'].__globals__['decode_jwt'] = lambda x: "user1"
    app.view_functions['reviews.moderate_review'].__globals__['decode_jwt'] = lambda x: "admin"

    yield client

@pytest.fixture
def setup_reviews_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Clear tables and add fresh data
    cursor.execute("DELETE FROM Customers")
    cursor.execute("DELETE FROM Goods")
    cursor.execute("DELETE FROM Reviews")

    cursor.execute("""
        INSERT INTO Customers (CustomerID, FullName, Username, Password, Age, Address, Gender, MaritalStatus, WalletBalance, IsAdmin)
        VALUES (1, 'Admin User', 'admin', 'password', 30, '123 Admin St', 'Male', 'Single', 1000.0, 1),
               (2, 'Regular User', 'user1', 'password', 25, '456 User St', 'Female', 'Single', 500.0, 0)
    """)
    cursor.execute("""
        INSERT INTO Goods (GoodID, Name, Category, PricePerItem, Description, StockCount)
        VALUES (1, 'Laptop', 'Electronics', 800.0, 'Latest model laptop', 50)
    """)
    cursor.execute("""
        INSERT INTO Reviews (ReviewID, CustomerID, GoodID, Rating, Comment, Status, Upvotes, Downvotes)
        VALUES (1, 2, 1, 5, 'Great product!', 'Accepted', 10, 0),
               (2, 2, 1, 3, 'Okay product', 'Pending', 0, 0)
    """)
    conn.commit()
    conn.close()

def test_submit_review_success(client, setup_reviews_data):
    data = {
        "CustomerID": 2,
        "GoodID": 1,
        "Rating": 4,
        "Comment": "Amazing value for money!"
    }
    response = client.post("/reviews/submit", json=data, headers={"Authorization": "Bearer <JWT_TOKEN>"})
    assert response.status_code == 201
    assert "Review submitted successfully" in response.json["message"]

def test_submit_review_invalid_rating(client, setup_reviews_data):
    data = {
        "CustomerID": 2,
        "GoodID": 1,
        "Rating": 6
    }
    response = client.post("/reviews/submit", json=data, headers={"Authorization": "Bearer <JWT_TOKEN>"})
    assert response.status_code == 400
    assert "Rating must be between 1 and 5" in response.json["error"]

def test_update_review_success(client, setup_reviews_data):
    data = {
        "CustomerID": 2,
        "Rating": 4,
        "Comment": "Updated comment"
    }
    response = client.put("/reviews/update/1", json=data, headers={"Authorization": "Bearer <JWT_TOKEN>"})
    assert response.status_code == 200
    assert "Review updated successfully" in response.json["message"]

def test_delete_review_success(client, setup_reviews_data):
    data = {
        "CustomerID": 2
    }
    response = client.delete("/reviews/delete/1", json=data, headers={"Authorization": "Bearer <JWT_TOKEN>"})
    assert response.status_code == 200
    assert "Review deleted successfully" in response.json["message"]

def test_get_product_reviews(client, setup_reviews_data):
    response = client.get("/reviews/product/1")
    assert response.status_code == 200
    reviews = response.json
    assert len(reviews) > 0
    assert reviews[0]["Rating"] == 5

def test_get_customer_reviews(client, setup_reviews_data):
    response = client.get("/reviews/customer/2")
    assert response.status_code == 200
    reviews = response.json
    assert len(reviews) > 0
    assert reviews[0]["GoodName"] == "Laptop"

def test_moderate_review_success(client, setup_reviews_data):
    data = {
        "CustomerID": 1,
        "Status": "Accepted"
    }
    response = client.put("/reviews/moderate/2", json=data, headers={"Authorization": "Bearer <JWT_TOKEN>"})
    assert response.status_code == 200
    assert "Review status updated successfully" in response.json["message"]

def test_upvote_review_success(client, setup_reviews_data):
    response = client.put("/reviews/upvote/1")
    assert response.status_code == 200
    assert "Review upvoted successfully" in response.json["message"]

def test_downvote_review_success(client, setup_reviews_data):
    response = client.put("/reviews/downvote/1")
    assert response.status_code == 200
    assert "Review downvoted successfully" in response.json["message"]

def test_get_review_details(client, setup_reviews_data):
    response = client.get("/reviews/details/1")
    assert response.status_code == 200
    review = response.json
    assert review["CustomerName"] == "Regular User"

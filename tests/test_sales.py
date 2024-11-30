import pytest
import sqlite3
from flask import Flask
from services.sales import sales_bp, execute_query

DB_PATH = "./eCommerce.db"

@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(sales_bp, url_prefix="/sales")
    app.config["TESTING"] = True
    client = app.test_client()
    yield client

@pytest.fixture
def setup_sales_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO Customers (CustomerID, FullName, Username, Password, Age, Address, Gender, MaritalStatus, WalletBalance)
        VALUES (1, 'Test User', 'testuser', 'password', 25, '123 Street', 'Male', 'Single', 1000.0)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO Goods (GoodID, Name, Category, PricePerItem, Description, StockCount)
        VALUES (1, 'Laptop', 'Electronics', 500.0, 'High-performance laptop', 10)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO HistoricalPurchases (PurchaseID, CustomerID, GoodID, Quantity, TotalAmount, PurchaseDate)
        VALUES (1, 1, 1, 2, 1000.0, CURRENT_TIMESTAMP)
    """)
    conn.commit()
    conn.close()

def test_display_available_goods(client, setup_sales_data):
    response = client.get("/sales/goods")
    assert response.status_code == 200
    goods = response.json
    assert len(goods) > 0
    assert goods[0]["Name"] == "Laptop"
    assert goods[0]["PricePerItem"] == 800.0

def test_get_good_details(client, setup_sales_data):
    response = client.get("/sales/goods/1")
    assert response.status_code == 200
    good = response.json
    assert good["GoodID"] == 1
    assert good["Name"] == "Laptop"
    assert good["Category"] == "Electronics"

def test_get_good_details_not_found(client, setup_sales_data):
    response = client.get("/sales/goods/999")
    assert response.status_code == 404
    assert response.json["error"] == "Good not found."

def test_make_sale_success(client, setup_sales_data):
    data = {
        "Username": "admin",
        "GoodName": "Laptop",
        "Quantity": 1
    }
    response = client.post("/sales/sale", json=data)
    assert response.status_code == 200
    assert "Purchase successful" in response.json["message"]


def test_make_sale_insufficient_funds(client, setup_sales_data):
    data = {
        "Username": "admin",
        "GoodName": "Laptop",
        "Quantity": 3
    }
    response = client.post("/sales/sale", json=data)
    assert response.status_code == 400
    assert "Insufficient funds" in response.json["error"]


def test_make_sale_insufficient_stock(client, setup_sales_data):
    data = {
        "Username": "admin",
        "GoodName": "Laptop",
        "Quantity": 100
    }
    response = client.post("/sales/sale", json=data)
    assert response.status_code == 400
    assert "Insufficient stock" in response.json["error"]

def test_get_customer_purchases(client, setup_sales_data):
    response = client.get("/sales/purchases/admin")
    assert response.status_code == 200
    purchases = response.json
    assert len(purchases) > 0
    assert purchases[0]["Name"] == "Laptop"
    assert purchases[0]["Quantity"] == 2

def test_get_customer_purchases_not_found(client, setup_sales_data):
    response = client.get("/sales/purchases/unknownuser")
    assert response.status_code == 404
    assert response.json["error"] == "Customer 'unknownuser' not found."

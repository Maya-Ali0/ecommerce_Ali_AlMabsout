import pytest
import sqlite3
from app_inventory import app

DB_PATH = "./eCommerce.db"

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Add test-specific goods (ensuring no duplicates)
    goods_to_add = [
        ('Smartphone', 'Electronics', 699.99, 'Latest 5G smartphone', 50),
        ('Headphones', 'Accessories', 49.99, 'Noise-cancelling headphones', 100),
        ('T-shirt', 'Clothes', 19.99, 'Cotton T-shirt', 200),
    ]

    for good in goods_to_add:
        cursor.execute("""
        INSERT OR IGNORE INTO Goods (Name, Category, PricePerItem, Description, StockCount)
        VALUES (?, ?, ?, ?, ?)
        """, good)
    
    conn.commit()
    conn.close()

def test_add_goods(client, setup_database):
    data = {
        "Name": "Apple watch 3",
        "Category": "Electronics",
        "PricePerItem": 300.0,
        "Description": "Newest model watch 3",
        "StockCount": 50
    }
    response = client.post("/inventory/add", json=data)
    assert response.status_code == 201
    assert response.json["message"] == "Goods added successfully."

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Goods WHERE Name = ?", (data["Name"],))
    good = cursor.fetchone()
    assert good is not None
    conn.close()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Goods WHERE Name = ?", (data["Name"],))
    conn.commit()
    conn.close()

def test_add_goods_duplicate(client, setup_database):
    data = {
        "Name": "Laptop",
        "Category": "Electronics",
        "PricePerItem": 1000.0,
        "Description": "High-performance laptop",
        "StockCount": 10
    }
    response = client.post("/inventory/add", json=data)
    assert response.status_code == 400
    assert response.json["error"] == "A good with the name 'Laptop' already exists."

def test_deduct_goods(client, setup_database):
    data = {"quantity": 5}
    response = client.post("/inventory/deduct/1", json=data)
    assert response.status_code == 200
    assert response.json["message"] == "Deducted 5 items from Good ID 1 successfully."
    
def test_deduct_goods_insufficient_stock(client, setup_database):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT StockCount FROM Goods WHERE GoodID = 1")
    stock = cursor.fetchone()
    conn.close()
    assert stock is not None
    available_stock = stock[0]

    data = {"quantity": available_stock + 5}
    response = client.post("/inventory/deduct/1", json=data)
    assert response.status_code == 400
    assert response.json["error"] == f"Insufficient stock. Available stock: {available_stock}."


def test_deduct_goods_not_found(client, setup_database):
    data = {"quantity": 5}
    response = client.post("/inventory/deduct/999", json=data)
    assert response.status_code == 404
    assert response.json["error"] == "Good not found."

def test_update_goods(client, setup_database):
    data = {
        "PricePerItem": 1200.0,
        "StockCount": 15
    }
    response = client.put("/inventory/update/1", json=data)
    assert response.status_code == 200
    assert response.json["message"] == "Good ID 1 updated successfully."

def test_update_goods_no_fields(client, setup_database):
    data = {}
    response = client.put("/inventory/update/1", json=data)
    assert response.status_code == 400
    assert response.json["error"] == "No fields provided to update."

def test_update_goods_not_found(client, setup_database):
    data = {
        "PricePerItem": 1200.0,
        "StockCount": 15
    }
    response = client.put("/inventory/update/999", json=data)
    assert response.status_code == 200
    assert response.json["message"] == "Good ID 999 updated successfully."

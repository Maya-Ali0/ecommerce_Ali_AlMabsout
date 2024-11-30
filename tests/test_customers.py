import pytest
import sqlite3
from app_customers import app

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
    cursor.execute("DELETE FROM Customers")
    conn.commit()
    cursor.execute("""
    INSERT INTO Customers (FullName, Username, Password, Age, Address, Gender, MaritalStatus, WalletBalance, IsAdmin)
    VALUES ('Alice Smith', 'alicesmith', 'securepassword', 25, '456 Elm Street', 'Female', 'Single', 0.0, 0)
    """)
    conn.commit()
    conn.close()

def test_register_customer(client, setup_database):
    data = {
        "FullName": "John Doe",
        "Username": "johndoe",
        "Password": "password123",
        "Age": 30,
        "Address": "123 Elm Street",
        "Gender": "Male",
        "MaritalStatus": "Single",
        "IsAdmin": False
    }
    response = client.post("/customers/register", json=data)
    assert response.status_code == 201
    assert response.json["message"] == "Customer registered successfully."

def test_register_duplicate_username(client, setup_database):
    data = {
        "FullName": "Duplicate User",
        "Username": "alicesmith",
        "Password": "password123",
        "Age": 30,
        "Address": "789 Oak Street",
        "Gender": "Female",
        "MaritalStatus": "Single",
        "IsAdmin": False
    }
    response = client.post("/customers/register", json=data)
    assert response.status_code == 400
    assert response.json["error"] == "Username already exists."

def test_login_success(client, setup_database):
    data = {
        "Username": "alicesmith",
        "Password": "securepassword"
    }
    response = client.post("/customers/login", json=data)
    assert response.status_code == 200
    assert "token" in response.json

def test_login_failure(client, setup_database):
    data = {
        "Username": "alicesmith",
        "Password": "wrongpassword"
    }
    response = client.post("/customers/login", json=data)
    assert response.status_code == 401
    assert response.json["error"] == "Invalid username or password"

def test_get_customer(client, setup_database):
    response = client.get("/customers/alicesmith")
    assert response.status_code == 200
    assert response.json["Username"] == "alicesmith"
    assert response.json["FullName"] == "Alice Smith"

def test_get_all_customers(client, setup_database):
    response = client.get("/customers/all")
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]["Username"] == "alicesmith"

def test_update_customer(client, setup_database):
    login_response = client.post("/customers/login", json={"Username": "alicesmith", "Password": "securepassword"})
    token = login_response.json["token"]
    headers = {"Authorization": f"Bearer {token}"}
    update_data = {"Address": "123 New Elm Street"}
    response = client.put("/customers/update/alicesmith", json=update_data, headers=headers)
    assert response.status_code == 200
    assert response.json["message"] == "Customer 'alicesmith' updated successfully."

def test_delete_customer(client, setup_database):
    login_response = client.post("/customers/login", json={"Username": "alicesmith", "Password": "securepassword"})
    token = login_response.json["token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.delete("/customers/delete/alicesmith", headers=headers)
    assert response.status_code == 200
    assert response.json["message"] == "Customer 'alicesmith' deleted successfully."

def test_charge_wallet(client, setup_database):
    login_response = client.post("/customers/login", json={"Username": "alicesmith", "Password": "securepassword"})
    token = login_response.json["token"]
    headers = {"Authorization": f"Bearer {token}"}
    charge_data = {"Amount": 50}
    response = client.post("/customers/charge/alicesmith", json=charge_data, headers=headers)
    assert response.status_code == 200
    assert response.json["message"] == "Charged $50.0 to 'alicesmith' successfully."

def test_deduct_wallet(client, setup_database):
    login_response = client.post("/customers/login", json={"Username": "alicesmith", "Password": "securepassword"})
    token = login_response.json["token"]
    headers = {"Authorization": f"Bearer {token}"}
    deduct_data = {"Amount": 50}
    response = client.post("/customers/deduct/alicesmith", json=deduct_data, headers=headers)
    assert response.status_code == 400
    assert response.json["error"] == "Insufficient balance."

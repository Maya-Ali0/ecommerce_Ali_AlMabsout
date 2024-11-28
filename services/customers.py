from flask import Blueprint, request, jsonify
import sqlite3

customers_bp = Blueprint("customers", __name__)

DB_PATH = "./eCommerce.db"

def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = None
    if fetchone:
        result = cursor.fetchone()
    elif fetchall:
        result = cursor.fetchall()
    if commit:
        conn.commit()
    conn.close()
    return result

@customers_bp.route("/register", methods=["POST"])
def register_customer():
    data = request.json
    try:
        query = """
        INSERT INTO Customers (FullName, Username, Password, Age, Address, Gender, MaritalStatus, WalletBalance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        execute_query(query, (
            data["FullName"], data["Username"], data["Password"], data["Age"],
            data["Address"], data["Gender"], data["MaritalStatus"], 0.0
        ), commit=True)
        return jsonify({"message": "Customer registered successfully."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists."}), 400

@customers_bp.route("/delete/<username>", methods=["DELETE"])
def delete_customer(username):
    query = "DELETE FROM Customers WHERE Username = ?"
    execute_query(query, (username,), commit=True)
    return jsonify({"message": f"Customer '{username}' deleted successfully."})

@customers_bp.route("/update/<username>", methods=["PUT"])
def update_customer(username):
    data = request.json
    fields = ", ".join(f"{key} = ?" for key in data.keys())
    query = f"UPDATE Customers SET {fields} WHERE Username = ?"
    params = list(data.values()) + [username]
    execute_query(query, params, commit=True)
    return jsonify({"message": f"Customer '{username}' updated successfully."})

@customers_bp.route("/all", methods=["GET"])
def get_all_customers():
    query = "SELECT FullName, Username, Age, Address, Gender, MaritalStatus, WalletBalance FROM Customers"
    customers = execute_query(query, fetchall=True)
    return jsonify(customers)

@customers_bp.route("/<username>", methods=["GET"])
def get_customer(username):
    query = "SELECT FullName, Username, Age, Address, Gender, MaritalStatus, WalletBalance FROM Customers WHERE Username = ?"
    customer = execute_query(query, (username,), fetchone=True)
    if customer:
        return jsonify(customer)
    return jsonify({"error": "Customer not found."}), 404

@customers_bp.route("/charge/<username>", methods=["POST"])
def charge_wallet(username):
    data = request.json
    amount = data.get("amount", 0)
    query = "UPDATE Customers SET WalletBalance = WalletBalance + ? WHERE Username = ?"
    execute_query(query, (amount, username), commit=True)
    return jsonify({"message": f"Charged ${amount} to '{username}' successfully."})

@customers_bp.route("/deduct/<username>", methods=["POST"])
def deduct_wallet(username):
    data = request.json
    amount = data.get("amount", 0)
    query = "SELECT WalletBalance FROM Customers WHERE Username = ?"
    wallet_balance = execute_query(query, (username,), fetchone=True)
    if wallet_balance and wallet_balance[0] >= amount:
        query = "UPDATE Customers SET WalletBalance = WalletBalance - ? WHERE Username = ?"
        execute_query(query, (amount, username), commit=True)
        return jsonify({"message": f"Deducted ${amount} from '{username}' successfully."})
    return jsonify({"error": "Insufficient balance."}), 400

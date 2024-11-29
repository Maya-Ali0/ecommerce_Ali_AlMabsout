"""
Blueprint for customer management in the eCommerce application.

Provides endpoints for customer operations, including registration,
deletion, updates, fetching details, and wallet operations.
"""

from flask import Blueprint, request, jsonify
import sqlite3
import re
import jwt
import datetime
from functools import wraps

customers_bp = Blueprint("customers", __name__)

DB_PATH = "./eCommerce.db"
SECRET_KEY = "A123"

def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    """
    Execute a SQL query against the database.

    Args:
        query (str): The SQL query to execute.
        params (tuple): Parameters for the SQL query.
        fetchone (bool): Whether to fetch one record.
        fetchall (bool): Whether to fetch all records.
        commit (bool): Whether to commit the transaction.

    Returns:
        Any: The result of the query execution.
    """
    conn = None
    try:
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
        return result
    finally:
        if conn:
            conn.close()

def generate_jwt(username):
    """
    Generate a JWT token for the given username.

    Args:
        username (str): The username of the authenticated user.

    Returns:
        str: A JWT token.
    """
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    token = jwt.encode({"Username": username, "exp": expiration}, SECRET_KEY, algorithm="HS256")
    return token

def decode_jwt(token):
    """
    Decode a JWT token.

    Args:
        token (str): The JWT token.

    Returns:
        str or None: The username if the token is valid, otherwise None.
    """
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return decoded["Username"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    """
    Decorator to ensure the request contains a valid JWT token.

    Args:
        f (function): The function to wrap.

    Returns:
        function: The decorated function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        try:
            token = token.split(" ")[1]
            username = decode_jwt(token)
            if not username:
                return jsonify({"error": "Invalid or expired token"}), 401
            kwargs["Username"] = username
        except Exception:
            return jsonify({"error": "Token is invalid"}), 401
        return f(*args, **kwargs)
    return decorated

@customers_bp.route("/register", methods=["POST"])
def register_customer():
    """
    Register a new customer.

    Expects a JSON payload with required fields:
    FullName, Username, Password, Age, Address, Gender, MaritalStatus.

    Returns:
        JSON: Success or error message.
    """
    data = request.json
    try:
        required_fields = ["FullName", "Username", "Password", "Age", "Address", "Gender", "MaritalStatus"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        username = data["Username"]
        username_pattern = r"^[a-zA-Z0-9_.-]{3,20}$"
        if not re.match(username_pattern, username):
            return jsonify({"error": "Invalid username. Must be 3-20 characters long and contain only letters, numbers, underscores, dots, or hyphens."}), 400

        existing_user = execute_query("SELECT * FROM Customers WHERE Username = ?", (username,), fetchone=True)
        if existing_user:
            return jsonify({"error": "Username already exists."}), 400

        is_admin = data.get("IsAdmin", False)
        if is_admin:
            existing_admin = execute_query("SELECT * FROM Customers WHERE IsAdmin = 1", fetchone=True)
            if existing_admin:
                return jsonify({"error": "An admin already exists."}), 400

        query = """
        INSERT INTO Customers (FullName, Username, Password, Age, Address, Gender, MaritalStatus, WalletBalance, IsAdmin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        execute_query(query, (
            data["FullName"], data["Username"], data["Password"], data["Age"],
            data["Address"], data["Gender"], data["MaritalStatus"], 0.0, is_admin
        ), commit=True)
        
        return jsonify({"message": "Customer registered successfully."}), 201
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            return jsonify({"error": "Username already exists."}), 400
        return jsonify({"error": "Database error occurred."}), 500
    except KeyError as e:
        return jsonify({"error": f"Missing required field: {e.args[0]}"}), 400
    
@customers_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate a user and return a JWT token.

    **Request JSON:**
    - Username: str (required)
    - Password: str (required)

    **Response:**
    - 200: Returns a JWT token if authentication is successful.
    - 400: Missing username or password.
    - 401: Invalid credentials.

    Returns:
        JSON: JWT token or error message.
    """
    data = request.json
    if "Username" not in data or "Password" not in data:
        return jsonify({"error": "Username and Password are required"}), 400

    username = data["Username"]
    password = data["Password"]

    query = "SELECT Password FROM Customers WHERE Username = ?"
    user = execute_query(query, (username,), fetchone=True)

    if not user or user[0] != password:
        return jsonify({"error": "Invalid username or password"}), 401

    token = generate_jwt(username)
    return jsonify({"token": token}), 200

@customers_bp.route("/delete/<username>", methods=["DELETE"])
@token_required
def delete_customer(username, **kwargs):
    """
    Delete a customer by username.

    **Protected Endpoint**: Requires a valid JWT token.

    **Path Parameter:**
    - username (str): The username of the customer to delete.

    **Response:**
    - 200: Successfully deleted the customer.
    - 401: Invalid or missing token.
    - 403: Unauthorized access.
    - 404: Customer not found.

    Args:
        username (str): Username from the path parameter.

    Returns:
        JSON: Success or error message.
    """
    if username != kwargs["Username"]:
        return jsonify({"error": "Unauthorized access"}), 403

    user_query = "SELECT CustomerID FROM Customers WHERE Username = ?"
    user = execute_query(user_query, (username,), fetchone=True)
    if not user:
        return jsonify({"error": f"Customer '{username}' not found."}), 404

    query = "DELETE FROM Customers WHERE Username = ?"
    execute_query(query, (username,), commit=True)
    return jsonify({"message": f"Customer '{username}' deleted successfully."}), 200

@customers_bp.route("/update/<username>", methods=["PUT"])
@token_required
def update_customer(username, **kwargs):
    """
    Update customer details.

    **Protected Endpoint**: Requires a valid JWT token.

    **Path Parameter:**
    - username (str): The username of the customer to update.

    **Request JSON:**
    - Any fields to update (e.g., Address, Age, etc.)

    **Response:**
    - 200: Successfully updated customer details.
    - 401: Invalid or missing token.
    - 403: Unauthorized access.

    Args:
        username (str): Username from the path parameter.

    Returns:
        JSON: Success message.
    """
    if username != kwargs["Username"]:
        return jsonify({"error": "Unauthorized access"}), 403

    data = request.json
    fields = ", ".join(f"{key} = ?" for key in data.keys())
    query = f"UPDATE Customers SET {fields} WHERE Username = ?"
    params = list(data.values()) + [username]
    execute_query(query, params, commit=True)
    return jsonify({"message": f"Customer '{username}' updated successfully."})

@customers_bp.route("/all", methods=["GET"])
def get_all_customers():
    """
    Get details of all customers.

    Returns:
        JSON: A list of customer details.
    """
    query = "SELECT FullName, Username, Age, Address, Gender, MaritalStatus, WalletBalance FROM Customers"
    customers = execute_query(query, fetchall=True)
    return jsonify(customers)

@customers_bp.route("/<username>", methods=["GET"])
def get_customer(username):
    """
    Get details of a specific customer.

    Args:
        username (str): The username of the customer.

    Returns:
        JSON: Customer details or error message.
    """
    query = "SELECT FullName, Username, Age, Address, Gender, MaritalStatus, WalletBalance FROM Customers WHERE Username = ?"
    customer = execute_query(query, (username,), fetchone=True)
    if customer:
        return jsonify(customer)
    return jsonify({"error": "Customer not found."}), 404

@customers_bp.route("/charge/<username>", methods=["POST"])
@token_required
def charge_wallet(username, **kwargs):
    """
    Charge a customer's wallet.

    **Protected Endpoint**: Requires a valid JWT token.

    **Request JSON:**
    - Amount: float (required, must be positive)

    **Path Parameter:**
    - username (str): The username of the customer.

    **Response:**
    - 200: Successfully charged the wallet.
    - 400: Missing or invalid amount.
    - 401: Invalid or missing token.
    - 403: Unauthorized access.

    Args:
        username (str): Username from the path parameter.

    Returns:
        JSON: Success or error message.
    """
    if username != kwargs["Username"]:
        print(kwargs["Username"])
        return jsonify({"error": "Unauthorized access"}), 403

    data = request.json
    if "Amount" not in data:
        return jsonify({"error": "'Amount' field is required in the request."}), 400

    try:
        amount = float(data["Amount"])
        if amount <= 0:
            return jsonify({"error": "'Amount' must be a positive number."}), 400
    except ValueError:
        return jsonify({"error": "'Amount' must be a valid number."}), 400

    query = "UPDATE Customers SET WalletBalance = WalletBalance + ? WHERE Username = ?"
    execute_query(query, (amount, username), commit=True)

    return jsonify({"message": f"Charged ${amount} to '{username}' successfully."}), 200

@customers_bp.route("/deduct/<username>", methods=["POST"])
@token_required
def deduct_wallet(username, **kwargs):
    """
    Deduct from a customer's wallet.

    **Protected Endpoint**: Requires a valid JWT token.

    **Request JSON:**
    - Amount: float (required, must be positive)

    **Path Parameter:**
    - username (str): The username of the customer.

    **Response:**
    - 200: Successfully deducted from the wallet.
    - 400: Missing or invalid amount, or insufficient balance.
    - 401: Invalid or missing token.
    - 403: Unauthorized access.

    Args:
        username (str): Username from the path parameter.

    Returns:
        JSON: Success or error message.
    """
    if username != kwargs["Username"]:
        return jsonify({"error": "Unauthorized access"}), 403

    data = request.json
    if "Amount" not in data:
        return jsonify({"error": "'Amount' field is required in the request."}), 400

    try:
        amount = float(data["Amount"])
        if amount <= 0:
            return jsonify({"error": "'Amount' must be a positive number."}), 400
    except ValueError:
        return jsonify({"error": "'Amount' must be a valid number."}), 400

    user_query = "SELECT WalletBalance FROM Customers WHERE Username = ?"
    user = execute_query(user_query, (username,), fetchone=True)
    if not user:
        return jsonify({"error": f"Customer '{username}' not found."}), 404

    wallet_balance = user[0]
    if wallet_balance >= amount:
        query = "UPDATE Customers SET WalletBalance = WalletBalance - ? WHERE Username = ?"
        execute_query(query, (amount, username), commit=True)
        return jsonify({"message": f"Deducted ${amount} from '{username}' successfully."}), 200

    return jsonify({"error": "Insufficient balance."}), 400

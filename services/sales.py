"""
Sales Management Module

This module provides APIs for managing sales, including displaying available goods,
retrieving good details, processing purchases, and fetching customer purchase history.
"""

from flask import Blueprint, request, jsonify
import sqlite3

sales_bp = Blueprint("sales", __name__)

DB_PATH = "./eCommerce.db"

def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    """
    Executes a SQL query on the eCommerce database.

    Args:
        query (str): The SQL query to execute.
        params (tuple): Parameters for the query.
        fetchone (bool): Whether to fetch a single row.
        fetchall (bool): Whether to fetch all rows.
        commit (bool): Whether to commit changes to the database.

    Returns:
        Any: Query results if fetchone or fetchall is True, otherwise None.
    """
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

@sales_bp.route("/goods", methods=["GET"])
def display_available_goods():
    """
    Retrieves a list of goods available for purchase.

    Returns:
        JSON: A list of goods, each containing:
              - Name (str): Name of the good.
              - PricePerItem (float): Price per item.
    """
    try:
        query = "SELECT Name, PricePerItem FROM Goods WHERE StockCount > 0"
        goods = execute_query(query, fetchall=True)

        labeled_goods = [{"Name": good[0], "PricePerItem": good[1]} for good in goods]

        return jsonify(labeled_goods), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sales_bp.route("/goods/<int:good_id>", methods=["GET"])
def get_good_details(good_id):
    """
    Retrieves detailed information about a specific good.

    Args:
        good_id (int): The ID of the good.

    Returns:
        JSON: Details of the good, including:
              - GoodID, Name, Category, PricePerItem, Description,
                StockCount, CreatedAt, and UpdatedAt.
              Or an error message if the good is not found.
    """
    try:
        query = """
        SELECT GoodID, Name, Category, PricePerItem, Description, StockCount, CreatedAt, UpdatedAt
        FROM Goods
        WHERE GoodID = ?
        """
        good = execute_query(query, (good_id,), fetchone=True)

        if good:
            labeled_good = {
                "GoodID": good[0],
                "Name": good[1],
                "Category": good[2],
                "PricePerItem": good[3],
                "Description": good[4],
                "StockCount": good[5],
                "CreatedAt": good[6],
                "UpdatedAt": good[7]
            }
            return jsonify(labeled_good), 200

        return jsonify({"error": "Good not found."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sales_bp.route("/sale", methods=["POST"])
def make_sale():
    """
    Processes a sale for a specific good.

    Expects a JSON payload with the following fields:
        - Username (str): Username of the customer.
        - GoodName (str): Name of the good to purchase.
        - Quantity (int): Quantity to purchase (must be greater than 0).

    Returns:
        JSON: A success message with the total cost of the purchase, or an error
              message if the operation fails (e.g., insufficient stock or funds).
    """
    data = request.json
    try:
        required_fields = ["Username", "GoodName", "Quantity"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' is required."}), 400

        username = data["Username"]
        good_name = data["GoodName"]
        quantity = data["Quantity"]

        if quantity <= 0:
            return jsonify({"error": "Quantity must be greater than 0."}), 400

        good_query = "SELECT GoodID, PricePerItem, StockCount FROM Goods WHERE Name = ?"
        good = execute_query(good_query, (good_name,), fetchone=True)
        if not good:
            return jsonify({"error": f"Good '{good_name}' not found."}), 404

        good_id, price_per_item, stock_count = good

        if stock_count < quantity:
            return jsonify({"error": f"Insufficient stock. Available stock: {stock_count}."}), 400

        total_cost = price_per_item * quantity

        customer_query = "SELECT CustomerID, WalletBalance FROM Customers WHERE Username = ?"
        customer = execute_query(customer_query, (username,), fetchone=True)
        if not customer:
            return jsonify({"error": f"Customer '{username}' not found."}), 404

        customer_id, wallet_balance = customer

        if wallet_balance < total_cost:
            return jsonify({"error": f"Insufficient funds. Wallet balance: ${wallet_balance}."}), 400

        update_customer_query = "UPDATE Customers SET WalletBalance = WalletBalance - ? WHERE CustomerID = ?"
        update_goods_query = "UPDATE Goods SET StockCount = StockCount - ? WHERE GoodID = ?"
        execute_query(update_customer_query, (total_cost, customer_id), commit=True)
        execute_query(update_goods_query, (quantity, good_id), commit=True)

        purchase_query = """
        INSERT INTO HistoricalPurchases (CustomerID, GoodID, Quantity, TotalAmount)
        VALUES (?, ?, ?, ?)
        """
        execute_query(purchase_query, (customer_id, good_id, quantity, total_cost), commit=True)

        return jsonify({"message": f"Purchase successful. Total cost: ${total_cost}"}), 200
    except sqlite3.IntegrityError as e:
        return jsonify({"error": f"Database integrity error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sales_bp.route("/purchases/<username>", methods=["GET"])
def get_customer_purchases(username):
    """
    Retrieves the purchase history for a specific customer.

    Args:
        username (str): The username of the customer.

    Returns:
        JSON: A list of purchases, including:
              - Name of the good, Quantity purchased, TotalAmount, and PurchaseDate.
              Or an error message if the customer is not found.
    """
    try:
        customer_query = "SELECT CustomerID FROM Customers WHERE Username = ?"
        customer = execute_query(customer_query, (username,), fetchone=True)
        if not customer:
            return jsonify({"error": f"Customer '{username}' not found."}), 404

        customer_id = customer[0]

        purchases_query = """
        SELECT Goods.Name, HistoricalPurchases.Quantity, HistoricalPurchases.TotalAmount, HistoricalPurchases.PurchaseDate
        FROM HistoricalPurchases
        JOIN Goods ON HistoricalPurchases.GoodID = Goods.GoodID
        WHERE HistoricalPurchases.CustomerID = ?
        """
        purchases = execute_query(purchases_query, (customer_id,), fetchall=True)

        return jsonify(purchases), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

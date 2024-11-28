from flask import Blueprint, request, jsonify
import sqlite3

sales_bp = Blueprint("sales", __name__)

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

@sales_bp.route("/goods", methods=["GET"])
def display_available_goods():
    try:
        query = "SELECT Name, PricePerItem FROM Goods WHERE StockCount > 0"
        goods = execute_query(query, fetchall=True)
        return jsonify(goods), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sales_bp.route("/goods/<int:good_id>", methods=["GET"])
def get_good_details(good_id):
    try:
        query = "SELECT * FROM Goods WHERE GoodID = ?"
        good = execute_query(query, (good_id,), fetchone=True)
        if good:
            return jsonify(good), 200
        return jsonify({"error": "Good not found."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sales_bp.route("/sale", methods=["POST"])
def make_sale():
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

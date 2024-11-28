from flask import Blueprint, request, jsonify
import sqlite3

inventory_bp = Blueprint("inventory", __name__)

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

@inventory_bp.route("/add", methods=["POST"])
def add_goods():
    data = request.json
    if not data:
        return jsonify({"error": "Request must contain JSON data."}), 400

    try:
        required_fields = ["Name", "Category", "PricePerItem", "Description", "StockCount"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' is required."}), 400

        valid_categories = ["Food", "Clothes", "Accessories", "Electronics"]
        if data["Category"] not in valid_categories:
            return jsonify({"error": f"Invalid category. Valid categories are: {', '.join(valid_categories)}"}), 400

        if not isinstance(data["PricePerItem"], (int, float)) or data["PricePerItem"] <= 0:
            return jsonify({"error": "PricePerItem must be a positive number."}), 400

        if not isinstance(data["StockCount"], int) or data["StockCount"] < 0:
            return jsonify({"error": "StockCount must be a non-negative integer."}), 400

        existing_good = execute_query("SELECT * FROM Goods WHERE Name = ?", (data["Name"],), fetchone=True)
        if existing_good:
            return jsonify({"error": f"A good with the name '{data['Name']}' already exists."}), 400

        query = """
        INSERT INTO Goods (Name, Category, PricePerItem, Description, StockCount)
        VALUES (?, ?, ?, ?, ?)
        """
        execute_query(query, (
            data["Name"], data["Category"], data["PricePerItem"],
            data["Description"], data["StockCount"]
        ), commit=True)

        return jsonify({"message": "Goods added successfully."}), 201
    except sqlite3.IntegrityError as e:
        return jsonify({"error": f"Database integrity error: {str(e)}"}), 500
    except ValueError as e:
        return jsonify({"error": f"Invalid value: {str(e)}"}), 400
    except KeyError as e:
        return jsonify({"error": f"Missing key: {e}"}), 400

@inventory_bp.route("/deduct/<int:good_id>", methods=["POST"])
def deduct_goods(good_id):
    data = request.json
    try:
        quantity_to_deduct = data.get("quantity", 0)
        if quantity_to_deduct <= 0:
            return jsonify({"error": "Quantity to deduct must be greater than 0."}), 400

        query = "SELECT StockCount FROM Goods WHERE GoodID = ?"
        stock = execute_query(query, (good_id,), fetchone=True)
        if not stock:
            return jsonify({"error": "Good not found."}), 404
        if stock[0] < quantity_to_deduct:
            return jsonify({"error": f"Insufficient stock. Available stock: {stock[0]}."}), 400

        query = "UPDATE Goods SET StockCount = StockCount - ? WHERE GoodID = ?"
        execute_query(query, (quantity_to_deduct, good_id), commit=True)

        return jsonify({"message": f"Deducted {quantity_to_deduct} items from Good ID {good_id} successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@inventory_bp.route("/update/<int:good_id>", methods=["PUT"])
def update_goods(good_id):
    data = request.json
    try:
        if not data:
            return jsonify({"error": "No fields provided to update."}), 400

        fields = ", ".join(f"{key} = ?" for key in data.keys())
        query = f"UPDATE Goods SET {fields} WHERE GoodID = ?"
        params = list(data.values()) + [good_id]

        result = execute_query(query, params, commit=True)
        if not result:
            return jsonify({"message": f"Good ID {good_id} updated successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

from flask import Flask, Blueprint, request, jsonify
import sqlite3

app = Flask(__name__)
reviews_bp = Blueprint("reviews", __name__)

DB_PATH = "./eCommerce.db"

def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    result = None
    try:
        cursor.execute(query, params)
        if fetchone:
            result = cursor.fetchone()
        elif fetchall:
            result = cursor.fetchall()
        if commit:
            conn.commit()
    finally:
        conn.close()
    return result

@reviews_bp.route("/submit", methods=["POST"])
def submit_review():
    data = request.json
    try:
        required_fields = ["CustomerID", "GoodID", "Rating"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        customer_query = "SELECT CustomerID FROM Customers WHERE CustomerID = ?"
        customer = execute_query(customer_query, (data["CustomerID"],), fetchone=True)
        if not customer:
            return jsonify({"error": "Invalid CustomerID. Customer does not exist."}), 400

        goods_query = "SELECT GoodID FROM Goods WHERE GoodID = ?"
        good = execute_query(goods_query, (data["GoodID"],), fetchone=True)
        if not good:
            return jsonify({"error": "Invalid GoodID. Product does not exist."}), 400

        if not (1 <= data["Rating"] <= 5):
            return jsonify({"error": "Rating must be between 1 and 5."}), 400

        query = """
        INSERT INTO Reviews (CustomerID, GoodID, Rating, Comment, IsApproved)
        VALUES (?, ?, ?, ?, ?)
        """
        execute_query(query, (
            data["CustomerID"], data["GoodID"], data["Rating"], data.get("Comment", ""), False
        ), commit=True)

        return jsonify({"message": "Review submitted successfully and awaits approval."}), 201

    except KeyError as e:
        return jsonify({"error": f"Missing key: {e.args[0]}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@reviews_bp.route("/update/<int:review_id>", methods=["PUT"])
def update_review(review_id):
    data = request.json
    try:
        if "CustomerID" not in data or "Rating" not in data:
            return jsonify({"error": "CustomerID and Rating are required."}), 400

        if not (1 <= data["Rating"] <= 5):
            return jsonify({"error": "Rating must be between 1 and 5."}), 400

        review_query = "SELECT CustomerID FROM Reviews WHERE ReviewID = ?"
        review = execute_query(review_query, (review_id,), fetchone=True)

        if not review:
            return jsonify({"error": "Review not found."}), 404

        customer_query = "SELECT IsAdmin FROM Customers WHERE CustomerID = ?"
        customer = execute_query(customer_query, (data["CustomerID"],), fetchone=True)

        if not customer:
            return jsonify({"error": "Customer not found."}), 404

        is_admin = customer[0]
        review_owner_id = review[0]

        if not is_admin and review_owner_id != data["CustomerID"]:
            return jsonify({"error": "Permission denied. You can only update your own review."}), 403

        update_query = """
        UPDATE Reviews
        SET Rating = ?, Comment = ?, UpdatedAt = CURRENT_TIMESTAMP
        WHERE ReviewID = ?
        """
        execute_query(update_query, (
            data["Rating"], data.get("Comment", ""), review_id
        ), commit=True)

        return jsonify({"message": "Review updated successfully."}), 200

    except KeyError as e:
        return jsonify({"error": f"Missing key: {e.args[0]}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
@reviews_bp.route("/delete/<int:review_id>", methods=["DELETE"])
def delete_review(review_id):
    data = request.json
    try:
        if "CustomerID" not in data:
            return jsonify({"error": "CustomerID is required."}), 400

        customer_query = "SELECT IsAdmin FROM Customers WHERE CustomerID = ?"
        customer = execute_query(customer_query, (data["CustomerID"],), fetchone=True)

        if not customer:
            return jsonify({"error": "Customer not found."}), 404

        is_admin = customer[0]

        if is_admin:
            delete_query = "DELETE FROM Reviews WHERE ReviewID = ?"
            execute_query(delete_query, (review_id,), commit=True)
        else:
            ownership_query = "SELECT CustomerID FROM Reviews WHERE ReviewID = ?"
            review_owner = execute_query(ownership_query, (review_id,), fetchone=True)

            if not review_owner or review_owner[0] != data["CustomerID"]:
                return jsonify({"error": "Review not found or permission denied."}), 403
            
            delete_query = "DELETE FROM Reviews WHERE ReviewID = ?"
            execute_query(delete_query, (review_id,), commit=True)

        return jsonify({"message": "Review deleted successfully."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reviews_bp.route("/product/<int:good_id>", methods=["GET"])
def get_product_reviews(good_id):
    try:
        query = """
        SELECT Reviews.ReviewID, Reviews.CustomerID, Reviews.Rating, Reviews.Comment, Reviews.CreatedAt, Reviews.IsApproved,
               Customers.FullName AS CustomerName
        FROM Reviews
        JOIN Customers ON Reviews.CustomerID = Customers.CustomerID
        WHERE GoodID = ? AND IsApproved = 1
        """
        reviews = execute_query(query, (good_id,), fetchall=True)

        if not reviews:
            return jsonify({"message": "No reviews found for this product."}), 404

        formatted_reviews = []
        for review in reviews:
            formatted_reviews.append({
                "ReviewID": review[0],
                "CustomerID": review[1],
                "CustomerName": review[6],
                "Rating": review[2],
                "Comment": review[3],
                "CreatedAt": review[4],
                "IsApproved": bool(review[5])
            })

        return jsonify(formatted_reviews), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reviews_bp.route("/customer/<int:customer_id>", methods=["GET"])
def get_customer_reviews(customer_id):
    try:
        query = """
        SELECT ReviewID, GoodID, Rating, Comment, CreatedAt, IsApproved
        FROM Reviews
        WHERE CustomerID = ?
        """
        reviews = execute_query(query, (customer_id,), fetchall=True)

        if not reviews:
            return jsonify({"message": "No reviews found for this customer."}), 404

        formatted_reviews = []
        for review in reviews:
            formatted_reviews.append({
                "ReviewID": review[0],
                "GoodID": review[1],
                "Rating": review[2],
                "Comment": review[3],
                "CreatedAt": review[4],
                "IsApproved": bool(review[5])
            })

        return jsonify(formatted_reviews), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reviews_bp.route("/moderate/<int:review_id>", methods=["PUT"])
def moderate_review(review_id):
    data = request.json
    try:
        if "CustomerID" not in data:
            return jsonify({"error": "CustomerID is required."}), 400

        customer_query = "SELECT IsAdmin FROM Customers WHERE CustomerID = ?"
        customer = execute_query(customer_query, (data["CustomerID"],), fetchone=True)

        if not customer:
            return jsonify({"error": "Customer not found."}), 404

        is_admin = customer[0]

        if not is_admin:
            return jsonify({"error": "Only admins can moderate reviews."}), 403

        query = """
        UPDATE Reviews
        SET IsApproved = ?
        WHERE ReviewID = ?
        """
        execute_query(query, (data["IsApproved"], review_id), commit=True)
        return jsonify({"message": "Review moderation updated successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reviews_bp.route("/details/<int:review_id>", methods=["GET"])
def get_review_details(review_id):
    try:
        query = """
        SELECT Reviews.ReviewID, Reviews.CustomerID, Reviews.GoodID, Reviews.Rating, Reviews.Comment, Reviews.CreatedAt, Reviews.IsApproved,
               Customers.FullName AS CustomerName
        FROM Reviews
        JOIN Customers ON Reviews.CustomerID = Customers.CustomerID
        WHERE ReviewID = ?
        """
        review = execute_query(query, (review_id,), fetchone=True)
        if not review:
            return jsonify({"error": "Review not found."}), 404

        formatted_review = {
            "ReviewID": review[0],
            "CustomerID": review[1],
            "GoodID": review[2],
            "Rating": review[3],
            "Comment": review[4],
            "CreatedAt": review[5],
            "IsApproved": bool(review[6]),
            "CustomerName": review[7]
        }

        return jsonify(formatted_review), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    app.run(debug=True)

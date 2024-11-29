"""
Blueprint for Reviews Management

This module provides routes and utilities for managing product reviews,
including creating, updating, deleting, and retrieving reviews. It also
includes review moderation functionalities for admins.
"""
from flask import Flask, Blueprint, request, jsonify
import sqlite3
import jwt
from functools import wraps
from services.customers import token_required,decode_jwt

app = Flask(__name__)
reviews_bp = Blueprint("reviews", __name__)

DB_PATH = "./eCommerce.db"
SECRET_KEY = "A123"

def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    """
    Executes a query on the SQLite database.

    Args:
        query (str): The SQL query to execute.
        params (tuple): The parameters for the query.
        fetchone (bool): Whether to fetch a single row.
        fetchall (bool): Whether to fetch all rows.
        commit (bool): Whether to commit the transaction.

    Returns:
        Any: Query results if fetchone or fetchall is True; otherwise, None.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
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

@reviews_bp.route("/submit", methods=["POST"])
@token_required
def submit_review(**kwargs):
    """
    Submits a new product review.

    **Authorization:** Requires a valid JWT token.

    **Request JSON:**
    - CustomerID (int): The ID of the customer submitting the review.
    - GoodID (int): The ID of the product being reviewed.
    - Rating (int): The rating (1-5).
    - Comment (str, optional): The review comment.

    **Headers:**
    - Authorization: Bearer <JWT_TOKEN>

    Returns:
        JSON: Success or error message.
    """
    data = request.json
    if "CustomerID" in data:
        customer_id = data["CustomerID"]
        username = get_username_from_customer_id(customer_id)
        if username != kwargs["Username"]:
            return jsonify({"error": "Unauthorized access"}), 403
    else:
         return jsonify({"error": "Missing required field: CustomerID"}), 400
    
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
        INSERT INTO Reviews (CustomerID, GoodID, Rating, Comment, Status, Upvotes, Downvotes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        execute_query(query, (
            data["CustomerID"], data["GoodID"], data["Rating"], 
            data.get("Comment", ""), "Pending", 0, 0
        ), commit=True)

        return jsonify({"message": "Review submitted successfully and awaits approval."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@reviews_bp.route("/update/<int:review_id>", methods=["PUT"])
@token_required
def update_review(review_id,**kwargs):
    """
    Updates an existing review.

    **Authorization:** Requires a valid JWT token.

    **Path Parameters:**
    - review_id (int): The ID of the review to update.

    **Request JSON:**
    - CustomerID (int): The ID of the customer submitting the review.
    - Rating (int): The updated rating (1-5).
    - Comment (str, optional): The updated review comment.

    **Headers:**
    - Authorization: Bearer <JWT_TOKEN>

    Returns:
        JSON: Success or error message.
    """
    data = request.json
    if "CustomerID" in data:
        customer_id = data["CustomerID"]
        username = get_username_from_customer_id(customer_id)
        if username != kwargs["Username"]:
            return jsonify({"error": "Unauthorized access"}), 403
    else:
         return jsonify({"error": "Missing required field: CustomerID"}), 400
    
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
@token_required
def delete_review(review_id,**kwargs):
    """
    Deletes a review.

    **Authorization:** Requires a valid JWT token.

    **Path Parameters:**
    - review_id (int): The ID of the review to delete.

    **Request JSON:**
    - CustomerID (int): The ID of the customer attempting to delete the review.

    **Headers:**
    - Authorization: Bearer <JWT_TOKEN>

    Returns:
        JSON: Success or error message.
    """
    data = request.json
    if "CustomerID" in data:
        customer_id = data["CustomerID"]
        username = get_username_from_customer_id(customer_id)
        if username != kwargs["Username"]:
            return jsonify({"error": "Unauthorized access"}), 403
    else:
         return jsonify({"error": "Missing required field: CustomerID"}), 400
    
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
    """
    Retrieves all approved reviews for a specific product, ordered by upvotes in descending order.

    Args:
        good_id (int): The ID of the product.

    Returns:
        JSON: A list of approved reviews or an error message.
    """
    try:
        query = """
        SELECT Reviews.ReviewID, Reviews.CustomerID, Reviews.Rating, Reviews.Comment, Reviews.CreatedAt, Reviews.Status,
               Reviews.Upvotes, Reviews.Downvotes, Customers.FullName AS CustomerName
        FROM Reviews
        JOIN Customers ON Reviews.CustomerID = Customers.CustomerID
        WHERE GoodID = ? AND Reviews.Status = 'Accepted'
        ORDER BY Reviews.Upvotes DESC
        """
        reviews = execute_query(query, (good_id,), fetchall=True)

        if not reviews:
            return jsonify({"message": "No approved reviews found for this product."}), 404

        formatted_reviews = []
        for review in reviews:
            formatted_reviews.append({
                "ReviewID": review[0],
                "CustomerID": review[1],
                "CustomerName": review[8],
                "Rating": review[2],
                "Comment": review[3],
                "CreatedAt": review[4],
                "Status": review[5],
                "Upvotes": review[6],
                "Downvotes": review[7]
            })

        return jsonify(formatted_reviews), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@reviews_bp.route("/customer/<int:customer_id>", methods=["GET"])
def get_customer_reviews(customer_id):
    """
    Retrieves all reviews by a specific customer.

    Args:
        customer_id (int): The ID of the customer.

    Returns:
        JSON: A list of reviews or an error message.
    """
    try:
        customer_query = "SELECT CustomerID FROM Customers WHERE CustomerID = ?"
        customer = execute_query(customer_query, (customer_id,), fetchone=True)
        if not customer:
            return jsonify({"error": f"Customer with ID {customer_id} does not exist."}), 404

        query = """
        SELECT Reviews.ReviewID, Reviews.GoodID, Reviews.Rating, Reviews.Comment, Reviews.CreatedAt,
               Reviews.Status, Reviews.Upvotes, Reviews.Downvotes, Goods.Name AS GoodName
        FROM Reviews
        JOIN Goods ON Reviews.GoodID = Goods.GoodID
        WHERE Reviews.CustomerID = ?
        """
        reviews = execute_query(query, (customer_id,), fetchall=True)

        if not reviews:
            return jsonify({"message": "No reviews found for this customer."}), 404

        formatted_reviews = [
            {
                "ReviewID": review["ReviewID"],
                "GoodID": review["GoodID"],
                "GoodName": review["GoodName"],
                "Rating": review["Rating"],
                "Comment": review["Comment"],
                "CreatedAt": review["CreatedAt"],
                "Status": review["Status"],
                "Upvotes": review["Upvotes"],
                "Downvotes": review["Downvotes"]
            }
            for review in reviews
        ]

        return jsonify(formatted_reviews), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@reviews_bp.route("/moderate/<int:review_id>", methods=["PUT"])
def moderate_review(review_id):
    """
    Updates the status of a review (moderation).

    Args:
        review_id (int): The ID of the review to moderate.

    Expects:
        JSON payload with:
        - CustomerID (int): The ID of the customer (must be an admin).
        - Status (str): The new status of the review. Must be one of:
          - "Pending"
          - "Accepted"
          - "Rejected"

    Returns:
        JSON:
            - Success message with a 200 status code if the moderation succeeds.
            - Error message with appropriate status codes if:
              - Required fields are missing (400).
              - Invalid status is provided (400).
              - Customer is not found (404).
              - Customer is not an admin (403).
              - Any other error occurs (500).

    Raises:
        - 400: If "CustomerID" or "Status" is missing in the request payload.
        - 400: If "Status" is not one of "Pending", "Accepted", or "Rejected".
        - 404: If the provided CustomerID does not exist.
        - 403: If the provided CustomerID does not belong to an admin.
        - 500: For unexpected server-side errors.
    """
    data = request.json
    try:
        if "CustomerID" not in data or "Status" not in data:
            return jsonify({"error": "CustomerID and Status are required."}), 400

        status = data["Status"]
        if status not in ["Pending", "Accepted", "Rejected"]:
            return jsonify({"error": "Invalid status. Must be 'Pending', 'Accepted', or 'Rejected'."}), 400

        customer_query = "SELECT IsAdmin FROM Customers WHERE CustomerID = ?"
        customer = execute_query(customer_query, (data["CustomerID"],), fetchone=True)
        if not customer:
            return jsonify({"error": "Customer not found."}), 404

        is_admin = customer[0]
        if not is_admin:
            return jsonify({"error": "Only admins can moderate reviews."}), 403

        query = """
        UPDATE Reviews
        SET Status = ?, UpdatedAt = CURRENT_TIMESTAMP
        WHERE ReviewID = ?
        """
        execute_query(query, (status, review_id), commit=True)
        return jsonify({"message": "Review status updated successfully."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@reviews_bp.route("/details/<int:review_id>", methods=["GET"])
def get_review_details(review_id):
    """
    Retrieves details for a specific review.

    Args:
        review_id (int): The ID of the review.

    Returns:
        JSON:
            - Review details if found.
            - Error message if the review does not exist or an unexpected error occurs.
    """
    try:
        query = """
        SELECT Reviews.ReviewID, Reviews.CustomerID, Reviews.GoodID, Reviews.Rating, Reviews.Comment, Reviews.CreatedAt,
               Reviews.Status, Reviews.Upvotes, Reviews.Downvotes, Customers.FullName AS CustomerName
        FROM Reviews
        JOIN Customers ON Reviews.CustomerID = Customers.CustomerID
        WHERE ReviewID = ?
        """
        review = execute_query(query, (review_id,), fetchone=True)

        if not review:
            return jsonify({"error": "Review not found."}), 404

        formatted_review = {
            "ReviewID": review["ReviewID"],
            "CustomerID": review["CustomerID"],
            "GoodID": review["GoodID"],
            "Rating": review["Rating"],
            "Comment": review["Comment"],
            "CreatedAt": review["CreatedAt"],
            "Status": review["Status"],
            "Upvotes": review["Upvotes"],
            "Downvotes": review["Downvotes"],
            "CustomerName": review["CustomerName"]
        }

        return jsonify(formatted_review), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@reviews_bp.route("/upvote/<int:review_id>", methods=["PUT"])
def upvote_review(review_id):
    """
    Increment the upvote count for a specific review.

    Args:
        review_id (int): The ID of the review to upvote.

    Returns:
        JSON: 
            - Success message if the review was upvoted successfully.
            - Error message if the review does not exist or if an unexpected error occurs.
        
    HTTP Status Codes:
        - 200: Review upvoted successfully.
        - 404: Review not found.
        - 500: Internal server error.
    """
    try:
        review_check_query = "SELECT ReviewID FROM Reviews WHERE ReviewID = ?"
        review = execute_query(review_check_query, (review_id,), fetchone=True)

        if not review:
            return jsonify({"error": "Review not found."}), 404

        upvote_query = "UPDATE Reviews SET Upvotes = Upvotes + 1 WHERE ReviewID = ?"
        execute_query(upvote_query, (review_id,), commit=True)

        return jsonify({"message": "Review upvoted successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@reviews_bp.route("/downvote/<int:review_id>", methods=["PUT"])
def downvote_review(review_id):
    """
    Increment the downvote count for a specific review.

    Args:
        review_id (int): The ID of the review to downvote.

    Returns:
        JSON:
            - Success message if the review was downvoted successfully.
            - Error message if the review does not exist or if an unexpected error occurs.
        
    HTTP Status Codes:
        - 200: Review downvoted successfully.
        - 404: Review not found.
        - 500: Internal server error.
    """
    try:
        review_check_query = "SELECT ReviewID FROM Reviews WHERE ReviewID = ?"
        review = execute_query(review_check_query, (review_id,), fetchone=True)

        if not review:
            return jsonify({"error": "Review not found."}), 404

        downvote_query = "UPDATE Reviews SET Downvotes = Downvotes + 1 WHERE ReviewID = ?"
        execute_query(downvote_query, (review_id,), commit=True)

        return jsonify({"message": "Review downvoted successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_username_from_customer_id(customer_id):
    """
    Fetches the Username corresponding to a given CustomerID.

    Args:
        customer_id (int): The ID of the customer.

    Returns:
        str: The username if found, else None.
    """
    query = "SELECT Username FROM Customers WHERE CustomerID = ?"
    result = execute_query(query, (customer_id,), fetchone=True)
    return result[0] if result else None

if __name__ == "__main__":
    app.run(debug=True)

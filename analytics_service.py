from flask import Flask, jsonify
import sqlite3
import pandas as pd

app = Flask(__name__)

DB_PATH = "eCommerce.db"

def execute_query(query):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql(query, conn)
    
@app.route('/analytics/total-revenue', methods=['GET'])
def total_revenue():
    query = """
    SELECT 
        DATE(PurchaseDate) AS PurchaseDate, 
        SUM(TotalAmount) AS TotalRevenue
    FROM historicalPurchases
    GROUP BY DATE(PurchaseDate)
    ORDER BY PurchaseDate;
    """
    df = execute_query(query)
    return jsonify(df.to_dict(orient="records"))

@app.route('/analytics/popular-products', methods=['GET'])
def popular_products():
    query = """
    SELECT 
        GoodID AS ProductID, 
        COUNT(*) AS PurchaseCount,         -- Number of times the product was purchased
        SUM(Quantity) AS TotalSold         -- Total quantity sold
    FROM historicalPurchases
    GROUP BY GoodID
    ORDER BY TotalSold DESC, PurchaseCount DESC
    LIMIT 10;                             -- Top 10 most popular products
    """
    df = execute_query(query)
    return jsonify(df.to_dict(orient="records"))


@app.route('/analytics/customer-demographics', methods=['GET'])
def customer_demographics():
    query = """
    SELECT 
        Gender, 
        MaritalStatus, 
        COUNT(*) AS CustomerCount 
    FROM Customers
    GROUP BY Gender, MaritalStatus;
    """
    df = execute_query(query)
    return jsonify(df.to_dict(orient="records"))

if __name__ == "__main__":
    app.run(debug=True, port=5005)

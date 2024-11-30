import os
import sqlite3

def create_database():
    # Connect to SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect("eCommerce.db")
    cursor = conn.cursor()


    # Create Customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Customers (
        CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
        FullName TEXT NOT NULL,
        Username TEXT NOT NULL UNIQUE,
        Password TEXT NOT NULL,
        Age INTEGER CHECK (Age > 0),
        Address TEXT,
        Gender TEXT CHECK (Gender IN ('Male', 'Female', 'Other')),
        MaritalStatus TEXT CHECK (MaritalStatus IN ('Single', 'Married', 'Divorced', 'Widowed')),
        WalletBalance REAL DEFAULT 0.0 CHECK (WalletBalance >= 0.0),
        IsAdmin BOOLEAN DEFAULT FALSE, -- Column to identify admin
        CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT SingleAdmin CHECK (IsAdmin IN (0, 1)) -- Ensure IsAdmin is boolean
    );
    """)

    # Create Goods table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Goods (
        GoodID INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Category TEXT CHECK (Category IN ('Food', 'Clothes', 'Accessories', 'Electronics')),
        PricePerItem REAL NOT NULL CHECK (PricePerItem > 0.0),
        Description TEXT,
        StockCount INTEGER NOT NULL CHECK (StockCount >= 0),
        CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Create Reviews table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Reviews (
        ReviewID INTEGER PRIMARY KEY AUTOINCREMENT,
        CustomerID INTEGER NOT NULL,
        GoodID INTEGER NOT NULL,
        Rating INTEGER NOT NULL CHECK (Rating BETWEEN 1 AND 5),
        Comment TEXT,
        CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        IsApproved BOOLEAN DEFAULT 0,
        FOREIGN KEY (CustomerID) REFERENCES Customers (CustomerID) ON DELETE CASCADE,
        FOREIGN KEY (GoodID) REFERENCES Goods (GoodID) ON DELETE CASCADE
    );
    """)

    # Create HistoricalPurchases table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS HistoricalPurchases (
        PurchaseID INTEGER PRIMARY KEY AUTOINCREMENT,
        CustomerID INTEGER NOT NULL,
        GoodID INTEGER NOT NULL,
        Quantity INTEGER NOT NULL CHECK (Quantity > 0),
        TotalAmount REAL NOT NULL CHECK (TotalAmount > 0.0),
        PurchaseDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (CustomerID) REFERENCES Customers (CustomerID) ON DELETE CASCADE,
        FOREIGN KEY (GoodID) REFERENCES Goods (GoodID) ON DELETE CASCADE
    );
    """)

    # Commit changes and close the connection
    conn.commit()
    conn.close()
    print("Database and tables created successfully.")

if __name__ == "__main__":
    create_database()
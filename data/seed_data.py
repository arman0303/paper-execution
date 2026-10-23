"""
Seed script to create and populate data/sample_ecommerce.db with realistic test records.
"""
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
DB_PATH = DATA_DIR / "sample_ecommerce.db"
SCHEMA_PATH = DATA_DIR / "schema.sql"

def create_database():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    # Insert Customers
    customers = [
        (1, "Alice Smith", "alice@example.com", "New York", "USA", "2024-01-10 10:00:00", "active"),
        (2, "Bob Jones", "bob@example.com", "London", "UK", "2024-01-15 11:30:00", "active"),
        (3, "Carlos Ray", "carlos@example.com", "Madrid", "Spain", "2024-02-01 09:15:00", "active"),
        (4, "Diana Prince", "diana@example.com", "New York", "USA", "2024-02-14 14:20:00", "active"),
        (5, "Evan Wright", "evan@example.com", "Toronto", "Canada", "2024-03-01 16:45:00", "inactive"),
        (6, "Fiona Gallagher", "fiona@example.com", "Chicago", "USA", "2024-03-10 12:00:00", "active"),
        (7, "George Clark", "george@example.com", "Berlin", "Germany", "2024-03-25 15:10:00", "active"),
        (8, "Hannah Abbott", "hannah@example.com", "London", "UK", "2024-04-05 18:30:00", "suspended"),
    ]
    cursor.executemany(
        "INSERT INTO customers (id, name, email, city, country, created_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        customers
    )

    # Insert Products
    products = [
        (1, "Ultra Wireless Headphones", "Electronics", 150.00, 45, 1),
        (2, "Ergonomic Mechanical Keyboard", "Electronics", 120.00, 30, 1),
        (3, "4K Ultra HD Monitor", "Electronics", 350.00, 15, 1),
        (4, "Organic Cotton T-Shirt", "Apparel", 25.00, 120, 1),
        (5, "Waterproof Hiking Jacket", "Apparel", 110.00, 25, 1),
        (6, "Stainless Steel Water Bottle", "Home & Kitchen", 20.00, 80, 1),
        (7, "AeroPress Coffee Maker", "Home & Kitchen", 40.00, 50, 1),
        (8, "Smart Fitness Tracker", "Electronics", 90.00, 0, 0), # Out of stock / inactive
    ]
    cursor.executemany(
        "INSERT INTO products (id, name, category, price, stock_quantity, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        products
    )

    # Insert Orders
    orders = [
        (1, 1, "2024-04-10 10:15:00", "completed", 270.00, "New York", "USA"),
        (2, 1, "2024-05-12 14:00:00", "completed", 120.00, "New York", "USA"),
        (3, 2, "2024-04-15 11:45:00", "completed", 350.00, "London", "UK"),
        (4, 3, "2024-04-20 16:30:00", "completed", 135.00, "Madrid", "Spain"),
        (5, 4, "2024-05-01 09:00:00", "completed", 470.00, "New York", "USA"),
        (6, 4, "2024-05-18 17:20:00", "pending", 60.00, "New York", "USA"),
        (7, 5, "2024-03-15 13:10:00", "cancelled", 150.00, "Toronto", "Canada"),
        (8, 6, "2024-05-05 15:40:00", "completed", 25.00, "Chicago", "USA"),
        (9, 7, "2024-05-20 18:00:00", "refunded", 110.00, "Berlin", "Germany"),
        (10, 2, "2024-05-22 10:30:00", "completed", 60.00, "London", "UK"),
    ]
    cursor.executemany(
        "INSERT INTO orders (id, customer_id, order_date, status, total_amount, shipping_city, shipping_country) VALUES (?, ?, ?, ?, ?, ?, ?)",
        orders
    )

    # Insert Order Items
    order_items = [
        (1, 1, 1, 1, 150.00, 0.0), # Order 1: 1 Headphone ($150)
        (2, 1, 2, 1, 120.00, 0.0), # Order 1: 1 Keyboard ($120)
        (3, 2, 2, 1, 120.00, 0.0), # Order 2: 1 Keyboard ($120)
        (4, 3, 3, 1, 350.00, 0.0), # Order 3: 1 Monitor ($350)
        (5, 4, 5, 1, 110.00, 0.0), # Order 4: 1 Hiking Jacket ($110)
        (6, 4, 4, 1, 25.00, 0.0),  # Order 4: 1 T-shirt ($25)
        (7, 5, 3, 1, 350.00, 0.0), # Order 5: 1 Monitor ($350)
        (8, 5, 2, 1, 120.00, 0.0), # Order 5: 1 Keyboard ($120)
        (9, 6, 6, 3, 20.00, 0.0),  # Order 6: 3 Water bottles ($60)
        (10, 7, 1, 1, 150.00, 0.0),# Order 7: Cancelled order item
        (11, 8, 4, 1, 25.00, 0.0), # Order 8: 1 T-shirt ($25)
        (12, 9, 5, 1, 110.00, 0.0),# Order 9: 1 Hiking Jacket ($110)
        (13, 10, 6, 1, 20.00, 0.0),# Order 10: 1 Water bottle ($20)
        (14, 10, 7, 1, 40.00, 0.0),# Order 10: 1 AeroPress ($40)
    ]
    cursor.executemany(
        "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, discount) VALUES (?, ?, ?, ?, ?, ?)",
        order_items
    )

    # Insert Payments
    payments = [
        (1, 1, "2024-04-10 10:16:00", "credit_card", 270.00, "successful"),
        (2, 2, "2024-05-12 14:02:00", "paypal", 120.00, "successful"),
        (3, 3, "2024-04-15 11:46:00", "credit_card", 350.00, "successful"),
        (4, 4, "2024-04-20 16:32:00", "credit_card", 135.00, "successful"),
        (5, 5, "2024-05-01 09:02:00", "paypal", 470.00, "successful"),
        (6, 6, "2024-05-18 17:21:00", "credit_card", 60.00, "failed"),
        (7, 7, "2024-03-15 13:11:00", "credit_card", 150.00, "failed"),
        (8, 8, "2024-05-05 15:42:00", "bank_transfer", 25.00, "successful"),
        (9, 9, "2024-05-20 18:02:00", "credit_card", 110.00, "refunded"),
        (10, 10, "2024-05-22 10:32:00", "crypto", 60.00, "successful"),
    ]
    cursor.executemany(
        "INSERT INTO payments (id, order_id, payment_date, payment_method, amount, status) VALUES (?, ?, ?, ?, ?, ?)",
        payments
    )

    conn.commit()
    conn.close()
    print(f"Successfully created and seeded sample database at {DB_PATH}")

if __name__ == "__main__":
    create_database()

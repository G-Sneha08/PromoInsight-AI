import os
import sqlite3
import pandas as pd

def setup_database():
    db_dir = "database"
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "promoinsight.db")
    
    # If database already exists, delete it to ensure a clean setup
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed existing database file.")
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Create PRODUCTS table
    print("Creating PRODUCTS table...")
    cursor.execute("""
    CREATE TABLE products (
        product_id TEXT PRIMARY KEY,
        product_name TEXT NOT NULL,
        category TEXT NOT NULL,
        brand TEXT NOT NULL,
        pack_size TEXT NOT NULL,
        unit_price REAL NOT NULL
    );
    """)
    
    # 2. Create REGIONS table
    print("Creating REGIONS table...")
    cursor.execute("""
    CREATE TABLE regions (
        region_id TEXT PRIMARY KEY,
        region_name TEXT NOT NULL,
        state_group TEXT NOT NULL
    );
    """)
    
    # 3. Create PROMOTIONS table
    print("Creating PROMOTIONS table...")
    cursor.execute("""
    CREATE TABLE promotions (
        promotion_id TEXT PRIMARY KEY,
        promotion_name TEXT NOT NULL,
        promotion_type TEXT NOT NULL,
        discount_percentage REAL NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        product_id TEXT,
        region_id TEXT,
        FOREIGN KEY (product_id) REFERENCES products(product_id),
        FOREIGN KEY (region_id) REFERENCES regions(region_id)
    );
    """)
    
    # 4. Create SALES table
    print("Creating SALES table...")
    cursor.execute("""
    CREATE TABLE sales (
        sale_id INTEGER PRIMARY KEY,
        sale_date DATE NOT NULL,
        product_id TEXT NOT NULL,
        region_id TEXT NOT NULL,
        units_sold INTEGER NOT NULL,
        sales_amount REAL NOT NULL,
        promotion_id TEXT,
        FOREIGN KEY (product_id) REFERENCES products(product_id),
        FOREIGN KEY (region_id) REFERENCES regions(region_id),
        FOREIGN KEY (promotion_id) REFERENCES promotions(promotion_id)
    );
    """)
    
    # 5. Create INVENTORY table
    print("Creating INVENTORY table...")
    cursor.execute("""
    CREATE TABLE inventory (
        inventory_id INTEGER PRIMARY KEY,
        snapshot_date DATE NOT NULL,
        product_id TEXT NOT NULL,
        region_id TEXT NOT NULL,
        opening_inventory INTEGER NOT NULL,
        received_units INTEGER NOT NULL,
        closing_inventory INTEGER NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(product_id),
        FOREIGN KEY (region_id) REFERENCES regions(region_id)
    );
    """)
    
    # Create indexes for optimal join and filter performance
    print("Creating database indexes...")
    cursor.execute("CREATE INDEX idx_sales_date ON sales(sale_date);")
    cursor.execute("CREATE INDEX idx_sales_prod_reg ON sales(product_id, region_id);")
    cursor.execute("CREATE INDEX idx_sales_promo ON sales(promotion_id);")
    
    cursor.execute("CREATE INDEX idx_inventory_date ON inventory(snapshot_date);")
    cursor.execute("CREATE INDEX idx_inventory_prod_reg ON inventory(product_id, region_id);")
    
    cursor.execute("CREATE INDEX idx_promotions_dates ON promotions(start_date, end_date);")
    cursor.execute("CREATE INDEX idx_promotions_prod_reg ON promotions(product_id, region_id);")
    
    conn.commit()
    
    # Populate data from CSVs
    print("Populating database from CSV datasets...")
    
    # Load csv data using pandas to handle missing/blank values appropriately
    df_products = pd.read_csv("data/products.csv")
    df_products.to_sql("products", conn, if_exists="append", index=False)
    print(f"Loaded {len(df_products)} products.")
    
    df_regions = pd.read_csv("data/regions.csv")
    df_regions.to_sql("regions", conn, if_exists="append", index=False)
    print(f"Loaded {len(df_regions)} regions.")
    
    df_promotions = pd.read_csv("data/promotions.csv")
    df_promotions.to_sql("promotions", conn, if_exists="append", index=False)
    print(f"Loaded {len(df_promotions)} promotions.")
    
    df_sales = pd.read_csv("data/sales.csv")
    # Replace empty promotion_id fields with None (which SQLite maps to NULL)
    df_sales["promotion_id"] = df_sales["promotion_id"].fillna(value="")
    # Replace empty string with None to allow NULL values in database
    df_sales.loc[df_sales["promotion_id"] == "", "promotion_id"] = None
    df_sales.to_sql("sales", conn, if_exists="append", index=False)
    print(f"Loaded {len(df_sales)} sales records.")
    
    df_inventory = pd.read_csv("data/inventory.csv")
    df_inventory.to_sql("inventory", conn, if_exists="append", index=False)
    print(f"Loaded {len(df_inventory)} inventory records.")
    
    # Verify row counts and integrity
    cursor.execute("SELECT COUNT(*) FROM sales WHERE promotion_id IS NOT NULL;")
    promo_sales_count = cursor.fetchone()[0]
    print(f"Sales records associated with promotions: {promo_sales_count}")
    
    conn.close()
    print("Database setup complete and verified.")

if __name__ == "__main__":
    setup_database()

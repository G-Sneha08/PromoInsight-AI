from typing import Dict, List, Any

# Complete Database Schema Metadata Catalog
METADATA_CATALOG: Dict[str, Any] = {
    "tables": {
        "products": {
            "description": "Master data for company products (beverage items).",
            "columns": {
                "product_id": {"type": "TEXT", "meaning": "Unique product code", "allowed_operators": ["equals", "not_equals", "in", "not_in"], "example": "P001"},
                "product_name": {"type": "TEXT", "meaning": "Brand/flavor name of product", "allowed_operators": ["equals", "not_equals", "in", "not_in", "contains"], "example": "Cola Classic 500ml"},
                "category": {"type": "TEXT", "meaning": "Beverage category", "allowed_operators": ["equals", "not_equals", "in", "not_in"], "example": "Carbonated Drinks", "allowed_values": ["Carbonated Drinks", "Packaged Water", "Fruit Juice", "Energy Drinks", "Iced Tea"]},
                "brand": {"type": "TEXT", "meaning": "Manufacturer brand name", "allowed_operators": ["equals", "not_equals", "in", "not_in"], "example": "FizzCo"},
                "pack_size": {"type": "TEXT", "meaning": "Packaging volume or count details", "allowed_operators": ["equals"], "example": "500ml"},
                "unit_price": {"type": "REAL", "meaning": "Standard retail unit price", "allowed_operators": ["equals", "greater_than", "less_than", "between"], "example": 1.50}
            }
        },
        "regions": {
            "description": "Master data for sales territories.",
            "columns": {
                "region_id": {"type": "TEXT", "meaning": "Unique region code", "allowed_operators": ["equals", "not_equals", "in", "not_in"], "example": "R01"},
                "region_name": {"type": "TEXT", "meaning": "Regional territory name", "allowed_operators": ["equals", "not_equals", "in", "not_in"], "example": "North", "allowed_values": ["North", "South", "East", "West", "Central"]},
                "state_group": {"type": "TEXT", "meaning": "US states bundled in this region", "allowed_operators": ["contains"], "example": "NY, PA, OH"}
            }
        },
        "promotions": {
            "description": "Details of discount and bundle marketing campaigns.",
            "columns": {
                "promotion_id": {"type": "TEXT", "meaning": "Unique promotion/campaign identifier", "allowed_operators": ["equals", "not_equals", "in", "not_in"], "example": "PROM01"},
                "promotion_name": {"type": "TEXT", "meaning": "Public or internal campaign name", "allowed_operators": ["equals", "contains"], "example": "Summer Soda Festival"},
                "promotion_type": {"type": "TEXT", "meaning": "Marketing style e.g. Discount, Bundle", "allowed_operators": ["equals"], "example": "Discount"},
                "discount_percentage": {"type": "REAL", "meaning": "Percentage discount off standard price", "allowed_operators": ["greater_than", "less_than", "between"], "example": 15.0},
                "start_date": {"type": "DATE", "meaning": "Campaign activation date", "allowed_operators": ["equals", "greater_than_or_equal", "less_than_or_equal", "between"], "example": "2025-07-01"},
                "end_date": {"type": "DATE", "meaning": "Campaign expiration date", "allowed_operators": ["equals", "greater_than_or_equal", "less_than_or_equal", "between"], "example": "2025-07-15"},
                "product_id": {"type": "TEXT", "meaning": "Target product code for campaign", "allowed_operators": ["equals", "in"], "example": "P001"},
                "region_id": {"type": "TEXT", "meaning": "Regional boundary for campaign", "allowed_operators": ["equals", "in"], "example": "R02"}
            }
        },
        "sales": {
            "description": "Transactional sales records (daily aggregate by product and region).",
            "columns": {
                "sale_id": {"type": "INTEGER", "meaning": "Primary key for sales record", "allowed_operators": ["equals"], "example": 1234},
                "sale_date": {"type": "DATE", "meaning": "Transaction date", "allowed_operators": ["equals", "greater_than_or_equal", "less_than_or_equal", "between"], "example": "2025-07-04"},
                "product_id": {"type": "TEXT", "meaning": "Associated product code", "allowed_operators": ["equals", "in", "not_in"], "example": "P001"},
                "region_id": {"type": "TEXT", "meaning": "Associated region code", "allowed_operators": ["equals", "in", "not_in"], "example": "R02"},
                "units_sold": {"type": "INTEGER", "meaning": "Quantity of beverage bottles/packs sold", "allowed_operators": ["greater_than", "less_than"], "example": 140},
                "sales_amount": {"type": "REAL", "meaning": "Net revenue generated from sale", "allowed_operators": ["greater_than", "less_than", "between"], "example": 210.0},
                "promotion_id": {"type": "TEXT", "meaning": "Active promotion code applied to sale", "allowed_operators": ["equals", "in", "is_null", "is_not_null"], "example": "PROM01"}
            }
        },
        "inventory": {
            "description": "Daily inventory balance snapshots by product and region.",
            "columns": {
                "inventory_id": {"type": "INTEGER", "meaning": "Primary key for inventory log", "allowed_operators": ["equals"], "example": 5678},
                "snapshot_date": {"type": "DATE", "meaning": "Stock snapshot date", "allowed_operators": ["equals", "greater_than_or_equal", "less_than_or_equal", "between"], "example": "2025-07-04"},
                "product_id": {"type": "TEXT", "meaning": "Product stock code", "allowed_operators": ["equals", "in"], "example": "P001"},
                "region_id": {"type": "TEXT", "meaning": "Region stock location code", "allowed_operators": ["equals", "in"], "example": "R02"},
                "opening_inventory": {"type": "INTEGER", "meaning": "Stock units at start of day", "allowed_operators": ["greater_than", "less_than"], "example": 1200},
                "received_units": {"type": "INTEGER", "meaning": "New stock deliveries received today", "allowed_operators": ["greater_than"], "example": 500},
                "closing_inventory": {"type": "INTEGER", "meaning": "Stock units remaining at end of day", "allowed_operators": ["greater_than", "less_than"], "example": 1060}
            }
        }
    },
    # Mapping for safe joins
    "joins": {
        ("sales", "products"): "sales.product_id = products.product_id",
        ("sales", "regions"): "sales.region_id = regions.region_id",
        ("sales", "promotions"): "sales.promotion_id = promotions.promotion_id",
        ("inventory", "products"): "inventory.product_id = products.product_id",
        ("inventory", "regions"): "inventory.region_id = regions.region_id",
        ("promotions", "products"): "promotions.product_id = products.product_id",
        ("promotions", "regions"): "promotions.region_id = regions.region_id"
    }
}

def get_field_table(field_name: str) -> str:
    """Returns which table a column belongs to."""
    for table_name, table_info in METADATA_CATALOG["tables"].items():
        if field_name in table_info["columns"]:
            return table_name
    raise ValueError(f"Field '{field_name}' not found in metadata catalog.")

def is_valid_column(field_name: str) -> bool:
    """Checks if field name exists in any table."""
    for table_name, table_info in METADATA_CATALOG["tables"].items():
        if field_name in table_info["columns"]:
            return True
    return False

def get_join_path(tables: List[str]) -> List[str]:
    """Resolves join statements given a list of unique tables."""
    if len(tables) <= 1:
        return []
    
    joins = []
    # Sort to use standard key lookup
    # A simple join resolver: if 'sales' is present, join others to sales. If 'inventory' is present, join to inventory.
    # If both sales and inventory are present (rare but possible), we join sales -> products -> inventory, etc.
    # Let's map joins to a central hub (products or regions)
    
    # We want to connect all tables in the list
    connected_tables = [tables[0]]
    remaining_tables = list(tables[1:])
    
    while remaining_tables:
        joined_any = False
        for t1 in connected_tables:
            for t2 in remaining_tables:
                # Check directly
                key = (t1, t2) if (t1, t2) in METADATA_CATALOG["joins"] else ((t2, t1) if (t2, t1) in METADATA_CATALOG["joins"] else None)
                if key:
                    joins.append(METADATA_CATALOG["joins"][key])
                    connected_tables.append(t2)
                    remaining_tables.remove(t2)
                    joined_any = True
                    break
            if joined_any:
                break
        if not joined_any:
            # If no direct join, we might need a bridge (e.g. products bridges sales and inventory)
            if "products" not in connected_tables and "products" not in remaining_tables:
                # Add products as bridge
                remaining_tables.append("products")
                continue
            raise ValueError(f"Could not resolve join path for tables: {tables}")
            
    return list(set(joins))

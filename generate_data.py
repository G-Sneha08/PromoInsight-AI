import os
import random
import csv
from datetime import datetime, timedelta

def generate_datasets():
    # Set fixed random seed for reproducibility
    random.seed(42)
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Define date range: 12 months (365 days)
    start_date = datetime(2025, 7, 1)
    end_date = datetime(2026, 6, 30)
    total_days = (end_date - start_date).days + 1
    date_list = [start_date + timedelta(days=x) for x in range(total_days)]
    
    # 1. Products (18 products across 5 categories)
    products = [
        {"product_id": "P001", "product_name": "Cola Classic 500ml", "category": "Carbonated Drinks", "brand": "FizzCo", "pack_size": "500ml", "unit_price": 1.50},
        {"product_id": "P002", "product_name": "Diet Cola 500ml", "category": "Carbonated Drinks", "brand": "FizzCo", "pack_size": "500ml", "unit_price": 1.60},
        {"product_id": "P003", "product_name": "Lemon Lime Fizz 1L", "category": "Carbonated Drinks", "brand": "FizzCo", "pack_size": "1L", "unit_price": 2.20},
        {"product_id": "P004", "product_name": "Orange Splash 2L", "category": "Carbonated Drinks", "brand": "FizzCo", "pack_size": "2L", "unit_price": 3.00},
        
        {"product_id": "P005", "product_name": "Pure Spring Water 500ml", "category": "Packaged Water", "brand": "H2O Pure", "pack_size": "500ml", "unit_price": 0.80},
        {"product_id": "P006", "product_name": "Sparkling Water 750ml", "category": "Packaged Water", "brand": "H2O Pure", "pack_size": "750ml", "unit_price": 1.20},
        {"product_id": "P007", "product_name": "Mineral Water 6-Pack", "category": "Packaged Water", "brand": "H2O Pure", "pack_size": "6x500ml", "unit_price": 4.50},
        
        {"product_id": "P008", "product_name": "Apple Juice 1L", "category": "Fruit Juice", "brand": "Orchard Fresh", "pack_size": "1L", "unit_price": 2.80},
        {"product_id": "P009", "product_name": "Orange Juice 1L", "category": "Fruit Juice", "brand": "Orchard Fresh", "pack_size": "1L", "unit_price": 2.90},
        {"product_id": "P010", "product_name": "Mango Nectar 1L", "category": "Fruit Juice", "brand": "Orchard Fresh", "pack_size": "1L", "unit_price": 3.20},
        {"product_id": "P011", "product_name": "Cranberry Blend 500ml", "category": "Fruit Juice", "brand": "Orchard Fresh", "pack_size": "500ml", "unit_price": 2.00},
        
        {"product_id": "P012", "product_name": "Bolt Energy Original 250ml", "category": "Energy Drinks", "brand": "Bolt", "pack_size": "250ml", "unit_price": 2.50},
        {"product_id": "P013", "product_name": "Bolt Energy Sugar-Free", "category": "Energy Drinks", "brand": "Bolt", "pack_size": "250ml", "unit_price": 2.60},
        {"product_id": "P014", "product_name": "Volt Super Charge 500ml", "category": "Energy Drinks", "brand": "Volt", "pack_size": "500ml", "unit_price": 3.50},
        
        {"product_id": "P015", "product_name": "Peach Iced Tea 500ml", "category": "Iced Tea", "brand": "Brewed Leaf", "pack_size": "500ml", "unit_price": 1.80},
        {"product_id": "P016", "product_name": "Lemon Iced Tea 500ml", "category": "Iced Tea", "brand": "Brewed Leaf", "pack_size": "500ml", "unit_price": 1.80},
        {"product_id": "P017", "product_name": "Green Tea Honey 500ml", "category": "Iced Tea", "brand": "Brewed Leaf", "pack_size": "500ml", "unit_price": 1.95},
        {"product_id": "P018", "product_name": "Matcha Iced Latte 250ml", "category": "Iced Tea", "brand": "Brewed Leaf", "pack_size": "250ml", "unit_price": 2.80}
    ]
    
    # 2. Regions (5 regions)
    regions = [
        {"region_id": "R01", "region_name": "North", "state_group": "NY, PA, OH, IL, MI"},
        {"region_id": "R02", "region_name": "South", "state_group": "TX, FL, GA, NC, VA"},
        {"region_id": "R03", "region_name": "East", "state_group": "MA, MD, NJ, CT, DE"},
        {"region_id": "R04", "region_name": "West", "state_group": "CA, WA, OR, AZ, CO"},
        {"region_id": "R05", "region_name": "Central", "state_group": "KS, NE, IA, MO, WI"}
    ]
    
    # 3. Promotions (10 promotions, including one overlapping and one underperforming)
    promotions = [
        # P001: Summer Soda Festival (FizzCo in South/West)
        {"promotion_id": "PROM01", "promotion_name": "Summer Soda Festival", "promotion_type": "Discount", "discount_percentage": 15.0, "start_date": "2025-07-01", "end_date": "2025-07-15", "product_id": "P001", "region_id": "R02"},
        {"promotion_id": "PROM02", "promotion_name": "Summer Soda Festival", "promotion_type": "Discount", "discount_percentage": 15.0, "start_date": "2025-07-01", "end_date": "2025-07-15", "product_id": "P001", "region_id": "R04"},
        # P004: Orange Splash Promo in East
        {"promotion_id": "PROM03", "promotion_name": "Orange Splash Promo", "promotion_type": "Discount", "discount_percentage": 20.0, "start_date": "2025-08-10", "end_date": "2025-08-25", "product_id": "P004", "region_id": "R03"},
        # P008: Back to School Juice (Apple Juice)
        {"promotion_id": "PROM04", "promotion_name": "Back to School Juice", "promotion_type": "Bundle", "discount_percentage": 10.0, "start_date": "2025-09-01", "end_date": "2025-09-20", "product_id": "P008", "region_id": "R01"},
        # P012: Bolt Energy Flash Sale (Underperforming promo: Discount 30% but sales actually dip due to supply chain issues)
        {"promotion_id": "PROM05", "promotion_name": "Bolt Energy Flash Sale", "promotion_type": "Discount", "discount_percentage": 30.0, "start_date": "2025-10-05", "end_date": "2025-10-12", "product_id": "P012", "region_id": "R02"},
        # P015 & P016: Thanksgiving Tea Blast (Overlapping Promotions: P015 in South, R02 has two promos overlapping)
        {"promotion_id": "PROM06", "promotion_name": "Thanksgiving Tea Blast", "promotion_type": "Discount", "discount_percentage": 25.0, "start_date": "2025-11-20", "end_date": "2025-11-30", "product_id": "P015", "region_id": "R02"},
        {"promotion_id": "PROM07", "promotion_name": "Thanksgiving Tea Overlap", "promotion_type": "Bundle", "discount_percentage": 15.0, "start_date": "2025-11-24", "end_date": "2025-11-30", "product_id": "P015", "region_id": "R02"}, # Overlap!
        # P005: Winter hydration
        {"promotion_id": "PROM08", "promotion_name": "Winter Hydration Promo", "promotion_type": "Discount", "discount_percentage": 10.0, "start_date": "2025-12-15", "end_date": "2026-01-05", "product_id": "P005", "region_id": "R01"},
        # P009: Spring Refresh (Orange Juice in West)
        {"promotion_id": "PROM09", "promotion_name": "Spring Juice Refresh", "promotion_type": "Discount", "discount_percentage": 15.0, "start_date": "2026-03-10", "end_date": "2026-03-25", "product_id": "P009", "region_id": "R04"},
        # P014: Volt Energy Kickoff (Central)
        {"promotion_id": "PROM10", "promotion_name": "Volt Energy Kickoff", "promotion_type": "Discount", "discount_percentage": 20.0, "start_date": "2026-05-01", "end_date": "2026-05-15", "product_id": "P014", "region_id": "R05"}
    ]
    
    # Keep promotions index list for easier validation during sales generation
    promo_intervals = []
    for p in promotions:
        p_start = datetime.strptime(p["start_date"], "%Y-%m-%d")
        p_end = datetime.strptime(p["end_date"], "%Y-%m-%d")
        promo_intervals.append({
            "id": p["promotion_id"],
            "product_id": p["product_id"],
            "region_id": p["region_id"],
            "start": p_start,
            "end": p_end,
            "discount": p["discount_percentage"]
        })
        
    # Write Products
    with open("data/products.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["product_id", "product_name", "category", "brand", "pack_size", "unit_price"])
        writer.writeheader()
        writer.writerows(products)
        
    # Write Regions
    with open("data/regions.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["region_id", "region_name", "state_group"])
        writer.writeheader()
        writer.writerows(regions)
        
    # Write Promotions
    with open("data/promotions.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["promotion_id", "promotion_name", "promotion_type", "discount_percentage", "start_date", "end_date", "product_id", "region_id"])
        writer.writeheader()
        writer.writerows(promotions)
        
    # 4. Generate Sales & Inventory
    sales_records = []
    inventory_records = []
    
    # Establish dynamic baseline for products
    # Product base units sold per day (e.g., P001 Cola might sell 100, P005 water sells 150, juice sells 40, energy sells 30, tea sells 50)
    base_sales = {
        "P001": 120, "P002": 80, "P003": 60, "P004": 50,
        "P005": 160, "P006": 90, "P007": 40,
        "P008": 45, "P009": 40, "P010": 30, "P011": 35,
        "P012": 50, "P013": 40, "P014": 30,
        "P015": 55, "P016": 55, "P017": 45, "P018": 25
    }
    
    # Establish seasonal multipliers by month (1 to 12 representing Jan to Dec)
    # Summer (Jun, Jul, Aug = 6,7,8) high for Carbonated, Water, Tea
    # Winter (Dec, Jan, Feb = 12,1,2) slightly lower for Carbonated, higher for some tea, lower for water
    seasonality = {
        "Carbonated Drinks": {1: 0.7, 2: 0.8, 3: 0.9, 4: 1.0, 5: 1.1, 6: 1.3, 7: 1.4, 8: 1.3, 9: 1.0, 10: 0.9, 11: 0.8, 12: 0.8},
        "Packaged Water":    {1: 0.6, 2: 0.7, 3: 0.9, 4: 1.1, 5: 1.2, 6: 1.4, 7: 1.5, 8: 1.4, 9: 1.1, 10: 0.9, 11: 0.7, 12: 0.6},
        "Fruit Juice":       {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0, 7: 1.0, 8: 1.0, 9: 1.1, 10: 1.1, 11: 1.0, 12: 1.0}, # Flat
        "Energy Drinks":     {1: 0.9, 2: 0.9, 3: 1.0, 4: 1.0, 5: 1.1, 6: 1.2, 7: 1.2, 8: 1.2, 9: 1.0, 10: 1.0, 11: 0.9, 12: 0.9},
        "Iced Tea":          {1: 0.6, 2: 0.7, 3: 0.9, 4: 1.1, 5: 1.2, 6: 1.4, 7: 1.4, 8: 1.3, 9: 1.0, 10: 0.8, 11: 0.7, 12: 0.6}
    }
    
    # Regional multiplier
    # South (R02) sells more classic products, North (R01) sells more tea, West (R04) sells more water and organic/juices
    regional_multiplier = {
        "R01": {"P001": 1.0, "P005": 0.9, "P008": 1.2, "P012": 1.0, "P015": 1.1},
        "R02": {"P001": 1.3, "P005": 1.1, "P008": 0.8, "P012": 1.1, "P015": 1.2},
        "R03": {"P001": 0.9, "P005": 1.0, "P008": 1.1, "P012": 0.9, "P015": 1.0},
        "R04": {"P001": 1.1, "P005": 1.3, "P008": 1.2, "P012": 1.2, "P015": 0.9},
        "R05": {"P001": 1.0, "P005": 1.0, "P008": 1.0, "P012": 1.0, "P015": 1.0}
    }
    
    # Steady growth product: P003 (Lemon Lime Fizz) grows 0.5% every week
    # Declining sales product: P018 (Matcha Iced Latte) drops 0.6% every week
    
    # Keep track of inventory levels for each product and region
    # Initialize inventory at start_date
    current_inventory = {}
    for p in products:
        for r in regions:
            current_inventory[(p["product_id"], r["region_id"])] = base_sales[p["product_id"]] * 10 # 10 days of base inventory
            
    sale_id = 1
    inventory_id = 1
    
    for dt in date_list:
        dt_str = dt.strftime("%Y-%m-%d")
        month = dt.month
        day_of_week = dt.weekday() # 0 = Monday, 6 = Sunday
        
        # We'll skip a few sales/inventory records to simulate missing records (approx 1% chance)
        skip_sales = random.random() < 0.01
        skip_inventory = random.random() < 0.01
        
        for p in products:
            p_id = p["product_id"]
            cat = p["category"]
            price = p["unit_price"]
            
            # Growth trend multipliers
            weeks_passed = (dt - start_date).days / 7.0
            trend_mult = 1.0
            if p_id == "P003":  # steady growth
                trend_mult = 1.0 + (weeks_passed * 0.005)
            elif p_id == "P018":  # declining sales
                trend_mult = max(0.2, 1.0 - (weeks_passed * 0.008))
                
            for r in regions:
                r_id = r["region_id"]
                
                # Check for promo
                active_promo_id = None
                promo_discount = 0.0
                is_overlap = False
                active_promos = []
                
                for pi in promo_intervals:
                    if pi["product_id"] == p_id and pi["region_id"] == r_id and pi["start"] <= dt <= pi["end"]:
                        active_promos.append(pi)
                
                if len(active_promos) > 1:
                    is_overlap = True
                    # If overlapping, we'll assign the first one but track overlap warning in the system
                    active_promo_id = active_promos[0]["id"]
                    # Total discount is combined but capped
                    promo_discount = min(40.0, sum(ap["discount"] for ap in active_promos))
                elif len(active_promos) == 1:
                    active_promo_id = active_promos[0]["id"]
                    promo_discount = active_promos[0]["discount"]
                
                # Base units calculation
                base = base_sales[p_id]
                seas = seasonality[cat][month]
                reg_mult = regional_multiplier.get(r_id, {}).get(p_id, 1.0)
                
                # Daily noise
                noise = random.uniform(0.85, 1.15)
                
                # Weekend effect (Saturdays and Sundays have 30% higher sales)
                weekend_mult = 1.3 if day_of_week in (5, 6) else 1.0
                
                # Calculate baseline units sold (without promo uplift)
                baseline_units = int(base * seas * reg_mult * weekend_mult * trend_mult * noise)
                if baseline_units < 1:
                    baseline_units = 1
                    
                # Promo Uplift factor
                uplift_mult = 1.0
                if active_promo_id:
                    if active_promo_id == "PROM05": # Bolt Energy Flash Sale (Underperforming campaign)
                        # Underperforms! Sells 15% fewer units than baseline (e.g. out of stock or negative reaction)
                        uplift_mult = 0.80
                    elif active_promo_id == "PROM07" or is_overlap:
                        # Overlap promo sells 1.4x baseline
                        uplift_mult = 1.40
                    else:
                        # Normal promo sells 1.5x to 1.8x baseline
                        uplift_mult = 1.0 + (promo_discount / 100.0) * 2.5 # e.g. 15% discount -> 1.375x
                
                units_sold = int(baseline_units * uplift_mult)
                
                # Sales Spikes (Anomalies)
                # Let's inject one significant sales spike (anomaly) for P001 Classic Cola in South (R02) on 2025-07-04 (Independence Day)
                if p_id == "P001" and r_id == "R02" and dt_str == "2025-07-04":
                    units_sold = units_sold * 4 # 4x spike
                # Let's inject a drop (inventory stockout anomaly) for P012 in South (R02) during PROM05: 2025-10-08 to 2025-10-10
                if p_id == "P012" and r_id == "R02" and "2025-10-08" <= dt_str <= "2025-10-10":
                    units_sold = 2 # stockout
                
                # Cap sold units by available inventory
                inv_key = (p_id, r_id)
                opening = current_inventory[inv_key]
                
                # Daily inventory receipt logic
                # Normally, we receive units to keep inventory around 7-10 days of base sales
                # Weekly restock or daily replenishment
                # Restock when inventory drops below 3 days of base sales
                received = 0
                if opening < base * 3:
                    received = int(base * 8 * random.uniform(0.9, 1.1))
                
                # Potential Stockout Case: P002 (Diet Cola) in West (R04) on 2026-02-15 to 2026-02-20
                # We stop receiving inventory
                if p_id == "P002" and r_id == "R04" and "2026-02-10" <= dt_str <= "2026-02-20":
                    received = 0
                    
                # Excess Inventory Case: P006 (Sparkling Water) in North (R01) gets massive received units in March
                if p_id == "P006" and r_id == "R01" and "2026-03-01" <= dt_str <= "2026-03-05":
                    received = int(base * 30) # 30x base received
                
                new_opening = opening + received
                
                # Verify stockout logic
                if units_sold > new_opening:
                    units_sold = new_opening # Sell all available
                    closing = 0
                else:
                    closing = new_opening - units_sold
                    
                current_inventory[inv_key] = closing
                
                # Calculate sales amount
                # Apply discount to unit price if promotion active
                net_price = price * (1.0 - (promo_discount / 100.0))
                sales_amount = round(units_sold * net_price, 2)
                
                # Create sales record
                if not skip_sales:
                    sales_records.append({
                        "sale_id": sale_id,
                        "sale_date": dt_str,
                        "product_id": p_id,
                        "region_id": r_id,
                        "units_sold": units_sold,
                        "sales_amount": sales_amount,
                        "promotion_id": active_promo_id if active_promo_id else ""
                    })
                    sale_id += 1
                
                # Create inventory record
                if not skip_inventory:
                    inventory_records.append({
                        "inventory_id": inventory_id,
                        "snapshot_date": dt_str,
                        "product_id": p_id,
                        "region_id": r_id,
                        "opening_inventory": opening,
                        "received_units": received,
                        "closing_inventory": closing
                    })
                    inventory_id += 1
                    
        # Let's inject a duplicate record for sales to simulate data quality issues (approx 0.05% chance of duplicating the last record)
        if len(sales_records) > 0 and random.random() < 0.0005:
            dup_rec = sales_records[-1].copy()
            # Change sale_id so it's a duplicate of content, not primary key
            dup_rec["sale_id"] = sale_id
            sales_records.append(dup_rec)
            sale_id += 1

    # Save Sales
    with open("data/sales.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sale_id", "sale_date", "product_id", "region_id", "units_sold", "sales_amount", "promotion_id"])
        writer.writeheader()
        writer.writerows(sales_records)
        
    # Save Inventory
    with open("data/inventory.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["inventory_id", "snapshot_date", "product_id", "region_id", "opening_inventory", "received_units", "closing_inventory"])
        writer.writeheader()
        writer.writerows(inventory_records)
        
    print(f"Data generation complete. Generated {len(products)} products, {len(regions)} regions, {len(promotions)} promotions, {len(sales_records)} sales rows, {len(inventory_records)} inventory rows.")

if __name__ == "__main__":
    generate_datasets()

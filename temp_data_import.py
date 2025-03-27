import csv
from datetime import datetime, timedelta
from models import Customer, Item, Order, OrderItem, db
from database import calculate_production_date, generate_subscription_orders
import uuid
import sys

def clean_database():
    """
    Delete all orders and order items from the database
    while preserving customers and items.
    """
    print("Cleaning the database...")
    with db.atomic():
        # Delete order items first (due to foreign key constraints)
        OrderItem.delete().execute()
        # Then delete orders
        Order.delete().execute()
    print("Database cleaned. All orders and order items have been deleted.")

def import_old_data(csv_filepath):
    """
    Import data from the old system's CSV file into the new database.
    
    CSV format:
    "Kunde","Item","Menge","Lieferdatum","Ansaehen","Woche_Wdh","Von","Bis","Preis"
    """
    # First clean the database
    clean_database()
    
    # Dictionary to cache customer and item objects
    customers_cache = {}
    items_cache = {}
    
    # Keep track of orders to avoid duplicates when multiple items are in the same order
    order_keys = {}  # key: (customer_name, delivery_date, subscription_type, from_date, to_date)
    
    # Open and read the CSV file
    print(f"Reading data from {csv_filepath}...")
    try:
        with open(csv_filepath, 'r', encoding='utf-8') as csvfile:
            # Use comma as delimiter (new format)
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            
            # Skip header row
            next(reader)
            
            # Start a transaction for better performance and atomicity
            with db.atomic():
                row_count = 0
                for row in reader:
                    row_count += 1
                    # Check if we have enough columns
                    if len(row) < 8:
                        print(f"Skipping row {row_count} with insufficient data: {row}")
                        continue
                    
                    # Extract data
                    customer_name = row[0].strip()
                    item_name = row[1].strip()
                    
                    # Convert amount from string with comma to float
                    try:
                        amount = float(row[2].replace(',', '.'))
                    except ValueError:
                        print(f"Invalid amount format in row {row_count}: {row}")
                        continue
                    
                    # Parse dates with explicit century adjustment
                    try:
                        # Parse delivery date (column 3)
                        delivery_date_str = row[3].strip()
                        if delivery_date_str:
                            try:
                                if len(delivery_date_str) == 10:  # DD.MM.YYYY format
                                    delivery_date = datetime.strptime(delivery_date_str, '%d.%m.%Y').date()
                                else:  # DD.MM.YY format
                                    delivery_date = datetime.strptime(delivery_date_str, '%d.%m.%y').date()
                                    # Adjust for centuries - assume 20xx for years < 50
                                    if delivery_date.year < 2000:
                                        delivery_date = delivery_date.replace(year=delivery_date.year + 100)
                            except ValueError:
                                # Try alternative format DD.MM.YYYY
                                delivery_date = datetime.strptime(delivery_date_str, '%d.%m.%Y').date()
                        else:
                            print(f"Missing delivery date in row {row_count}: {row}")
                            continue
                        
                        # Parse production/seeding date (column 4)
                        production_date = None
                        production_date_str = row[4].strip() if len(row) > 4 else ""
                        if production_date_str:
                            try:
                                if len(production_date_str) == 10:  # DD.MM.YYYY format
                                    production_date = datetime.strptime(production_date_str, '%d.%m.%Y').date()
                                else:  # DD.MM.YY format
                                    production_date = datetime.strptime(production_date_str, '%d.%m.%y').date()
                                    if production_date.year < 2000:
                                        production_date = production_date.replace(year=production_date.year + 100)
                            except ValueError:
                                print(f"Invalid production date format in row {row_count}: {production_date_str}")
                                # Not a critical error, will calculate later
                        
                        # Parse subscription type (column 5)
                        subscription_type = 0
                        if len(row) > 5 and row[5].strip():
                            try:
                                subscription_type = int(row[5].strip())
                            except ValueError:
                                print(f"Invalid subscription type in row {row_count}: {row[5]}")
                                subscription_type = 0
                        
                        # Parse from date for subscriptions (column 6)
                        from_date = None
                        if subscription_type > 0 and len(row) > 6 and row[6].strip():
                            from_date_str = row[6].strip()
                            try:
                                if len(from_date_str) == 10:  # DD.MM.YYYY format
                                    from_date = datetime.strptime(from_date_str, '%d.%m.%Y').date()
                                else:  # DD.MM.YY format
                                    from_date = datetime.strptime(from_date_str, '%d.%m.%y').date()
                                    if from_date.year < 2000:
                                        from_date = from_date.replace(year=from_date.year + 100)
                            except ValueError:
                                # Try alternative format
                                from_date = datetime.strptime(from_date_str, '%d.%m.%Y').date()
                        
                        # Parse to date for subscriptions (column 7)
                        to_date = None
                        if subscription_type > 0 and len(row) > 7 and row[7].strip():
                            to_date_str = row[7].strip()
                            try:
                                if len(to_date_str) == 10:  # DD.MM.YYYY format
                                    to_date = datetime.strptime(to_date_str, '%d.%m.%Y').date()
                                else:  # DD.MM.YY format
                                    to_date = datetime.strptime(to_date_str, '%d.%m.%y').date()
                                    if to_date.year < 2000:
                                        to_date = to_date.replace(year=to_date.year + 100)
                            except ValueError:
                                # Try alternative format
                                to_date = datetime.strptime(to_date_str, '%d.%m.%Y').date()
                        
                        # Debug output
                        print(f"Row {row_count}: Customer={customer_name}, Item={item_name}, Amount={amount}")
                        print(f"  Delivery={delivery_date}, Production={production_date}")
                        print(f"  Subscription: Type={subscription_type}, From={from_date}, To={to_date}")
                        
                    except ValueError as e:
                        print(f"Date parsing error in row {row_count} {row}: {e}")
                        continue
                    
                    # Get or create customer
                    if customer_name not in customers_cache:
                        try:
                            customer = Customer.get(Customer.name == customer_name)
                        except Customer.DoesNotExist:
                            print(f"Customer not found: {customer_name}. Creating new customer.")
                            customer = Customer.create(name=customer_name)
                        customers_cache[customer_name] = customer
                    else:
                        customer = customers_cache[customer_name]
                    
                    # Get item
                    if item_name not in items_cache:
                        try:
                            item = Item.get(Item.name == item_name)
                        except Item.DoesNotExist:
                            print(f"Item not found: {item_name}. Skipping row {row_count}.")
                            continue
                        items_cache[item_name] = item
                    else:
                        item = items_cache[item_name]
                    
                    # Create a unique key for this order to avoid duplicates
                    order_key = (customer_name, delivery_date, subscription_type, 
                                from_date, to_date)
                    
                    # Check if we already created this order
                    if order_key in order_keys:
                        order = order_keys[order_key]
                    else:
                        # Determine if this is a future order
                        is_future = delivery_date > datetime.now().date()
                        
                        # If production date wasn't provided, calculate it
                        if not production_date:
                            # For calculation, we need a temporary order item
                            temp_order_item = OrderItem(item=item, amount=amount)
                            production_date = calculate_production_date(delivery_date, [temp_order_item])
                        
                        # Create the order
                        order = Order.create(
                            customer=customer,
                            delivery_date=delivery_date,
                            production_date=production_date,
                            from_date=from_date,
                            to_date=to_date,
                            subscription_type=subscription_type,
                            halbe_channel=False,  # Default to False
                            order_id=uuid.uuid4(),
                            is_future=is_future
                        )
                        order_keys[order_key] = order
                    
                    # Create order item
                    OrderItem.create(
                        order=order,
                        item=item,
                        amount=amount
                    )
                    
                print(f"Imported {row_count} rows from CSV file.")
                
                # Now generate all subscription orders
                print("Generating subscription orders...")
                subscription_count = 0
                total_subscription_orders = 0
                
                # Process each order that has a subscription type > 0
                for order_key, order in order_keys.items():
                    if order.subscription_type > 0 and order.from_date and order.to_date:
                        print(f"Processing subscription order: {order.customer.name}, delivery: {order.delivery_date}, type: {order.subscription_type}")
                        
                        # Get all items for this order
                        items = list(order.order_items)
                        
                        # Verify we have valid from/to dates
                        if not order.from_date or not order.to_date:
                            print(f"Warning: Missing from_date or to_date for subscription order {order.id}, customer: {order.customer.name}")
                            continue
                            
                        # Generate future orders
                        future_orders = generate_subscription_orders(order)
                        print(f"Generated {len(future_orders)} future orders for {order.customer.name}")
                        total_subscription_orders += len(future_orders)
                        
                        for future_order_data in future_orders:
                            future_order = Order.create(
                                **future_order_data,
                                order_id=uuid.uuid4()
                            )
                            
                            # Copy items to future order
                            for item_data in items:
                                OrderItem.create(
                                    order=future_order,
                                    item=item_data.item,
                                    amount=item_data.amount
                                )
                            subscription_count += 1
                
                print(f"Generated {subscription_count} subscription orders out of {total_subscription_orders} expected.")
                
                # Count orders by delivery date to verify distribution
                delivery_date_counts = {}
                for order in Order.select():
                    date_str = order.delivery_date.strftime('%Y-%m-%d')
                    if date_str in delivery_date_counts:
                        delivery_date_counts[date_str] += 1
                    else:
                        delivery_date_counts[date_str] = 1
                
                print("Orders by delivery date:")
                for date_str, count in sorted(delivery_date_counts.items()):
                    print(f"  {date_str}: {count} orders")
                
        print("Import completed successfully!")
    except Exception as e:
        print(f"Error importing data: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    # Provide the path to your CSV file
    csv_path = "new_orders.csv"
    
    if import_old_data(csv_path):
        print("✅ Data migration completed successfully!")
    else:
        print("❌ Data migration failed.")
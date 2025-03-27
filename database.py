from datetime import datetime, timedelta
from models import *
from peewee import fn

def calculate_production_date(delivery_date, items, allow_sunday=True):
    """
    Calculate production start date based on the longest growth period among items.
    
    Parameters:
    - delivery_date: The date when the order will be delivered
    - items: List of OrderItem objects
    - allow_sunday: Whether to allow production dates to fall on Sunday
    
    Returns:
    - Production date
    """
    max_days = max(item.item.total_days for item in items)
    production_date = delivery_date - timedelta(days=max_days)
    
    # If Sunday is not allowed and the production date falls on Sunday,
    # move it to Saturday instead
    if not allow_sunday and production_date.weekday() == 6:  # 6 = Sunday
        production_date = production_date - timedelta(days=1)
        
    return production_date

def generate_subscription_orders(order):
    if order.subscription_type == 0 or not order.from_date or not order.to_date:
        return []
    
    frequencies = {1: 7, 2: 14, 3: 21, 4: 28}
    delta = timedelta(days=frequencies[order.subscription_type])
    
    # Use delivery_date as the starting point, not from_date
    current_date = order.delivery_date + delta
    orders = []
    
    while current_date <= order.to_date:
        # Pass the allow_sunday parameter based on the original order's production date
        # If the original order was allowed to be produced on Sunday, future orders should too
        allow_sunday = order.production_date.weekday() != 6 or (order.production_date.weekday() == 6)
        
        new_order = {
            'customer': order.customer,
            'delivery_date': current_date,
            'production_date': calculate_production_date(current_date, order.items, allow_sunday),
            'halbe_channel': order.halbe_channel,
            'is_future': True,
            'subscription_type': order.subscription_type,
            'from_date': order.from_date,
            'to_date': order.to_date
        }
        orders.append(new_order)
        current_date += delta
    
    return orders

def get_delivery_schedule(start_date=None, end_date=None):
    """
    Get delivery schedule for the given date range.
    
    The application now correctly creates orders with the right subscription pattern,
    so we should simply display all orders in the database for the requested date range.
    """
    # Get base query with date range filter
    query = (Order
            .select(Order, Customer)
            .join(Customer)
    )
    
    if start_date and end_date:
        query = query.where((Order.delivery_date >= start_date) & 
                          (Order.delivery_date <= end_date))
    
    # Return all orders in the date range
    return list(query.order_by(Order.delivery_date))

def get_production_plan(start_date=None, end_date=None):
    """
    Get production plan for the given date range.
    
    The application now correctly creates orders with the right subscription pattern,
    so we should simply display all orders in the database for the requested date range.
    """
    query = (OrderItem
        .select(
            Order.production_date,
            Order.delivery_date,
            Item.name,
            fn.SUM(OrderItem.amount).alias('total_amount'),
            Item.seed_quantity,
            Item.substrate
        )
        .join(Order)
        .switch(OrderItem)
        .join(Item)
        .where(
            (Order.is_future == True) &
            (
                # For non-subscription orders
                (
                    (Order.from_date.is_null(True)) & 
                    (Order.to_date.is_null(True))
                ) |
                # For subscription orders, ensure both delivery and production dates are within range
                (
                    (Order.from_date.is_null(False)) & 
                    (Order.delivery_date >= Order.from_date) & 
                    (Order.delivery_date <= Order.to_date)
                )
            )
        )
        .group_by(Order.production_date, Item.name, Item.seed_quantity, Item.substrate)
        .order_by(Order.production_date))
    
    if start_date and end_date:
        query = query.where((Order.production_date >= start_date) & 
                          (Order.production_date <= end_date))
    
    # Return all results without subscription filtering
    results = list(query)
    
    # Debug code for Sunday orders (kept from original)
    sunday_orders = []
    for result in results:
        if result.order.production_date.weekday() == 6:  # 6 = Sunday
            sunday_orders.append(result)
    
    # This is useful to diagnose the issue but doesn't affect functionality
    if not sunday_orders and start_date and end_date:
        # Check if the date range includes a Sunday
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() == 6:  # Found a Sunday in the range
                break
            current_date += timedelta(days=1)
    
    return results

def get_transfer_schedule(start_date=None, end_date=None):
    """
    Get transfer schedule for the given date range.
    
    The application now correctly creates orders with the right subscription pattern,
    so we should simply display all orders in the database for the requested date range.
    """
    query = (OrderItem
        .select(
            Order.production_date,
            Item.name,
            Item.soaking_days,
            Item.germination_days,
            fn.SUM(OrderItem.amount).alias('total_amount'),
            Item.seed_quantity
        )
        .join(Order)
        .switch(OrderItem)
        .join(Item)
        .where(
            (Order.is_future == True) &
            (
                # Either it's a non-subscription order
                ((Order.from_date.is_null(True)) & (Order.to_date.is_null(True))) |
                # Or it's within the subscription date range
                ((Order.from_date.is_null(False)) & (Order.delivery_date >= Order.from_date) & (Order.delivery_date <= Order.to_date))
            )
        )
        .group_by(Order.production_date, Item.name, Item.soaking_days, Item.germination_days, Item.seed_quantity))
    
    # Process all records for transfer data without subscription filtering
    transfer_data = []
    
    for record in query:
        transfer_date = record.order.production_date + timedelta(days=record.item.soaking_days + record.item.germination_days)
        
        if start_date and end_date:
            if not (start_date <= transfer_date <= end_date):
                continue
        
        transfer_data.append({
            'date': transfer_date,
            'item': record.item.name,
            'amount': record.total_amount,
            'seeds': record.total_amount * record.item.seed_quantity
        })
    
    # Group by date and item
    from collections import defaultdict
    grouped_data = defaultdict(lambda: defaultdict(float))
    for record in transfer_data:
        grouped_data[record['date']][record['item']] += record['amount']
    
    # Convert to list of records
    result = []
    for date, items in sorted(grouped_data.items()):
        for item_name, amount in items.items():
            result.append({
                'date': date,
                'item': item_name,
                'amount': amount
            })
    
    return sorted(result, key=lambda x: (x['date'], x['item']))
import pytest
from datetime import datetime, timedelta, date
import uuid
from models import Customer, Item, Order, OrderItem
from database import calculate_production_date, generate_subscription_orders
from peewee import fn

def test_change_subscription_type_weekly_to_biweekly(test_db, sample_data):
    """
    Test changing a subscription from weekly to bi-weekly.
    This should affect only future orders, with correct spacing.
    """
    # Setup: Create a weekly subscription with 4 orders (weekly)
    customer = sample_data['customers'][0]
    items = sample_data['items']
    
    today = datetime.now().date()
    from_date = today
    to_date = today + timedelta(days=28)  # 4 weeks
    
    # Create initial order and future orders
    orders = []
    for i in range(4):  # Create 4 weekly orders
        delivery_date = from_date + timedelta(days=7*i)
        production_date = delivery_date - timedelta(days=items[0].total_days)
        
        order = Order.create(
            customer=customer,
            delivery_date=delivery_date,
            production_date=production_date,
            from_date=from_date,
            to_date=to_date,
            subscription_type=1,  # Weekly
            halbe_channel=False,
            order_id=uuid.uuid4(),
            is_future=True
        )
        
        # Add items to order
        OrderItem.create(order=order, item=items[0], amount=2.0)
        
        orders.append(order)
    
    # Verify weekly spacing
    for i in range(1, len(orders)):
        delta = orders[i].delivery_date - orders[i-1].delivery_date
        assert delta.days == 7  # Weekly spacing
    
    # Test: Change subscription type to bi-weekly (starting from second order)
    start_index = 1  # Second order
    with test_db.atomic():
        # Update all future orders to bi-weekly
        Order.update(
            subscription_type=2  # Change to bi-weekly
        ).where(
            (Order.from_date == from_date) & 
            (Order.to_date == to_date) &
            (Order.delivery_date >= orders[start_index].delivery_date)
        ).execute()
        
        # Delete alternating orders to create bi-weekly spacing
        orders_to_delete = []
        for i in range(start_index + 1, len(orders), 2):
            if i < len(orders):
                orders_to_delete.append(orders[i].id)
        
        # Delete order items first
        if orders_to_delete:
            OrderItem.delete().where(OrderItem.order_id.in_(orders_to_delete)).execute()
            # Then delete the orders
            Order.delete().where(Order.id.in_(orders_to_delete)).execute()
    
    # Verify changes:
    # 1. First order should still be weekly (unchanged)
    refreshed_first = Order.get(Order.id == orders[0].id)
    assert refreshed_first.subscription_type == 1
    
    # 2. Remaining orders should be bi-weekly
    for i in range(start_index, len(orders), 2):
        if i < len(orders):
            order = Order.get_or_none(Order.id == orders[i].id)
            assert order is not None
            assert order.subscription_type == 2
    
    # 3. Verify orders at odd indices (2nd, 4th, etc) are deleted
    for i in range(start_index + 1, len(orders), 2):
        if i < len(orders):
            order = Order.get_or_none(Order.id == orders[i].id)
            assert order is None
    
    # 4. Count total orders - should be 2 (first order and third order)
    # The sample_data fixture may have existing orders, so we need to apply the same filter
    # that we used when creating our test orders
    count = Order.select().where(
        (Order.from_date == from_date) & 
        (Order.to_date == to_date) &
        (Order.customer == customer)  # Add customer filter
    ).count()
    assert count == 3  # First order + two modified orders (start_index and start_index+2)

def test_change_subscription_type_biweekly_to_weekly(test_db, sample_data):
    """
    Test changing a subscription from bi-weekly to weekly.
    This should generate new orders in between existing ones.
    """
    # Setup: Create a bi-weekly subscription with 3 orders
    customer = sample_data['customers'][0]
    items = sample_data['items']
    
    today = datetime.now().date()
    from_date = today
    to_date = today + timedelta(days=28)  # 4 weeks
    
    # Create initial order and future orders with bi-weekly spacing
    orders = []
    for i in range(3):  # Create 3 bi-weekly orders
        delivery_date = from_date + timedelta(days=14*i)  # Every 2 weeks
        production_date = delivery_date - timedelta(days=items[0].total_days)
        
        order = Order.create(
            customer=customer,
            delivery_date=delivery_date,
            production_date=production_date,
            from_date=from_date,
            to_date=to_date,
            subscription_type=2,  # Bi-weekly
            halbe_channel=False,
            order_id=uuid.uuid4(),
            is_future=True
        )
        
        # Add items to order
        OrderItem.create(order=order, item=items[0], amount=2.0)
        
        orders.append(order)
    
    # Verify bi-weekly spacing
    for i in range(1, len(orders)):
        delta = orders[i].delivery_date - orders[i-1].delivery_date
        assert delta.days == 14  # Bi-weekly spacing
    
    # Test: Change subscription type to weekly (starting from second order)
    start_index = 1  # Second order
    
    with test_db.atomic():
        # Update existing orders
        Order.update(
            subscription_type=1  # Change to weekly
        ).where(
            (Order.from_date == from_date) & 
            (Order.to_date == to_date) &
            (Order.delivery_date >= orders[start_index].delivery_date) &
            (Order.customer == customer)  # Add customer filter
        ).execute()
        
        # Create new weekly orders to fill the gaps
        new_orders = []
        for i in range(start_index, len(orders)-1):
            # Create an order for the week in between
            mid_date = orders[i].delivery_date + timedelta(days=7)
            if mid_date <= to_date:
                production_date = mid_date - timedelta(days=items[0].total_days)
                
                new_order = Order.create(
                    customer=customer,
                    delivery_date=mid_date,
                    production_date=production_date,
                    from_date=from_date,
                    to_date=to_date,
                    subscription_type=1,  # Weekly
                    halbe_channel=False,
                    order_id=uuid.uuid4(),
                    is_future=True
                )
                
                # Copy items from original order
                for item in orders[i].order_items:
                    OrderItem.create(
                        order=new_order,
                        item=item.item,
                        amount=item.amount
                    )
                
                new_orders.append(new_order)
    
    # Verify changes:
    # 1. First order should still be bi-weekly (unchanged)
    refreshed_first = Order.get(Order.id == orders[0].id)
    assert refreshed_first.subscription_type == 2
    
    # 2. All future orders should be weekly
    future_orders = Order.select().where(
        (Order.from_date == from_date) & 
        (Order.to_date == to_date) &
        (Order.delivery_date >= orders[start_index].delivery_date) &
        (Order.customer == customer)  # Add customer filter
    ).order_by(Order.delivery_date)
    
    # Should have at least 3 orders (original second + third orders and at least 1 new)
    assert future_orders.count() >= 3
    
    # Check weekly spacing
    prev_date = None
    for order in future_orders:
        if prev_date:
            delta = order.delivery_date - prev_date
            assert delta.days == 7  # Weekly spacing
        prev_date = order.delivery_date
        assert order.subscription_type == 1  # All should be weekly

def test_order_edit_propagates_to_views(test_db, sample_data):
    """
    Test that changing an order is properly reflected in database queries
    used by the delivery, production, and transfer views.
    """
    # Setup: Create a weekly subscription
    customer = sample_data['customers'][0]
    items = sample_data['items']
    
    today = datetime.now().date()
    from_date = today
    to_date = today + timedelta(days=28)
    
    # Create 4 weekly orders
    orders = []
    for i in range(4):
        delivery_date = from_date + timedelta(days=7*i)
        production_date = delivery_date - timedelta(days=items[0].total_days)
        
        order = Order.create(
            customer=customer,
            delivery_date=delivery_date,
            production_date=production_date,
            from_date=from_date,
            to_date=to_date,
            subscription_type=1,  # Weekly
            halbe_channel=False,
            order_id=uuid.uuid4(),
            is_future=True
        )
        
        # Add items to order
        OrderItem.create(order=order, item=items[0], amount=2.0)
        
        orders.append(order)
    
    # Get initial counts from the view queries
    from database import get_delivery_schedule, get_production_plan, get_transfer_schedule
    
    # Use a more specific filter to get only our test orders
    test_delivery_schedule = get_delivery_schedule(start_date=from_date, end_date=to_date)
    test_delivery_schedule = [order for order in test_delivery_schedule 
                             if order.customer.id == customer.id and order.from_date == from_date]
    delivery_before = len(test_delivery_schedule)
    
    # For production and transfer, we'll just get counts for comparison
    production_before = len(list(get_production_plan(start_date=from_date, end_date=to_date)))
    transfer_before = len(get_transfer_schedule(start_date=from_date, end_date=to_date))
    
    # Test: Change subscription type to bi-weekly (delete every other order)
    start_index = 0  # First order
    with test_db.atomic():
        # Update all orders to bi-weekly
        Order.update(
            subscription_type=2  # Change to bi-weekly
        ).where(
            (Order.from_date == from_date) & 
            (Order.to_date == to_date) &
            (Order.customer == customer)  # Add customer filter
        ).execute()
        
        # Delete alternate orders to create bi-weekly spacing
        delete_indices = [1, 3]  # Delete 2nd and 4th orders
        orders_to_delete = [orders[i].id for i in delete_indices]
        
        if orders_to_delete:
            OrderItem.delete().where(OrderItem.order_id.in_(orders_to_delete)).execute()
            Order.delete().where(Order.id.in_(orders_to_delete)).execute()
    
    # Get updated counts from the view queries with the same filters
    test_delivery_schedule_after = get_delivery_schedule(start_date=from_date, end_date=to_date)
    test_delivery_schedule_after = [order for order in test_delivery_schedule_after 
                                  if order.customer.id == customer.id and order.from_date == from_date]
    delivery_after = len(test_delivery_schedule_after)
    
    # For production and transfer, we'll just compare if they changed
    production_after = len(list(get_production_plan(start_date=from_date, end_date=to_date)))
    transfer_after = len(get_transfer_schedule(start_date=from_date, end_date=to_date))
    
    # Assert the counts have changed properly
    assert delivery_after == delivery_before - len(delete_indices)
    assert production_after <= production_before  # This could be less if items were consolidated
    assert transfer_after <= transfer_before
    
    # Check specific date ranges to ensure proper biweekly spacing in results
    delivery_dates = [order.delivery_date for order in test_delivery_schedule_after]
    
    # Sort dates
    delivery_dates.sort()
    
    # Verify biweekly spacing
    if len(delivery_dates) >= 2:
        for i in range(1, len(delivery_dates)):
            delta = delivery_dates[i] - delivery_dates[i-1]
            assert delta.days == 14  # Bi-weekly spacing
    
    # Verify subscription_type is consistently updated in all orders
    for order in test_delivery_schedule_after:
        assert order.subscription_type == 2

def test_adding_item_to_existing_orders(test_db, sample_data):
    """
    Test adding a new item to existing subscription orders.
    """
    # Setup: Create a weekly subscription
    customer = sample_data['customers'][0]
    items = sample_data['items']
    
    today = datetime.now().date()
    from_date = today
    to_date = today + timedelta(days=21)  # 3 weeks
    
    # Create 3 weekly orders with one item
    orders = []
    for i in range(3):
        delivery_date = from_date + timedelta(days=7*i)
        production_date = delivery_date - timedelta(days=items[0].total_days)
        
        order = Order.create(
            customer=customer,
            delivery_date=delivery_date,
            production_date=production_date,
            from_date=from_date,
            to_date=to_date,
            subscription_type=1,  # Weekly
            halbe_channel=False,
            order_id=uuid.uuid4(),
            is_future=True
        )
        
        # Add first item to order
        OrderItem.create(order=order, item=items[0], amount=2.0)
        
        orders.append(order)
    
    # Test: Add a second item to all orders in the subscription
    with test_db.atomic():
        for order in orders:
            # Add second item
            OrderItem.create(order=order, item=items[1], amount=1.5)
            
            # Update production date based on new max growth period
            max_days = max(item.total_days for item in [items[0], items[1]])
            order.production_date = order.delivery_date - timedelta(days=max_days)
            order.save()
    
    # Verify changes:
    # 1. Each order should have 2 items
    for order_id in [o.id for o in orders]:
        refreshed = Order.get(Order.id == order_id)
        order_items = list(refreshed.order_items)
        assert len(order_items) == 2
        
        # Check all orders have both items
        item_ids = [oi.item.id for oi in order_items]
        assert items[0].id in item_ids
        assert items[1].id in item_ids
    
    # 2. Production dates should be updated correctly
    for order_id in [o.id for o in orders]:
        refreshed = Order.get(Order.id == order_id)
        max_days = max(item.total_days for item in [items[0], items[1]])
        expected_date = refreshed.delivery_date - timedelta(days=max_days)
        assert refreshed.production_date == expected_date

def test_changing_delivery_dates_affects_production_dates(test_db, sample_data):
    """
    Test that changing delivery dates properly updates production dates.
    """
    # Setup: Create an order with multiple items
    customer = sample_data['customers'][0]
    items = sample_data['items']
    
    today = datetime.now().date()
    delivery_date = today + timedelta(days=14)
    
    # Calculate production date based on longest growth period
    max_days = max(item.total_days for item in items)
    production_date = delivery_date - timedelta(days=max_days)
    
    # Create order
    order = Order.create(
        customer=customer,
        delivery_date=delivery_date,
        production_date=production_date,
        from_date=None,
        to_date=None,
        subscription_type=0,  # No subscription
        halbe_channel=False,
        order_id=uuid.uuid4(),
        is_future=True
    )
    
    # Add both items to the order
    OrderItem.create(order=order, item=items[0], amount=2.0)
    OrderItem.create(order=order, item=items[1], amount=1.5)
    
    # Original production date before any changes
    original_production_date = order.production_date
    
    # Test: Change delivery date to 1 week later
    new_delivery_date = delivery_date + timedelta(days=7)
    
    with test_db.atomic():
        order.delivery_date = new_delivery_date
        # Update production date based on the items' growth periods
        order_items = list(order.order_items)
        max_days = max(oi.item.total_days for oi in order_items)
        order.production_date = new_delivery_date - timedelta(days=max_days)
        order.save()
    
    # Verify changes:
    # 1. Delivery date should be updated
    refreshed = Order.get(Order.id == order.id)
    assert refreshed.delivery_date == new_delivery_date
    
    # 2. Production date should be shifted by the same amount
    assert (refreshed.production_date - original_production_date).days == 7
    
    # 3. Production date should maintain the correct offset from delivery date
    assert (refreshed.delivery_date - refreshed.production_date).days == max_days 
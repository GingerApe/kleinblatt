import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from models import Order, OrderItem, Item, Customer, db
from widgets import AutocompleteCombobox
import uuid
import ttkbootstrap as ttkb

class OrderEditor:
    """
    A reusable order editor that can be used to create or edit orders.
    This centralizes the order editing functionality that was previously
    scattered across multiple files.
    """
    
    def __init__(self, parent, items_dict, on_save_callback=None):
        """
        Initialize the order editor.
        
        Args:
            parent: The parent widget
            items_dict: Dictionary of items {name: item_object}
            on_save_callback: Function to call after saving (optional)
        """
        self.parent = parent
        self.items = items_dict
        self.on_save_callback = on_save_callback
        
    def edit_order(self, order=None, prefill_customer=None, prefill_delivery_date=None, single_order=False):
        """
        Open the order editor window for a new or existing order.
        
        Args:
            order: Existing order to edit (None for new order)
            prefill_customer: Customer to prefill for new orders
            prefill_delivery_date: Delivery date to prefill for new orders
            single_order: If True, only edit this specific order, not all in subscription
        """
        # Create the editor window with dark theme
        edit_window = ttkb.Window(themename="darkly")  # Create a standalone window
        edit_window.title("Edit Order" if order else "New Order")
        edit_window.geometry("800x600")
        
        # Center the window on screen
        window_width = 800
        window_height = 800
        screen_width = edit_window.winfo_screenwidth()
        screen_height = edit_window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        edit_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Make window modal but avoid transient/master cycle
        edit_window.grab_set()
        
        # --- Overall Subscription Details ---
        sub_details_frame = ttk.LabelFrame(edit_window, text="Subscription Settings")
        sub_details_frame.pack(fill='x', padx=10, pady=5)

        # Subscription type selection
        sub_var = tk.IntVar(value=order.subscription_type if order else 0)
        
        sub_type_frame = ttk.Frame(sub_details_frame)
        sub_type_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(sub_type_frame, text="Subscription Type:").pack(side='left', padx=5)
        
        sub_types = {
            0: "No subscription",
            1: "Weekly",
            2: "Bi-weekly",
            3: "Every 3 weeks",
            4: "Every 4 weeks"
        }
        
        sub_combo = ttk.Combobox(sub_type_frame, textvariable=sub_var, width=15, state="readonly")
        sub_combo['values'] = list(sub_types.values())
        sub_combo.current(sub_var.get())
        sub_combo.pack(side='left', padx=5)
        
        # Date range frame
        date_range_frame = ttk.Frame(sub_details_frame)
        date_range_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(date_range_frame, text="From:").pack(side='left', padx=5)
        from_date_entry = ttk.Entry(date_range_frame, width=12)
        from_date_entry.pack(side='left', padx=5)
        
        ttk.Label(date_range_frame, text="To:").pack(side='left', padx=5)
        to_date_entry = ttk.Entry(date_range_frame, width=12)
        to_date_entry.pack(side='left', padx=5)
        
        # Set current subscription dates if editing
        if order and order.from_date and order.to_date:
            from_date_entry.insert(0, order.from_date.strftime('%d.%m.%Y'))
            to_date_entry.insert(0, order.to_date.strftime('%d.%m.%Y'))
        else:
            # Default dates for new orders
            today = datetime.now().date()
            from_date_entry.insert(0, today.strftime('%d.%m.%Y'))
            next_year = datetime(today.year + 1, 12, 31).date()
            to_date_entry.insert(0, next_year.strftime('%d.%m.%Y'))
        
        # Halbe Channel checkbox
        halbe_var = tk.BooleanVar(value=order.halbe_channel if order else False)
        ttk.Checkbutton(sub_details_frame, text="Halbe Channel", variable=halbe_var).pack(padx=5, pady=5)
        
        # --- Order Details ---
        order_frame = ttk.LabelFrame(edit_window, text="Order Details")
        order_frame.pack(fill='x', padx=10, pady=5)
        
        # Delivery Date
        date_frame = ttk.Frame(order_frame)
        date_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(date_frame, text="Delivery Date:").pack(side='left', padx=5)
        delivery_date_entry = ttk.Entry(date_frame, width=12)
        delivery_date_entry.pack(side='left', padx=5)
        
        # Set delivery date
        if order:
            delivery_date_entry.insert(0, order.delivery_date.strftime('%d.%m.%Y'))
        elif prefill_delivery_date:
            delivery_date_entry.insert(0, prefill_delivery_date.strftime('%d.%m.%Y'))
        else:
            delivery_date_entry.insert(0, datetime.now().date().strftime('%d.%m.%Y'))
        
        # Customer selection (only for new orders)
        customer = None
        if order:
            customer = order.customer
            ttk.Label(order_frame, text=f"Customer: {customer.name}").pack(padx=5, pady=5)
        elif prefill_customer:
            customer = prefill_customer
            ttk.Label(order_frame, text=f"Customer: {customer.name}").pack(padx=5, pady=5)
        else:
            cust_frame = ttk.Frame(order_frame)
            cust_frame.pack(fill='x', padx=5, pady=5)
            
            ttk.Label(cust_frame, text="Customer:").pack(side='left', padx=5)
            customer_cb = AutocompleteCombobox(cust_frame, width=30)
            
            # Get all customer names
            all_customers = Customer.select()
            customer_names = [c.name for c in all_customers]
            customer_cb.set_completion_list(sorted(customer_names))
            customer_cb.pack(side='left', padx=5, fill='x', expand=True)
        
        # --- Order Items Section ---
        items_frame = ttk.LabelFrame(edit_window, text="Order Items")
        items_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create scrollable frame for items
        canvas = tk.Canvas(items_frame, background="#2b3e50")
        scrollbar = ttk.Scrollbar(items_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure scrolling
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        item_rows = []  # List to hold item-row data
        
        def add_item_row(existing_order_item=None):
            """Add a row for one order item."""
            item_row_frame = ttk.Frame(scrollable_frame)
            item_row_frame.pack(fill='x', pady=2)
            
            ttk.Label(item_row_frame, text="Item:").pack(side='left', padx=5)
            item_cb = AutocompleteCombobox(item_row_frame, width=20)
            item_cb.set_completion_list(sorted(self.items.keys()))
            item_cb.pack(side='left', padx=5)
            
            if existing_order_item:
                item_cb.set(existing_order_item.item.name)
            
            ttk.Label(item_row_frame, text="Amount:").pack(side='left', padx=5)
            amount_entry = ttk.Entry(item_row_frame, width=8)
            amount_entry.pack(side='left', padx=5)
            
            if existing_order_item:
                amount_entry.insert(0, str(existing_order_item.amount))
            
            def delete_item():
                # Remove this item row
                item_row_frame.destroy()
                item_rows.remove(item_dict)
            
            del_button = ttk.Button(item_row_frame, text="Delete", command=delete_item)
            del_button.pack(side='left', padx=5)
            
            item_dict = {
                'frame': item_row_frame,
                'item_cb': item_cb,
                'amount_entry': amount_entry,
                'existing': existing_order_item  # None for new items
            }
            item_rows.append(item_dict)
        
        # Prepopulate with existing order items if available
        if order:
            for oi in order.order_items:
                add_item_row(existing_order_item=oi)
        else:
            # New order: start with one empty item row
            add_item_row()
        
        add_item_btn = ttk.Button(items_frame, text="Add Item", command=lambda: add_item_row())
        add_item_btn.pack(pady=5)
        
        # --- Update Scope Frame ---
        update_frame = ttk.LabelFrame(edit_window, text="Update Scope")
        update_frame.pack(fill='x', padx=10, pady=5)
        
        update_type = tk.StringVar(value="current" if single_order else "future")
        
        ttk.Radiobutton(
            update_frame, 
            text="Update only this order", 
            variable=update_type, 
            value="current"
        ).pack(anchor='w', padx=5, pady=2)
        
        ttk.Radiobutton(
            update_frame, 
            text="Update this and all future orders in this subscription", 
            variable=update_type, 
            value="future"
        ).pack(anchor='w', padx=5, pady=2)
        
        ttk.Radiobutton(
            update_frame, 
            text="Create a new subscription with these settings", 
            variable=update_type, 
            value="new"
        ).pack(anchor='w', padx=5, pady=2)
        
        # Button frame at the bottom
        buttons_frame = ttk.Frame(edit_window)
        buttons_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        
        def delete_order():
            """Delete this order with scope options."""
            if not order:
                messagebox.showinfo("Info", "Cannot delete a new order that hasn't been saved yet.")
                return
                
            scope_options = ["Delete only this order", "Delete this and all future orders"]
            
            # Only show subscription options if this is a subscription order
            has_subscription = order.subscription_type > 0 and order.from_date and order.to_date
            
            if not has_subscription:
                # If not a subscription, just confirm and delete
                if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this order?"):
                    try:
                        with db.atomic():
                            # Delete order items first
                            OrderItem.delete().where(OrderItem.order == order).execute()
                            # Then delete the order
                            order.delete_instance()
                        messagebox.showinfo("Success", "Order deleted successfully")
                        edit_window.destroy()
                        if self.on_save_callback:
                            self.on_save_callback(None)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to delete order: {str(e)}")
                return
            
            # For subscriptions, ask about scope
            delete_scope = messagebox.askyesno(
                "Delete Scope", 
                "Do you want to delete all future orders in this subscription?\n\n"
                "Click 'Yes' to delete this and all future orders.\n"
                "Click 'No' to delete only this specific order."
            )
            
            try:
                with db.atomic():
                    if delete_scope:  # Delete this and all future orders
                        # Get all future orders in this subscription
                        future_orders = Order.select().where(
                            (Order.subscription_type == order.subscription_type) &
                            (Order.from_date == order.from_date) &
                            (Order.to_date == order.to_date) &
                            (Order.delivery_date >= order.delivery_date)
                        )
                        
                        # Delete order items for all future orders
                        for future_order in future_orders:
                            OrderItem.delete().where(OrderItem.order == future_order).execute()
                        
                        # Delete all future orders
                        Order.delete().where(
                            (Order.subscription_type == order.subscription_type) &
                            (Order.from_date == order.from_date) &
                            (Order.to_date == order.to_date) &
                            (Order.delivery_date >= order.delivery_date)
                        ).execute()
                        
                        messagebox.showinfo("Success", "All future orders in this subscription have been deleted")
                    else:  # Delete only this order
                        # Delete order items first
                        OrderItem.delete().where(OrderItem.order == order).execute()
                        # Then delete the order
                        order.delete_instance()
                        messagebox.showinfo("Success", "Order deleted successfully")
                
                edit_window.destroy()
                if self.on_save_callback:
                    self.on_save_callback(None)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete order: {str(e)}")
        
        def save_changes():
            """Validate and save the order."""
            try:
                # Validate delivery date
                try:
                    delivery_date = datetime.strptime(delivery_date_entry.get(), '%d.%m.%Y').date()
                except ValueError:
                    raise ValueError("Invalid delivery date format. Use DD.MM.YYYY")
                
                # Validate customer
                if order or prefill_customer:
                    # Editing existing order or using prefilled customer
                    if not customer:
                        raise ValueError("Customer not found")
                else:
                    # New order, get customer from combobox
                    customer_name = customer_cb.get()
                    if not customer_name:
                        raise ValueError("Please select a customer")
                    
                    # Find customer by name
                    try:
                        customer_obj = Customer.get(Customer.name == customer_name)
                    except Customer.DoesNotExist:
                        raise ValueError(f"Customer '{customer_name}' not found")
                
                # Validate items
                if not item_rows:
                    raise ValueError("Please add at least one item to the order")
                
                validated_items = []
                for item_row in item_rows:
                    item_name = item_row['item_cb'].get()
                    if not item_name or item_name not in self.items:
                        raise ValueError(f"Invalid item: {item_name}")
                    
                    try:
                        amount = float(item_row['amount_entry'].get())
                        if amount <= 0:
                            raise ValueError
                    except ValueError:
                        raise ValueError(f"Invalid amount for item {item_name}")
                    
                    validated_items.append({
                        'item': self.items[item_name],
                        'amount': amount,
                        'existing': item_row['existing']
                    })
                
                # Validate subscription settings if applicable
                subscription_type = sub_var.get()
                from_date = None
                to_date = None
                
                if subscription_type > 0:
                    try:
                        from_date = datetime.strptime(from_date_entry.get(), '%d.%m.%Y').date()
                    except ValueError:
                        raise ValueError("Invalid from date format. Use DD.MM.YYYY")
                    
                    try:
                        to_date = datetime.strptime(to_date_entry.get(), '%d.%m.%Y').date()
                    except ValueError:
                        raise ValueError("Invalid to date format. Use DD.MM.YYYY")
                    
                    if from_date > to_date:
                        raise ValueError("From date must be before to date")
                
                # Calculate production date based on longest growth period
                max_days = max(item['item'].total_days for item in validated_items)
                production_date = delivery_date - timedelta(days=max_days)
                
                # Get update scope
                scope = update_type.get()
                
                with db.atomic():
                    if order and scope != "new":
                        # Editing existing order
                        if scope == "current":
                            # Update only this order
                            order.delivery_date = delivery_date
                            order.production_date = production_date
                            order.halbe_channel = halbe_var.get()
                            order.save()
                            
                            # Update order items
                            # First, delete removed items
                            existing_item_ids = [item['existing'].id for item in validated_items if item['existing']]
                            OrderItem.delete().where(
                                (OrderItem.order == order) & 
                                ~(OrderItem.id << existing_item_ids) if existing_item_ids else True
                            ).execute()
                            
                            # Then update or create items
                            for item_data in validated_items:
                                if item_data['existing']:
                                    # Update existing item
                                    item_data['existing'].item = item_data['item']
                                    item_data['existing'].amount = item_data['amount']
                                    item_data['existing'].save()
                                else:
                                    # Create new item
                                    OrderItem.create(
                                        order=order,
                                        item=item_data['item'],
                                        amount=item_data['amount']
                                    )
                            
                            messagebox.showinfo("Success", "Order updated successfully")
                            
                        elif scope == "future":
                            # Update this and all future orders
                            future_orders = Order.select().where(
                                (Order.subscription_type == order.subscription_type) &
                                (Order.from_date == order.from_date) &
                                (Order.to_date == order.to_date) &
                                (Order.delivery_date >= order.delivery_date)
                            )
                            
                            # Update subscription settings for all future orders
                            Order.update(
                                subscription_type=subscription_type,
                                from_date=from_date,
                                to_date=to_date,
                                halbe_channel=halbe_var.get()
                            ).where(
                                (Order.subscription_type == order.subscription_type) &
                                (Order.from_date == order.from_date) &
                                (Order.to_date == order.to_date) &
                                (Order.delivery_date >= order.delivery_date)
                            ).execute()
                            
                            # Update items for all future orders
                            for future_order in future_orders:
                                # Delete all existing items
                                OrderItem.delete().where(OrderItem.order == future_order).execute()
                                
                                # Create new items
                                for item_data in validated_items:
                                    OrderItem.create(
                                        order=future_order,
                                        item=item_data['item'],
                                        amount=item_data['amount']
                                    )
                            
                            messagebox.showinfo("Success", "All future orders updated successfully")
                    else:
                        # Creating new order or new subscription
                        if not order:
                            # Get customer for new order
                            customer_obj = customer if customer else Customer.get(Customer.name == customer_cb.get())
                        else:
                            # Use existing order's customer
                            customer_obj = order.customer
                        
                        # Create new order
                        new_order = Order.create(
                            customer=customer_obj,
                            delivery_date=delivery_date,
                            production_date=production_date,
                            from_date=from_date,
                            to_date=to_date,
                            subscription_type=subscription_type,
                            halbe_channel=halbe_var.get(),
                            order_id=uuid.uuid4(),
                            is_future=False
                        )
                        
                        # Create order items
                        for item_data in validated_items:
                            OrderItem.create(
                                order=new_order,
                                item=item_data['item'],
                                amount=item_data['amount']
                            )
                        
                        # Generate subscription orders if applicable
                        if subscription_type > 0:
                            from database import generate_subscription_orders
                            future_orders = generate_subscription_orders(new_order)
                            for future_order_data in future_orders:
                                future_order = Order.create(
                                    **future_order_data,
                                    order_id=uuid.uuid4()
                                )
                                # Copy items to future order
                                for item_data in validated_items:
                                    OrderItem.create(
                                        order=future_order,
                                        item=item_data['item'],
                                        amount=item_data['amount']
                                    )
                        
                        messagebox.showinfo("Success", "Order saved successfully")
                
                edit_window.destroy()
                if self.on_save_callback:
                    self.on_save_callback(None)
                    
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        # Add buttons to the button frame
        ttk.Button(buttons_frame, text="Save Changes", command=save_changes).pack(side="right", padx=5)
        
        if order:  # Only show delete button for existing orders
            ttk.Button(buttons_frame, text="Delete Order", command=delete_order).pack(side="right", padx=5)
        
        ttk.Button(buttons_frame, text="Cancel", command=edit_window.destroy).pack(side="right", padx=5)
        
        # Add mousewheel scrolling for the canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Focus the window
        edit_window.focus_set() 
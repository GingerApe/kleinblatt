import os
from datetime import datetime, timedelta, date
from fpdf import FPDF
from models import Order, OrderItem, Item, Customer
from peewee import *
import tkinter as tk
from tkinter import messagebox
from collections import defaultdict

class SchedulePrinter:
    def __init__(self):
        self.output_dir = "output"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _create_header(self, pdf, title, week_date):
        pdf.set_font('Arial', 'B', 20)
        pdf.cell(0, 10, title, 0, 1, 'C')
        
        # Week information
        pdf.set_font('Arial', '', 12)
        monday = week_date - timedelta(days=week_date.weekday())
        sunday = monday + timedelta(days=6)
        pdf.cell(0, 10, f'Woche: {monday.strftime("%d.%m.%Y")} - {sunday.strftime("%d.%m.%Y")}', 0, 1, 'C')
        pdf.ln(5)

    def _add_weekly_plan_table(self, pdf, data_by_day, week_date):
        """
        Creates a weekly plan table with 7 groups (one per day: Monday to Sunday).
        Each day group has two subcolumns: "Item" and "Menge" (amount).
        The data_by_day dictionary is expected to have keys as dates (in "%d.%m.%Y") and values as dictionaries
        mapping item names to either an amount (for transfers) or a dict containing "amount" (for production).
        """
        # Calculate widths (assume a 10-unit margin on each side)
        available_width = pdf.w - 20
        day_width = available_width / 7
        subcol_width = day_width / 2

        # German day names
        german_days = {
            0: "Montag",
            1: "Dienstag",
            2: "Mittwoch", 
            3: "Donnerstag",
            4: "Freitag",
            5: "Samstag",
            6: "Sonntag"
        }

        # Header row: Day name and date (merged cell per day)
        pdf.set_font("Arial", "B", 12)
        header_height = 10
        monday = week_date - timedelta(days=week_date.weekday())
        for i in range(7):
            day_date = monday + timedelta(days=i)
            day_text = f"{german_days[i]} ({day_date.strftime('%d.%m')})"
            pdf.cell(day_width, header_height, day_text, border=1, align="C")
        pdf.ln(header_height)

        # Subheader row: "Item" and "Menge" for each day
        pdf.set_font("Arial", "", 10)
        subheader_height = 7
        for i in range(7):
            pdf.cell(subcol_width, subheader_height, "Item", border=1, align="C")
            pdf.cell(subcol_width, subheader_height, "Menge", border=1, align="C")
        pdf.ln(subheader_height)

        # Prepare data for each day in order
        days_data = []
        max_rows = 0
        for i in range(7):
            day_date = monday + timedelta(days=i)
            date_str = day_date.strftime("%d.%m.%Y")
            if date_str in data_by_day:
                day_dict = data_by_day[date_str]
                # Convert each day's dictionary into a list of (item, amount) tuples.
                day_items = []
                for item, value in day_dict.items():
                    if isinstance(value, dict):
                        # Production schedule: value is a dict with 'amount'
                        day_items.append((item, str(value["amount"])))
                    else:
                        # Transfer schedule: value is the amount
                        day_items.append((item, str(value)))
                days_data.append(day_items)
                if len(day_items) > max_rows:
                    max_rows = len(day_items)
            else:
                days_data.append([])

        # Print rows for each day side-by-side
        row_height = 7
        for row in range(max_rows):
            for day_items in days_data:
                if row < len(day_items):
                    item, amount = day_items[row]
                    pdf.set_font("Arial", "", 10)
                    pdf.cell(subcol_width, row_height, item, border=1, align="C")
                    pdf.cell(subcol_width, row_height, amount, border=1, align="C")
                else:
                    pdf.set_font("Arial", "", 10)
                    pdf.cell(subcol_width, row_height, "", border=1)
                    pdf.cell(subcol_width, row_height, "", border=1)
            pdf.ln(row_height)
        pdf.ln(10)
        
    def _add_table(self, pdf, headers, data):
        pdf.set_fill_color(200, 200, 200)
        pdf.set_font('Arial', 'B', 10)
        
        # Calculate optimal column widths - give more space to the middle column
        col_widths = [pdf.w * 0.25, pdf.w * 0.5, pdf.w * 0.15]  # Customer, Items, Halbe Channel
        
        # Set up header
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 7, str(header), 1, 0, 'C', True)
        pdf.ln()
        
        pdf.set_font('Arial', '', 10)
        for row in data:
            # First, calculate how much height we need for the middle column
            # Create a temporary PDF object to calculate text height
            temp_pdf = FPDF()
            temp_pdf.add_page()
            temp_pdf.set_font('Arial', '', 10)
            
            # Set a reference position
            start_y = temp_pdf.get_y()
            
            # Calculate maximum line width for content (same as we'll use in actual cell)
            max_width = col_widths[1] - 4  # Subtract margin
            
            # Simulate writing text to calculate height
            temp_pdf.multi_cell(max_width, 4, str(row[1]), 0, 'L')
            
            # Calculate how much height was used
            end_y = temp_pdf.get_y()
            needed_height = end_y - start_y
            
            # Set minimum cell height (6) or calculated height + padding
            cell_height = max(6, needed_height + 2)  # Add 2 for padding
            
            # Start drawing the actual row
            # Handle customer name (first column)
            pdf.cell(col_widths[0], cell_height, str(row[0]), 1, 0, 'L')
            
            # Handle items list with proper wrapping (middle column)
            # Save current position
            x_pos = pdf.get_x()
            y_pos = pdf.get_y()
            
            # Draw the cell border first
            pdf.cell(col_widths[1], cell_height, '', 1, 0)
            
            # Write the text with word wrapping
            pdf.set_xy(x_pos + 2, y_pos + 1)  # Add small padding
            pdf.multi_cell(max_width, 4, str(row[1]), 0, 'L')
            
            # Restore position for next cell
            pdf.set_xy(x_pos + col_widths[1], y_pos)
            
            # Handle Halbe Channel (third column)
            pdf.cell(col_widths[2], cell_height, str(row[2]), 1, 0, 'C')
            pdf.ln()
        pdf.ln(10)

    from peewee import prefetch

    def get_week_delivery_schedule(self, week_date):
        monday = week_date - timedelta(days=week_date.weekday())
        sunday = monday + timedelta(days=6)
        
        # Use prefetch to avoid duplicate orders due to the join on OrderItem and Item
        deliveries_query = (Order
                            .select()
                            .where(Order.delivery_date.between(monday, sunday))
                            .order_by(Order.delivery_date))
        deliveries = prefetch(deliveries_query, Customer, OrderItem, Item)
        
        daily_data = {}
        for delivery in deliveries:
            date_str = delivery.delivery_date.strftime("%d.%m.%Y")
            if date_str not in daily_data:
                daily_data[date_str] = {}
            
            customer_name = delivery.customer.name
            if customer_name not in daily_data[date_str]:
                daily_data[date_str][customer_name] = {
                    'items': [],
                    'halbe_channel': delivery.halbe_channel
                }
            
            for item in delivery.order_items:
                # Format the amount: remove decimals if it's a whole number
                amount_str = str(int(item.amount)) if item.amount == int(item.amount) else str(item.amount)
                daily_data[date_str][customer_name]['items'].append(f"{item.item.name}: {amount_str}")
        
        # Format the data for display
        formatted_data = {}
        for date_str, customers in daily_data.items():
            formatted_data[date_str] = []
            for customer_name, info in customers.items():
                half_channel_status = "Ja" if info['halbe_channel'] else "Nein"
                formatted_items = ", ".join(info['items'])
                
                formatted_data[date_str].append([
                    customer_name,
                    formatted_items,
                    half_channel_status
                ])
        
        return {
            "headers": ["Kunde", "Items", "Halbe Channel"],
            "daily_data": formatted_data
        }

    def get_week_production_plan(self, week_date):
        monday = week_date - timedelta(days=week_date.weekday())
        sunday = monday + timedelta(days=6)
        
        productions = (Order
                    .select(Order, OrderItem, Item)
                    .join(OrderItem)
                    .join(Item)
                    .where(Order.production_date.between(monday, sunday))
                    .order_by(Order.production_date))
        
        daily_items = {}
        for prod in productions:
            date_str = prod.production_date.strftime("%d.%m.%Y")
            if date_str not in daily_items:
                daily_items[date_str] = {}
            
            for item in prod.order_items:
                if item.item.name not in daily_items[date_str]:
                    daily_items[date_str][item.item.name] = {
                        'amount': 0,
                        'half_channel': "Ja" if prod.halbe_channel else "Nein"
                    }
                
                daily_items[date_str][item.item.name]['amount'] += item.amount
        
        return daily_items

    def get_week_transfer_schedule(self, week_date):
        monday = week_date - timedelta(days=week_date.weekday())
        sunday = monday + timedelta(days=6)
        
        transfers = (Order
                    .select(Order, OrderItem, Item)
                    .join(OrderItem)
                    .join(Item)
                    .order_by(Order.production_date))
        
        # Track items by germination date
        daily_transfers = {}
        
        for transfer in transfers:
            for item in transfer.order_items:
                # Calculate germination (transfer) date
                prod_date = transfer.production_date
                germ_date = prod_date - timedelta(days=item.item.growth_days)
                
                if monday <= germ_date <= sunday:
                    date_str = germ_date.strftime("%d.%m.%Y")
                    if date_str not in daily_transfers:
                        daily_transfers[date_str] = {}
                    
                    if item.item.name not in daily_transfers[date_str]:
                        daily_transfers[date_str][item.item.name] = 0
                    
                    daily_transfers[date_str][item.item.name] += item.amount
        
        return daily_transfers

    def print_week_schedule(self, schedule_type, week_date=None):
        if week_date is None:
            week_date = date.today()

        pdf = FPDF()
        pdf.add_page('L')  # Landscape orientation

        if schedule_type == "delivery":
            title = "Wöchentlicher Lieferplan"
            schedule_data = self.get_week_delivery_schedule(week_date)
            self._create_header(pdf, title, week_date)
            for date_str, deliveries in schedule_data["daily_data"].items():
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, f'Datum: {date_str}', 0, 1, 'L')
                self._add_table(pdf, schedule_data["headers"], deliveries)

        elif schedule_type == "production":
            title = "Wöchentlicher Produktionsplan"
            daily_items = self.get_week_production_plan(week_date)
            self._create_header(pdf, title, week_date)
            self._add_weekly_plan_table(pdf, daily_items, week_date)

        else:  # transfer
            title = "Wöchentlicher Transferplan"
            daily_transfers = self.get_week_transfer_schedule(week_date)
            self._create_header(pdf, title, week_date)
            self._add_weekly_plan_table(pdf, daily_transfers, week_date)

        filename = f"{schedule_type}_schedule_{week_date.strftime('%Y%m%d')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        pdf.output(filepath)
        return filepath

    def print_all_schedules(self, week_date=None):
        """Print all schedules for specified week"""
        if week_date is None:
            week_date = date.today()

        pdf = FPDF()
        
        # Delivery Schedule
        pdf.add_page('L')
        title = "Wöchentlicher Lieferplan"
        schedule_data = self.get_week_delivery_schedule(week_date)
        self._create_header(pdf, title, week_date)
        for date_str, deliveries in schedule_data["daily_data"].items():
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, f'Datum: {date_str}', 0, 1, 'L')
            self._add_table(pdf, schedule_data["headers"], deliveries)
        
        # Production Plan
        pdf.add_page('L')
        title = "Wöchentlicher Produktionsplan"
        daily_items = self.get_week_production_plan(week_date)
        self._create_header(pdf, title, week_date)
        for date_str, items in daily_items.items():
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, f'Datum: {date_str}', 0, 1, 'L')
            data = []
            for item_name, info in items.items():
                data.append([
                    item_name,
                    f"{info['amount']}",
                    info['half_channel']
                ])
            self._add_table(pdf, ["Item", "Menge", "Halbe Channel"], data)
        
        # Transfer Schedule
        pdf.add_page('L')
        title = "Wöchentlicher Transferplan"
        daily_transfers = self.get_week_transfer_schedule(week_date)
        self._create_header(pdf, title, week_date)
        for date_str, transfers in daily_transfers.items():
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, f'Transfer Datum: {date_str}', 0, 1, 'L')
            data = [[item, f"{amount}"] for item, amount in transfers.items()]
            self._add_table(pdf, ["Item", "Menge"], data)
        
        filename = f"all_schedules_{week_date.strftime('%Y%m%d')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        pdf.output(filepath)
        return filepath

def ask_week_selection():
    """Ask user which week to print"""
    dialog = tk.Toplevel()
    dialog.title("Woche auswählen")
    dialog.geometry("300x150")
    
    result = {"week": None}
    
    def set_current():
        result["week"] = "current"
        dialog.destroy()
    
    def set_next():
        result["week"] = "next"
        dialog.destroy()
    
    tk.Label(dialog, text="Welche Woche möchten Sie drucken?").pack(pady=10)
    
    tk.Button(dialog, text="Aktuelle Woche", command=set_current, fg="black", bg="white", highlightbackground="white").pack(pady=5)
    tk.Button(dialog, text="Nächste Woche", command=set_next, fg="black", bg="white", highlightbackground="white").pack(pady=5)
    
    dialog.transient()
    dialog.grab_set()
    dialog.wait_window()
    
    return result["week"]
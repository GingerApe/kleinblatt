import os
from datetime import datetime, timedelta, date
from fpdf import FPDF
from models import Order, OrderItem, Item, Customer
from peewee import *
import tkinter as tk
from tkinter import messagebox

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
        pdf.cell(0, 10, f'Week: {monday.strftime("%d.%m.%Y")} - {sunday.strftime("%d.%m.%Y")}', 0, 1, 'C')
        pdf.ln(5)

    def _add_table(self, pdf, headers, data):
        pdf.set_fill_color(200, 200, 200)
        pdf.set_font('Arial', 'B', 10)
        
        # Calculate column widths based on content and number of columns
        col_width = pdf.w / len(headers) - 10
        
        for header in headers:
            pdf.cell(col_width, 7, str(header), 1, 0, 'C', True)
        pdf.ln()
        
        pdf.set_font('Arial', '', 10)
        for row in data:
            for item in row:
                pdf.cell(col_width, 6, str(item), 1, 0, 'C')
            pdf.ln()
        pdf.ln(10)

    def get_week_delivery_schedule(self, week_date):
        monday = week_date - timedelta(days=week_date.weekday())
        sunday = monday + timedelta(days=6)
        
        deliveries = (Order
                     .select(Order, Customer, OrderItem, Item)
                     .join(Customer)
                     .switch(Order)
                     .join(OrderItem)
                     .join(Item)
                     .where(Order.delivery_date.between(monday, sunday))
                     .order_by(Order.delivery_date))
        
        daily_data = {}
        for delivery in deliveries:
            date_str = delivery.delivery_date.strftime("%d.%m.%Y")
            if date_str not in daily_data:
                daily_data[date_str] = []
            
            items_info = []
            for item in delivery.order_items:
                items_info.append(f"{item.item.name}: {item.amount}g")
            
            # Set "Ja" or "Nein" based on halbe_channel
            half_channel_status = "Ja" if delivery.halbe_channel else "Nein"
            
            daily_data[date_str].append([
                delivery.customer.name,
                ", ".join(items_info),
                half_channel_status  # Use "Ja" or "Nein"
            ])
        
        return {
            "headers": ["Kunde", "Items", "Halbe Channel"],
            "daily_data": daily_data
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
            for item in transfer.items:
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
        pdf.add_page('L')

        if schedule_type == "delivery":
            title = "Weekly Delivery Schedule"
            schedule_data = self.get_week_delivery_schedule(week_date)
            
            self._create_header(pdf, title, week_date)
            for date_str, deliveries in schedule_data["daily_data"].items():
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, f'Date: {date_str}', 0, 1, 'L')
                self._add_table(pdf, schedule_data["headers"], deliveries)

        elif schedule_type == "production":
            title = "Weekly Production Plan"
            daily_items = self.get_week_production_plan(week_date)
            
            self._create_header(pdf, title, week_date)
            for date_str, items in daily_items.items():
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, f'Date: {date_str}', 0, 1, 'L')
                
                data = []
                for item_name, info in items.items():
                    data.append([
                        item_name,
                        f"{info['amount']}",
                        info['half_channel']
                    ])
                
                self._add_table(pdf, ["Item", "Menge", "Halbe Channel"], data)

        else:  # transfer
            title = "Weekly Transfer Schedule"
            daily_transfers = self.get_week_transfer_schedule(week_date)
            
            self._create_header(pdf, title, week_date)
            for date_str, transfers in daily_transfers.items():
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, f'Transfer Date: {date_str}', 0, 1, 'L')
                
                data = [[item, (f"{amount:.1f}".rstrip("0").rstrip("."))] for item, amount in transfers.items()]
                self._add_table(pdf, ["Item", "Menge"], data)

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
        title = "Weekly Delivery Schedule"
        schedule_data = self.get_week_delivery_schedule(week_date)
        self._create_header(pdf, title, week_date)
        for date_str, deliveries in schedule_data["daily_data"].items():
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, f'Date: {date_str}', 0, 1, 'L')
            self._add_table(pdf, schedule_data["headers"], deliveries)
        
        # Production Plan
        pdf.add_page('L')
        title = "Weekly Production Plan"
        daily_items = self.get_week_production_plan(week_date)
        self._create_header(pdf, title, week_date)
        for date_str, items in daily_items.items():
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, f'Date: {date_str}', 0, 1, 'L')
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
        title = "Weekly Transfer Schedule"
        daily_transfers = self.get_week_transfer_schedule(week_date)
        self._create_header(pdf, title, week_date)
        for date_str, transfers in daily_transfers.items():
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, f'Transfer Date: {date_str}', 0, 1, 'L')
            data = [[item, (f"{amount:.1f}".rstrip("0").rstrip("."))] for item, amount in transfers.items()]
            self._add_table(pdf, ["Item", "Menge"], data)
        
        filename = f"all_schedules_{week_date.strftime('%Y%m%d')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        pdf.output(filepath)
        return filepath

def ask_week_selection():
    """Ask user which week to print"""
    dialog = tk.Toplevel()
    dialog.title("Select Week")
    dialog.geometry("300x150")
    
    result = {"week": None}
    
    def set_current():
        result["week"] = "current"
        dialog.destroy()
    
    def set_next():
        result["week"] = "next"
        dialog.destroy()
    
    tk.Label(dialog, text="Which week would you like to print?").pack(pady=10)
    
    tk.Button(dialog, text="Current Week", command=set_current, fg="black", bg="white", highlightbackground="white").pack(pady=5)
    tk.Button(dialog, text="Next Week", command=set_next, fg="black", bg="white", highlightbackground="white").pack(pady=5)
    
    dialog.transient()
    dialog.grab_set()
    dialog.wait_window()
    
    return result["week"]

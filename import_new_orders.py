import csv
from datetime import datetime
import os

def parse_new_orders(input_file, output_file):
    """
    Parse the new_orders.csv file and convert it to a format compatible 
    with the import_old_data function in temp_data_import.py
    
    Output CSV format:
    "Kunde","Item","Menge","Lieferdatum","Ansaehen","Woche_Wdh","Von","Bis","Preis"
    """
    print(f"Parsing {input_file}...")
    
    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # The first two rows contain the weekdays and dates
    weekdays = lines[0].strip().split('\t')
    dates = lines[1].strip().split('\t')
    
    # Clean empty entries from weekdays and dates
    weekdays = [day for day in weekdays if day]
    dates = [date for date in dates if date]
    
    # Dictionary to map weekday to date
    weekday_to_date = {}
    for i in range(min(len(weekdays), len(dates))):
        weekday_to_date[weekdays[i]] = dates[i]
    
    print(f"Weekdays and dates: {weekday_to_date}")
    
    # List to store processed rows
    processed_rows = []
    
    # Process the data rows (starting from line 2)
    current_weekday = None
    delivery_date = None
    
    for line_num in range(2, len(lines)):
        line = lines[line_num].strip()
        if not line:
            continue
        
        # Split the line by tabs
        cells = line.split('\t')
        cells = [cell.strip() for cell in cells if cell.strip()]
        
        # Process the cells
        for i in range(0, len(cells), 2):
            if i + 1 < len(cells):  # Make sure we have a pair
                customer_name = cells[i]
                items_str = cells[i+1]
                
                # Determine which weekday/date column we're in
                col_index = i // 2
                if col_index < len(weekdays):
                    current_weekday = weekdays[col_index]
                    delivery_date = weekday_to_date.get(current_weekday, "")
                
                # Skip if no delivery date
                if not delivery_date:
                    print(f"Warning: No delivery date for row {line_num+1}, column {i}. Skipping.")
                    continue
                
                # Format the delivery date (DD.MM.YY)
                try:
                    # Convert from DD.MM.YY to a datetime object
                    date_obj = datetime.strptime(delivery_date, '%d.%m.%y')
                    formatted_date = date_obj.strftime('%d.%m.%y')
                except ValueError:
                    print(f"Warning: Invalid date format '{delivery_date}'. Skipping.")
                    continue
                
                # Parse items and quantities
                if items_str.startswith('"') and items_str.endswith('"'):
                    items_str = items_str[1:-1]  # Remove enclosing quotes
                
                items_list = items_str.split('\n')
                
                for item_entry in items_list:
                    if ':' in item_entry:
                        item_name, amount_str = item_entry.split(':', 1)
                        item_name = item_name.strip()
                        amount_str = amount_str.strip()
                        
                        # Add row to processed data
                        # Format: "Kunde","Item","Menge","Lieferdatum","Ansaehen","Woche_Wdh","Von","Bis","Preis"
                        processed_row = [
                            customer_name,  # Kunde
                            item_name,      # Item
                            amount_str,     # Menge
                            formatted_date, # Lieferdatum
                            "",             # Ansaehen (Production date - empty)
                            "0",            # Woche_Wdh (Subscription type - 0 for one-time)
                            "",             # Von (From date - empty)
                            "",             # Bis (To date - empty)
                            ""              # Preis (Price - empty)
                        ]
                        processed_rows.append(processed_row)
    
    # Write the output CSV file
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        # Write header
        writer.writerow(["Kunde", "Item", "Menge", "Lieferdatum", "Ansaehen", "Woche_Wdh", "Von", "Bis", "Preis"])
        # Write data
        writer.writerows(processed_rows)
    
    print(f"Converted {len(processed_rows)} order items to {output_file}")
    return True

def import_new_orders():
    """
    Convert new_orders.csv to a proper CSV format and import it using temp_data_import.py
    """
    input_file = "new_orders.csv"
    output_file = "converted_orders.csv"
    
    # Convert the new orders file to proper CSV format
    if parse_new_orders(input_file, output_file):
        print(f"✅ Successfully converted {input_file} to {output_file}")
        
        # Now import the converted file using the existing import function
        from temp_data_import import import_old_data
        
        if import_old_data(output_file):
            print("✅ Data import completed successfully!")
        else:
            print("❌ Data import failed.")
    else:
        print(f"❌ Failed to convert {input_file}")

if __name__ == "__main__":
    import_new_orders() 
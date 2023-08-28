# Import necessary modules and libraries
import Adafruit_DHT
import time
import mysql.connector
import threading
from datetime import datetime
from statistics import mean, stdev

# Script start message
print("Script started")

# Configuration for DHT22 sensors
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN1 = 4
DHT_PIN2 = 17

# Database configuration
DB_CONFIG = {
    'user': 'root',
    'password': '2prZ_s$@C&t',  # Replace with your actual password
    'host': 'localhost',
    'database': 'kbmonitorsql'
}

# Buffer to store the last 5 readings
data_buffer = []

# Function to filter outliers using standard deviation
def filter_outliers(data):
    if len(data) < 2:
        return data  # Not enough data to filter
    
    data_mean = mean(data)
    data_stdev = stdev(data)
    
    # Filter out data points that are more than 2 standard deviations away from the mean
    return [x for x in data if abs(x - data_mean) <= 2 * data_stdev]

def store_data(temp1, hum1, temp2, hum2):
    try:
        print("Attempting to store data...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(current_time)
        cursor.execute(
            "INSERT INTO sensor_data (timestamp, temperature1, humidity1, temperature2, humidity2) VALUES (%s, %s, %s, %s, %s)",
            (current_time, temp1, hum1, temp2, hum2)
        )
        conn.commit()
        cursor.close()
        conn.close()
        print("Data successfully stored.")
    except Exception as e:
        print(f"Failed to store data: {e}")
        
# Data collection function
def data_collector():
    last_temp1, last_hum1 = None, None
    last_temp2, last_hum2 = None, None
    while True:
        try:
            humidity1, temperature1 = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN1)
            humidity2, temperature2 = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN2)
            
            # Validate the readings and use last valid readings if needed
            if humidity1 is not None and humidity1 <= 100:
                last_hum1 = humidity1
            if temperature1 is not None and temperature1 <= 50:
                last_temp1 = temperature1
            if humidity2 is not None and humidity2 <= 100:
                last_hum2 = humidity2
            if temperature2 is not None and temperature2 <= 50:
                last_temp2 = temperature2
            data_buffer.append((last_temp1, last_hum1, last_temp2, last_hum2))

            time.sleep(10)  # Sleep 2 seconds between DHT readings
        except Exception as err:
            print(f"Error reading sensor data: {err}")

# Function to filter and store data
def filter_and_store_data():
    print("Attempting to filter and store data...")
    if len(data_buffer) >= 6:
        temperatures1 = [entry[0] for entry in data_buffer]
        humidities1 = [entry[1] for entry in data_buffer]
        temperatures2 = [entry[2] for entry in data_buffer]
        humidities2 = [entry[3] for entry in data_buffer]

        # Apply the new filter_outliers function to each list
        filtered_temps1 = filter_outliers(temperatures1)
        filtered_hums1 = filter_outliers(humidities1)
        filtered_temps2 = filter_outliers(temperatures2)
        filtered_hums2 = filter_outliers(humidities2)
        
        # Check if any filtered list is empty
        if any(len(lst) == 0 for lst in [filtered_temps1, filtered_hums1, filtered_temps2, filtered_hums2]):
            print("Filtered data is empty for some parameters, skipping this iteration.")
            data_buffer.clear()
            return
                
        # Calculate the filtered mean
        filtered_mean_temp1 = mean(filtered_temps1)
        filtered_mean_hum1 = mean(filtered_hums1)
        filtered_mean_temp2 = mean(filtered_temps2)
        filtered_mean_hum2 = mean(filtered_hums2)

        # Store the filtered data
        store_data(filtered_mean_temp1, filtered_mean_hum1, filtered_mean_temp2, filtered_mean_hum2)
        print("Filtered data successfully stored in the database.")

        # Clear the buffer
        data_buffer.clear()
        
# Main function
def main_thread():
    time.sleep(15)  # Initial delay to allow data_collector to populate data_buffer
    while True:
        if len(data_buffer) >= 6:
            print("Buffer length sufficient, attempting to filter and store data...")
            filter_and_store_data()  # Directly call filter_and_store_data
        else:
            print(f"Buffer Length: {len(data_buffer)} (waiting for more data)")
        time.sleep(10)

# Start data collection in a separate thread
collector_thread = threading.Thread(target=data_collector)
collector_thread.start()

# Start the main thread
main_thread()

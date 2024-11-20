import json
import time
from datetime import datetime
import requests
import os
from pymodbus.client import ModbusTcpClient
import inspect

# File to store the machine data (timestamp, error type, message, function)
DATA_FILE = "machine_data.txt"
FAILED_REQUESTS_FILE = "/root/deepsea/failed_requests.json"


# Function to store data in a text file with timestamp, error type, message, and function name
def store_data(timestamp, error_type, message):
    # Get the name of the function that called store_data
    caller_function = inspect.stack()[1].function

    # Define the directory and file where data will be stored
    file_directory = "/root/deepsea/data_files"

    if not os.path.exists(file_directory):
        os.makedirs(file_directory)

    data_path = os.path.join(file_directory, DATA_FILE)

    # Store the timestamp, error type, function name, and message
    with open(data_path, "a") as data_file:
        print(f"{timestamp} - {error_type} - {caller_function} - {message}\n")
        data_file.write(f"{timestamp} - {error_type} - {caller_function} - {message}\n")


# Example call to store_data
store_data("timestamp", "error_type", "message")

# Modbus connection
try:
    client = ModbusTcpClient('192.168.2.2')  # Modbus server IP
    conn = client.connect()
    if conn:
        store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "INFO", "Modbus connection established.")
    else:
        store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ERROR", "Failed to establish Modbus connection.")
except Exception as e:
    store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ERROR", f"Modbus connection error: {e}")


# Function to read data from Modbus machine
def read_machine():
    try:
        result = client.read_holding_registers(0, 4)

        if not result.isError():
            store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "INFO", f"Read registers: {result.registers}")
            return result.registers
        else:
            store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ERROR", "Error reading registers")
            return [0, 0, 0, 0]

    except Exception as e:
        store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ERROR", f"Modbus read error: {e}")
        return [0, 0, 0, 0]


# Function to read data from JSON file
def read_json(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data['data']
    except Exception as e:
        store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ERROR", f"Error reading JSON file: {e}")
        return []


# Function to store failed requests in a JSON file
def store_failed_request(data):
    if os.path.exists(FAILED_REQUESTS_FILE):
        with open(FAILED_REQUESTS_FILE, 'r') as file:
            failed_requests = json.load(file)
    else:
        failed_requests = []

    failed_requests.append(data)

    with open(FAILED_REQUESTS_FILE, 'w') as file:
        json.dump(failed_requests, file)


# Function to remove successful requests from failed requests file
def remove_successful_requests(successful_requests):
    if os.path.exists(FAILED_REQUESTS_FILE):
        with open(FAILED_REQUESTS_FILE, 'r') as file:
            failed_requests = json.load(file)

        remaining_requests = [req for req in failed_requests if req not in successful_requests]

        if remaining_requests:
            with open(FAILED_REQUESTS_FILE, 'w') as file:
                json.dump(remaining_requests, file)
        else:
            os.remove(FAILED_REQUESTS_FILE)


# Function to send status to server
def send_status_to_server(machine_id, status_type, status_value):
    timestamp = datetime.now().strftime("%Y%m%dT%H:%M:%S")[:-3]
    current_data_send = {
        "date_time": timestamp,
        "machine_id": machine_id,
        "status": status_type
    }
    url = "https://deepseaerp.com/ajax_add_machine"

    try:
        response = requests.post(url, json=current_data_send)
        if response.status_code == 200:
            store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "INFO", f"Sent data to server: {current_data_send}")
        else:
            store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ERROR", f"Failed to send data: {response.status_code}")
            store_failed_request(current_data_send)
    except requests.exceptions.RequestException as e:
        store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ERROR", f"Error sending data to server: {e}")
        store_failed_request(current_data_send)
        return

    send_failed_requests()


# Function to resend failed requests
def send_failed_requests():
    if os.path.exists(FAILED_REQUESTS_FILE):
        with open(FAILED_REQUESTS_FILE, 'r') as file:
            failed_requests = json.load(file)

        successfully_sent_requests = []

        for request_data in failed_requests:
            try:
                response = requests.post("https://deepseaerp.com/ajax_add_machine", json=request_data)
                if response.status_code == 200:
                    store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "INFO", f"Resent succeeded: {request_data}")
                    successfully_sent_requests.append(request_data)
                else:
                    store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ERROR", f"Failed to resend: {request_data}")
            except requests.exceptions.RequestException as e:
                store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ERROR", f"Error resending failed data: {e}")

        if successfully_sent_requests:
            remove_successful_requests(successfully_sent_requests)


# Function to monitor machine changes
def monitor_changes(file_path=None):
    # previous_data = read_json(file_path)
    previous_data = read_machine()



    while True:
        try:
            # current_data = read_json(file_path)
            current_data = read_machine()
            store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "INFO", "Monitoring changes...")

            for i in range(0, len(current_data), 4):
                if i + 3 < len(current_data):
                    machine_index = i // 4 + 1
                    states = ["stop", "idle", "start", "settings"]
                    for j in range(4):
                        if previous_data[i + j] == 1 and current_data[i + j] == 2:
                            status_message = f"Machine {machine_index} {states[j]} is on"
                            store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "INFO", status_message)
                            send_status_to_server(machine_index, states[j], "on")
                        elif previous_data[i + j] == 2 and current_data[i + j] == 1:
                            status_message = f"Machine {machine_index} {states[j]} is off"
                            store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "INFO", status_message)
                            # send_status_to_server(machine_index, states[j], "off")

            previous_data = current_data
            print("prev data - ",previous_data)
            print("curt data - ",current_data)

        except Exception as e:
            store_data(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ERROR", f"Error in monitoring: {e}")

        time.sleep(1)  # Monitor every second


if __name__ == "__main__":
    file_path = "/root/deepsea/machine.json"
    monitor_changes(file_path)

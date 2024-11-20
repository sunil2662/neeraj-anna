import requests
import datetime
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
import time
import logging
import os

import json

current_date = datetime.datetime.now().strftime('%d-%m-%Y')

# Generate the dynamic file name by concatenating the current date with the base file name
dynamic_file_name = f"{current_date}_deepsea_log_file.log"

# Construct the full file path
log_file_path = os.path.join(r'/home/pi/backup/', dynamic_file_name)

print('log_file_path',log_file_path)

# log_file_path = r'F:/all_projects/postrequest_deepsea/log_file.log'

# Configure logging to store messages in a file
logging.basicConfig(filename=log_file_path, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')



client = ModbusClient(method="rtu", port="/dev/ttyUSB0", stopbits=1, bytesize=8, parity='E', baudrate=9600)
connection = client.connect()
print(connection)






# def post_request(status):
#     current_time = datetime.datetime.now()
#     timestamp = current_time.strftime("%d%m%Y%H%M%S")
#
#     # url = f'https://deepseaerp.com/ajax_add_machine'  http://192.168.29.220:8000/testing/
#     url = f'http://127.0.0.1:8000/homee/'
#     data = {
#         'machine_id': '29',
#         'status': status,
#         'date_time': datetime.datetime.now().isoformat().split('.')[0]
#     }
#
#     response = requests.post(url, json=data)
#     print('response',response)
#
#     # Check the status code of the response
#     if response.status_code == 200:
#         print('POST request was successful!')
#         print('Response:', response.text)
#     else:
#         print(f'POST request failed with status code {response.status_code}')
#         print('Response:', response.text)



# Function to send POST request
def post_request(s,d):
    print(s,d)
    url = f'https://deepseaerp.com/ajax_add_machine'
    # url = 'http://127.0.0.1:8000/homee/'
    global post_data
    post_data=d


    response = requests.post(url, json=post_data)
    return response

# Function to backup data
def backup_data(data):
    with open(r'/home/pi/backup/backup.json', 'a') as f:
        json.dump(data, f)
        f.write('\n')

# Function to send backup data
def send_backup_data():
    if os.path.exists(r'/home/pi/backup/backup.json'):
        with open(r'/home/pi/backup/backup.json', 'r') as f:
            for line in f:
                try:
                    global b_data
                    b_data = json.loads(line)
                    # print('b_data',b_data)
                    b_response = post_request(status,b_data)
                    if b_response.status_code == 200:
                        print('Backup data sent successfully:', b_data)
                        logging.info(b_data)

                    else:
                        print("failed to send backup data",b_response.status_code)
                except Exception as e:
                    print('Error sending backup data:', e)
            # print('after_lopp',b_data)
            # return b_data



data = {'machine_id': '29', 'status': 'test_status', 'date_time': datetime.datetime.now().isoformat().split('.')[0]}
# response = post_request(status,data)



def color(bit):
    if bit == 1:
        return 'On'
    elif bit == 2:
        return 'Off'


prev_red = 2
prev_yellow = 2
prev_green = 0

'''
try:
    current_tower = client.read_holding_registers(4096,3,unit=0x01)
    if current_tower.registers[0]==2 and current_tower.registers[1]==2 and current_tower.registers[2]==2:
        post_request('stop')
        print('red on - stop')
except Exception as e:
        print('Error -> ',e)
'''
prev_status = "null"
prev_tower = [0, 0, 0]
while True:
    try:
        current_tower = client.read_holding_registers(4096, 3, unit=0x01)
        print(current_tower.registers)

        if current_tower.registers != prev_tower:
            num_changes = sum(1 for x, y in zip(prev_tower, current_tower.registers) if x != y)
            prev_tower = current_tower.registers

        print("num_changes ", num_changes)

        if current_tower.registers == [2, 2, 2] or current_tower.registers == [1, 2, 2]:
            status = "stop"
            tower_color = "stop         red"
            # count = count+1



        elif current_tower.registers == [2, 1, 2]:
            status = "idle_start"
            tower_color = "idle_start   yellow"
            # count = count+1


        elif current_tower.registers == [2, 2, 1]:
            status = "start"
            tower_color = "start        green"
            # count = count+1


        elif current_tower.registers == [2, 1, 1] or current_tower.registers == [1, 2,
                                                                                 1] or current_tower.registers == [1, 1,
                                                                                                                   2] or current_tower.registers == [
            1, 1, 1]:
            status = "settings"
            tower_color = "settings     dual on"
            # count = 1 ++




        else:
            print("----------new------------")

        if status != prev_status:
            print(tower_color)
            response=post_request(status,data)
            prev_status = status
            if response.status_code == 200:
                print('POST request was successful!', response.text)
                # r'F:/all_projects/postrequest_deepsea/log_file.log'

                # Log messages

                logging.info(data)

                send_backup_data()

                with open(r'/home/pi/backup/backup.json', 'w') as f:
                    f.truncate(0)


            else:
                print(f'POST request failed with status code {response.status_code}')
                print('Backing up data...')
                backup_data(data)


    except Exception as e:
        print('Error -> ', e)

    time.sleep(1)

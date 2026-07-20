import threading #allows the program to run multiple functions at the same time
import time
import copy

from pollingInverterID import poll_inverter_id
from pollingInverterState import poll_inverter_state_init, poll_inverter_state
from pollingInverterMeasurements import poll_inverter_measurements

from inverter_ip import inverter_ip_mapping

import threading
import time
import copy

# Create a global lock
inverter_lock = threading.Lock()

def run_measurements_polling(ip, port, id, UNIT_ID, lock): 
    while True:
        try:
            #lock, so the 5-sec loop waits
            with lock:
                poll_inverter_measurements(ip, port, id, UNIT_ID)
        except Exception as e:
            print(f"Error in polling inverter measurements for ip {ip}: {e}")
        
        time.sleep(5 * 60) 

def run_inverter_state_polling(baseline_data, ip, port, id, UNIT_ID, lock):
    baseline = copy.deepcopy(baseline_data)

    while True:
        try:
            #lock, so the 5-min loop waits
            with lock:
                poll_inverter_state(baseline, ip, port, id, UNIT_ID)
        except Exception as e:
            print(f"Error polling inverter state for ip {ip}: {e}")
        
        time.sleep(5) 

def start_inverter_polling(inverter):
    ip = inverter["ip"]
    port = inverter["port"]
    id = inverter["id"]
    UNIT_ID = inverter["UNIT_ID"]

    print(f"Initializing inverter {id} ({ip})")

    try:
        poll_inverter_id(ip, port, id, UNIT_ID)
    except Exception as e:
        print(f"Failed to poll inverter id for ip {ip}: {e}")

    baseline_data = None
    try:
        baseline_data = poll_inverter_state_init(ip, port, id, UNIT_ID)
    except Exception as e:
        print(f"Failed to initialize inverter state's baseline data for ip {ip}: {e}")
    
    # Pass the lock down to the threads
    t_5min = threading.Thread(
        target=run_measurements_polling,
        args=(ip, port, id, UNIT_ID, inverter_lock),
        daemon=True
    )
    t_5min.start()

    if baseline_data:
        t_5sec = threading.Thread(
            target=run_inverter_state_polling,
            args=(baseline_data, ip, port, id, UNIT_ID, inverter_lock),
            daemon=True
        )
        t_5sec.start()


if __name__ == "__main__":

    #Iterate through all inverters
    for inverter in inverter_ip_mapping:
        start_inverter_polling(inverter)
        try:
            while True:
                time.sleep(1)
        
        except KeyboardInterrupt:
            print("Polling stopped")

    

    
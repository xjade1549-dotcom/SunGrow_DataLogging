import time
import copy
from datetime import datetime, timedelta, timezone
from pymodbus.client import ModbusTcpClient

#Importing the database's cursor
from db_connect import get_db_cursor

#Importing the mapped files, these registers need to be logged every 5 mins
from inverter_work_state import inverter_work_state_mapping
from inverter_mode_selection import inverter_mode_selection_mapping
from inverter_fault_alarm import inverter_fault_alarm_mapping

#Importing the file to decode binary numbers into decimal numbers
from decode import decode_binary

master_mapping = inverter_work_state_mapping + inverter_mode_selection_mapping + inverter_fault_alarm_mapping

def poll_inverter_state_init(ip, port, id, UNIT_ID):
    INVERTER_IP = ip
    PORT = port

    tz = timezone(timedelta(hours=7)) # Matches the GMT+7 timezone

    client = ModbusTcpClient(INVERTER_IP, port = PORT)

    # 1. connecting to the inverter and poll the data, via pymodbus

    if not client.connect(): #if pymodbus couldn't connect to the machine via given ip and port
        print(f"Couldn't connect to the inverter via the given {INVERTER_IP} and {PORT}")
        return None
    first_output = {"timestamp": str(datetime.now(tz).replace(microsecond=0))}

    for name,adr,data_type,scale,space, reg_size in master_mapping:  #reading every registers, depending on its type
        
        #Seperate input registers and holding registers
        if space == "3X":#read the input registers
            data = client.read_input_registers(address=adr-1, count=reg_size, slave = UNIT_ID)
        elif space == "4X": #read the holding regs
            data = client.read_holding_registers(address=adr-1, count=reg_size, slave=UNIT_ID)

        if not data.isError():
            #Log normal data into first_output dict
            if name not in ["local_remote_control", "qp_curve_2", "qu_curve_2"]:
                first_output[name] = decode_binary(client, data.registers, data_type, scale) #dict form: the output named 'voltage' will have a value, processed from the decode_binary function, according to their registers and type
            #Log special data into first_output dict 
            else:
                first_output[name] = list(client.convert_from_registers(data.registers, data_type=client.DATATYPE.UINT16))
        
        else:
            first_output[name] = None

    client.close()

    # 2. SQL for inserting inverter's data into timescaleDB 
    with get_db_cursor() as cursor:
        #1. for inverter_mode_selection table
        mode_fields = [
            "timestamp", "pid_work_state", "local_remote_control", "power_limitation_switch",
            "reactive_power_adj_mode", "qp_curve_2", "qu_curve_2", "power_limitation_setting",
            "power_factor_setting", "reactive_power_pct_setting", "power_limitation_adj", "reactive_power_adj"
        ]
        
        mode_query = """
            INSERT INTO inverter_mode_selection (
                inverter_id,
                timestamp,
                pid_work_state, 
                local_remote_control, 
                power_limitation_switch,
                reactive_power_adj_mode, 
                qp_curve_2, 
                qu_curve_2, 
                power_limitation_setting,
                power_factor_setting, 
                reactive_power_pct_setting, 
                power_limitation_adj, 
                reactive_power_adj
            )
            VALUES (
                %(inverter_id)s,
                %(timestamp)s,
                %(pid_work_state)s, 
                %(local_remote_control)s, 
                %(power_limitation_switch)s, 
                %(reactive_power_adj_mode)s, 
                %(qp_curve_2)s,
                %(qu_curve_2)s, 
                %(power_limitation_setting)s, 
                %(power_factor_setting)s, 
                %(reactive_power_pct_setting)s, 
                %(power_limitation_adj)s, 
                %(reactive_power_adj)s
            );
        """
        
        mode_payload = {k: first_output.get(k) for k in mode_fields}
        mode_payload["inverter_id"] = id
        mode_payload["timestamp"] = str(datetime.now(tz).replace(microsecond=0))
        cursor.execute(mode_query, mode_payload)

        #2. for inverter_state table
        state_fields = ["start_stop_control", "work_state", "work_state_bitwise", "work_status1", "work_status2", "heart_beat"]
        state_query = """
            INSERT INTO inverter_work_state (inverter_id, timestamp, start_stop_control, work_state, work_state_bitwise, work_status1, work_status2, heart_beat)
            VALUES (%(inverter_id)s, %(timestamp)s, %(start_stop_control)s, %(work_state)s, %(work_state_bitwise)s, %(work_status1)s, %(work_status2)s, %(heart_beat)s);
        """
        state_payload = {k: first_output.get(k, None) for k in state_fields}
        state_payload["inverter_id"] = id
        state_payload["timestamp"] = first_output["timestamp"]
        cursor.execute(state_query, state_payload)

        #3. for inverter_fault_alarm table
        if first_output["fault_alarm_code_1"] != 0 or first_output["pid_alarm_code"] != 0 : #fault alarm table should only be recorded iff there's a false alarm code/ pid alarm code. Otherwise, it should stay empty

            alarm_query = """
                INSERT INTO inverter_fault_alarm (inverter_id, device_fault_timestamp, fault_alarm_code_1, pid_alarm_code)
                VALUES (%(inverter_id)s, %(timestamp)s, %(fault_alarm_code_1)s, %(pid_alarm_code)s); """
            
            cursor.execute(alarm_query, {
                "inverter_id": id,
                "timestamp": first_output["timestamp"],
                "fault_alarm_code_1": first_output.get("fault_alarm_code_1", None),
                "pid_alarm_code": first_output.get("pid_alarm_code", None)

            })

    return first_output

#################################

#Happens recursively every 5 sec
def poll_inverter_state(baseline_data, ip, port, id, UNIT_ID): 
    INVERTER_IP = ip
    PORT = port

    tz = timezone(timedelta(hours=7))
    client = ModbusTcpClient(INVERTER_IP, port = PORT)

    # 1. connect to the inverter and query the data
    if not client.connect():
        print(f"Couldn't connect to the inverter via the given {INVERTER_IP} and {PORT}")
        return
    
    current_poll = {}
    timestamp = str(datetime.now(tz).replace(microsecond=0))
    if not client.connected:
        if not client.connect():
            print("Connection lost. Retrying in 5 seconds...")
            time.sleep(5)

    
    for name, adr, data_type, scale, space, reg_size in master_mapping:
        
        if space == "3X":#read the input registers
            data = client.read_input_registers(address=adr-1, count=reg_size, slave = UNIT_ID)
        elif space == "4X": #read the holding regs
            data = client.read_holding_registers(address=adr-1, count=reg_size, slave=UNIT_ID)

        if not data.isError():
            #Logging normal data into current_poll dict
            if name not in ["local_remote_control", "qp_curve_2", "qu_curve_2"]:
                current_poll[name] = decode_binary(client, data.registers, data_type, scale)
            #Logging special data into current_poll dict
            else:
                current_poll[name] = list(client.convert_from_registers(data.registers, data_type=client.DATATYPE.UINT16))
        else:
            current_poll[name] = baseline_data.get(name)

# 2. check if the data we polled this time has changed from the previous polling
    
    mode_changed = state_changed = alarm_changed = False #see if there are any changes in these tables

    mode_fields = ["pid_work_state", "local_remote_control", "power_limitation_switch", "reactive_power_adj_mode", "qp_curve_2", "qu_curve_2", "power_limitation_setting", "power_factor_setting", "reactive_power_pct_setting", "power_limitation_adj", "reactive_power_adj"]
    state_fields = ["start_stop_control", "work_state", "work_state_bitwise", "work_status1", "work_status2", "heart_beat"]
    alarm_fields = ["fault_alarm_code_1", "pid_alarm_code"]

    #check for diferences
    for k in mode_fields:
        if current_poll.get(k) != baseline_data.get(k):
            mode_changed = True
            baseline_data[k] = current_poll[k]

    for k in state_fields:
        if current_poll.get(k) != baseline_data.get(k):
            state_changed = True
            baseline_data[k] = current_poll[k]

    for k in alarm_fields:
        if current_poll.get(k) != baseline_data.get(k):
            alarm_changed = True
            baseline_data[k] = current_poll[k]
# 3. if the data change, log the changes into database    
    if mode_changed or state_changed or alarm_changed:
        with get_db_cursor() as cursor:
            if mode_changed:
                print(f"[{timestamp}]: inverter_mode_selection Changed")
                mode_query = """
                    INSERT INTO inverter_mode_selection (inverter_id, timestamp, pid_work_state, local_remote_control, 
                    power_limitation_switch, reactive_power_adj_mode, qp_curve_2, qu_curve_2, power_limitation_setting,
                    power_factor_setting, reactive_power_pct_setting, power_limitation_adj, reactive_power_adj)
                    VALUES (%(inverter_id)s, %(timestamp)s, %(pid_work_state)s, %(local_remote_control)s, 
                    %(power_limitation_switch)s, %(reactive_power_adj_mode)s, %(qp_curve_2)s, %(qu_curve_2)s, %(power_limitation_setting)s, 
                    %(power_factor_setting)s, %(reactive_power_pct_setting)s, %(power_limitation_adj)s, %(reactive_power_adj)s);
                """
                mode_payload = {k: baseline_data[k] for k in mode_fields}
                mode_payload.update({"inverter_id": id, "timestamp": timestamp})
                cursor.execute(mode_query, mode_payload)

            if state_changed:
                print(f"[{timestamp}]: inverter_work_state changed")
                state_query = """
                    INSERT INTO inverter_work_state (inverter_id, timestamp, start_stop_control, work_state, work_state_bitwise, work_status1, work_status2, heart_beat)
                    VALUES (%(inverter_id)s, %(timestamp)s, %(start_stop_control)s, %(work_state)s, %(work_state_bitwise)s, %(work_status1)s, %(work_status2)s, %(heart_beat)s);
                """
                payload = {k: baseline_data[k] for k in state_fields}
                payload.update({"inverter_id": id, "timestamp": timestamp})
                cursor.execute(state_query, payload)
            
            if alarm_changed:
                print(f"[{timestamp}] Change caught in Fault Alarms. Inserting record...")
                alarm_query = """
                    INSERT INTO inverter_fault_alarm (inverter_id, device_fault_timestamp, fault_alarm_code_1, pid_alarm_code)
                    VALUES (%(inverter_id)s, %(timestamp)s, %(fault_alarm_code_1)s, %(pid_alarm_code)s);
                """
                payload = {k: baseline_data[k] for k in alarm_fields}
                payload.update({"inverter_id": id, "timestamp": timestamp})
                cursor.execute(alarm_query, payload)

    
    client.close()

if __name__ == "__main__":
    data = poll_inverter_state_init('192.168.100.140', 502, 2, 1)
    poll_inverter_state(copy.deepcopy(data), '192.168.100.140', 502, 2, 1)
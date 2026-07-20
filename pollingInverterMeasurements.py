from datetime import datetime, timedelta, timezone
from pymodbus.client import ModbusTcpClient

#Importing the mapped files, these registers need to be logged every 5 mins
from inverter_running_time_energy import inverter_running_time_energy_mapping
from inverter_and_grid import inverter_and_grid_mapping

#Importing cursor for the database
from db_connect import get_db_cursor

#Importing a function to decode binary numbers to decimal numbers
from decode import decode_binary

master_mapping = inverter_running_time_energy_mapping + inverter_and_grid_mapping

def poll_inverter_measurements(ip, port, id, UNIT_ID):
    INVERTER_IP = ip
    PORT = port

    tz = timezone(timedelta(hours=7)) # Matches the GMT+7 timezone
    client = ModbusTcpClient(INVERTER_IP, port = PORT)

    if not client.connect(): #if pymodbus couldn't connect to the machine via given ip and port
        print(f"Couldn't connect to the inverter via the given {INVERTER_IP} and {PORT}")
        return

    output = {"timestamp": str(datetime.now(tz).replace(microsecond=0)),
              "inverter_id": id}

    for name,adr,data_type,scale,space,reg_size in master_mapping: 

        if space == "3X":#read the input registers
            data = client.read_input_registers(address=adr-1, count=reg_size, slave = UNIT_ID)
        elif space == "4X": #read the holding regs
            data = client.read_holding_registers(address=adr-1, count=reg_size, slave=UNIT_ID)

        #check if polled data is valid, and format the data
        if not data.isError():
            output[name] = decode_binary(client, data.registers, data_type, scale) #dict form: the output named 'voltage' will have a value, processed from the decode_binary function, according to their registers and type
        else:
            output[name] = None
            print(f"polling error at {name} ({adr})")

    client.close()

    try:
        yr = output.get("system_clock_year")
        mo = output.get("system_clock_month")
        dy = output.get("system_clock_day")
        hr = output.get("system_clock_hour")
        mi = output.get("system_clock_minute")
        sc = output.get("system_clock_second")

        if None not in (yr, mo, dy, hr, mi, sc):
            year = int(yr)
            if year < 100: #sometime, modbus returns 2-digit year
                year+=2000
            output["system_clock"] = f"{year:04d}-{int(mo):02d}-{int(dy):02d} {int(hr):02d}:{int(mi):02d}:{int(sc):02d}"
        
        else:
            output["system_clock"] = None
    
    except Exception as e:
        print(f"Error parsing system clock data: {e}")
        output["system_clock"] = None

    

    with get_db_cursor() as cursor:
        #1. query data for the inverter_running_time_energy table
        energy_query = """
            INSERT INTO inverter_running_time_energy (inverter_id, timestamp, daily_power_yields, monthly_power_yields, daily_running_time, total_power_yields, total_running_time)
            VALUES (%(inverter_id)s, %(timestamp)s, %(daily_power_yields)s, %(monthly_power_yields)s, %(daily_running_time)s, %(total_power_yields)s, %(total_running_time)s);
            """
        cursor.execute(energy_query, {k: output.get(k, None) for k in ["inverter_id", "timestamp", "daily_power_yields", "monthly_power_yields", "daily_running_time", "total_power_yields", "total_running_time"]})
        
        #2. query data for the inverter_and_grid table
        grid_query = """
            INSERT INTO inverter_and_grid (
                inverter_id, timestamp, internal_temperature, system_clock, negative_voltage_to_ground, bus_voltage, total_dc_power,
                array_insulation_resistance, active_power_regulation_setpoint, reactive_power_regulation_setpoint,
                total_active_power, total_reactive_power, power_factor, phase_a_voltage, phase_b_voltage, phase_c_voltage,
                phase_a_current, phase_b_current, phase_c_current, grid_frequency, mppt_1_voltage, mppt_1_current,
                mppt_2_voltage, mppt_2_current, string_1_current, string_2_current
            )
            VALUES (
                %(inverter_id)s, %(timestamp)s, %(internal_temperature)s, %(system_clock)s, %(negative_voltage_to_ground)s, %(bus_voltage)s, %(total_dc_power)s,
                %(array_insulation_resistance)s, %(active_power_regulation_setpoint)s, %(reactive_power_regulation_setpoint)s,
                %(total_active_power)s, %(total_reactive_power)s, %(power_factor)s, %(phase_a_voltage)s, %(phase_b_voltage)s, %(phase_c_voltage)s,
                %(phase_a_current)s, %(phase_b_current)s, %(phase_c_current)s, %(grid_frequency)s, %(mppt_1_voltage)s, %(mppt_1_current)s,
                %(mppt_2_voltage)s, %(mppt_2_current)s, %(string_1_current)s, %(string_2_current)s
            );"""
        
        grid_keys = [
            "inverter_id", "timestamp", "internal_temperature", "system_clock", "negative_voltage_to_ground", "bus_voltage", "total_dc_power",
            "array_insulation_resistance", "active_power_regulation_setpoint", "reactive_power_regulation_setpoint",
            "total_active_power", "total_reactive_power", "power_factor", "phase_a_voltage", "phase_b_voltage", "phase_c_voltage",
            "phase_a_current", "phase_b_current", "phase_c_current", "grid_frequency", "mppt_1_voltage", "mppt_1_current",
            "mppt_2_voltage", "mppt_2_current", "string_1_current", "string_2_current"
        ]

        cursor.execute(grid_query, {k: output.get(k, None) for k in grid_keys})

if __name__ == "__main__":
    poll_inverter_measurements('192.168.100.140', 502, 2, 1)
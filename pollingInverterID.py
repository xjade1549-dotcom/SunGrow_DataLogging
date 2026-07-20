from pymodbus.client import ModbusTcpClient

#Importing the mapped files, these registers need to be logged once
from inverters import inverters_mapping
master_mapping = inverters_mapping

#Importing a file that decodes binary numbers
from decode import decode_binary

#Importing the cursor to pick data to and from the database
from db_connect import get_db_cursor


#Polling static data from inverter
def poll_inverter_id(ip, port, id, UNIT_ID): #can be used for every inverters
    INVERTER_IP = ip
    PORT = port

    client = ModbusTcpClient(INVERTER_IP, port=PORT)
    if not client.connect():
        print(f"Couldn't connect to the inverter at IP {INVERTER_IP} port {PORT}")
        return None
    output = {}

    for name, adr, data_type, scale, space, reg_size in master_mapping: # example format in master_mapping list: ("pid_work_state", 5150, "U16", 1.0, "3X")
        
        if space == "3X":# input register (read-only data) 
            data = client.read_input_registers(address=int(adr)-1, count=reg_size, slave=UNIT_ID) #these data are in binary
        elif space == "4X": #holding register (read/write data)
            data = client.read_holding_registers(address=int(adr)-1, count=reg_size, slave=UNIT_ID)#these data are in binary
        
        #Decode normal data
        if adr not in [4990, 4954, 4969]:
            #decoding binary data into decimal data, the storing in the output dict
            if not data.isError():
                output[name] = decode_binary(client, data.registers, data_type, scale)
            else:
                print(f"[{name}:{adr}] Couldn't be read ")
                output[name] = None
        #Decode special data: serial_number, arm_software_ver, dsp_software_ver
        else:
            if data is not None and not data.isError():
                output[name] = client.convert_from_registers(data.registers, data_type=client.DATATYPE.STRING).strip()
            else:
                print(f"[{name}:{adr}] Couldn't be read ")
                output[name] = None

    client.close()

    #Inserting the polled data into the database
    query = """
    INSERT INTO inverters (
        inverter_id, serial_number, protocol_num, protocol_ver, 
        arm_software_ver, dsp_software_ver, device_type_code, nominal_active_power, 
        output_type, nominal_reactive_power, present_country
    )
    VALUES (
        %(inverter_id)s, %(serial_number)s, %(protocol_num)s, %(protocol_ver)s,
        %(arm_software_ver)s, %(dsp_software_ver)s, %(device_type_code)s, %(nominal_active_power)s,
        %(output_type)s, %(nominal_reactive_power)s, %(present_country)s
    )
    ON CONFLICT (inverter_id) DO UPDATE SET
        serial_number = EXCLUDED.serial_number,
        arm_software_ver = EXCLUDED.arm_software_ver,
        dsp_software_ver = EXCLUDED.dsp_software_ver,
        nominal_active_power = EXCLUDED.nominal_active_power; """

    output["inverter_id"] = id

    db_fields = [
        "inverter_id", "serial_number", "protocol_num", 
        "protocol_ver", "arm_software_ver", "dsp_software_ver", "device_type_code", 
        "nominal_active_power", "output_type", "nominal_reactive_power", "present_country"
    ]

    with get_db_cursor() as cursor:
        cursor.execute(query, {k: output.get(k, None) for k in db_fields}) #output is a tuple, consisting of a key (the name of each data), and a value (the data itself)

if __name__ == "__main__":
    poll_inverter_id('192.168.100.140', 502, 2, 1)
from pymodbus.constants import Endian

def decode_binary(client, registers, data_type, scale):
    #1. Handle string data
    if data_type == "UTF-8":
        byte_array = bytearray()
        for reg in registers:
            byte_array.extend(reg.to_bytes(2, byteorder='big'))
        return byte_array.decode('utf-8').strip('\x00').strip()
    elif data_type == "UTF-16":
        byte_array = bytearray()
        for reg in registers:
            byte_array.extend(reg.to_bytes(2, byteorder='big'))
        return byte_array.decode('utf-16').strip('\x00').strip()
    
    #2. Handle numeric data

    elif data_type == "U16":
        val = client.convert_from_registers(registers, data_type=client.DATATYPE.UINT16)
    elif data_type == "S16":
        val = client.convert_from_registers(registers, data_type=client.DATATYPE.INT16)
    elif data_type == "U32":
        val = client.convert_from_registers(
            registers, 
            data_type=client.DATATYPE.UINT32, 
            word_order="little"  # Handles double-word little endian swapping
        )
    elif data_type == "S32":
        val = client.convert_from_registers(
            registers, 
            data_type=client.DATATYPE.INT32, 
            word_order="little"
        )
    else:
        return None
    
    if isinstance(val, list):
        val = val[0]

    return round(float(val) * scale, 1)
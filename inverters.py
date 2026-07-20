#name, adr, data_type, scale, space, reg_size
inverters_mapping = [
    ("protocol_num", 4950, "U32", 1.0, "3X", 2),
    ("protocol_ver", 4952, "U32", 1.0, "3X", 2),
    ("arm_software_ver", 4954, "UTF-16", 1.0, "3X", 15),
    ("dsp_software_ver", 4969, "UTF-16", 1.0, "3X", 15),
    ("serial_number", 4990, "UTF-8", 1.0, "3X", 10),
    ("device_type_code", 5000, "U16", 1.0, "3X", 1),
    ("nominal_active_power", 5001, "U16", 0.1, "3X", 1),
    ("output_type", 5002, "U16", 1.0, "3X", 1),
    ("nominal_reactive_power", 5049, "U16", 0.1, "3X", 1),
    ("present_country", 5114, "U16", 1.0, "3X", 1),
    ("installed_pv_power", 5016, "U16", 0.01, "4X", 1)
]
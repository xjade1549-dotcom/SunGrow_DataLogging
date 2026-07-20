#name, adr, data_type, scale, space, reg_size
inverter_mode_selection_mapping = [
    ("pid_work_state", 5150, "U16", 1.0, "3X", 1),
    ("power_limitation_switch", 5007, "U16", 1.0, "4X", 1),
    ("power_limitation_setting", 5008, "U16", 0.1, "4X", 1),
    ("power_factor_setting", 5019, "S16", 0.001, "4X", 1),
    ("local_remote_control", 5021, "U16", 1.0, "4X", 13),
    ("reactive_power_adj_mode", 5036, "U16", 1.0, "4X", 1),
    ("reactive_power_pct_setting", 5037, "S16", 0.1, "4X", 1),
    ("power_limitation_adj", 5039, "U16", 0.1, "4X", 1),
    ("reactive_power_adj", 5040, "S16", 0.1, "4X", 1),
    ("qp_curve_2", 5116, "String/Block", 1.0, "4X", 19),
    ("qu_curve_2", 5135, "String/Block", 1.0, "4X", 19)
]
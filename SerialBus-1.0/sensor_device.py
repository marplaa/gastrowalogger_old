#VALUE_TYPE_FLAG = 0
#VALUE_TYPE_BYTE = 1
#VALUE_TYPE_INT = 2
#VALUE_TYPE_FLOAT = 3

##DATA_TYPE_BYTE = 0
##DATA_TYPE_INT = 1
##DATA_TYPE_FLOAT = 2
##DATA_TYPE_STRING = 3

# value_ids
DATA = 0
LOW_THRES = 1 
HIGH_THRES = 2
MIN_IMPULSE_LENGTH = 3
MIN_IDLE_LENGTH = 4 
MAX_FAILS = 5 
HYSTERESE = 6
INTERVAL = 7
INVERT = 8
SENSOR_VALUE = 16



value_id_type_map = {0:2, 1:2, 2:2, 3:2, 4:2, 5:1, 6:1, 7:1, 8:0, 16:2}

def get_value_types():
    """return a dictionary of value_id:value_type pairs"""
    return value_id_type_map

def get_data_type():
    """return a dictionary of value_id:value_type pairs"""
    return 1 #for integer

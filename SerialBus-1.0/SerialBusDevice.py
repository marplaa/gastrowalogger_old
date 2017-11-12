from SerialBus import SerialBusTCP

VALUE_TYPE_FLAG = 0
VALUE_TYPE_BYTE = 1
VALUE_TYPE_INT = 2
VALUE_TYPE_FLOAT = 3
DATA_TYPE_BYTE = 0
DATA_TYPE_INT = 1
DATA_TYPE_FLOAT = 2
DATA_TYPE_STRING = 3

class SerialBusDevice:

    def __init__(self, device_addr, serialbus=None, host=None, port=None, device_type=None):
        if serialbus is not None:
            self.serialbus = serialbus
        else:
            if host is not None and port is not None:
                self.serialbus = SerialBusTCP()
                try:
                    self.serialbus.connect(host, port)
                except:
                    raise


        self.device_addr = device_addr
        self.device_type = device_type

    def set_device_addr(self, addr):
        self.device_addr = addr

    def set_device_type(self, device_type):
        self.device_type = device_type

    def set_bus(self, bus):
        self.serialbus = bus

    def get_value(self, value_id, value_type="auto"):

        if value_type == "auto" and self.device_type is not None:
            value_type = self.device_type.get_value_types()[value_id]
            
        
        answer = self.serialbus.send_request_wait(self.device_addr, bytes([24 + value_type, value_id]))

        if not (answer[0] == (24 + value_type) and answer[1] == value_id):
            return None

        if value_type == VALUE_TYPE_FLAG:
            if answer[2] == 0:
                return False
            else:
                return True
        elif value_type == VALUE_TYPE_BYTE:
            return answer[2]
        elif value_type == VALUE_TYPE_INT:
            return int.from_bytes(answer[2:], byteorder = "big")
        elif value_type == VALUE_TYPE_FLOAT:
            return float.from_bytes(answer[2:], byteorder = "big")
        else:
            return "false"



    def set_value(self, value_id, value, value_type="auto"):
        #answer = self.serialbus.send_request_wait(self.device_addr, bytes([24 + value_type, value_id]))

        if value_type == "auto" and self.device_type is not None:
            value_type = self.device_type.get_value_types()[value_id]
            
        if value_type == VALUE_TYPE_FLAG:
            if value:
                data = bytes([1])
            else:
                data = bytes([0])
        elif value_type == VALUE_TYPE_BYTE:
            data = value.to_bytes(1, byteorder='big')
        elif value_type == VALUE_TYPE_INT:
            data = value.to_bytes(2, byteorder='big')
        elif value_type == VALUE_TYPE_FLOAT:
            data = value.to_bytes(4, byteorder='big')
        else:
            return False

        self.serialbus.send_msg(self.device_addr, bytes([28 + value_type, value_id]) + data)
        answer = self.get_value(value_id, value_type)
        
        if answer == value:
            return True
        else:
            return False
        
    def get_data(self, value_type="auto"):

        if value_type == "auto" and self.device_type is not None:
            value_type = self.device_type.get_data_type()
            
        answer = self.serialbus.send_request_wait(self.device_addr, bytes([32 + value_type]))

        if not (answer[0] == (32 + value_type)):
            return None

        if value_type == DATA_TYPE_BYTE:
            return answer[1]

        elif value_type == DATA_TYPE_INT:
            return int.from_bytes(answer[1:], byteorder = "big")
        elif value_type == DATA_TYPE_FLOAT:
            return float.from_bytes(answer[1:], byteorder = "big")
        elif value_type == DATA_TYPE_STRING:
            return str.from_bytes(answer[1:], byteorder = "big") # todo
        else:
            return "false"

    def get_config(self, timeout=10**4):
        import json
        answer = self.serialbus.send_request_wait(self.device_addr, bytes([4]), timeout = timeout)
        answer_str = "";
        if answer is not None:
            for char in answer:
                answer_str += (chr(char))
            return json.loads(answer_str)
        else:
            return None

    def get_status(self):
        answer = self.serialbus.send_request_wait(self.device_addr, bytes([11 << 2]))
        answer_str = "";
        for char in answer:
            answer_str += (chr(char))
        return answer_str


    def reset_defaults(self):
        self.serialbus.send_msg(self.device_addr, bytes([10 << 2]))

    def reset_device(self):
        self.serialbus.send_msg(self.device_addr, bytes([2 << 2]))

    def connect(self, host, port):
        if not self.serialbus.is_connected():
            self.serialbus.connect(host, port)

    def close(self):
        self.serialbus.close()
        
    def start_calibration(self):
        serialbus.send_msg(self.device_addr, bytes([0b00101001]))
        
    def stop_calibration(self):
        serialbus.send_msg(self.device_addr, bytes([0b00101000]))
            

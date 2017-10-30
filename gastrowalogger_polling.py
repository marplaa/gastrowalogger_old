#!/usr/bin/env python3
import sqlite3
import time
import datetime
from SerialBus import SerialBusTCP
import SerialBusDevice
import sensor_device
import logging
import sys


last_values = {}
sensors = {}
_database = ""
_sb_host = ""
_sb_port = -1
conn = None

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_sensors():
    
    # get active sensors
    cur = conn.execute("SELECT * FROM sensors WHERE id IN (SELECT * FROM active)")
    row = cur.fetchone()
    while row is not None:
        sensors.update({row["label"] + ":" + str(row["id"]) :  row})
        row = cur.fetchone()
    
    for sensor in sensors:
        last_values[sensor] = (0, -1)
        

def store_data():
    global last_values
    
    serialbus = SerialBusTCP()
    serialbus.connect(_sb_host, _sb_port)
    
    timestamp = int(time.time())
    
    #aquire sensor data
    
    for sensor in sensors:
        try:
            device = SerialBusDevice.SerialBusDevice(sensors[sensor]["address"], serialbus=serialbus, device_type=sensor_device)
            value =  int(device.get_data())
            if last_values[sensor][1] == 0 and value != 0:
                conn.execute("INSERT INTO consumptions (sensor, 'timestamp', 'count') VALUES (?,?,?)", (sensors[sensor]["id"], last_values[sensor][0], 0))
            
            if value != 0:
                conn.execute("INSERT INTO consumptions (sensor, 'timestamp', 'count') VALUES (?,?,?)", (sensors[sensor]["id"], timestamp, value))
                
            last_values[sensor] = (timestamp, value)
        except Exception as e:
            if hasattr(e, 'message'):
                print(e.message)
            else:
                print(e)
            pass
        
    serialbus.close()
    conn.commit()
    

def start_polling(database, sb_host, sb_port, interval):
    global conn, _sb_host, _sb_port
    _database = database
    _sb_host = sb_host
    _sb_port = sb_port
    
    print('Started new polling thread (database=' + _database + ", SerialBus-Host=" + _sb_host + ", SerialBus-Port=" + str(_sb_port) + ", interval=" + str(interval) +")")
    
    conn = sqlite3.connect(_database)
    conn.row_factory = dict_factory
    
    try:
        
        while True:
            get_sensors()
            store_data()
            time.sleep(interval)
    
    except Exception as e:
        if hasattr(e, 'message'):
            print(e.message)
        else:
            print(e)
            
if __name__ == '__main__':
    import configparser
    
    config = configparser.ConfigParser()
    config.read(sys.path[0] + '/config.ini')
    
    database = config.get("DATABASE", "DATABASE")
    if not database.startswith("/"):
        database = sys.path[0] + "/" + database
        
    start_polling(database, config.get("SERIALBUS", "SERIALBUS_HOST"), config.getint("SERIALBUS", "SERIALBUS_PORT"), config.getint("GASTROWALOGGER", "RECORDING_INTERVAL"))





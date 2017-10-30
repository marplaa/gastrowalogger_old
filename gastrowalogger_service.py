#!/usr/bin/env python3
import argparse
from threading import Thread
import subprocess

import gastrowalogger_polling
import weather_polling
import configparser
import logging
import sys
import atexit
from time import sleep


config = configparser.ConfigParser()
config.read(sys.path[0] + '/config.ini')

logfile = config.get("GASTROWALOGGER", "LOG_FILE")
if not logfile.startswith("/"):
    logfile = sys.path[0] + "/" + logfile

logging.basicConfig(filename=logfile,level=logging.DEBUG, format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
print('Started')

sensor_polling_thread = None
weather_polling_thread = None
server_proc = None

def start_polling_sensors():
    global sensor_polling_thread
    
    sensor_polling_thread = Thread(target=gastrowalogger_polling.start_polling, args=(database, config.get("SERIALBUS", "SERIALBUS_HOST"), config.getint("SERIALBUS", "SERIALBUS_PORT"), config.getint("GASTROWALOGGER", "RECORDING_INTERVAL")))
    
    sensor_polling_thread.daemon = True

    sensor_polling_thread.start()
    
def start_polling_weather():
    global sensor_polling_thread
    
    weather_polling_thread = Thread(target=weather_polling.start_polling, args=(database, config.get("WEATHER", "API_KEY")))
    
    weather_polling_thread.daemon = True

    weather_polling_thread.start()
    

def start_server(host, port):
    logfile = config.get("GASTROWALOGGER", "SERVER_LOG_FILE")
    if not logfile.startswith("/"):
        logfile = sys.path[0] + "/" + logfile

    try:
        global server_proc
        #server_proc = subprocess.Popen(["gunicorn", "--bind", host + ":" + str(port), "wsgi:application", "--worker-class", "eventlet", "-w", "1"])
        server_proc = subprocess.Popen(["bin/gunicorn", "--bind", host + ":" + str(port), "--log-file", logfile, "wsgi:application", "--worker-class", "eventlet", "-w", "1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=sys.path[0])
    
        print("Started gunicorn server (PID: " + str(server_proc.pid) + ") at: " + host + ":" + str(port))
    except Exception as e:
        if hasattr(e, 'message'):
            print(e.message)
        else:
            print(e)
        pass


    
def clean_up():
    
    if server_proc:
        server_proc.terminate()
    #error_lines = server_proc.communicate()[1]

    #logging.info("gunicorn: " + error_lines.decode("utf-8"))
        

atexit.register(clean_up)


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='Gastrowalogger Service')
    
    parser.add_argument('--no_polling', action='store_true')
    parser.add_argument('--no_weather', action='store_true')

    args = parser.parse_args()
    
    database = config.get("DATABASE", "DATABASE")
    if not database.startswith("/"):
        database = sys.path[0] + "/" + database
    
    if not args.no_polling:
        start_polling_sensors()
    if not args.no_weather:
        start_polling_weather()
    #sensor_polling_thread = Thread(target=gastrowalogger_polling.start_polling_sensors, args=(database, config.get("SERIALBUS", "SERIALBUS_HOST"), config.getint("SERIALBUS", "SERIALBUS_PORT"), config.getint("GASTROWALOGGER", "RECORDING_INTERVAL")))
    #server_proc = subprocess.Popen(["gunicorn", "--bind", host + ":" + str(port), "wsgi:application", "--worker-class", "eventlet", "-w", "1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #server_thread = Thread(target=start_server, args=(config.get("GASTROWALOGGER", "HOST"), config.getint("GASTROWALOGGER", "PORT")))
    start_server(config.get("GASTROWALOGGER", "HOST"), config.getint("GASTROWALOGGER", "PORT"))
    
    #sensor_polling_thread.daemon = True

    
    #sensor_polling_thread.start()
    #server_thread.start()
    
    while True:
        # everything fine
        sleep(60)
        
        if not args.no_polling:
            if not sensor_polling_thread.is_alive():
                #restart polling thread
                print("Polling thread closed")
                start_polling_sensors()
        if not args.no_weather:
            if not weather_polling_thread.is_alive():
                #restart polling thread
                print("Weather thread closed")
                start_polling_weather()
        if server_proc.poll() is not None:
            print("Server Process stopped: " + server_proc.poll())
            start_server(config.get("GASTROWALOGGER", "HOST"), config.getint("GASTROWALOGGER", "PORT"))
    #clean_up()

    

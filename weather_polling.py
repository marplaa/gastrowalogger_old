#!/usr/bin/env python3
import sqlite3
import time
import datetime
from apixu.client import ApixuClient, ApixuException

#api_key = '532d0aaea88544cb82a155247163012'

client = None

_database = ""
conn = None

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

#current = client.getCurrentWeather(q='Hamm')


def store_data():
    global client
            
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    
    data_yesterday = client.getForecastWeather(q='Hamm', dt=yesterday.strftime('%Y-%m-%d'))

    date_epoch = data_yesterday['forecast']['forecastday'][0]['date_epoch']
    weather_yesterday = data_yesterday['forecast']['forecastday'][0]['day']
    
    
    conn.execute("INSERT INTO weather ('timestamp', 'avg_temp', 'precip_mm') VALUES (?,?,?)", (date_epoch, weather_yesterday['avgtemp_c'], weather_yesterday['totalprecip_mm']))
        
        # print("speichern...")
    #else:
     #   print("nicht speichern")
    #last_temp = temp
    #last_pressure = pressure
    # Save (commit) the changes
    #print(last_temp, last_pressure)
    conn.commit()
    

def start_polling(database, api_key):
    global client, conn
    
    client = ApixuClient(api_key)

    _database = database
    
    print('Started new weather thread (database=' + _database + ", api_key=" + api_key)
    
    conn = sqlite3.connect(_database)
    conn.row_factory = dict_factory
    
    try:
    
        while True:
            store_data()
            time.sleep(86400)

    except:
        #raise
        
        raise


if __name__ == '__main__':
    import configparser
    
    config = configparser.ConfigParser()
    config.read(sys.path[0] + '/config.ini')
    
    database = config.get("DATABASE", "DATABASE")
    api_key = config.get("WEATHER", "API_KEY")
    if not database.startswith("/"):
        database = sys.path[0] + "/" + database
        
    start_polling(database, api_key)

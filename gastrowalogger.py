import os
import sqlite3
import threading
import configparser
from flask import Flask, jsonify, request, session, g, redirect, url_for, abort, render_template, flash, make_response
from SerialBus import SerialBusTCP, SerialBusDevice
import sensor_device
from datetime import datetime, timedelta
from time import timezone
import json
from flask_socketio import SocketIO, send, emit
from pytz import timezone
import pytz
import logging
import sys
import math
from flask.ext.babel import Babel, gettext, ngettext, Locale
from babel.dates import parse_date, parse_time, format_date, format_time, format_datetime

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class NoSuchSensorError(Error):
    """Exception raised for errors in the input.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message
        
class NoDataError(Error):
    pass


#_serialbus = None

lock = threading.Lock()

# create our little application :)
app = Flask(__name__)
#app.config.from_object('config.BaseConfig')

# Load default config and override config from an environment variable
# app.config.update(dict(
#     DATABASE='gastrowalogger.db'
# ))
app.config.from_envvar('GASTROWALOGGER_SETTINGS', silent=True)

#app.secret_key = 'A0Zsr98j/3yX*R~XHH!jm22WX/,?RT'
socketio = SocketIO(app)


#app.run(host= '192.168.2.76')

# if __name__ == '__main__':
#     socketio.run(app, debug=True)

# CONSTANTS TODO implement in app.config

def get_sensor_by_name(sensor_name):
    
    if sensor_name not in sensors:
        raise NoSuchSensorError(sensor_name)
    else:
        return sensors[sensor_name]
    
def get_active_sensor_by_type(type):
    for sensor in sensors:
        if sensors[sensor]["type"] == type and sensors[sensor]["status"] == "active":
            return get_sensor_by_name(sensor)
    raise NoSuchSensorError(sensor_name)
        

config = configparser.ConfigParser()
config.read(sys.path[0] + '/config.ini')

app.secret_key = config.get("GASTROWALOGGER", "SECRET_KEY")

tz = timezone(config.get("TIME", "TIMEZONE"))
babel = Babel(app)

logfile = config.get("GASTROWALOGGER", "LOG_FILE")
if not logfile.startswith("/"):
    logfile = sys.path[0] + "/" + logfile

logging.basicConfig(filename=logfile,level=logging.DEBUG, format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
logging.info('Started FLASK app')


sensors = {}

types = {"water" : "1A",
         "gas" : "1B",
         "power" : "1C"
         }


@babel.localeselector
def get_locale():
    return config.get("GASTROWALOGGER", "LOCALE")

def get_sensors():
    db = get_db()
    # get active sensors
    cur = db.execute("SELECT * FROM sensors WHERE id IN (SELECT * FROM active)")
    row = cur.fetchone()
    while row is not None:
        row.update({"status" : "active"})
        sensors.update({row["label"] + "-" + str(row["id"]) :  row})
        row = cur.fetchone()
        
    cur = db.execute("SELECT * FROM sensors WHERE id NOT IN (SELECT * FROM active)")
    row = cur.fetchone()
    while row is not None:
        row.update({"status" : "inactive"})
        sensors.update({row["label"] + "-" + str(row["id"]) :  row})
        row = cur.fetchone()
    
    
app.before_first_request(get_sensors)

@app.context_processor
def inject_dict_for_all_templates():
    return dict(sensors=sensors)
        
#except:
    #pass
    
@app.route('/sensor/_get_sensors')
def get_sensors_json():
    return jsonify(sensors)

@app.route('/sensor/sensor', methods=['GET'])
def sensor_settings():

    try:
        if request.args.get("type"):
            type = request.args["type"]
            for sensor in sensors:
                if sensors[sensor]["type"] == type and sensors[sensor]["status"] == "active":
                    sensor_name = sensor
                    break
        else:
            sensor_name = request.args.get("sensor")
        sensor = sensors[sensor_name]
        if sensor is not None:
            settings = get_sensor_settings(sensor)
            settings.update({"resolution" : config.getint(sensor["type"].upper(), "PLOTTING_RESOLUTION")})
            settings.update({"sensor" : sensor_name})
        
            return render_template('sensor_settings.html', settings = settings, sensor = sensor, current_sensor = sensor_name)
    
    except:
        flash("Error while retrieving data from device: ")
        raise
        return render_template('sensor_settings.html')

    
def get_sensor_settings(sensor):
    
    global lock
    with lock:
        try:
            settings = {}
            serialbus = connect_serialbus()
            device = SerialBusDevice(sensor['address'], serialbus, device_type = sensor_device)

            settings["highThres"] = device.get_value(sensor_device.HIGH_THRES)
            settings["lowThres"] = device.get_value(sensor_device.LOW_THRES)
            settings["hysteresis"] = device.get_value(sensor_device.HYSTERESE)
            settings["min_impulse_length"] = device.get_value(sensor_device.MIN_IMPULSE_LENGTH)
            settings["min_idle_length"] = device.get_value(sensor_device.MIN_IDLE_LENGTH)
            settings["max_fails"] = device.get_value(sensor_device.MAX_FAILS)
            settings["interval"] = device.get_value(sensor_device.INTERVAL)
            settings["count"] = device.get_value(sensor_device.DATA)
            if device.get_value(sensor_device.INVERT):
                invert = True
            else:
                invert = False
            settings["invert"] = invert
            return settings
            #return jsonify(settings)
        except:
            flash("Error while retrieving data from device: ")
            raise
            return -1
        finally:
            if serialbus is not None:
                serialbus.close()
                
@app.route('/sensor/_set_settings', methods=['POST'])
def set_sensor_settings():
    try:
        sensor_name = request.form["sensor"]
        sensor = sensors[sensor_name]
        
        ok = True
        serialbus = connect_serialbus()
        device = SerialBusDevice(sensor["address"], serialbus, device_type = sensor_device)
        ok &= device.set_value(sensor_device.HIGH_THRES, int(request.form["highThres"]))
        ok &= device.set_value(sensor_device.LOW_THRES, int(request.form["lowThres"]))
        ok &= device.set_value(sensor_device.MIN_IMPULSE_LENGTH, int(request.form["min_impulse_length"]))
        ok &= device.set_value(sensor_device.MIN_IDLE_LENGTH, int(request.form["min_idle_length"]))
        ok &= device.set_value(sensor_device.MAX_FAILS, int(request.form["max_fails"]))
        ok &= device.set_value(sensor_device.HYSTERESE, int(request.form["hysteresis"]))
        ok &= device.set_value(sensor_device.INTERVAL, int(request.form["interval"]))
        if 'invert' in request.form:
            ok &= device.set_value(sensor_device.INVERT, True)
        else:
            ok &= device.set_value(sensor_device.INVERT, False)

        return jsonify(ok)
    except:
        raise
    finally:
        if serialbus is not None:
            serialbus.close()

@app.route('/sensors/_activate', methods=['POST'])
def activate_sensor():
    sensor = request.form['sensor']
    
    sensors_new = {}
    sensors[sensor].update({"status" : "active"})
    
    try:
        # Reading data back
        
        with open('sensors.json', 'r') as f:
            sensors_new = json.load(f)
        
    except:
        pass
    
    sensors_new.update({sensor : sensors[sensor]})
    
    # Writing JSON data
    with open('sensors.json', 'w') as f:
        json.dump(sensors_new, f)
        return jsonify({"id" : sensors[sensor]["id"]})
    
    return jsonify(-1)

@app.route('/sensors/_toggle_status', methods=['POST'])
def toggle_sensor_status():
    
    sensor = request.form['sensor']
    if sensors[sensor]["status"] == "active":
        
        # deactivate
        sensors[sensor].update({"status" : "inactive"})
        db = get_db()
        cur = db.execute("DELETE FROM active WHERE sensor = ?", (sensors[sensor]["id"],)) 
        db.commit()

        
    elif sensors[sensor]["status"] == "inactive":
        # activate
        sensors[sensor].update({"status" : "active"})
        db = get_db()
        cur = db.execute("INSERT INTO active (sensor) VALUES (?)", (sensors[sensor]["id"],)) 
        db.commit()

    else:
        return -1

    return jsonify({"id" : sensors[sensor]["id"], "status" : sensors[sensor]["status"]})



@app.route('/sensor/_get_calibration_data', methods=['GET'])
def get_calibration_data_():
    
    sensor_name = request.args["sensor"]
    sensor = sensors[sensor_name]
    
    global lock
    with lock:
        try:
            data = {}

            serialbus = connect_serialbus()
            device = SerialBusDevice(sensor["address"], serialbus, device_type = sensor_device)

            data["highThres"] = device.get_value(sensor_device.HIGH_THRES)
            data["lowThres"] = device.get_value(sensor_device.LOW_THRES)
            data["value"] = device.get_value(sensor_device.SENSOR_VALUE)
            data["count"] = device.get_value(sensor_device.DATA)
            return jsonify(data)
        except:
            raise
            return jsonify(-1)
        finally:
            if serialbus is not None:
                serialbus.close()



            

@app.route('/sensor/_get_settings', methods=['GET'])
def _get_sensor_settings():
    sensor_name = request.args["sensor"]
    sensor = sensors[sensor_name]
    return jsonify(get_sensor_settings(sensor))


def get_meter_reading(sensor):
    meter_reading = 0
    
    db = get_db()
    #print("SELECT SUM(count) * " + str(config.getfloat(sensor["type"].upper(),"UNITS_PER_IMPULSE"))  + " + last_reading.reading AS reading FROM consumptions, (SELECT MAX(timestamp) as timestamp, reading FROM readings WHERE sensor = ?) AS last_reading WHERE consumptions.sensor = ? and consumptions.timestamp > last_reading.timestamp")
    cur = db.execute("SELECT SUM(count) * " + str(config.getfloat(sensor["type"].upper(),"UNITS_PER_IMPULSE"))  + " + last_reading.reading AS reading FROM consumptions, (SELECT MAX(timestamp) as timestamp, reading FROM readings WHERE sensor = ?) AS last_reading WHERE consumptions.sensor = ? and consumptions.timestamp > last_reading.timestamp", (sensor["id"],sensor["id"]))
    row = cur.fetchone()
    
    if row is not None:
        if row['reading'] is not None:
            meter_reading = row['reading']
        
        else:
            cur = db.execute("SELECT reading FROM readings WHERE sensor = ? ORDER BY timestamp DESC", (sensor["id"],))
            row = cur.fetchone()
            if row is not None:
                if row['reading'] is not None:
                    meter_reading = row['reading']

             
    #db.close()
    logging.info("meter_reading: " + str(meter_reading))
    return meter_reading
    
@app.route('/meters/save_meter_reading', methods=['POST'])
def save_meter_reading():
    
    new_reading = request.form["value"]
    note = request.form["note"]
    sensor = request.form["sensor"]
    
    if not note:
        note=""
    if new_reading and sensor:
        try:
        
            db = get_db()
            cur = db.execute("INSERT INTO readings (sensor, timestamp, reading, note) VALUES (?, strftime('%s', 'now'), ?, ?)", (sensors[sensor]["id"], new_reading, note))
            db.commit()
            db.close()
            flash(gettext('New reading was successfully added!'), 'success')
            logging.info("added new meter reading for Sensor " + sensors[sensor]["alias"] + "; reading: " + new_reading)
        except:
            flash(gettext('Error while adding reading'), 'danger')
            logging.error("failed to add new meter reading for Sensor " + sensors[sensor]["alias"] + "; reading: " + new_reading)
            pass
        
    else:
        flash('Keinen ZÃ¤hlerstand angegeben!', 'info')
        
    return redirect('/meters/meter_reading?sensor=' + sensor)


@app.route('/sensor/current', methods=['GET'])
def current_usage():
    
    if request.args.get("type"):
        type = request.args["type"]
        for sensor in sensors:
            if sensors[sensor]["type"] == type and sensors[sensor]["status"] == "active":
                #sensor_name = sensor
                #break
                 return redirect('sensor/current?sensor=' + sensor)
    else:
        sensor_name = request.args.get("sensor")
     
    db = get_db()
    cur = db.execute('SELECT amount FROM prices WHERE type = ? ORDER BY timestamp_from DESC', (types[sensors[sensor_name]["type"]],))
    entry = cur.fetchone()
    db.close()
    return render_template('current_usage.html', euro_per_m3 = entry['amount'], sensor = sensor_name)

@app.route('/sensor/_get_live_data', methods=['GET'])
def _get_live_data():
    
    sensor_name = request.args.get("sensor")
    sensor = sensors[sensor_name]
    
    try:
        serialbus = connect_serialbus()
        device = SerialBusDevice(sensor["address"], serialbus, device_type = sensor_device)
        value = device.get_value(sensor_device.DATA);
        return jsonify(value)
    except:
        return jsonify(-1)


@app.route('/meters/meter_reading', methods=['GET'])
def meter_reading():
    
    if request.args.get("type"):
        type = request.args["type"]
        for sensor in sensors:
            if sensors[sensor]["type"] == type and sensors[sensor]["status"] == "active":
                #sensor_name = sensor
                #break
                 return redirect('meters/meter_reading?sensor=' + sensor)
    else:
        sensor_name = request.args.get("sensor")
        
    sensor = sensors[sensor_name]

    db = get_db()
    cur = db.execute('SELECT amount FROM prices WHERE type = ? ORDER BY timestamp_from DESC', (types[sensors[sensor_name]["type"]],))
    entry = cur.fetchone()
    price_per_unit = entry["amount"]
    
    entries = []
    
    cur = db.execute("SELECT timestamp AS date, reading, note FROM readings where sensor = ? ORDER BY timestamp", (sensor["id"],))
    row = cur.fetchone()
    while row is not None:
        row.update({"date" : format_datetime(tz.fromutc(datetime.utcfromtimestamp(row["date"])), locale = config.get("GASTROWALOGGER", "LOCALE"), format = "short")})
        entries.append(row)
        row = cur.fetchone()
    
    return render_template('meter_readings.html', entries = entries, meter_reading = round(get_meter_reading(sensor), 5), price_per_unit = price_per_unit, current_sensor = sensor_name)


@app.route('/charts', methods=['GET'])
def plot_chart():
    
    if request.args.get("type"):
        type = request.args["type"]
        for sensor in sensors:
            if sensors[sensor]["type"] == type and sensors[sensor]["status"] == "active":
                return redirect('/charts?sensor=' + sensor)
    else:
        sensor_name = request.args.get("sensor")
    
    if sensor_name not in sensors:
        flash(gettext("Unknown sensor:") + " " + sensor_name, 'danger')
        return redirect('/')
        
    return render_template('charts.html', current_sensor=sensor_name)

@app.route('/sensor/rename', methods=['POST'])
def _rename_sensor():
    sensor_name = request.form["sensor"]
    new_alias = request.form["new_alias"]
    
    if sensor_name not in sensors:
        flash(gettext("Unknown sensor:") + " " + sensor_name, 'danger')
        return redirect('/')
    
    try:
        db = get_db()
        cur = db.execute("UPDATE sensors SET alias = ? WHERE id = ?", (new_alias, sensors[sensor_name]["id"])) 
        db.commit()
        get_sensors()
        flash(gettext("Alias successfully changed!"), "success")
        return redirect('/sensor/sensor?sensor=' + sensor_name)
    except Exception as e:
        if hasattr(e, 'message'):
            flash(gettext("Error while saving new alias for:") + " " + sensor_name + " - " + e.message, "danger")
            return redirect('/sensor/sensor?sensor=' + sensor_name)
        else:
            flash(gettext("Error while saving new alias for:") + " " + sensor_name + " - " + str(e), "danger")
            return redirect('/sensor/sensor?sensor=' + sensor_name)
            

def add_sensor_to_database(sensor):
    
    if sensor not in sensors:
        return -1

    sensor = sensors[sensor]

    values = [sensor["label"], sensor["id"], sensor["type"], sensor["vendor"], sensor["author"], sensor["description"], sensor["alias"], sensor["email"], sensor["address"], sensor["version"]]

    db = get_db()
    cur = db.execute("INSERT INTO sensors (label, id, type, vendor, author, description, alias, email, address, version)  VALUES (?, ?, ? ,? ,? ,?, ?, ?, ?, ?)", values) 
    db.commit()
    



@app.route('/charts/_get_chart_old2', methods=['POST', 'GET'])
def calculate_chart_old2():#+from_time, to_time):
    
    sensor_name = request.args["sensor"]
    try:
        sensor = get_sensor_by_name(sensor_name)
    except NoSuchSensorError():
        #flash(gettext('No such Sensor:') + " " + sensor_name, 'danger')
        return jsonify({"status" : "error", "error_msg" : gettext('No such Sensor') + ": " + sensor_name})
        

    resolution = int(request.form["resolution"])
    locale = config.get("GASTROWALOGGER", "LOCALE")

    from_date = parse_date(request.form["from_date"], locale=locale)
    from_time = parse_time(request.form["from_time"]+":00", locale=locale)
    from_date_time = datetime.combine(from_date, from_time)
    
    to_date = parse_date(request.form["to_date"], locale=locale)
    to_time = parse_time(request.form["to_time"]+":00", locale=locale)
    to_date_time = datetime.combine(to_date, to_time)
    
    data = get_data(sensor, from_date_time, to_date_time, resolution, locale)
    
    gjson = {}
    
    gjson['cols'] = [{'label': gettext("date"), 'type': 'string' }, 
                     {'label': "x" + str(config.getfloat(sensor["type"].upper(),"UNITS_PER_IMPULSE")) + " " + config.get(sensor["type"].upper(), "UNIT_STRING"), 'type': 'number' },
                     {"type": "string", "p" : { "role" : "style" } }
                     ]
    
    gjson['rows'] = []
    
    gjson['sensor'] = sensor
    
    gjson['status'] = "ok"
    
    for row in data["rows"]:
        time_from = format_time(row["datetime_from"], locale=locale, format='short')
        time_to = format_time(row["datetime_to"], locale=locale, format='short')
        date = format_date(row["datetime_from"], locale=locale, format='short')  
            
        x_text = date + ' ' + gettext("from") + " " + time_from + ' ' + gettext("to") + ' ' + time_to
        x_label = date
        if resolution < 86400:
            x_label = time_from
        elif resolution >= 2*86400:
            # more than two days, show startdate and enddate of point
            date_to = format_date(row["datetime_to"], locale=locale, format='short')
            x_text = date + ' ' + gettext("to") + ' ' + date_to
        
        #date_time = datetime.datetime.fromtimestamp(int(row['timestamp'])).strftime('%H:%M:%S')
        gjson['rows'].append({'c':[{'v': x_label, 'f' : x_text},
                                   {'v': row['value']}, 
                                   {'v': "fill-color: #FF3"}
                                   ]})
    
    #gjson['rows'] = [{'c':[{'v':'a'}, {'v':6}]}, {'c':[{'v':'b'}, {'v': 4}]}]
    return jsonify(gjson)

@app.route('/charts/_get_chart', methods=['POST', 'GET'])
def calculate_chart():#+from_time, to_time):
    
    sensor_name = request.args["sensor"]
    try:
        sensor = get_sensor_by_name(sensor_name)
    except NoSuchSensorError():
        #flash(gettext('No such Sensor:') + " " + sensor_name, 'danger')
        return jsonify({"status" : "error", "error_msg" : gettext('No such Sensor') + ": " + sensor_name})
        

    resolution = int(request.form["resolution"])
    locale = config.get("GASTROWALOGGER", "LOCALE")

    from_date = parse_date(request.form["from_date"], locale=locale)
    from_time = parse_time(request.form["from_time"]+":00", locale=locale)
    from_date_time = datetime.combine(from_date, from_time)
    
    to_date = parse_date(request.form["to_date"], locale=locale)
    to_time = parse_time(request.form["to_time"]+":00", locale=locale)
    to_date_time = datetime.combine(to_date, to_time)
    
    data = get_data(sensor, from_date_time, to_date_time, resolution, locale)
    
    gjson = {}
    
    gjson['labels'] = []
    gjson['data'] = []
    
    gjson['sensor'] = sensor
    
    gjson['status'] = "ok"
    
    for row in data["rows"]:
        time_from = format_time(row["datetime_from"], locale=locale, format='short')
        time_to = format_time(row["datetime_to"], locale=locale, format='short')
        date = format_date(row["datetime_from"], locale=locale, format='short')  
            
        x_text = date + ' ' + gettext("from") + " " + time_from + ' ' + gettext("to") + ' ' + time_to
        x_label = date
        if resolution < 86400:
            x_label = time_from
        elif resolution >= 2*86400:
            # more than two days, show startdate and enddate of point
            date_to = format_date(row["datetime_to"], locale=locale, format='short')
            x_text = date + ' ' + gettext("to") + ' ' + date_to
        
        #date_time = datetime.datetime.fromtimestamp(int(row['timestamp'])).strftime('%H:%M:%S')
        gjson["labels"].append(x_label)
        gjson["data"].append(row['value'])
    
    #gjson['rows'] = [{'c':[{'v':'a'}, {'v':6}]}, {'c':[{'v':'b'}, {'v': 4}]}]
    return jsonify(gjson)

@app.route('/charts/_get_csv', methods=['POST', 'GET'])
def calculate_csv():
    
    sensor_name = request.args["sensor"]
    try:
        sensor = get_sensor_by_name(sensor_name)
    except NoSuchSensorError():
        #flash(gettext('No such Sensor:') + " " + sensor_name, 'danger')
        return jsonify({"status" : "error", "error_msg" : gettext('No such Sensor:') + " " + sensor_name})
        

    resolution = int(request.form["resolution"])
    locale = config.get("GASTROWALOGGER", "LOCALE")

    from_date = parse_date(request.form["from_date"], locale=locale)
    from_time = parse_time(request.form["from_time"]+":00", locale=locale)
    from_date_time = datetime.combine(from_date, from_time)
    
    to_date = parse_date(request.form["to_date"], locale=locale)
    to_time = parse_time(request.form["to_time"]+":00", locale=locale)
    to_date_time = datetime.combine(to_date, to_time)
    
    data = get_data(sensor, from_date_time, to_date_time, resolution, locale)
    
    csv = gettext("date") + ";" + gettext("from") + ";" + gettext("to") + ";x"  + str(config.getfloat(sensor["type"].upper(),"UNITS_PER_IMPULSE")) + " " + config.get(sensor["type"].upper(),"UNIT_STRING") + "\n"
    
    filename = sensor["type"] + "_consumption_" + request.form["from_date"] + "-" +  request.form["to_date"]
    
    for row in data["rows"]:
        time_from = format_time(row["datetime_from"], locale=locale, format='short')
        time_to = format_time(row["datetime_to"], locale=locale, format='short')
        date = format_date(row["datetime_from"], locale=locale, format='short')
            

        #date_time = datetime.datetime.fromtimestamp(int(row['timestamp'])).strftime('%H:%M:%S')
        csv += date + ';' + time_from + ";" + time_to + ';' + str(row['value']) + '\n'
    
    response = make_response(csv)
    # This is the key: Set the right header for the response
    # to be downloaded, instead of just printed on the browser
    response.headers["Content-Disposition"] = "attachment; filename=" + filename + ".csv"
    return response
    

def get_data(sensor, from_date_time, to_date_time, resolution, locale):
    
    data = {}

    from_date_time_tz = tz.normalize(tz.localize(from_date_time))
    from_date_time_utc = from_date_time_tz.astimezone(pytz.timezone('UTC'))    

    to_date_time_tz = tz.normalize(tz.localize(to_date_time))
    to_date_time_utc = to_date_time_tz.astimezone(pytz.timezone('UTC'))    
    
#     to_datetime = datetime.strptime(request.form["to_date"] + ' ' + request.form["to_time"], '%d.%m.%Y %H:%M')
#     to_date_time_tz = tz.normalize(tz.localize(to_datetime))
#     to_date_time_utc = to_date_time_tz.astimezone(pytz.timezone('UTC'))

    
    from_time = from_date_time_utc.timestamp()  # minus one hour for timezone   # from_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() # from_datetime.timestamp()
    to_time = to_date_time_utc.timestamp()  #to_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() #to_datetime.timestamp()
    
    db = get_db()
    
    cur = db.execute("SELECT timestamp, count from consumptions where sensor = ? and timestamp between ? and ? ORDER BY timestamp", (sensor["id"], from_date_time_utc.timestamp(), to_date_time_utc.timestamp()))

    data['columns'] = ["from_datetime", "to_datetime", "values"]
    
    data['rows'] = []
    
    # ab hier in lokaler zeit rechnen weil bei abrundung des tages sonst probleme auftreten. die timestamp ist also quasi utc+00
    
    logging.info(str(from_date_time_tz) + "  " + str(to_date_time_tz))

    
#     from_time = tz.fromutc(datetime.utcfromtimestamp(from_time))
#     to_time = tz.fromutc(datetime.utcfromtimestamp(to_time))
#     from_time = from_time.timestamp()
#     to_time = to_time.timestamp()
    
    #print(datetime.utcfromtimestamp(from_time), datetime.utcfromtimestamp(to_time))

    points_count = int((to_date_time_tz - from_date_time_tz) / timedelta(seconds = resolution)) + 1
    
    logging.info("points count " + str(points_count))
#    from_time += 3600
#    to_time += 3600

    until = from_date_time_tz + timedelta(seconds = resolution) #- (from_time % resolution)) #  +  resolution
    
    row = cur.fetchone()
    #timestamp_aktuell = row['timestamp'] #+ 3600
    if row is not None:
        current_date = tz.fromutc(datetime.utcfromtimestamp(row['timestamp'])) #+ 2*3600
    else:
        raise NoDataError()
    end_of_data = False
    
    for i in range(0, points_count):

        if not end_of_data:
            
            #### mit timedelta oderso, sonst gehts nicht mit daylightsaving -.-
            sumcount = 0
            datetime_from = until - timedelta(seconds = resolution)
            datetime_to = until - timedelta(seconds = 1)

            if (current_date < until):
                while current_date < datetime_to:
                    sumcount += row['count']
                    row = cur.fetchone()
                    if (row == None):
                        end_of_data = True
                        break
                    current_date = tz.fromutc(datetime.utcfromtimestamp(row['timestamp'])) #+ 2*3600
                    
            #print(datetime.utcfromtimestamp(datetime_to), date, datetime.utcfromtimestamp(current_date))
                
            data['rows'].append({"datetime_from" : datetime_from, "datetime_to" : datetime_to, "value" : sumcount})
        
        
        until += timedelta(seconds = resolution)
        
    #db.close()
    
    return data

    


        
@app.route('/weather/_get_weather', methods=['POST'])
def weather():
    
    from_date = datetime.datetime.strptime(request.form["von_date"])
    to_date = datetime.datetime.strptime(request.form["bis_date"])
    
    from_time_ts = from_date.timestamp()  
    to_time_ts = to_date.timestamp() 
    db = get_db()
    cur = db.execute("SELECT timestamp, avg_temp, precip_mm from weather where timestamp between ? and ?", (from_time_ts, to_time_ts))
    
    
    
    
    points_count = int((to_time - from_time) / 86400) + 1
    
    gjson = {}
    
    gjson['cols'] = [{'label': 'Datum', 'type': 'string' }, {'label': 'Liter', 'type': 'number' }, {'type': 'string', "role": "tooltip", 'p': {'role': 'tooltip'}}]
    
    gjson['rows'] = []
    
    # ab hier in lokaler zeit rechnen weil bei abrundung des tages sonst probleme auftreten. die timestamp ist also quasi utc+00
    from_time += 3600
    to_time += 3600
    
    zeitpunkt_bis = from_time + (resolution - (from_time % resolution)) #  +  resolution
    
    row = cur.fetchone()
    timestamp_aktuell = row['timestamp'] + 3600
    end_of_data = False
    
    for i in range(0, points_count):
        
        if not end_of_data:
            
            sumcount = 0
            datum_zeit_von = tz.normalize(datetime.datetime.utcfromtimestamp((zeitpunkt_bis-resolution)))
            datum_zeit_bis = tz.normalize(datetime.datetime.utcfromtimestamp((zeitpunkt_bis - 1)))
            uhrzeit_von = datum_zeit_von.strftime('%H:%M')
            uhrzeit_bis = datum_zeit_bis.strftime('%H:%M')
            datum = datum_zeit_von.strftime('%d.%m.%Y')
        
            if (timestamp_aktuell < zeitpunkt_bis):
                while timestamp_aktuell < zeitpunkt_bis:
                    sumcount += row['count']
                    row = cur.fetchone()
                    if (row == None):
                        end_of_data = True
                        break
                    timestamp_aktuell = row['timestamp'] + 3600
                
            
            if to_time - from_time > 86400:
                x_label = datum + ' ' + uhrzeit_von
            else:
                x_label = uhrzeit_von
            gjson['rows'].append({'c':[{'v': x_label, 'f':datum + ' von ' + uhrzeit_von + ' bis ' + uhrzeit_bis + ' Uhr'}, {'v': sumcount}, {'v': 'hmhm'}]})
        
        zeitpunkt_bis += resolution
        
    #db.close()
    
    return jsonify(gjson)

# def to_google_charts_json(entries):
#     
#     gjson = {}
#     
#     gjson['cols'] = [{'label': 'Datum', 'type': 'string' }, {'label': 'Liter', 'type': 'number' }]
#     
#     gjson['rows'] = []
#     
#     for row in entries:
#         time_from = format_time(datetime_from, locale=config.get("GASTROWALOGGER", "LOCALE"))
#         time_to = format_time(datetime_to, locale=config.get("GASTROWALOGGER", "LOCALE"))
#         date = format_date(datetime_from, locale=config.get("GASTROWALOGGER", "LOCALE"))      
#         #date_time = datetime.datetime.fromtimestamp(int(row['timestamp'])).strftime('%H:%M:%S')
#         gjson['rows'].append({'c':[{'v': row['datetime_from'] + row['datetime_to']}, {'v': row['verbrauch']}]})
#     
#     #gjson['rows'] = [{'c':[{'v':'a'}, {'v':6}]}, {'c':[{'v':'b'}, {'v': 4}]}]
#     return jsonify(gjson)

@app.route('/')
def home_page():
    sensor_rows = []
    sensor_types = {"gas": [],
                    "power": [],
                    "water": [],}

    sensor_data = {}
    for sensor in sensors:
        sensor_data[sensor] = round(get_meter_reading(sensors[sensor]),4)
        sensor_types[sensors[sensor]["type"]].append(sensor)
    
    for i in range (0, math.ceil(len(sensors)/3)):
        row = []
        if len(sensor_types["gas"]) > 0:
            row.append(sensor_types["gas"].pop())
        else:
            row.append(0)
        if len(sensor_types["power"]) > 0:
            row.append(sensor_types["power"].pop())
        else:
            row.append(0)
        if len(sensor_types["water"]) > 0:
            row.append(sensor_types["water"].pop())
        else:
            row.append(0)
        
        sensor_rows.append(row)
    
    
    return render_template('home.html', sensor_data = sensor_data, sensor_rows = sensor_rows)

@app.route('/settings')
def settings():

    settings_general = {"tzones" : pytz.all_timezones,
                        "date_format" : Locale(config.get("GASTROWALOGGER", "LOCALE")).date_formats['short'],
                        "time_format" : Locale(config.get("GASTROWALOGGER", "LOCALE")).time_formats['short'],
                        "timezone" : config.get("TIME", "TIMEZONE"),
                        "database" : config.get("DATABASE", "DATABASE")}
    
    return render_template('settings.html', settings_serialbus = get_serialbus_settings(), settings_general = settings_general, locales = Locale("de_DE").time_formats['short'])

@app.route('/attribution')
def attribution():    
    return render_template('attribution.html')

def get_serialbus_settings():
    settings = {}
    settings["serialbus_host"] = config.get("SERIALBUS", "SERIALBUS_HOST")
    settings["serialbus_port"] = config.getint("SERIALBUS", "SERIALBUS_PORT")
    return settings
    
def get_database_settings():
    settings = {}
    settings["serialbus_host"] = app.config["SERIALBUS_HOST"]
    settings["serialbus_port"] = app.config["SERIALBUS_PORT"]

@app.route('/sensors/_get_sensors')
def _get_sensors():
    return jsonify(sensors)

@socketio.on('discover_addresses')
def discover_sensors_socketsio(message):
    
    global sensors

    loading_percent = 0
    #sensors = {}
    
    addresses_str = message['data']
    if addresses_str:
        addresses_str.replace(" ", "")
        addresses_list = addresses_str.split(',')
        addresses = list(map(int, addresses_list))
    else:
        addresses = list(range(1,30))
        
    i = 0
    for address in addresses:
        emit("new_progress", loading_percent, json=True)
        loading_percent = i / len(addresses)
        serialbus = connect_serialbus()
        device = SerialBusDevice(address, serialbus)
        sensor_conf = device.get_config(timeout = 1000)
        if sensor_conf:
            if sensor_conf["label"] + "-" + sensor_conf["id"] not in sensors:
                sensor_conf.update({"address" : address})
                sensor_conf.update({"alias" : sensor_conf["label"] + "@" + str(address)})
                sensor_conf.update({"status" : "inactive"})
                if sensor_conf["type"] == "1A":
                    #Water sensor
                    sensor_conf.update({"type" : "water"})
                elif sensor_conf["type"] == "1B":
                    #Gas sensor
                    sensor_conf.update({"type" : "gas"})
                elif sensor_conf["type"] == "1C":
                    #Gas sensor
                    sensor_conf.update({"type" : "power"})
                
                sensors.update({sensor_conf["label"] + "-" + sensor_conf["id"] :  sensor_conf})
                add_sensor_to_database(sensor_conf["label"] + "-" + sensor_conf["id"])
                emit("discovered", sensors, json=True)
        serialbus.close()
        i += 1
        
        
    emit("new_progress", 1, json=True)
    emit("discovered", sensors, json=True)
    #return jsonify(sensors)


def save_sensors():
    # Writing JSON data
    with open('sensors.json', 'w') as f:
         json.dump(sensors, f)

def connect_serialbus():
    try:
        #from SerialBus import SerialBusTCP
        serialbus = SerialBusTCP()
        serialbus.connect(config.get("SERIALBUS", "SERIALBUS_HOST"), config.getint("SERIALBUS", "SERIALBUS_PORT"))
        return serialbus
    except:
        return None
        

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(config.get('DATABASE', 'DATABASE'))
    rv.row_factory = dict_factory
    return rv

# def init_db():
#     db = get_db()
#     with app.open_resource('schema.sql', mode='r') as f:
#         db.cursor().executescript(f.read())
#     db.commit()
# 
# @app.cli.command('initdb')
# def initdb_command():
#     """Initializes the database."""
#     init_db()
#     print('Initialized the database.')


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()
        
        
        
            
# @app.route('/gas/_set_settings', methods=['POST'])
# def set_settings_gas():
#     try:
#         ok = True
#         serialbus = connect_serialbus()
#         device = SerialBusDevice(app.config["GAS_METER_ADDR"], serialbus, device_type = sensor_device)
#         ok &= device.set_value(sensor_device.HIGH_THRES, int(request.form["highThres"]))
#         ok &= device.set_value(sensor_device.LOW_THRES, int(request.form["lowThres"]))
#         ok &= device.set_value(sensor_device.MIN_IMPULSE_LENGTH, int(request.form["min_impulse_length"]))
#         ok &= device.set_value(sensor_device.MIN_IDLE_LENGTH, int(request.form["min_idle_length"]))
#         ok &= device.set_value(sensor_device.MAX_FAILS, int(request.form["max_fails"]))
#         ok &= device.set_value(sensor_device.HYSTERESE, int(request.form["hysteresis"]))
#         ok &= device.set_value(sensor_device.INTERVAL, int(request.form["interval"]))
#         if 'invert' in request.form:
#             ok &= device.set_value(sensor_device.INVERT, True)
#         else:
#             ok &= device.set_value(sensor_device.INVERT, False)
# 
#         return jsonify(ok)
#     except:
#         raise
#     finally:
#         if serialbus is not None:
#             serialbus.close()
#             
            
            
# @app.route('/water/_calibrate')
# def calibrate_water():
#     global lock
#     with lock:
#         try:
#             serialbus = connect_serialbus()
#             answer = serialbus.send_msg(23, bytes([0b00101101]))
#             return jsonify(1)
#         except:
#             raise
#         finally:
#             if serialbus is not None:
#                 serialbus.close()
#     
#         return jsonify(-1)
# 
# @app.route('/gas/_calibrate')
# def calibrate_gas():
#     try:
#         serialbus = connect_serialbus()
#         answer = serialbus.send_msg(7, bytes([0b00101101]))
#     except:
#         raise
#     finally:
#         if serialbus is not None:
#             serialbus.close()
#             
# 
# @app.route('/water/_stop_calibration')
# def stop_calibrate_water():
#     global lock
#     with lock:
#         try:
#             serialbus = connect_serialbus()
#             answer = serialbus.send_msg(23, bytes([0b00101100]))
#             return jsonify(1)
#         except:
#             raise
#         finally:
#             if serialbus is not None:
#                 serialbus.close()
#         return jsonify(-1)
# 
# @app.route('/gas/_stop_calibration')
# def stop_calibrate_gas():
#     try:
#         serialbus = connect_serialbus()
#         answer = serialbus.send_msg(7, bytes([0b00101100]))
#     except:
#         raise
#     finally:
#         if serialbus is not None:
#             serialbus.close()


#@app.route('/water/_get_value')
#def _get_value():
#    return jsonify(get_value())

# @app.route('/water/_get_live_data')
# def _get_live_data():
#     try:
#         serialbus = connect_serialbus()
#         device = SerialBusDevice(app.config["WATER_METER_ADDR"], serialbus, device_type = sensor_device)
#         value = device.get_value(sensor_device.DATA);
#         return jsonify(value)
#     except:
#         return jsonify(-1)
#     finally:
#         if serialbus is not None:
#             serialbus.close()
# 
# 
# 
# @app.route('/water/_get_calibration_data')
# def get_calibration_data_water():
#     
#     global lock
#     with lock:
#         try:
#             data = {}
# 
#             serialbus = connect_serialbus()
#             device = SerialBusDevice(app.config["WATER_METER_ADDR"], serialbus, device_type = sensor_device)
# 
#             data["highThres"] = device.get_value(sensor_device.HIGH_THRES)
#             data["lowThres"] = device.get_value(sensor_device.LOW_THRES)
#             data["value"] = device.get_value(sensor_device.SENSOR_VALUE)
#             data["count"] = device.get_value(sensor_device.DATA)
#             return jsonify(data)
#         except:
#             raise
#             return jsonify(-1)
#         finally:
#             if serialbus is not None:
#                 serialbus.close()
#                 
#                 
# @app.route('/gas/_get_calibration_data')
# def get_calibration_data_gas():
#     
#     global lock
#     with lock:
#         try:
#             data = {}
# 
#             serialbus = connect_serialbus()
#             device = SerialBusDevice(app.config["GAS_METER_ADDR"], serialbus, device_type = sensor_device)
# 
#             data["highThres"] = device.get_value(sensor_device.HIGH_THRES)
#             data["lowThres"] = device.get_value(sensor_device.LOW_THRES)
#             data["value"] = device.get_value(sensor_device.SENSOR_VALUE)
#             data["count"] = device.get_value(sensor_device.DATA)
#             return jsonify(data)
#         except:
#             raise
#             return jsonify(-1)
#         finally:
#             if serialbus is not None:
#                 serialbus.close()
# 
# 
# def get_count():
#     
#     global lock
#     with lock:
#         try:
#             serialbus = connect_serialbus()
#             device = SerialBusDevice(app.config["WATER_METER_ADDR"], serialbus, device_type = sensor_device)
#             return jsonify(device.get_value(sensor_device.DATA))
#         except:
#             return jsonify(-1)
#         finally:
#             if serialbus is not None:
#                 serialbus.close()
# 
# @app.route('/water/_get_settings')
# def _get_settings_water():
#     
#     return jsonify(get_water_settings())
# 
# 
# @app.route('/gas/_get_settings')
# def _get_settings_gas():
#     return jsonify(get_gas_settings())
# 
# @app.route('/water/_load_defaults')
# def _load_defaults():
# 
#     serialbus = connect_serialbus()
#     device = SerialBusDevice(app.config["WATER_METER_ADDR"], serialbus, device_type = sensor_device)
#     device.reset_defaults()
#     serialbus.close()
#     
#     return jsonify(get_water_settings())
# 
# @app.route('/water/_get_sensor_info')
# def _get_sensor_info_water():
#     
#     global lock
#     with lock:
#         try:
#             serialbus = connect_serialbus()
#             
#             answer = serialbus.send_request_wait(23, bytes([4]))
#             answer_str = "";
#     
#             for char in answer:
#                 answer_str += (chr(char))
#             
#             return answer_str
#         except:
#             raise
#             return -1
#         
#         finally:
#             if serialbus is not None:
#                 serialbus.close()
#                 
#                 
# def _get_sensor_info_gas():
#     
#     global lock
#     with lock:
#         try:
#             serialbus = connect_serialbus()
#             
#             answer = serialbus.send_request_wait(7, bytes([4]))
#             answer_str = "";
#     
#             for char in answer:
#                 answer_str += (chr(char))
#             
#             return answer_str
#         except:
#             raise
#             return -1
#         
#         finally:
#             if serialbus is not None:
#                 serialbus.close()
# 
# 
# 
# 
#                 
# def get_gas_settings():
#     
#     global lock
#     with lock:
#         try:
#             settings = {}
#             serialbus = connect_serialbus()
#             device = SerialBusDevice(app.config["GAS_METER_ADDR"], serialbus, device_type = sensor_device)
# 
#             settings["highThres"] = device.get_value(sensor_device.HIGH_THRES)
#             settings["lowThres"] = device.get_value(sensor_device.LOW_THRES)
#             settings["hysteresis"] = device.get_value(sensor_device.HYSTERESE)
#             settings["min_impulse_length"] = device.get_value(sensor_device.MIN_IMPULSE_LENGTH)
#             settings["min_idle_length"] = device.get_value(sensor_device.MIN_IDLE_LENGTH)
#             settings["max_fails"] = device.get_value(sensor_device.MAX_FAILS)
#             settings["interval"] = device.get_value(sensor_device.INTERVAL)
#             settings["count"] = device.get_value(sensor_device.DATA)
#             if device.get_value(sensor_device.INVERT):
#                 invert = True
#             else:
#                 invert = False
#             settings["invert"] = invert
#             return settings
#             #return jsonify(settings)
#         except:
#             flash("Error while retrieving data from device: ")
#             raise
#             return -1
#         finally:
#             if serialbus is not None:
#                 serialbus.close()



################## WATER #######################

# @app.route('/water/sensor', methods=['GET'])
# def plot_sensor_water():
# 
#     try:
#         sensor_name = request.args["sensor"]
#         sensor = sensors[sensor_name]
#         if sensor is not None:
#             settings = get_sensor_settings(sensor)
#         
#             return render_template('wassersensor.html', settings = settings, sensor = sensor)
#     
#     except:
#         flash("Error while retrieving data from device: ")
#         raise
#         return render_template('wassersensor.html')
# 
# 
# 
# @app.route('/water/wasser_plot')
# def wasser_plot():
#     
# #     db = get_db()
# #     cur = db.execute('SELECT * FROM wasser')
# #     entries = cur.fetchall()
# #     db.close()
#     
#     return render_template('wasser_plot.html')#, entries = entries)
# 
# @app.route('/water/wasserverbrauch')
# def wasserverbrauch():
#     
#     db = get_db()
#     cur = db.execute('SELECT preis FROM wasserpreise ORDER BY timestamp_von DESC')
#     entry = cur.fetchone()
#     db.close()
#     return render_template('wasserverbrauch.html', euro_per_m3 = entry['preis'] )
# 
# @app.route('/water/save_zaehlerstand', methods=['POST'])
# def save_zaehlerstand_wasser():
#     
#     zaehlerstand = request.form["qm"]
#     anmerkung = request.form["note"]
#     
#     if not anmerkung:
#         anmerkung=""
#     if zaehlerstand:
#         try:
#         
#             db = get_db()
#             cur = db.execute("INSERT INTO zaehlerstaende_wasser (timestamp, stand, anmerkung) VALUES (strftime('%s', 'now'), ?, ?)", (zaehlerstand, anmerkung))
#             db.commit()
#             db.close()
#             flash('Neuen ZÃ¤hlerstand hinzugefÃ¼gt!', 'success')
#         except:
#             flash('Fehler beim einfÃ¼gen', 'danger')
#         
#     else:
#         flash('Keinen ZÃ¤hlerstand angegeben!', 'info')
#         
#     return redirect('/water/zaehlerstand')
# 
# @app.route('/water/_get_costs', methods=['POST'])
# def _get_costs_water():#+from_time, to_time):
#     
#     from_date = datetime.datetime.strptime(request.form["from"] + ' +0100', '%d.%m.%Y %z')
#     
#     db = get_db()
#     cur = db.execute('SELECT SUM(count)*0.001 AS qm FROM wasser WHERE timestamp > ?' , (from_date.timestamp(),))
#     qm = cur.fetchone()['qm']
#     
#     cur = db.execute('SELECT preis, MAX(timestamp_von) FROM wasserpreise')
#     euro_per_m3 = cur.fetchone()['preis']
#     
#     db.close()
#     
#     if qm and euro_per_m3:
#         return jsonify(qm * euro_per_m3)
#     else:
#         return jsonify(-1)
#     
# 
# # TODO: die vier methoden kapseln
# @app.route('/water/_get_verbrauch', methods=['POST'])
# def verbrauch_wasser():#+from_time, to_time):
#     
#     resolution = int(request.form["aufloesung"])
#     
#     from_datetime = datetime.datetime.strptime(request.form["von_date"] + ' ' + request.form["von_uhr"] + ' +0100', '%d.%m.%Y %H:%M %z')
#     to_datetime = datetime.datetime.strptime(request.form["bis_date"] + ' ' + request.form["bis_uhr"] + ' +0100', '%d.%m.%Y %H:%M %z')
#     
#     from_time = from_datetime.timestamp()  # minus one hour for timezone   # from_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() # from_datetime.timestamp()
#     to_time = to_datetime.timestamp()  #to_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() #to_datetime.timestamp()
#     db = get_db()
#     cur = db.execute("SELECT timestamp, count from wasser where timestamp between ? and ?", (from_time, to_time))
#     
#     
#     
#     
#     points_count = int((to_time - from_time) / resolution) + 1
#     
#     gjson = {}
#     
#     gjson['cols'] = [{'label': 'Datum', 'type': 'string' }, {'label': 'Liter', 'type': 'number' }, {'type': 'string', "role": "tooltip", 'p': {'role': 'tooltip'}}]
#     
#     gjson['rows'] = []
#     
#     # ab hier in lokaler zeit rechnen weil bei abrundung des tages sonst probleme auftreten. die timestamp ist also quasi utc+00
#     from_time += 3600
#     to_time += 3600
#     
#     zeitpunkt_bis = from_time + (resolution - (from_time % resolution)) #  +  resolution
#     
#     row = cur.fetchone()
#     timestamp_aktuell = row['timestamp'] + 3600
#     end_of_data = False
#     
#     for i in range(0, points_count):
#         
#         if not end_of_data:
#             
#             sumcount = 0
#             datum_zeit_von = datetime.datetime.utcfromtimestamp((zeitpunkt_bis-resolution))
#             datum_zeit_bis = datetime.datetime.utcfromtimestamp((zeitpunkt_bis - 1))
#             uhrzeit_von = datum_zeit_von.strftime('%H:%M')
#             uhrzeit_bis = datum_zeit_bis.strftime('%H:%M')
#             datum = datum_zeit_von.strftime('%d.%m.%Y')
#         
#             if (timestamp_aktuell < zeitpunkt_bis):
#                 while timestamp_aktuell < zeitpunkt_bis:
#                     sumcount += row['count']
#                     row = cur.fetchone()
#                     if (row == None):
#                         end_of_data = True
#                         break
#                     timestamp_aktuell = row['timestamp'] + 3600
#                 
#             
#             if to_time - from_time > 86400:
#                 x_label = datum + ' ' + uhrzeit_von
#             else:
#                 x_label = uhrzeit_von
#             gjson['rows'].append({'c':[{'v': x_label, 'f':datum + ' von ' + uhrzeit_von + ' bis ' + uhrzeit_bis + ' Uhr'}, {'v': sumcount}, {'v': 'hmhm'}]})
#         
#         zeitpunkt_bis += resolution
#         
#     db.close()
#     
#     return jsonify(gjson)
# 
# 
# 
# @app.route('/water/_get_verbrauch_file', methods=['POST'])
# def verbrauch_file_wasser():#+from_time, to_time):
#     
#     resolution = int(request.form["aufloesung"])
#     
#     from_datetime = datetime.datetime.strptime(request.form["von_date"] + ' ' + request.form["von_uhr"] + ' +0100', '%d.%m.%Y %H:%M %z')
#     to_datetime = datetime.datetime.strptime(request.form["bis_date"] + ' ' + request.form["bis_uhr"] + ' +0100', '%d.%m.%Y %H:%M %z')
#     
#     from_time = from_datetime.timestamp()  # minus one hour for timezone   # from_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() # from_datetime.timestamp()
#     to_time = to_datetime.timestamp()  #to_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() #to_datetime.timestamp()
#     db = get_db()
#     cur = db.execute("SELECT timestamp, count from wasser where timestamp between ? and ?", (from_time, to_time))
#     
#     
#     
#     
#     points_count = int((to_time - from_time) / resolution) + 1
#     
#     csv = ""
#     filename = "Wasserverbrauch_" + request.form["von_date"] + "-" +  request.form["bis_date"]
#     
#     # ab hier in lokaler zeit rechnen weil bei abrundung des tages sonst probleme auftreten. die timestamp ist also quasi utc+00
#     from_time += 3600
#     to_time += 3600
#     
#     zeitpunkt_bis = from_time + (resolution - (from_time % resolution)) #  +  resolution
#     
#     row = cur.fetchone()
#     timestamp_aktuell = row['timestamp'] + 3600
#     end_of_data = False
#     
#     for i in range(0, points_count):
#         
#         if not end_of_data:
#             
#             sumcount = 0
#             datum_zeit_von = datetime.datetime.utcfromtimestamp((zeitpunkt_bis-resolution))
#             datum_zeit_bis = datetime.datetime.utcfromtimestamp((zeitpunkt_bis - 1))
#             uhrzeit_von = datum_zeit_von.strftime('%H:%M')
#             uhrzeit_bis = datum_zeit_bis.strftime('%H:%M')
#             datum = datum_zeit_von.strftime('%d.%m.%Y')
#         
#             if (timestamp_aktuell < zeitpunkt_bis):
#                 while timestamp_aktuell < zeitpunkt_bis:
#                     sumcount += row['count']
#                     row = cur.fetchone()
#                     if (row == None):
#                         end_of_data = True
#                         break
#                     timestamp_aktuell = row['timestamp'] + 3600
#                 
#             
#             if to_time - from_time > 86400:
#                 x_label = datum + ' ' + uhrzeit_von
#             else:
#                 x_label = uhrzeit_von
#             csv += datum + ';' + uhrzeit_von + ':00;' + str(sumcount) + '\n' #gjson['rows'].append({'c':[{'v': x_label, 'f':datum + ' von ' + uhrzeit_von + ' bis ' + uhrzeit_bis + ' Uhr'}, {'v': sumcount}, {'v': 'hmhm'}]})
#         
#         zeitpunkt_bis += resolution
#         
#     db.close()
#     
#     
#     response = make_response(csv)
#     # This is the key: Set the right header for the response
#     # to be downloaded, instead of just printed on the browser
#     response.headers["Content-Disposition"] = "attachment; filename=" + filename + ".csv"
#     return response
# 
# 
# @app.route('/water/zaehlerstand')
# def wasser_zaehlerstand():
#     
#     db = get_db()
#     cur = db.execute("SELECT id, datetime(timestamp, 'unixepoch', 'localtime') AS datum, stand, anmerkung FROM zaehlerstaende_wasser")
#     entries = cur.fetchall()
#     #cur = db.execute("CREATE VIEW last_reading_water AS SELECT MAX(timestamp) AS timestamp, stand FROM zaehlerstaende_wasser")
#     
#     
#     cur = db.execute('SELECT preis, MAX(timestamp_von) FROM wasserpreise')
#     euro_per_m3 = cur.fetchone()['preis']
#     
#     #db.close()
#     
#     return render_template('zaehlerstand_wasser.html', entries = entries, meter_reading = round(get_water_meter_reading(), 5), euro_per_m3 = euro_per_m3)
# 
# def get_water_meter_reading():
#     db = get_db()
#     cur = db.execute("SELECT SUM(count)*0.001+last_reading_water.stand AS reading FROM wasser, last_reading_water WHERE wasser.timestamp > last_reading_water.timestamp")
#     meter_reading = cur.fetchone()['reading']
#     
#     if not meter_reading:
#         cur = db.execute("SELECT stand FROM last_reading_water")
#         meter_reading = cur.fetchone()['stand']
#         
#     return meter_reading
# 
# @app.route('/water/_set_settings', methods=['POST'])
# def set_settings_water():
#     try:
#         ok = True
#         serialbus = connect_serialbus()
#         device = SerialBusDevice(app.config["WATER_METER_ADDR"], serialbus, device_type = sensor_device)
#         ok &= device.set_value(sensor_device.HIGH_THRES, int(request.form["highThres"]))
#         ok &= device.set_value(sensor_device.LOW_THRES, int(request.form["lowThres"]))
#         ok &= device.set_value(sensor_device.MIN_IMPULSE_LENGTH, int(request.form["min_impulse_length"]))
#         ok &= device.set_value(sensor_device.MIN_IDLE_LENGTH, int(request.form["min_idle_length"]))
#         ok &= device.set_value(sensor_device.MAX_FAILS, int(request.form["max_fails"]))
#         ok &= device.set_value(sensor_device.HYSTERESE, int(request.form["hysteresis"]))
#         ok &= device.set_value(sensor_device.INTERVAL, int(request.form["interval"]))
#         if 'invert' in request.form:
#             ok &= device.set_value(sensor_device.INVERT, True)
#         else:
#             ok &= device.set_value(sensor_device.INVERT, False)
# 
#         return jsonify(ok)
#     except:
#         raise
#     finally:
#         if serialbus is not None:
#             serialbus.close()
# 
# def get_sensor_settings():
#     
#     global lock
#     with lock:
#         try:
#             settings = {}
#             serialbus = connect_serialbus()
#             device = SerialBusDevice(app.config["WATER_METER_ADDR"], serialbus, device_type = sensor_device)
# 
#             settings["highThres"] = device.get_value(sensor_device.HIGH_THRES)
#             settings["lowThres"] = device.get_value(sensor_device.LOW_THRES)
#             settings["hysteresis"] = device.get_value(sensor_device.HYSTERESE)
#             settings["min_impulse_length"] = device.get_value(sensor_device.MIN_IMPULSE_LENGTH)
#             settings["min_idle_length"] = device.get_value(sensor_device.MIN_IDLE_LENGTH)
#             settings["max_fails"] = device.get_value(sensor_device.MAX_FAILS)
#             settings["interval"] = device.get_value(sensor_device.INTERVAL)
#             settings["count"] = device.get_value(sensor_device.DATA)
#             if device.get_value(sensor_device.INVERT):
#                 invert = True
#             else:
#                 invert = False
#             settings["invert"] = invert
#             return settings
#             #return jsonify(settings)
#         except:
#             flash("Error while retrieving data from device: ")
#             raise
#             return -1
#         finally:
#             if serialbus is not None:
#                 serialbus.close()
# 
# def get_water_settings():
#     
#     global lock
#     with lock:
#         try:
#             settings = {}
#             serialbus = connect_serialbus()
#             device = SerialBusDevice(app.config["WATER_METER_ADDR"], serialbus, device_type = sensor_device)
# 
#             settings["highThres"] = device.get_value(sensor_device.HIGH_THRES)
#             settings["lowThres"] = device.get_value(sensor_device.LOW_THRES)
#             settings["hysteresis"] = device.get_value(sensor_device.HYSTERESE)
#             settings["min_impulse_length"] = device.get_value(sensor_device.MIN_IMPULSE_LENGTH)
#             settings["min_idle_length"] = device.get_value(sensor_device.MIN_IDLE_LENGTH)
#             settings["max_fails"] = device.get_value(sensor_device.MAX_FAILS)
#             settings["interval"] = device.get_value(sensor_device.INTERVAL)
#             settings["count"] = device.get_value(sensor_device.DATA)
#             if device.get_value(sensor_device.INVERT):
#                 invert = True
#             else:
#                 invert = False
#             settings["invert"] = invert
#             return settings
#             #return jsonify(settings)
#         except:
#             flash("Error while retrieving data from device: ")
#             raise
#             return -1
#         finally:
#             if serialbus is not None:
#                 serialbus.close()
# ################## END WATER ####################
# 
# 
# 
# @app.route('/gas/gassensor')
# def plot_sensor_gas():
# 
#     try:
# 
#         settings = get_gas_settings()
#         sensor = json.loads(_get_sensor_info_gas());
#         
#         return render_template('gassensor.html', settings = settings, sensor = sensor)
# 
#         #return render_template('wassersensor.html', highThres = highThres, lowThres = lowThres, hysteresis = hysteresis, invert = invert)
#     except:
#         flash("Error while retrieving data from device: ")
#         raise
#         return render_template('wassersensor.html')
#     finally:
#         #serialbus.close()
#         pass
# 
# @app.route('/login')
# def login():
#     
#     return render_template('login.html')
# 
# 
# 
# @app.route('/gas/gas_charts', methods=['GET'])
# def gas_plot():
#     
#     db = get_db()
#     cur = db.execute('SELECT * FROM gas')
#     entries = cur.fetchall()
#     db.close()
#     
#     return render_template('gas_charts.html', entries = entries)


# @app.route('/gas/save_meter_reading', methods=['POST'])
# def save_zaehlerstand_gas():
#     
#     zaehlerstand = request.form["qm"]
#     anmerkung = request.form["note"]
#     
#     if not anmerkung:
#         anmerkung=""
#     if zaehlerstand:
#         try:
#         
#             db = get_db()
#             cur = db.execute("INSERT INTO gas_meter_readings (timestamp, reading, note) VALUES (strftime('%s', 'now'), ?, ?)", (zaehlerstand, anmerkung))
#             db.commit()
#             db.close()
#             flash('Neuen ZÃ¤hlerstand hinzugefÃ¼gt!', 'success')
#         except:
#             flash('Fehler beim einfÃ¼gen', 'danger')
#         
#     else:
#         flash('Keinen ZÃ¤hlerstand angegeben!', 'info')
#         
#     return redirect('/gas/meter_readings')
# 
# 
# 
# 
# 
#     
# @app.route('/gas/_get_costs', methods=['POST'])
# def _get_costs_gas():#+from_time, to_time):
#     
#     from_date = datetime.datetime.strptime(request.form["from"] + ' +0100', '%d.%m.%Y %z')
#     
#     db = get_db()
#     cur = db.execute('SELECT SUM(count)*0.01 AS qm FROM gas WHERE timestamp > ?' , (from_date.timestamp(),))
#     qm = cur.fetchone()['qm']
#     
#     cur = db.execute('SELECT cost, MAX(timestamp_from) FROM gas_prices')
#     euro_per_m3 = cur.fetchone()['cost']
#     
#     db.close()
#     
#     if qm and euro_per_m3:
#         return jsonify(qm * euro_per_m3)
#     else:
#         return jsonify(-1)
#     
#     
# 
# 
# 
# 
# 
# @app.route('/gas/_get_data_file', methods=['POST'])
# def verbrauch_file_gas():#+from_time, to_time):
#     
#     resolution = int(request.form["resolution"])
#     
#     from_datetime = datetime.datetime.strptime(request.form["from_date"] + ' ' + request.form["from_time"] + ' +0100', '%d.%m.%Y %H:%M %z')
#     to_datetime = datetime.datetime.strptime(request.form["to_date"] + ' ' + request.form["to_time"] + ' +0100', '%d.%m.%Y %H:%M %z')
#     
#     from_time = from_datetime.timestamp()  # minus one hour for timezone   # from_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() # from_datetime.timestamp()
#     to_time = to_datetime.timestamp()  #to_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() #to_datetime.timestamp()
#     db = get_db()
#     cur = db.execute("SELECT timestamp, count from gas where timestamp between ? and ?", (from_time, to_time))
#     
#     
#     points_count = int((to_time - from_time) / resolution) + 1
#     
#     csv = ""
#     filename = "Gasverbrauch_" + request.form["from_date"] + "-" +  request.form["to_date"]
#     
#     # ab hier in lokaler zeit rechnen weil bei abrundung des tages sonst probleme auftreten. die timestamp ist also quasi utc+00
#     from_time += 3600
#     to_time += 3600
#     
#     zeitpunkt_bis = from_time + (resolution - (from_time % resolution)) #  +  resolution
#     
#     row = cur.fetchone()
#     timestamp_aktuell = row['timestamp'] + 3600
#     end_of_data = False
#     
#     for i in range(0, points_count):
#         
#         if not end_of_data:
#             
#             sumcount = 0
#             datum_zeit_von = datetime.datetime.utcfromtimestamp((zeitpunkt_bis-resolution))
#             datum_zeit_bis = datetime.datetime.utcfromtimestamp((zeitpunkt_bis - 1))
#             uhrzeit_von = datum_zeit_von.strftime('%H:%M')
#             uhrzeit_bis = datum_zeit_bis.strftime('%H:%M')
#             datum = datum_zeit_von.strftime('%d.%m.%Y')
#         
#             if (timestamp_aktuell < zeitpunkt_bis):
#                 while timestamp_aktuell < zeitpunkt_bis:
#                     sumcount += row['count']
#                     row = cur.fetchone()
#                     if (row == None):
#                         end_of_data = True
#                         break
#                     timestamp_aktuell = row['timestamp'] + 3600
#                 
#             
#             if to_time - from_time > 86400:
#                 x_label = datum + ' ' + uhrzeit_von
#             else:
#                 x_label = uhrzeit_von
#             csv += datum + ';' + uhrzeit_von + ':00;' + str(sumcount) + '\n' #gjson['rows'].append({'c':[{'v': x_label, 'f':datum + ' von ' + uhrzeit_von + ' bis ' + uhrzeit_bis + ' Uhr'}, {'v': sumcount}, {'v': 'hmhm'}]})
#         
#         zeitpunkt_bis += resolution
#         
#     db.close()
#     
#     
#     response = make_response(csv)
#     # This is the key: Set the right header for the response
#     # to be downloaded, instead of just printed on the browser
#     response.headers["Content-Disposition"] = "attachment; filename=" + filename + ".csv"
#     return response
# 
# @app.route('/gas/_get_data_file_weather', methods=['POST'])
# def verbrauch_file_gas_weather():#+from_time, to_time):
#     
#     resolution = int(request.form["resolution"])
#     
#     from_datetime = datetime.datetime.strptime(request.form["from_date"] + ' ' + request.form["from_time"] + ' +0100', '%d.%m.%Y %H:%M %z')
#     to_datetime = datetime.datetime.strptime(request.form["to_date"] + ' ' + request.form["to_time"] + ' +0100', '%d.%m.%Y %H:%M %z')
#     
#     from_time = from_datetime.timestamp()  # minus one hour for timezone   # from_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() # from_datetime.timestamp()
#     to_time = to_datetime.timestamp()  #to_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() #to_datetime.timestamp()
#     db = get_db()
#     cur = db.execute("SELECT timestamp, count from gas where timestamp between ? and ?", (from_time, to_time))
#     
#     
#     points_count = int((to_time - from_time) / resolution) + 1
#     
#     csv = ""
#     filename = "Gasverbrauch_" + request.form["from_date"] + "-" +  request.form["to_date"]
#     
#     # ab hier in lokaler zeit rechnen weil bei abrundung des tages sonst probleme auftreten. die timestamp ist also quasi utc+00
#     from_time += 3600
#     to_time += 3600
#     
#     zeitpunkt_bis = from_time + (resolution - (from_time % resolution)) #  +  resolution
#     
#     row = cur.fetchone()
#     timestamp_aktuell = row['timestamp'] + 3600
#     end_of_data = False
#     temp = 0;
#     
#     for i in range(0, points_count):
#         
#         if not end_of_data:
#             
#             sumcount = 0
#             datum_zeit_von = datetime.datetime.utcfromtimestamp((zeitpunkt_bis-resolution))
#             datum_zeit_bis = datetime.datetime.utcfromtimestamp((zeitpunkt_bis - 1))
#             uhrzeit_von = datum_zeit_von.strftime('%H:%M')
#             uhrzeit_bis = datum_zeit_bis.strftime('%H:%M')
#             datum = datum_zeit_von.strftime('%d.%m.%Y')
#         
#             if (timestamp_aktuell < zeitpunkt_bis):
#                 while timestamp_aktuell < zeitpunkt_bis:
#                     sumcount += row['count']
#                     row = cur.fetchone()
#                     if (row == None):
#                         end_of_data = True
#                         break
#                     timestamp_aktuell = row['timestamp'] + 3600
#                 
#             cur_temp = db.execute("SELECT avg_temp from weather where timestamp between ? and ?", (zeitpunkt_bis-resolution, zeitpunkt_bis - 1))
#             temp_row = cur_temp.fetchone()
#             if temp_row is not None:
#                 temp = temp_row['avg_temp']
#             csv += datum + ';' + uhrzeit_von + ':00;' + str(sumcount) + ";" + str(temp) + '\n'
#         
#         zeitpunkt_bis += resolution
#         
#     db.close()
#     
#     
#     response = make_response(csv)
#     # This is the key: Set the right header for the response
#     # to be downloaded, instead of just printed on the browser
#     response.headers["Content-Disposition"] = "attachment; filename=" + filename + ".csv"
#     return response
# 
# 
# @app.route('/gas/_get_chart', methods=['POST'])
# def verbrauch_gas():#+from_time, to_time):
#     
#     resolution = int(request.form["resolution"])
#     
#     from_datetime = datetime.datetime.strptime(request.form["from_date"] + ' ' + request.form["from_time"] + ' +0100', '%d.%m.%Y %H:%M %z')
#     to_datetime = datetime.datetime.strptime(request.form["to_date"] + ' ' + request.form["to_time"] + ' +0100', '%d.%m.%Y %H:%M %z')
#     
#     from_time = from_datetime.timestamp()  # minus one hour for timezone   # from_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() # from_datetime.timestamp()
#     to_time = to_datetime.timestamp()  #to_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() #to_datetime.timestamp()
#     db = get_db()
#     cur = db.execute("SELECT timestamp, count from gas where timestamp between ? and ?", (from_time, to_time))
#     
#     
#     
#     
#     points_count = int((to_time - from_time) / resolution) + 1
#     
#     gjson = {}
#     
#     gjson['cols'] = [{'label': 'Datum', 'type': 'string' }, {'label': 'x 0.01mÂ³', 'type': 'number' }, {'type': 'string', "role": "tooltip", 'p': {'role': 'tooltip'}}]
#     
#     gjson['rows'] = []
#     
#     # ab hier in lokaler zeit rechnen weil bei abrundung des tages sonst probleme auftreten. die timestamp ist also quasi utc+00
#     from_time += 3600
#     to_time += 3600
#     
#     zeitpunkt_bis = from_time + (resolution - (from_time % resolution)) #  +  resolution
#     
#     row = cur.fetchone()
#     timestamp_aktuell = row['timestamp'] + 3600
#     end_of_data = False
#     
#     for i in range(0, points_count):
#         
#         if not end_of_data:
#             
#             sumcount = 0
#             datum_zeit_von = datetime.datetime.utcfromtimestamp((zeitpunkt_bis-resolution))
#             datum_zeit_bis = datetime.datetime.utcfromtimestamp((zeitpunkt_bis - 1))
#             uhrzeit_von = datum_zeit_von.strftime('%H:%M')
#             uhrzeit_bis = datum_zeit_bis.strftime('%H:%M')
#             datum = datum_zeit_von.strftime('%d.%m.%Y')
#         
#             if (timestamp_aktuell < zeitpunkt_bis):
#                 while timestamp_aktuell < zeitpunkt_bis:
#                     sumcount += row['count']
#                     row = cur.fetchone()
#                     if (row == None):
#                         end_of_data = True
#                         break
#                     timestamp_aktuell = row['timestamp'] + 3600
#                 
#             
#             if to_time - from_time > 86400:
#                 x_label = datum + ' ' + uhrzeit_von
#             else:
#                 x_label = uhrzeit_von
#             gjson['rows'].append({'c':[{'v': x_label, 'f':datum + ' von ' + uhrzeit_von + ' bis ' + uhrzeit_bis + ' Uhr'}, {'v': sumcount}, {'v': 'hmhm'}]})
#         
#         zeitpunkt_bis += resolution
#         
#     #db.close()
#     
#     return jsonify(gjson)

# @app.route('/gas/meter_readings')
# def gas_meter_reading():
#     
#     db = get_db()
#     cur = db.execute("SELECT id, datetime(timestamp, 'unixepoch', 'localtime') AS date, reading, note FROM gas_meter_readings")
#     entries = cur.fetchall()
#     #cur = db.execute("CREATE VIEW last_reading_water AS SELECT MAX(timestamp) AS timestamp, stand FROM zaehlerstaende_wasser")
#     
#     
#     cur = db.execute('SELECT cost, MAX(timestamp_from) FROM gas_prices')
#     euro_per_m3 = cur.fetchone()['cost']
#     if not euro_per_m3:
#         euro_per_m3 = 0;
#     
#     #db.close()
#     
#     return render_template('meter_reading_gas.html', entries = entries, meter_reading = round(get_gas_meter_reading(), 3), euro_per_m3 = euro_per_m3)

# @app.route('/water/_get_thresholds????')
# def get_thresholds():
#     
#     global lock
#     with lock:
#         try:
#             thresholds = {}
#             serialbus = connect_serialbus()
#             
#             answer = serialbus.send_request_wait(23, bytes([0b00011010, 2]))
#             
#             thresholds["highThres"] = int.from_bytes(answer[2:], byteorder = "big")
#             print(thresholds["highThres"])
#             answer = serialbus.send_request_wait(23, bytes([0b00011010, 1]))
#             serialbus.close()
#             thresholds["lowThres"] = int.from_bytes(answer[2:], byteorder = "big")
#             
#             return thresholds
#         except:
#             raise
#             print("abbruch")
#             return -1

# @app.route('/sensors/_get_discover_progress', methods=['GET'])
# def _get_discover_progress():
#     return jsonify(loading_percent)

# @app.route('/sensors/_discover', methods=['POST'])
# def discover_sensors():
#     
#     global sensors
# 
#     loading_percent = 0
#     sensors = {}
#     
#     addresses_str = request.form["addresses-list"]
#     if addresses_str:
#         addresses_str.replace(" ", "")
#         addresses_list = addresses_str.split(',')
#         addresses = list(map(int, addresses_list))
#     else:
#         addresses = list(range(1,31))
#         
#     i = 0
#     for address in addresses:
#         send(jsonify(loading_percent), json=True)
#         loading_percent = i / len(addresses)
#         serialbus = connect_serialbus()
#         device = SerialBusDevice(address, serialbus)
#         sensor_conf = device.get_config(timeout = 600)
#         if sensor_conf:
#             sensor_conf.update({"address" : address})
#             sensor_conf.update({"alias" : sensor_conf["label"] + "@" + str(address)})
#             sensor_conf.update({"active" : 0})
#             # TODO change in firmware to sensor_id
#             sensor_conf["sensor_id"] = sensor_conf.pop("id")
#             if sensor_conf["type"] == "1A":
#                 #Water sensor
#                 sensor_conf.update({"type" : "water"})
#             elif sensor_conf["type"] == "1B":
#                 #Gas sensor
#                 sensor_conf.update({"type" : "gas"})
#             elif sensor_conf["type"] == "1C":
#                 #Gas sensor
#                 sensor_conf.update({"type" : "power"})
#             
#             sensors.update({sensor_conf["label"] + ":" + sensor_conf["sensor_id"] :  sensor_conf})
#         serialbus.close()
#         i += 1
#         
#         
# 
#     return jsonify(sensors)

# @app.route('/charts/_get_chart_old', methods=['POST', 'GET'])
# def calculate_chart_old():#+from_time, to_time):
#     
#     gjson = {}
#     
#     sensor = request.args["sensor"]
#     gjson['sensor'] = sensors[sensor]
#     
#     if sensor not in sensors:
#         return jsonify(-1)
#     
#     resolution = int(request.form["resolution"])
# 
#     from_date = parse_date(request.form["from_date"], locale=config.get("GASTROWALOGGER", "LOCALE"))
#     from_time = parse_time(request.form["from_time"]+":00", locale=config.get("GASTROWALOGGER", "LOCALE"))
#     from_date_time = datetime.combine(from_date, from_time)
#     from_date_time_tz = tz.normalize(tz.localize(from_date_time))
#     from_date_time_utc = from_date_time_tz.astimezone(pytz.timezone('UTC'))    
#     
#     to_date = parse_date(request.form["to_date"], locale=config.get("GASTROWALOGGER", "LOCALE"))
#     to_time = parse_time(request.form["to_time"]+":00", locale=config.get("GASTROWALOGGER", "LOCALE"))
#     to_date_time = datetime.combine(to_date, to_time)
#     to_date_time_tz = tz.normalize(tz.localize(to_date_time))
#     to_date_time_utc = to_date_time_tz.astimezone(pytz.timezone('UTC'))    
#     
# #     to_datetime = datetime.strptime(request.form["to_date"] + ' ' + request.form["to_time"], '%d.%m.%Y %H:%M')
# #     to_date_time_tz = tz.normalize(tz.localize(to_datetime))
# #     to_date_time_utc = to_date_time_tz.astimezone(pytz.timezone('UTC'))
# 
#     
#     from_time = from_date_time_utc.timestamp()  # minus one hour for timezone   # from_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() # from_datetime.timestamp()
#     to_time = to_date_time_utc.timestamp()  #to_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() #to_datetime.timestamp()
#     db = get_db()
#     cur = db.execute("SELECT timestamp, count from consumptions where sensor = ? and timestamp between ? and ? ORDER BY timestamp", (sensors[sensor]["id"], from_date_time_utc.timestamp(), to_date_time_utc.timestamp()))
# 
#     gjson['cols'] = [{'label': 'Datum', 'type': 'string' }, {'label': 'x 0.01mÂ³', 'type': 'number' }, {'type': 'string', "role": "tooltip", 'p': {'role': 'tooltip'}}]
#     
#     gjson['rows'] = []
#     
#     # ab hier in lokaler zeit rechnen weil bei abrundung des tages sonst probleme auftreten. die timestamp ist also quasi utc+00
#     
#     logging.info(str(from_date_time_tz) + "  " + str(to_date_time_tz))
# 
#     
# #     from_time = tz.fromutc(datetime.utcfromtimestamp(from_time))
# #     to_time = tz.fromutc(datetime.utcfromtimestamp(to_time))
# #     from_time = from_time.timestamp()
# #     to_time = to_time.timestamp()
#     
#     #print(datetime.utcfromtimestamp(from_time), datetime.utcfromtimestamp(to_time))
# 
#     points_count = int((to_date_time - from_date_time) / timedelta(seconds = resolution)) + 1
#     
#     logging.info("points count " + str(points_count))
# #    from_time += 3600
# #    to_time += 3600
# 
#     until = from_date_time_tz + timedelta(seconds = resolution) #- (from_time % resolution)) #  +  resolution
#     
#     row = cur.fetchone()
#     #timestamp_aktuell = row['timestamp'] #+ 3600
#     if row is not None:
#         current_date = tz.fromutc(datetime.utcfromtimestamp(row['timestamp'])) #+ 2*3600
#     else:
#         return jsonify(-1)
#     end_of_data = False
#     
#     for i in range(0, points_count):
# 
#         if not end_of_data:
#             
#             #### mit timedelta oderso, sonst gehts nicht mit daylightsaving -.-
#             sumcount = 0
#             datetime_from = until - timedelta(seconds = resolution)
#             datetime_to = until - timedelta(seconds = 1)
#             time_from = format_time(datetime_from, locale=config.get("GASTROWALOGGER", "LOCALE"))
#             time_to = format_time(datetime_to, locale=config.get("GASTROWALOGGER", "LOCALE"))
#             date = format_date(datetime_from, locale=config.get("GASTROWALOGGER", "LOCALE"))      
#             
#             
#         
#             if (current_date < until):
#                 while current_date < datetime_to:
#                     sumcount += row['count']
#                     row = cur.fetchone()
#                     if (row == None):
#                         end_of_data = True
#                         break
#                     current_date = tz.fromutc(datetime.utcfromtimestamp(row['timestamp'])) #+ 2*3600
#                     
#             #print(datetime.utcfromtimestamp(datetime_to), date, datetime.utcfromtimestamp(current_date))
#                 
#             
#             if resolution >= 86400:
#                 x_label = date # + ' ' + time_from
#             else:
#                 x_label = time_from
#             gjson['rows'].append({'c':[{'v': x_label, 'f':date + ' von ' + time_from + ' bis ' + time_to + ' Uhr'}, {'v': sumcount}, {'v': 'hmhm'}]})
#         
#         
#         until += timedelta(seconds = resolution)
#         
#     #db.close()
#     
#     return jsonify(gjson)

# @app.route('/charts/_get_csv_old', methods=['POST'])
# def get_csv_old():#+from_time, to_time):
#      
#     sensor = request.form["sensor"]
#     
#     if sensor not in sensors:
#         return jsonify(-1)
#     
#     resolution = int(request.form["resolution"])
#     
# 
#     
#     from_datetime = datetime.strptime(request.form["from_date"] + ' ' + request.form["from_time"], '%d.%m.%Y %H:%M')
#     #from_datetime.replace(tzinfo=tz)
#     to_datetime = datetime.strptime(request.form["to_date"] + ' ' + request.form["to_time"], '%d.%m.%Y %H:%M')
#    # to_datetime.replace(tzinfo=tz)
#     
#     from_time = from_datetime.timestamp()  # minus one hour for timezone   # from_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() # from_datetime.timestamp()
#     to_time = to_datetime.timestamp()  #to_datetime.replace(tzinfo=datetime.timezone.utc).timestamp() #to_datetime.timestamp()
#     db = get_db()
#     cur = db.execute("SELECT timestamp, count from consumptions where sensor = ? and timestamp between ? and ? ORDER BY timestamp", (sensors[sensor]["id"], from_time, to_time))
# 
#     gjson = {}
#     
#     gjson['cols'] = [{'label': 'Datum', 'type': 'string' }, {'label': 'x 0.01mÂ³', 'type': 'number' }, {'type': 'string', "role": "tooltip", 'p': {'role': 'tooltip'}}]
#     
#     gjson['rows'] = []
#     
#     # ab hier in lokaler zeit rechnen weil bei abrundung des tages sonst probleme auftreten. die timestamp ist also quasi utc+00
# 
#     from_time = tz.fromutc(datetime.utcfromtimestamp(from_time))
#     to_time = tz.fromutc(datetime.utcfromtimestamp(to_time))
#     from_time = from_time.timestamp()
#     to_time = to_time.timestamp() 
#     
#     points_count = int((to_time - from_time) / resolution) + 1
# 
#     
#     zeitpunkt_bis = from_time + resolution #- (from_time % resolution)) #  +  resolution
#      
#     csv = ""
#     filename = gettext("water") + "_consumption" + request.form["from_date"] + "-" +  request.form["to_date"]
#      
#     # ab hier in lokaler zeit rechnen weil bei abrundung des tages sonst probleme auftreten. die timestamp ist also quasi utc+00
# 
#      
#      
#     row = cur.fetchone()
#     timestamp_aktuell = row['timestamp'] + 3600
#     end_of_data = False
#      
#     for i in range(0, points_count):
#          
#         if not end_of_data:
#              
#             sumcount = 0
#             datum_zeit_von = tz.fromutc(datetime.utcfromtimestamp((zeitpunkt_bis-resolution)))
#             datum_zeit_bis = tz.fromutc(datetime.utcfromtimestamp((zeitpunkt_bis - 1)))
#             uhrzeit_von = datum_zeit_von.strftime('%H:%M')
#             uhrzeit_bis = datum_zeit_bis.strftime('%H:%M')
#             datum = datum_zeit_von.strftime('%d.%m.%Y')
#             
#             
#         
#             if (timestamp_aktuell < zeitpunkt_bis):
#                 while timestamp_aktuell < zeitpunkt_bis:
#                     sumcount += row['count']
#                     row = cur.fetchone()
#                     if (row == None):
#                         end_of_data = True
#                         break
#                     timestamp_aktuell = row['timestamp'] #+ 2*3600
#                     
#             #print(datetime.utcfromtimestamp(zeitpunkt_bis), datum, datetime.utcfromtimestamp(timestamp_aktuell))
#                 
#             
#             if to_time - from_time > 86400:
#                 x_label = datum + ' ' + uhrzeit_von
#             else:
#                 x_label = uhrzeit_von
#             csv += datum + ';' + uhrzeit_von + ':00;' + str(sumcount) + '\n' #gjson['rows'].append({'c':[{'v': x_label, 'f':datum + ' von ' + uhrzeit_von + ' bis ' + uhrzeit_bis + ' Uhr'}, {'v': sumcount}, {'v': 'hmhm'}]})
#          
#         zeitpunkt_bis += resolution
#          
#     db.close()
#      
#      
#     response = make_response(csv)
#     # This is the key: Set the right header for the response
#     # to be downloaded, instead of just printed on the browser
#     response.headers["Content-Disposition"] = "attachment; filename=" + filename + ".csv"
#     return response

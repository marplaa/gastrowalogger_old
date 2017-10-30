#!/usr/bin/env python3
import os
import sys
import sqlite3
from shutil import copyfile
from subprocess import call
import fileinput


def init_db():
    db = sqlite3.connect(config.get('DATABASE', 'DATABASE'))
    db.row_factory = dict_factory
    with app.open_resource(sys.path[0] + 'schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()
    
    
if __name__ == '__main__':
    #print("Initialize database...\n")
    #init_db()
    print("setting up systemd service...\n")
    with fileinput.FileInput("gastrowalogger.service", inplace=True, backup='.bak') as file:
        for line in file:
            print(line.replace("{{working_dir}}", sys.path[0]).replace("{{exec}}", sys.path[0] + "/bin/python gastrowalogger_service.py"), end='')
            
    copyfile(sys.path[0] + "/gastrowalogger.service", "/etc/systemd/system/gastrowalogger.service")
    call(["systemctl", "enable", "gastrowalogger.service"])

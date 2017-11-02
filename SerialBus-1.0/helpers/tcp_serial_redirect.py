#!/usr/bin/env python
#
# Redirect data from a TCP/IP connection to a serial port and vice versa.
#
# (C) 2002-2016 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause

import sys
import socket
import serial
import serial.threaded
import time
from serial.tools import list_ports


class SerialToNet(serial.threaded.Protocol):
    """serial->socket"""

    def __init__(self):
        self.socket = None

    def __call__(self):
        return self

    def data_received(self, data):
        if self.socket is not None:
            self.socket.sendall(data)

    def connection_lost(self, exc):
        sys.stdout.write('port closed\n')
            

def get_device_vidpid(vendor_id, product_id):

    # a list containing active ports
    portlist = list(serial.tools.list_ports.comports())

    for device in portlist:
        if device.pid == product_id and device.vid == vendor_id:
            return device.device

def get_device_vidpid_serialnum(vendor_id, product_id, serialnum):

    # a list containing active ports
    portlist = list(serial.tools.list_ports.comports())

    for device in portlist:
        if device.pid == product_id and device.vid == vendor_id:
            # connect and ask for serialnum
            try:
                print("check for serialnum (", str(args.serialnum) , ") on port: ", device.device)
                ser = serial.Serial(
                port = device.device,
                baudrate = args.BAUDRATE,
                parity = serial.PARITY_NONE,
                stopbits = serial.STOPBITS_ONE,
                bytesize = serial.EIGHTBITS,
                timeout = 5)
                
                ser.setDTR(False)
                time.sleep(2)
                ser.setDTR(True)

                time.sleep(2)

                ser.write(bytes([255, 0, 1]))

                line = ser.readline()
                print("recieved: ", line[:len(line)-1])
                ser.close()
                

                if line[:len(line)-1] == serialnum:
                    return device.device
                
                
            except serial.SerialException:
                raise
                pass           


if __name__ == '__main__':  # noqa
    import argparse

    parser = argparse.ArgumentParser(
        description='Simple Serial to Network (TCP/IP) redirector.',
        epilog="""\
NOTE: no security measures are implemented. Anyone can remotely connect
to this service over the network.
Only one connection at once is supported. When the connection is terminated
it waits for the next connect.
""")

    group = parser.add_argument_group('serial settings')

    exclusive_group = group.add_mutually_exclusive_group(required=True)

    exclusive_group.add_argument(
        '--serialport',
        help="serial port name")

    exclusive_group.add_argument(
        '--vidpid',
        type=int,
        nargs=2,
        help='USB-device vendorID and deviceID e.g. 6790 29987')

    parser.add_argument(
        '--serialnum',
        help='serial number of the USB <-> SerialBus bridge device')
    
    parser.add_argument(
        'BAUDRATE',
        type=int,
        nargs='?',
        help='set baud rate, default: %(default)s',
        default=9600)

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='suppress non error messages',
        default=False)

    parser.add_argument(
        '--develop',
        action='store_true',
        help='Development mode, prints Python internals on errors',
        default=False)

    group = parser.add_argument_group('serial port')

    group.add_argument(
        "--parity",
        choices=['N', 'E', 'O', 'S', 'M'],
        type=lambda c: c.upper(),
        help="set parity, one of {N E O S M}, default: N",
        default='N')

    group.add_argument(
        '--rtscts',
        action='store_true',
        help='enable RTS/CTS flow control (default off)',
        default=False)

    group.add_argument(
        '--xonxoff',
        action='store_true',
        help='enable software flow control (default off)',
        default=False)

    group.add_argument(
        '--rts',
        type=int,
        help='set initial RTS line state (possible values: 0, 1)',
        default=None)

    group.add_argument(
        '--dtr',
        type=int,
        help='set initial DTR line state (possible values: 0, 1)',
        default=None)

    group = parser.add_argument_group('network settings')

    exclusive_group = group.add_mutually_exclusive_group()

    exclusive_group.add_argument(
        '-P', '--localport',
        type=int,
        help='local TCP port',
        default=7777)

    exclusive_group.add_argument(
        '-c', '--client',
        metavar='HOST:PORT',
        help='make the connection as a client, instead of running a server',
        default=False)

    args = parser.parse_args()



    def connect_to_serial():

        global ser
        global ser_to_net
        global serial_worker

        # connect to serial port
        if args.serialport is not None:
            serialport = args.serialport
        else:
            if args.serialnum is not None:
                serialport = get_device_vidpid_serialnum(args.vidpid[0], args.vidpid[1], args.serialnum)
            else:
                serialport = get_device_vidpid(args.vidpid[0], args.vidpid[1])
            
        ser = serial.serial_for_url(serialport, do_not_open=True)


        ser.baudrate = args.BAUDRATE
        ser.parity = args.parity
        ser.rtscts = args.rtscts
        ser.xonxoff = args.xonxoff

        if args.rts is not None:
            ser.rts = args.rts

        if args.dtr is not None:
            ser.dtr = args.dtr

        if not args.quiet:
            sys.stderr.write(
                '--- TCP/IP to Serial redirect on {p.name}  {p.baudrate},{p.bytesize},{p.parity},{p.stopbits} ---\n'
                '--- type Ctrl-C / BREAK to quit\n'.format(p=ser))

        try:
            ser.open()
        except serial.SerialException as e:
            if args.develop:
                raise
            sys.stderr.write('Could not open serial port {}: {}\n'.format(ser.name, e))
            time.sleep(5)
            connect_to_serial()
            return
            

        ser_to_net = SerialToNet()
        serial_worker = serial.threaded.ReaderThread(ser, ser_to_net)
        serial_worker.start()

    
    connect_to_serial()
    
        

    if not args.client:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(('', args.localport))
        srv.listen(1)
    try:
        intentional_exit = False
        while True:
            if args.client:
                host, port = args.client.split(':')
                sys.stderr.write("Opening connection to {}:{}...\n".format(host, port))
                client_socket = socket.socket()
                try:
                    client_socket.connect((host, int(port)))
                except socket.error as msg:
                    sys.stderr.write('WARNING: {}\n'.format(msg))
                    time.sleep(5)  # intentional delay on reconnection as client
                    continue
                sys.stderr.write('Connected\n')
                client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                #~ client_socket.settimeout(5)
            else:
                sys.stderr.write('Waiting for connection on {}...\n'.format(args.localport))
                client_socket, addr = srv.accept()
                sys.stderr.write('Connected by {}\n'.format(addr))
                # More quickly detect bad clients who quit without closing the
                # connection: After 1 second of idle, start sending TCP keep-alive
                # packets every 1 second. If 3 consecutive keep-alive packets
                # fail, assume the client is gone and close the connection.
                client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
                client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 1)
                client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
                client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            try:
                ser_to_net.socket = client_socket
             
                # enter network <-> serial loop
                while True:
                    try:
                        data = client_socket.recv(1024)
                        if not data:
                            break
                        ser.write(data)                # get a bunch of bytes and send them

                    except (serial.SerialException, serial.serialutil.SerialException):
                        if args.develop:
                            raise
                        # error with serialport... try to reconnect
                        serial_worker.stop()
                        sys.stderr.write('serialport error. retry in 5 secs...')
                        time.sleep(5)
                        connect_to_serial()
                        break
                    except socket.error as msg:
                        if args.develop:
                            raise
                        sys.stderr.write('ERROR: {}\n'.format(msg))
                        # probably got disconnected
                        break
                    
                        
            except KeyboardInterrupt:
                intentional_exit = True
                raise
            except socket.error as msg:
                if args.develop:
                    raise
                sys.stderr.write('ERROR: {}\n'.format(msg))
            finally:
                ser_to_net.socket = None
                
                client_socket.close()
                sys.stderr.write('Disconnected\n')
                if args.client and not intentional_exit:
                    time.sleep(5)  # intentional delay on reconnection as client
    except KeyboardInterrupt:
        pass

    sys.stderr.write('\n--- exit ---\n')
serial_worker.stop()

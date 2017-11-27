/*
 Copyright 2016, 2017 Martin Plaas

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "Arduino.h"
#include "SerialBus.h"

//#define DEBUG

const int TIMEOUT = -1;

HardwareSerial *_serial;
int _msg_index = 0;

byte _myAddress;

unsigned long _timeout_r = 0;
unsigned long _timeout_s = 0;

byte _message_in[60];
int _message_in_length = 0; // without 4 Byte header and 1 byte checksum (only data)
byte _checksum_in = 0;

boolean _permission_to_send = false;
boolean _data_pending = false;

boolean _data_acked = false;
boolean _wait_for_ack = false;
byte _checksum_to_ack = 0;

void (*_callback_ack)();

byte *_data_out;

int _data_out_length = 0;
int _data_out_index = 0;

int _max485_sendPin = 255;
byte _wait_to_send_time = 10;
unsigned long _last_byte_millis = 0;

void (*_callback_function)(byte[], int);

SerialBus::SerialBus(HardwareSerial *serial, long baudrate, byte address,
		void (*callback)(byte[], int)) {

	init(serial, baudrate, address, callback, NULL, 255);

}

SerialBus::SerialBus(HardwareSerial *serial, long baudrate, byte address,
		void (*callback)(byte[], int), int sendPin) {
	init(serial, baudrate, address, callback, NULL, sendPin);
}

SerialBus::SerialBus(HardwareSerial *serial, long baudrate, byte address,
		void (*callback)(byte[], int), void (*callback_ack)(), int sendPin) {
	init(serial, baudrate, address, callback, callback_ack, sendPin);
}

void SerialBus::init(HardwareSerial *serial, long baudrate, byte address,
		void (*callback)(byte[], int), void (*callback_ack)(), int sendPin) {
	_msg_index = 0;
	_myAddress = address;
	_baudrate = baudrate;

	_timeout_r = 0;
	_timeout_s = 0;

	_checksum_in = 0;
	_message_out_length = 0;
	_message_in_length = 0;
	_max485_sendPin = 255;
	_callback_function = callback;
	_callback_ack = callback_ack;
	_serial = serial;
	_max485_sendPin = sendPin;
}

void SerialBus::setAckCallback(void (*callback_ack)()) {
	_callback_ack = callback_ack;
}

void SerialBus::start() {
	if (_max485_sendPin != 255) {
		pinMode(_max485_sendPin, OUTPUT);
		digitalWrite(_max485_sendPin, LOW);
	}
#ifdef DEBUG
	_serial->print("Starting. My Address: ");
	_serial->println(_myAddress, DEC);

#endif

}

boolean SerialBus::waiting() {
	return _timeout_r != 0;
}

void SerialBus::check() {

	if (_timeout_r != 0 && (millis() > _timeout_r) && !_serial->available()) {
		// Message took to long, error

		cleanUp();
	} else {

	}

	while (_serial->available()) {
		byte inByte = (byte) _serial->read();

		// If no header was detected yet
		if (_msg_index == 0) {
			if (inByte == B11111111) {

				_msg_index = 1;
				_message_in[0] = inByte;
			}
		} else {
			if (_msg_index > 3 && _msg_index <= _message_in_length + 4) {
				// Message is retrieved here ########################

				_message_in[_msg_index] = inByte;
				_msg_index++;
				while (_serial->available()
						&& _msg_index <= _message_in_length + 4) {
					inByte = (byte) _serial->read();
					_message_in[_msg_index] = inByte;
					_msg_index++;
				}

				if (_msg_index == _message_in_length + 5) {
					//Transmission complete!!!!!

					_last_byte_millis = millis();

					_checksum_in = _message_in[_msg_index - 1];
					_message_in[_msg_index - 1] = B0;

					if (get_XOR_checksum(_message_in, 4 + _message_in_length)
							== _checksum_in) {

						_timeout_r = 0;
						_msg_index = 0;

						newMessageReceived();
						//return;

					} else {
						cleanUp();
					}

				}

			} else if (_msg_index == 1) {

				if (((inByte & B00011111) == _myAddress) && (inByte & B10000000)
						&& (inByte | B01100000)) {

					_permission_to_send = (inByte & B00100000);
					_msg_index = 2;
					_message_in[1] = inByte;

				} else {
					if (inByte == B11111111) {
						_msg_index = 1;
					} else {
						_msg_index = 0;
					}
				}
			} else if (_msg_index == 2) {

				if (inByte == B11111111) {

					_msg_index = 3;
					_message_in[2] = inByte;
				} else {
					_msg_index = 0;

				}
			} else if (_msg_index == 3) {
				if ((inByte & B10000001)
						&& (((inByte & B01111110) >> 1) <= 56)) {
					// COMPLETE HEADER ########################

					_msg_index = 4;
					_message_in[3] = inByte;
					_message_in_length = ((inByte & B01111110) >> 1) - 1; // -1 for checksum
					_timeout_r = millis()
							+ ((_message_in_length + 1) * (_baudrate / 8000))
							+ 2000;

				} else {
					if (inByte == B11111111) {
						_msg_index = 1;
					} else {
						_msg_index = 0;
					}
				}
			}
		}

	}

}

void SerialBus::cleanUp() {
	_msg_index = 0;
	_timeout_r = 0;
	_message_in_length = 0;
	_checksum_in = 0;
	//_message_out_length = 0;
}

void SerialBus::newMessageReceived() {

	if ((_message_in[1] & B01100000) && _data_pending) {
		// send next part
		//delay(10);
		transmitDataBlock();

	} else if (_wait_for_ack) {
		if (_message_in[4] == _checksum_to_ack) { // is ack

			_data_acked = true;
			_checksum_to_ack = 0;
			_wait_for_ack = false;
			cleanUp();
			if (_callback_ack != NULL) {
				_callback_ack();
			}
		}
	} else {
		byte msg[_message_in_length];
		for (byte i = 0; i < _message_in_length; i++) {
			msg[i] = _message_in[i + 4];
		}
		_callback_function(msg, _message_in_length);
		cleanUp();

	}

}

boolean SerialBus::sendRawMessage(byte msg[], byte msg_length) {

	while (millis() < _last_byte_millis + _wait_to_send_time) {

	}

	byte i = 0;

	_timeout_s = millis() + msg_length * (_baudrate / 8000) + 2000;
	digitalWrite(_max485_sendPin, HIGH);

	while ((i < msg_length) && (millis() < _timeout_s)) {
		_serial->write(msg[i]);
		i++;
	}
	if (i < msg_length) {
		return false;
	}

	_serial->flush();
	digitalWrite(_max485_sendPin, LOW);

	return true;
}

void SerialBus::createHeader(byte message[], byte size, boolean pending,
		boolean ack) {
	message[0] = B11111111;
	message[1] = _myAddress;
	if (pending) {
		message[1] |= B00100000;
	}
	if (ack) {
		message[1] |= B01000000;
	}

	message[2] = B11111111;
	message[3] = B10000001 | ((size + 1) << 1);
}

byte SerialBus::sendData(byte *data, int length) {
	_data_out = data;
	_data_out_length = length;
	_data_out_index = 0;
	_data_pending = true;
	_wait_for_ack = false;
	return (transmitDataBlock());
}

byte SerialBus::sendDataAck(byte *data, int length) {
	_data_out = data;
	_data_out_length = length;
	_data_pending = true;
	_wait_for_ack = true;
	_data_acked = false;
	_checksum_to_ack = transmitDataBlock();
	return _checksum_to_ack;
}

int SerialBus::sendDataAckWait(byte *data, int length, unsigned long timeout) {

	sendDataAck(data, length);

	unsigned long startmillis = millis();
	unsigned long currentmillis = millis();
	while (!_data_acked) {
		if (currentmillis - startmillis > timeout) {
			_data_acked = false;
			_checksum_to_ack = 0;
			_wait_for_ack = false;
			cleanUp();
			return TIMEOUT;
		}

		check();
		currentmillis = millis();
	}

	return 1;
}

byte SerialBus::transmitDataBlock() {
	byte *_data_out_old = _data_out;
	int _data_out_index_old = _data_out_index;

	if (_permission_to_send && _data_out_index < _data_out_length) {

		byte message_size = 0;
		boolean pending = false;

		if (_data_out_length - _data_out_index > 55) {
			message_size = 55;
			pending = true;
		} else {
			message_size = _data_out_length - _data_out_index;
			pending = false;
		}

		byte message[message_size + 5];

		createHeader(message, message_size, pending, _wait_for_ack);

		for (byte i = 0; i < message_size; i++) {
			message[i + 4] = *_data_out;
			_data_out++;
			_data_out_index++;
		}
		byte chksm = get_XOR_checksum(message, message_size + 3);
		message[message_size + 4] = chksm;
		_permission_to_send = false;
		if (sendRawMessage(message, message_size + 5)) {
			if (_data_out_index < _data_out_length - 1) {
				_data_pending = true;
			} else {
				_data_pending = false;
				_data_out_index = 0;
			}
			return chksm;
		} else {
			_data_out = _data_out_old;
			_data_out_index = _data_out_index_old;
		}
	}
	return 0;
}

byte SerialBus::get_XOR_checksum(byte str[], byte toIndex) {
	byte checksum = B0;
	for (byte i = 0; i <= toIndex; i++) {
		checksum ^= str[i];
	}
	return checksum;
}

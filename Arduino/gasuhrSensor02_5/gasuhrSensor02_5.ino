//#define DEBUG
#include "Arduino.h"
#include "SerialBus.h"

//#include <EEPROM.h>
#include "EEPROMex.h"

#define LM_SIZE 5
#define promini

// for settings
#define CONFIG_VERSION "ls1"
#define memoryBase 32

byte deviceInfo[] = "{\"id\":\"3\",\"type\":\"1B\",\"vendor\":\"Martin Plaas\",\"label\":\"Gaszaehler\",\"description\":\"Gaszaehler\",\"version\":\"V0.2\",\"author\":\"Martin Plaas\",\"email\":\"martin.plaas@gmail.com\"}";
String deviceStatus = "OK";
int configAdress = 0;

struct StoreStruct {
	char version[4];   // This is for mere detection if they are your settings
	unsigned int lowThres, highThres, minImpulseLength, minIdleLength; // The variables of your settings
	byte maxFails, hysterese, interval;
	boolean invert;
} std_config = { CONFIG_VERSION, 200, 800, 200, 800, 255, 70, 5, false };

StoreStruct config;
//----------------------

// These constants won't change:
#ifdef promini
const int sensorPin = A3;    // pin that the sensor is attached to
const int buttonPin = 4;    // pin that the sensor is attached to
const int ledPin = 3;
#endif

#ifdef nano
const int sensorPin = A7;    // pin the sensor is attached to
const int buttonPin = 4;     // pin the button is attached to
const int ledPin = 3;
#endif

void new_message(byte msg[], int len);
const byte myAddress = 7;

SerialBus bus(&Serial, 19200, myAddress, new_message, 2);

// variables:
unsigned int sensorValue = 0;         // the sensor value
unsigned int analogValue = 0;

unsigned int impulses = 0;
unsigned int impulsesData = 0; // wird nicht automatisch gelÃ¶scht nach dem abfragen... ist und value # 0 set und abfragbar
unsigned int impulsesOld = 0;

unsigned long LEDpreviousMillis = 0;        // will store last time LED was updated

int ledState = LOW;             // ledState used to set the LED

#define calibrateWaitTime 2000

byte checksum = 0;

boolean calibration_active = false;
#define max_calibration_time 100000

boolean impulse = false;
unsigned long startImpulseMillis = 0;
unsigned long startIdleMillis = millis();
unsigned long impulseDuration = 0;
unsigned long idleDuration = 0;
unsigned long prevMillis = 0;
unsigned long currentMillis = 0;

byte failCount = 0;



void setup() {

	pinMode(13, OUTPUT);
	//pinMode(9, OUTPUT);
	pinMode(buttonPin, INPUT_PULLUP);
	pinMode(sensorPin, INPUT);
	pinMode(ledPin, OUTPUT);

	digitalWrite(13, LOW);
	digitalWrite(ledPin, HIGH);

	// tone(9, 2500, 500);
	Serial.begin(19200);
	// turn on LED to signal the start of the calibration period:

	bus.start();

	EEPROM.setMemPool(memoryBase, EEPROMSizeNano); //Set memorypool base to 32
	configAdress = EEPROM.getAddress(sizeof(StoreStruct)); // Size of config object

#ifdef DEBUG
	Serial.print("configaddress: ");
	Serial.println(configAdress);
#endif

	loadConfig();

  //deviceStatus = "{\"id\":\"00-00-02\",\"label\":\"Wasserzaehler\",\"description\":\"Wasserzaehler\",\"version\":\"V0.2\",\"author\":\"Martin Plaas\",\"email\":\"martin.plaas@gmail.com\"}";

#ifdef DEBUG
	Serial.println("starte...");
#endif

}

boolean loadConfig() {
	StoreStruct _strg;
	EEPROM.readBlock(configAdress, _strg);
#ifdef DEBUG
	Serial.print("read config: ");
	Serial.println(_strg.version);
#endif
	if (strcmp(_strg.version, CONFIG_VERSION) == 0) {
		config = _strg;
		return true;
	} else {
		config = std_config;
		saveConfig();
		return false;
	}

}

void saveConfig() {
	EEPROM.writeBlock(configAdress, config);
}

unsigned long runningAverage(int M) {

	static int LM[LM_SIZE];      // LastMeasurements
	static byte index = 0;
	static long sum = 0;
	static byte count = 0;

	// keep sum updated to improve speed.
	sum -= LM[index];
	LM[index] = M;
	sum += LM[index];
	index++;
	index = index % LM_SIZE;
	if (count < LM_SIZE)
		count++;

	return sum / count;
}

void calibrateSensor() {
#ifdef DEBUG
	Serial.println("calibrate...");
#endif
  deviceStatus = "CALIBRATE";
	unsigned long startMillis = millis();
	boolean record = false;
	calibration_active = true;

	int between;
	int dist;
	unsigned int sensorMin = 1023;        // minimum sensor value
	unsigned int sensorMax = 0;           // maximum sensor value

	while (calibration_active && millis() - startMillis < max_calibration_time
			&& digitalRead(buttonPin) == HIGH) {

		delay(10);
		// read the sensor:
		analogValue = analogRead(sensorPin);
		if (config.invert) {
			analogValue = 1023 - analogValue;
		}

		sensorValue = runningAverage(analogValue);

		if (!record && millis() - startMillis > calibrateWaitTime) {
			record = true;
		}

		if (record) {
			// record the maximum sensor value
			if (sensorValue > sensorMax) {
				sensorMax = sensorValue;
			}

			// record the minimum sensor value
			if (sensorValue < sensorMin) {
				sensorMin = sensorValue;
			}
		}

		between = sensorMax - sensorMin;
		dist = (((float) config.hysterese / 100) * between) / 2;

		config.lowThres = sensorMin + dist;
		config.highThres = sensorMax - dist;

		blinky(200);

		if (Serial.available() || bus.waiting()) {
			bus.check();
		}

   
	}

  deviceStatus = "OK";

	saveConfig();

#ifdef DEBUG
	Serial.print("sensorMin: ");
	Serial.println(sensorMin, DEC);
	Serial.print("sensorMax: ");
	Serial.println(sensorMax, DEC);

	Serial.print("lowThres: ");
	Serial.println(config.lowThres, DEC);
	Serial.print("highThres: ");
	Serial.println(config.highThres, DEC);
#endif

	delay(1000);
	digitalWrite(13, LOW);

}

void blinky(unsigned long interval) {
	unsigned long currMillis = millis();
	if (currMillis - LEDpreviousMillis >= interval) {
		// save the last time you blinked the LED
		LEDpreviousMillis = currMillis;
		// if the LED is off turn it on and vice-versa:
		if (ledState == LOW) {
			ledState = HIGH;
		} else {
			ledState = LOW;
		}

		// set the LED with the ledState of the variable:
		digitalWrite(13, ledState);
	}
}

void software_Reset() // Restarts program from beginning but does not reset the peripherals and registers
{
  asm volatile ("  jmp 0");  
}  

void new_message(byte msg[], int len) {
	byte command = msg[0] >> 2;
	byte type = msg[0] & B00000011;

#ifdef DEBUG
	Serial.print("command: ");
	Serial.println(command, DEC);
	Serial.print("type: ");
	Serial.println(type, DEC);
#endif

	if (command == 8) {
		if (type == 1) {
			sendData();
		}
	} else if (command == 1) {
		//static byte msg[] = "{\"id\":\"00-00-01\",\"label\":\"Wasserzaehler\",\"description\":\"Wasserzaehler\",\"version\":\"V0.2\",\"author\":\"Martin Plaas\",\"email\":\"martin.plaas@gmail.com\"}";
		bus.sendData(deviceInfo, sizeof(deviceInfo)-1);
	} else if (command == 2) { // reset
    software_Reset();
	} else if (command == 3) { // WAKE UP

	} else if (command == 4) { // SLEEP

	} else if (command == 10) { // calibrate
		if (type == 1) {
			calibrateSensor();
		} else {
			calibration_active = false;
		}

	}  else if (command == 11) {
    int i;
    static byte statusArray[64];
    for (i = 0; i < deviceStatus.length(); i++) {
      statusArray[i] = deviceStatus.charAt(i);
    }
    bus.sendData(statusArray, i);
	} else if (command == 6) { // get value
		if (type == 2) { // integer
			static byte answer[4];
			answer[0] = B00011010;
			answer[1] = msg[1];
			if (msg[1] == 16) { // sensor value
				answer[2] = highByte(sensorValue);
				answer[3] = lowByte(sensorValue);
			} else if (msg[1] == 0) { // data
				answer[2] = highByte(impulsesData);
				answer[3] = lowByte(impulsesData);
			} else if (msg[1] == 1) { // low thres
				answer[2] = highByte(config.lowThres);
				answer[3] = lowByte(config.lowThres);
			} else if (msg[1] == 2) {
				answer[2] = highByte(config.highThres);
				answer[3] = lowByte(config.highThres);
			} else if (msg[1] == 3) {
				answer[2] = highByte(config.minImpulseLength);
				answer[3] = lowByte(config.minImpulseLength);
			} else if (msg[1] == 4) {
				answer[2] = highByte(config.minIdleLength);
				answer[3] = lowByte(config.minIdleLength);
			} else if (msg[1] == 9) {
        answer[2] = highByte(impulses);
        answer[3] = lowByte(impulses);
      } else if (msg[1] == 10) {
        answer[2] = highByte(impulsesOld);
        answer[3] = lowByte(impulsesOld);
      }
			bus.sendData(answer, 4);
		} else if (type == 1) { // byte
			static byte answer[3];
			answer[0] = B00011001;
			answer[1] = msg[1];
			if (msg[1] == 5) { // sensor value
				answer[2] = config.maxFails;
			} else if (msg[1] == 6) { // low thres
				answer[2] = config.hysterese;
			} else if (msg[1] == 7) {
				answer[2] = config.interval;
			}
			bus.sendData(answer, 3);
		} else if (type == 0) { // flag
			static byte answer[3];
			answer[0] = B00011000;
			answer[1] = msg[1];
			if (msg[1] == 8) { // sensor value
				if (config.invert) {
					answer[2] = 1;
				} else {
					answer[2] = 0;
				}
			}
			bus.sendData(answer, 3);
		}
	} else if (command == 7) { // SET value
		if (type == 2) { // integer
			int value = msg[2] * 256 + msg[3];
			if (msg[1] == 16) { // sensor value

			} else if (msg[1] == 0) { // data
				impulsesData = value;

			} else if (msg[1] == 1) { // low thres
				config.lowThres = value;

			} else if (msg[1] == 2) {
				config.highThres = value;

			} else if (msg[1] == 3) {
				config.minImpulseLength = value;

			} else if (msg[1] == 4) {
				config.minIdleLength = value;

			}

		} else if (type == 1) { // byte
			byte value = msg[2];
			if (msg[1] == 5) { // sensor value
				config.maxFails = value;
			} else if (msg[1] == 6) { // low thres
				config.hysterese = value;
			} else if (msg[1] == 7) {
				config.interval = value;
			}

		} else if (type == 0) { // flag / boolean
			boolean flag = msg[2];
			if (msg[1] == 8) { // sensor value
				config.invert = flag;
			}

		}
		saveConfig();
	} else if (command == 9) { // reset to standard
		config = std_config;
		saveConfig();
	}

}

void sendData() {
	impulsesOld = impulses;
	static byte msg[3];
	msg[0] = ((byte) 8 << 2) | (byte) 1;
	msg[1] = highByte(impulsesOld);
	msg[2] = lowByte(impulsesOld);
//delay(1000);
//checksum = bus.sendData(msg, 3);
	if (bus.sendDataAckWait(msg, 3, 2000) > 0) {
		dataAcked();
    deviceStatus = "OK";
	} else {
    // error handling
    deviceStatus = "ERROR - TIMEOUT: 'sendData'";
	}

#ifdef DEBUG
	Serial.print("checksum: ");
	Serial.println(checksum);
#endif
}

void dataAcked() {
#ifdef DEBUG
	Serial.println("Acked");
#endif
	impulses = impulses - impulsesOld;
}

void countImpulse() {
	impulses++;
	impulsesData++;
#ifdef DEBUG

	Serial.println(impulses);

#endif
}

void loop() {

/*	boolean impulse = false;
	unsigned long startImpulseMillis = 0;
	unsigned long startIdleMillis = millis();
	unsigned long impulseDuration = 0;
	unsigned long idleDuration = 0;
	unsigned long prevMillis = 0;

	byte failCount = 0;*/

impulse = false;
startImpulseMillis = 0;
startIdleMillis = millis();
impulseDuration = 0;
idleDuration = 0;
prevMillis = 0;

failCount = 0;

	while (digitalRead(buttonPin) == HIGH) {

		currentMillis = millis();

		if (currentMillis - prevMillis >= config.interval) {
			analogValue = analogRead(sensorPin);

			if (config.invert) {
				analogValue = 1023 - analogValue;
			}

			sensorValue = runningAverage(analogValue);

#ifdef DEBUGi
			if (digitalRead(2) == LOW) {
				Serial.println(sensorValue);
			}
#endif

			if (impulse) {
				if (sensorValue < config.lowThres) {
#ifdef DEBUG
					digitalWrite(13, LOW);
#endif
					impulseDuration = millis() - startImpulseMillis;
					if (impulseDuration > config.minImpulseLength) {
						// Ein valider Impuls
						startIdleMillis = millis();
						countImpulse();
						impulse = false;
						failCount = 0;

					} else {
						// ein zu kurzer impuls --> fehler (noise?) solange ignorieren bis > maxFails, dann abbrechen
						failCount++;
						if (failCount > config.maxFails) {
							failCount = 0;
							impulse = false;
							startIdleMillis = millis();
						}
					}

				}
			} else {
				if (sensorValue > config.highThres) {

					idleDuration = millis() - startIdleMillis;
					if (idleDuration > config.minIdleLength) {
						// Ein möglicher valider Impuls
						impulse = true;
						startImpulseMillis = millis();
#ifdef DEBUG
						digitalWrite(13, HIGH);
#endif
					}

				}
			}

			prevMillis = millis();

		}

		if (Serial.available() || bus.waiting()) {
			bus.check();
		}

	}

	while (digitalRead(buttonPin) == LOW) {
	}
	delay(1000);
	calibrateSensor();

}


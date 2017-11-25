#include "SerialBus.h"

const byte myAddress = 10;
int max485Pin = 2;

void new_message(byte msg[], int len);

SerialBus bus(&Serial, 19200, myAddress, new_message, max485Pin);

void setup() {
  // put your setup code here, to run once:
  Serial.begin(19200);
  bus.start();
}

void loop() {
  // put your main code here, to run repeatedly:
  if (Serial.available()){
    bus.check();
  }

}


void new_message(byte msg[], int len) {
  bus.sendData(msg, len);
}


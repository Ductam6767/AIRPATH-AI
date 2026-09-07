// AIRPATH-AI ESP32 BLE stub (Đ — flash with Arduino IDE / PlatformIO)
// Matches web/src/ble/bleTransport.ts Nordic UART UUIDs.
//
// Dependencies: NimBLE-Arduino (or ESP32 BLE Arduino)
// Phone: open app → Safety assistant → Pair BLE & send

#include <NimBLEDevice.h>

#define SERVICE_UUID        "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define CHARACTERISTIC_UUID "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

#define PIN_LEFT  25
#define PIN_RIGHT 26

NimBLECharacteristic* pTxCharacteristic;

class ServerCallbacks : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer* s) { Serial.println("BLE connected"); }
  void onDisconnect(NimBLEServer* s) {
    Serial.println("BLE disconnected");
    NimBLEDevice::startAdvertising();
  }
};

class RxCallbacks : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* c) {
    std::string value = c->getValue();
    Serial.print("RX: ");
    Serial.println(value.c_str());
    // TODO: parse JSON — turn left/right, speed_target_kmh, drive OLED + relays
    if (value.find("\"left\"") != std::string::npos) {
      digitalWrite(PIN_LEFT, HIGH);
      digitalWrite(PIN_RIGHT, LOW);
    } else if (value.find("\"right\"") != std::string::npos) {
      digitalWrite(PIN_RIGHT, HIGH);
      digitalWrite(PIN_LEFT, LOW);
    } else {
      digitalWrite(PIN_LEFT, LOW);
      digitalWrite(PIN_RIGHT, LOW);
    }
  }
};

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LEFT, OUTPUT);
  pinMode(PIN_RIGHT, OUTPUT);

  NimBLEDevice::init("AIRPATH-Assist");
  NimBLEServer* pServer = NimBLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());
  NimBLEService* pService = pServer->createService(SERVICE_UUID);
  pTxCharacteristic = pService->createCharacteristic(
      CHARACTERISTIC_UUID,
      NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR);
  pTxCharacteristic->setCallbacks(new RxCallbacks());
  pService->start();
  NimBLEAdvertising* pAdvertising = NimBLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->start();
  Serial.println("AIRPATH BLE ready");
}

void loop() {
  delay(200);
}

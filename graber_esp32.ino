#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

// Константы времени
const unsigned long SCAN_DURATION_MS = 10 * 60 * 1000; // 10 минут
unsigned long startTime = 0;
bool isScanActive = true;

BLEScan* pBLEScan;

// Переменная для ручной фильтрации дубликатов (хранит адрес последнего устройства)
String lastProcessedAddress = "";

// Функция для вывода сырого payload в формате HEX
void printRawPayload(uint8_t* payload, size_t length) {
  if (length == 0) {
    Serial.print("EMPTY");
    return;
  }
  for (size_t i = 0; i < length; i++) {
    if (payload[i] < 0x10) Serial.print("0");
    Serial.print(payload[i], HEX);
    Serial.print(" ");
  }
}

// Класс-обработчик пойманных пакетов (Callback)
class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice advertisedDevice) {
        // Проверяем таймер: если 10 минут прошло, останавливаем сканер
        if (millis() - startTime >= SCAN_DURATION_MS) {
            if (isScanActive) {
                Serial.println("\n[SYSTEM] 10 minutes elapsed. Stopping scan...");
                pBLEScan->stop();
                isScanActive = false;
            }
            return;
        }

        BLEAddress bleAddress = advertisedDevice.getAddress();
        String currentAddress = String(bleAddress.toString().c_str());

        // Простая программная фильтрация дубликатов, чтобы не спамить в консоль 
        // одним и тем же пакетом каждую миллисекунду
        if (currentAddress == lastProcessedAddress) {
            return; 
        }
        lastProcessedAddress = currentAddress;

        // 1. Выводим адрес (MAC)
        Serial.print("ADDR: ");
        Serial.print(currentAddress);
        Serial.print(" | ");

        // 2. Выводим тип адреса (0 = Public, 1 = Random, 2 = Public ID, 3 = Random ID)
        Serial.print("TYPE: ");
        Serial.print(advertisedDevice.getAddressType());
        Serial.print(" | ");

        // 3. Выводим RSSI (уровень сигнала)
        Serial.print("RSSI: ");
        Serial.print(advertisedDevice.getRSSI());
        Serial.print(" dBm | ");

        // 4. Выводим сырой payload (Raw Payload)
        Serial.print("PAYLOAD: ");
        uint8_t* rawData = advertisedDevice.getPayload();
        size_t rawLen = advertisedDevice.getPayloadLength();
        printRawPayload(rawData, rawLen);

        Serial.println(); 
    }
};

void setup() {
  Serial.begin(115200);
  
  while (!Serial) {
    delay(10);
  }

  Serial.println("[SYSTEM] Initializing BLE...");
  BLEDevice::init("ESP32-C3-Scanner");
  
  pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  
  // ВАЖНО ПО ТЗ: Пассивное сканирование (только слушаем эфир)
  pBLEScan->setActiveScan(false); 
  
  pBLEScan->setInterval(100); // 100 мс
  pBLEScan->setWindow(50);    // 50 мс

  Serial.println("[SYSTEM] Starting 10-minute passive BLE scan...");
  startTime = millis(); 
}

void loop() {
  if (isScanActive) {
    // Используем самую базовую и совместимую перегрузку метода start()
    pBLEScan->start(1, false); 
    pBLEScan->clearResults(); 
  } else {
    Serial.println("[SYSTEM] Scan finished. Idle mode.");
    delay(10000); 
  }
}

import serial
import serial.tools.list_ports
import time
import sys

# Фиксированные идентификаторы Espressif USB-JTAG/Serial для ESP32-C3 / S3
ESP32_VID = 0x303A
ESP32_PID = 0x1001
BAUD_RATE = 115200
OUTPUT_FILE = 'esp32_ble_log.txt'


def find_esp32_port():
    """Автоматический поиск COM-порта платы ESP32-C3 по VID/PID."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Проверяем совпадение VID и PID
        if port.vid == ESP32_VID and port.pid == ESP32_PID:
            return port.device
    return None


def main():
    print("=== Автоматический регистратор BLE-логов ===")
    print("Поиск платы ESP32-C3 в системе...")

    # Пытаемся найти плату
    esp_port = find_esp32_port()

    if not esp_port:
        print("[ОШИБКА] Плата ESP32-C3 не найдена!")
        print("Проверьте USB-кабель и убедитесь, что Монитор порта в Arduino IDE ЗАКРЫТ.")
        sys.exit(1)

    print(f"[УСПЕХ] Обнаружена плата на порту: {esp_port}")
    print(f"Логи будут сохранены в файл: '{OUTPUT_FILE}'")
    print("Для остановки нажмите Ctrl + C\n")

    try:
        # Подключаемся к найденному порту
        ser = serial.Serial(esp_port, BAUD_RATE, timeout=1)

        # Аппаратный пинок платы: дергаем линии DTR/RTS, чтобы ESP32 перезагрузилась
        # Это заставит её начать 10-минутный отсчет ровно в момент запуска скрипта
        ser.setDTR(False)
        ser.setRTS(False)
        time.sleep(0.1)
        ser.setDTR(True)
        ser.setRTS(True)

        # Очищаем буфер
        ser.reset_input_buffer()

        # Открываем файл на компьютере и начинаем запись
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            while True:
                if ser.in_waiting > 0:
                    # Читаем строку из порта, декодируем и убираем лишние пробелы/переносы
                    line = ser.readline().decode('utf-8', errors='ignore')

                    # Дублируем вывод в консоль ПК
                    print(line, end='')

                    # Записываем в текстовый файл
                    f.write(line)
                    f.flush()  # Принудительно сохраняем на жесткий диск ПК без буферизации

    except KeyboardInterrupt:
        print("\n[ИНФО] Запись остановлена пользователем.")
    except Exception as e:
        print(f"\n[ОШИБКА] Сбой связи с платой: {e}")


if __name__ == '__main__':
    main()

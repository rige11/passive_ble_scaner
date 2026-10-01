import serial
import serial.tools.list_ports
import time
import sys
import re

# Фиксированные идентификаторы Espressif USB-JTAG/Serial для ESP32-C3 / S3
ESP32_VID = 0x303A
ESP32_PID = 0x1001
BAUD_RATE = 115200
OUTPUT_FILE = 'esp32_ble_log.txt'

# Структуры для сбора статистики и логов
unique_devices = set()  # Хранит все уникальные MAC-адреса
type_0_devices = set()  # Хранит MAC-адреса с TYPE: 0 (Public)
type_1_devices = set()  # Хранит MAC-адреса с TYPE: 1 (Random)
all_log_lines = []  # Временный буфер для строк лога


def find_esp32_port():
    """Автоматический поиск COM-порта платы ESP32-C3 по VID/PID."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == ESP32_VID and port.pid == ESP32_PID:
            return port.device
    return None


def parse_line_for_stats(line):
    """Парсит строку лога и собирает статистику по уникальным устройствам."""
    match = re.search(r"ADDR:\s*([0-9a-fA-F:]+)\s*\|\s*TYPE:\s*(\d)", line)
    if match:
        mac = match.group(1).lower()
        addr_type = int(match.group(2))

        is_new = mac not in unique_devices
        unique_devices.add(mac)

        if addr_type == 0:
            type_0_devices.add(mac)
        elif addr_type == 1:
            type_1_devices.add(mac)

        return is_new
    return False


def generate_report_string():
    """Генерирует текстовую строку с итоговым отчетом."""
    report = "=" * 50 + "\n"
    report += "📊 ИТОГОВАЯ СТАТИСТИКА BLE СКАНИРОВАНИЯ (10 МИНУТ)\n"
    report += "=" * 50 + "\n"
    report += f" Всего поймано уникальных устройств: {len(unique_devices)}\n"
    report += f" ├─ С типом адреса 0 (Public):       {len(type_0_devices)}\n"
    report += f" └─ С типом адреса 1 (Random):       {len(type_1_devices)}\n"

    if len(unique_devices) > 0:
        random_percentage = (len(type_1_devices) / len(unique_devices)) * 100
        report += f"\n Доля Random-адресов в эфире: {random_percentage:.1f}%\n"
        report += " (Показывает высокий уровень приватности современных гаджетов)\n"
    report += "=" * 50 + "\n\n"
    return report


def save_all_to_file():
    """Записывает статистику в начало файла, а затем добавляет весь лог."""
    print(f"\n[ФАЙЛ] Формируем финальный отчет в '{OUTPUT_FILE}'...")
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            # 1. Пишем сгенерированную статистику в самое начало
            f.write(generate_report_string())

            # 2. Дописываем все накопленные строки лога ниже
            f.write("=== ПОЛНЫЙ СЫРОЙ ЛОГ СКАНИРОВАНИЯ ===\n")
            f.writelines(all_log_lines)
        print("[УСПЕХ] Файл успешно обновлен! Статистика добавлена в начало.")
    except Exception as e:
        print(f"[ОШИБКА] Не удалось сохранить файл: {e}")


def main():
    print("=== Автоматический регистратор BLE-логов ===")
    print("Поиск платы ESP32-C3 в системе...")

    esp_port = find_esp32_port()

    if not esp_port:
        print("[ОШИБКА] Плата ESP32-C3 не найдена!")
        print("Проверьте USB-кабель и убедитесь, что Монитор порта в Arduino IDE ЗАКРЫТ.")
        sys.exit(1)

    print(f"[УСПЕХ] Обнаружена плата на порту: {esp_port}")
    print("Логи выводятся на экран в реальном времени.")
    print("Скрипт завершится автоматически через 10 минут, отчет будет записан в НАЧАЛО файла.\n")
    print("Ждем запуска платы...\n")

    try:
        ser = serial.Serial(esp_port, BAUD_RATE, timeout=1)

        # Аппаратный авто-сброс платы при старте скрипта
        ser.setDTR(False)
        ser.setRTS(False)
        time.sleep(0.1)
        ser.setDTR(True)
        ser.setRTS(True)

        ser.reset_input_buffer()

        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore')

                # Мгновенный вывод в консоль ПК
                print(line, end='', flush=True)

                # Сохраняем строку во временный буфер памяти
                all_log_lines.append(line)

                # Парсим строку для накопления статистики
                is_new_device = parse_line_for_stats(line)

                if is_new_device:
                    sys.stdout.write(
                        f"\r[ПРОГРЕСС] Уникальных устройств в базе: {len(unique_devices)} | Ожидайте окончания...\n")
                    sys.stdout.flush()

                # Проверяем маркер завершения сканирования
                if "[SYSTEM] 10 minutes elapsed" in line or "Scan finished" in line:
                    time.sleep(1)
                    # Выводим статистику в консоль
                    print(generate_report_string())
                    # Перезаписываем файл: статистика встанет НАВЕРХ
                    save_all_to_file()
                    break

    except KeyboardInterrupt:
        print("\n[ИНФО] Запись принудительно прервана пользователем.")
        print(generate_report_string())
        save_all_to_file()
    except Exception as e:
        print(f"\n[ОШИБКА] Сбой связи с платой: {e}")


if __name__ == '__main__':
    main()

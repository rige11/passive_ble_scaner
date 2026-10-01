import serial
import serial.tools.list_ports
import time
import sys
import re
from pathlib import Path

# Фиксированные идентификаторы Espressif USB-JTAG/Serial для ESP32-C3 / S3
ESP32_VID = 0x303A
ESP32_PID = 0x1001
BAUD_RATE = 115200

# ОПРЕДЕЛЯЕМ ПУТЬ: Поднимаемся на 2 каталога выше от папки скрипта
# Например, если скрипт в .../project/tools/script.py, то .parent.parent вернет .../project/
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = SCRIPT_DIR.parent.parent / 'esp32_ble_log.txt'

# Структуры для сбора статистики и логов
unique_devices = set()
type_0_devices = set()
type_1_devices = set()
all_log_lines = []


def find_esp32_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == ESP32_VID and port.pid == ESP32_PID:
            return port.device
    return None


def parse_line_for_stats(line):
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
    print(f"\n[ФАЙЛ] Сохраняем отчет на два уровня выше: '{OUTPUT_FILE}'...")
    try:
        # Убеждаемся, что целевая папка существует
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(generate_report_string())
            f.write("=== ПОЛНЫЙ СЫРОЙ ЛОГ СКАНИРОВАНИЯ ===\n")
            f.writelines(all_log_lines)
        print("[УСПЕХ] Файл успешно сохранен по новому пути!")
    except Exception as e:
        print(f"[ОШИБКА] Не удалось сохранить файл: {e}")


def main():
    print("=== Автоматический регистратор BLE-логов ===")
    print("Поиск платы ESP32-C3 в системе...")

    esp_port = find_esp32_port()

    if not esp_port:
        print("[ОШИБКА] Плата ESP32-C3 не найдена!")
        sys.exit(1)

    print(f"[УСПЕХ] Обнаружена плата на порту: {esp_port}")
    print(f"Целевой файл для отчета: {OUTPUT_FILE}\n")

    try:
        ser = serial.Serial(esp_port, BAUD_RATE, timeout=1)
        ser.setDTR(False)
        ser.setRTS(False)
        time.sleep(0.1)
        ser.setDTR(True)
        ser.setRTS(True)
        ser.reset_input_buffer()

        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore')
                print(line, end='', flush=True)
                all_log_lines.append(line)

                is_new_device = parse_line_for_stats(line)
                if is_new_device:
                    sys.stdout.write(f"\r[ПРОГРЕСС] Уникальных устройств в базе: {len(unique_devices)}\n")
                    sys.stdout.flush()

                if "[SYSTEM] 10 minutes elapsed" in line or "Scan finished" in line:
                    time.sleep(1)
                    print(generate_report_string())
                    save_all_to_file()
                    break

    except KeyboardInterrupt:
        print("\n[ИНФО] Запись прервана пользователем.")
        print(generate_report_string())
        save_all_to_file()
    except Exception as e:
        print(f"\n[ОШИБКА] Сбой связи с платой: {e}")


if __name__ == '__main__':
    main()

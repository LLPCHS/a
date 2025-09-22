import json
from datetime import datetime, timedelta
import winreg

# تنظیمات
RESTART_LOG_FILE = "restart_log.json"  # فایل برای ذخیره لاگ ری‌استارت‌ها
TIME_WINDOW = 180  # بازه زمانی 3 دقیقه (180 ثانیه)
RESTART_THRESHOLD = 3  # تعداد ری‌استارت‌های مورد نیاز
PROGRAM_NAME = "نام_برنامه_شما"  # نام دقیق برنامه را اینجا وارد کنید

def load_restart_log():
    """بارگذاری لاگ ری‌استارت‌ها از فایل JSON"""
    try:
        with open(RESTART_LOG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_restart_log(restart_times):
    """ذخیره لاگ ری‌استارت‌ها در فایل JSON"""
    try:
        with open(RESTART_LOG_FILE, 'w') as f:
            json.dump(restart_times, f)
    except Exception as e:
        print(f"Error saving restart log: {e}")

def remove_from_autostart():
    """حذف برنامه از اتواستارت کاربر فعلی"""
    registry_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path, 0, winreg.KEY_ALL_ACCESS)
        try:
            winreg.DeleteValue(key, PROGRAM_NAME)
            print(f"Program '{PROGRAM_NAME}' removed from autostart ({registry_path}).")
        except FileNotFoundError:
            print(f"Program '{PROGRAM_NAME}' not found in autostart ({registry_path}).")
        except Exception as e:
            print(f"Error removing program from {registry_path}: {e}")
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        print(f"Error accessing registry ({registry_path}): {e}")

def main():
    """بررسی ری‌استارت‌ها و حذف برنامه از اتواستارت در صورت لزوم"""
    current_time = datetime.now()
    restart_times = load_restart_log()
    restart_times.append(current_time.isoformat())
    
    # فیلتر کردن ری‌استارت‌های خارج از بازه 3 دقیقه
    restart_times = [
        t for t in restart_times
        if (current_time - datetime.fromisoformat(t)).total_seconds() <= TIME_WINDOW
    ]
    
    # ذخیره لاگ به‌روزرسانی‌شده
    save_restart_log(restart_times)
    
    # بررسی تعداد ری‌استارت‌ها
    if len(restart_times) >= RESTART_THRESHOLD:
        print("Three restarts detected within 3 minutes. Removing program from autostart...")
        remove_from_autostart()
        save_restart_log([])  # پاک کردن لاگ پس از حذف
    else:
        print(f"Restart count: {len(restart_times)}. Waiting for {RESTART_THRESHOLD - len(restart_times)} more restarts.")

if __name__ == "__main__":
    main()
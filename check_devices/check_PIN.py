import pyautogui
import time
import subprocess

# تنظیمات اولیه
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

def automate_program(program_path):
    print("شروع اتوماسیون...")
    
    # اجرای برنامه با مسیر مشخص
    print(f"اجرای برنامه از مسیر: {program_path}")
    subprocess.Popen(program_path)
    time.sleep(5)  # زمان برای بارگذاری برنامه

    # فعال کردن پنجره برنامه
    pyautogui.hotkey('alt', 'tab')
    time.sleep(1)

    # پیدا کردن تب Service با استفاده از تصویر
    print("جستجو و کلیک روی تب Service...")
    service_tab = pyautogui.locateOnScreen('service_tab.png', confidence=0.8)
    if service_tab:
        pyautogui.click(service_tab)
    else:
        print("تب Service پیدا نشد!")
        return

    # مکث کوتاه برای باز شدن منو
    time.sleep(1)

    # پیدا کردن گزینه Open-Register با استفاده از تصویر
    print("جستجو و کلیک روی گزینه Open-Register...")
    open_register = pyautogui.locateOnScreen('open_register.png', confidence=0.8)
    if open_register:
        pyautogui.click(open_register)
    else:
        print("گزینه Open-Register پیدا نشد!")
        return

    # انتظار 10 ثانیه
    print("انتظار 10 ثانیه...")
    time.sleep(10)

    # چک کردن تصویر WFS_ASYNC_GetInfo قبل از F2
    print("چک کردن تصویر WFS_ASYNC_GetInfo...")
    wfs_info = pyautogui.locateOnScreen('wfs_info.png', confidence=0.8)
    if wfs_info:
        print("تصویر WFS_ASYNC_GetInfo پیدا شد.")
        # فشار کلید F2
        print("فشار کلید F2...")
        pyautogui.press('f2')
    else:
        print("تصویر WFS_ASYNC_GetInfo پیدا نشد!")
        return

    # انتظار 2 ثانیه
    print("انتظار 2 ثانیه...")
    time.sleep(2)

    # گرفتن اسکرین‌شات
    print("گرفتن اسکرین‌شات...")
    screenshot = pyautogui.screenshot()
    screenshot.save(f'screenshot_{time.strftime("%Y%m%d_%H%M%S")}.png')
    print("اسکرین‌شات ذخیره شد.")

    # چک کردن دکمه OK به تنهایی
    print("چک کردن دکمه OK...")
    ok_button = pyautogui.locateOnScreen('ok_button.png', confidence=0.8)
    if ok_button:
        print("دکمه OK پیدا شد.")
        # کلیک روی دکمه OK
        print("کلیک روی دکمه OK...")
        pyautogui.click(ok_button)
    else:
        print("دکمه OK پیدا نشد!")
        return

    # بستن برنامه
    print("بستن برنامه...")
    pyautogui.hotkey('alt', 'f4')
    time.sleep(1)  # زمان برای ظاهر شدن پیغام تأیید

    # چک کردن دکمه NO برای تأیید بستن
    print("چک کردن دکمه NO...")
    no_button = pyautogui.locateOnScreen('no_button.png', confidence=0.8)
    if no_button:
        print("دکمه NO پیدا شد.")
        # کلیک روی دکمه NO
        print("کلیک روی دکمه NO...")
        pyautogui.click(no_button)
    else:
        print("دکمه NO پیدا نشد!")
        return

if __name__ == "__main__":
    # مسیر برنامه (لطفاً مسیر دقیق را جایگزین کنید)
    program_path = "C:\ABTGSP\TEST\PIN300.exe"  # مثال: مسیر را اینجا مشخص کنید
    print("5 ثانیه تا شروع...")
    time.sleep(5)
    automate_program(program_path)
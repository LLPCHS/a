import sys
import subprocess
from PyQt5.QtWidgets import QApplication
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtCore import QTimer, Qt, QUrl, QObject, pyqtSignal, pyqtSlot
import datetime
import jdatetime
import psutil
import os

def kill_process_by_name(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'].lower() == process_name.lower():
            try:
                proc.kill()
            except:
                pass

def start_process(process_path):
    try:
        if os.path.isfile(process_path):
            subprocess.Popen(process_path, shell=False)
    except:
        pass

class DateTimeController(QObject):
    showWarning = pyqtSignal()
    updateDateTime = pyqtSignal(str, str)
    updateDayMax = pyqtSignal(int)
    closeApplication = pyqtSignal()

    def __init__(self):
        super().__init__()
        current_year = datetime.datetime.now().year
        if current_year >= 2025:
            sys.exit(0)

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_date)
        self.timer.start(60000)
        self.check_date()

    def check_date(self):
        current_year = datetime.datetime.now().year
        if current_year < 2025:
            # Check if ITM.exe is running
            itm_running = False
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == 'itm.exe':
                    itm_running = True
                    break
            
            if itm_running:
                # ITM.exe is running, proceed with killing processes
                kill_process_by_name('ITM.exe')
                kill_process_by_name('chrome.exe')
                self.showWarning.emit()
            else:
                # ITM.exe is not running, start a timer to check again
                self.wait_timer = QTimer()
                self.wait_timer.timeout.connect(self.check_date)
                self.wait_timer.start(1000)  # Check every 1 second

    @pyqtSlot(int, int)
    def update_day_max(self, year, month):
        if month in [1, 2, 3, 4, 5, 6]:
            max_day = 31
        elif month in [7, 8, 9, 10, 11]:
            max_day = 30
        else:
            try:
                jdatetime.date(year, 12, 1)
                try:
                    jdatetime.date(year, 12, 30)
                    max_day = 30
                except ValueError:
                    max_day = 29
            except:
                max_day = 29
        self.updateDayMax.emit(max_day)

    @pyqtSlot(int, int, int, int, int)
    def set_system_datetime(self, jy, jm, jd, hour, minute):
        try:
            jalali_date = jdatetime.date(jy, jm, jd)
            gregorian_date = jalali_date.togregorian()
            gy, gm, gd = gregorian_date.year, gregorian_date.month, gregorian_date.day

            period = "AM"
            if hour >= 12:
                period = "PM"
                if hour > 12:
                    hour -= 12
            elif hour == 0:
                hour = 12

            date_str = f"{gm:02d}-{gd:02d}-{gy}"
            time_str = f"{hour:02d}:{minute:02d}:00 {period}"

            subprocess.run(['cmd.exe', '/c', f'date {date_str}'], check=True, shell=True)
            subprocess.run(['cmd.exe', '/c', f'time {time_str}'], check=True, shell=True)

            self.updateDateTime.emit(
                f"تاریخ و ساعت تنظیم شد: {gy}-{gm:02d}-{gd:02d} {hour:02d}:{minute:02d} {period}",
                "success"
            )

            # اجرای برنامه‌ها بعد از تنظیم موفق
            start_process("C:\\Program Files\\ITM\\ITM.exe")
            start_process("C:\\Program Files\\ITM\\plugins\\google-chrome\\chrome.exe")

            self.closeApplication.emit()
        except ValueError as e:
            self.updateDateTime.emit(f"تاریخ شمسی نامعتبر: {str(e)}", "error")
        except subprocess.CalledProcessError as e:
            self.updateDateTime.emit(f"خطا در تنظیم تاریخ یا ساعت سیستم: {str(e)}", "error")
        except Exception as e:
            self.updateDateTime.emit(f"خطا: {str(e)}", "error")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()
    
    controller = DateTimeController()
    engine.rootContext().setContextProperty("controller", controller)
    
    engine.load(QUrl.fromLocalFile("datetime.qml"))
    
    if not engine.rootObjects():
        sys.exit(-1)
    
    sys.exit(app.exec_())
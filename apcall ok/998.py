#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Complete Contact Dialer Application – Revised:
– Added “تماس با فایل صوتی” checkbox to toggle audio playback
– Added “قطع تماس” button to hang up active calls
– Normal calls now stay active until user clicks “قطع تماس”
– Removed recording and transcription features
– Added 'Called' status with checkmark in listbox
– Persist contacts dataframe across sessions
– Added button to clear contacts list
– Run Firefox in headless mode
– Fixed issue with cat_cb AttributeError by reordering UI initialization
– Optimized delays: retry delay 3s, inter-call delay 0.5s
"""

import os
import json
import re
import threading
import time
import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd
import pygame

import keyboard
import pyperclip

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options

import pickle  # for persisting dataframe

import logging  # Added for file logging

CONFIG_FILE = "config.json"
CONTACTS_FILE = "contacts.pkl"
LOG_FILE = "dialer.log"  # Added log file

# Setup logging to file
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')


def sanitize_selector(raw: str) -> str:
    s = raw.strip()
    if s.startswith("<") and s.endswith(">"):
        inner = s[1:-1].strip()
        parts = re.findall(r'(\w+)=(?:"|\')([^"\']+)(?:"|\')', inner)
        tag = inner.split()[0]
        attrs = "".join(f'[{k}="{v}"]' for k, v in parts)
        return tag + attrs
    return s


def is_persian(text: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', text))


class ContactDialerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📞 Contact Dialer")
        self.geometry("900x720")
        self.resizable(False, False)

        # init audio
        pygame.mixer.init()

        # call control
        self.play_audio_call_var = tk.BooleanVar(value=True)
        self.hangup_event = threading.Event()
        self.call_active = False

        # state
        self.config_data = {}
        self.contacts_df = pd.DataFrame()
        self.filtered_df = pd.DataFrame()
        self.audio_path = None
        self.driver = None

        # load config and build UI
        self._load_or_init_config()
        self._build_ui()  # Moved before _load_persisted_contacts
        self._populate_audio_devices()
        self._populate_settings()
        self._load_persisted_contacts()  # Moved after _build_ui

        # global hotkey: Ctrl+Shift+C
        keyboard.add_hotkey(
            "ctrl+shift+c",
            lambda: self.after(0, self._hotkey_manual_call)
        )

    def _load_or_init_config(self):
        default = {
            "site_url": "",
            "username": "",
            "password": "",
            "selectors": {
                "username": "input[name=\"login\"]",
                "password": "input[name=\"password\"]",
                "login_button": "button[type=\"submit\"]",
                "dialer_button": "button#dialer-button",
                "phone_input": "input[name=\"phone\"]",
                "call_button": "button.call-now",
                "hangup_button": "",
                "pause_indicator": ".mdi-pause"
            },
            "schedule": {
                "start": "09:00",
                "end": "18:00"
            },
            "audio": {
                "repeat": 1,
                "delay": 5,
                "output_index": None
            },
            "detect": {
                "ring_timeout": 15,  # Reduced from 25s
                "off_busy_threshold": 3.0,
                "answered_grace": 0.4
            }
        }

        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, encoding="utf-8") as f:
                user_cfg = json.load(f)
            self.config_data = self._deep_merge(default, user_cfg)
        else:
            self.config_data = default
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)

    def _deep_merge(self, base, override):
        merged = {}
        for k, v in base.items():
            if k in override and isinstance(v, dict):
                merged[k] = self._deep_merge(v, override[k])
            elif k in override:
                merged[k] = override[k]
            else:
                merged[k] = v
        for k in override:
            if k not in merged:
                merged[k] = override[k]
        return merged

    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)

        # Tab1: تنظیمات Dialer
        tab1 = ttk.Frame(nb)
        nb.add(tab1, text="تنظیمات Dialer")
        pad = {"padx": 8, "pady": 4}

        # site, user, speaker, pass
        ttk.Label(tab1, text="آدرس سایت:").grid(row=0, column=0, **pad, sticky="w")
        self.site_url_var = tk.StringVar()
        ttk.Entry(tab1, textvariable=self.site_url_var, width=50).grid(row=0, column=1, **pad)

        ttk.Label(tab1, text="نام کاربری:").grid(row=1, column=0, **pad, sticky="w")
        self.username_var = tk.StringVar()
        ttk.Entry(tab1, textvariable=self.username_var, width=30).grid(row=1, column=1, **pad)

        ttk.Label(tab1, text="اسپیکر:").grid(row=1, column=2, **pad, sticky="w")
        self.output_cb = ttk.Combobox(tab1, state="readonly", width=30)
        self.output_cb.grid(row=1, column=3, **pad)

        ttk.Label(tab1, text="رمز عبور:").grid(row=2, column=0, **pad, sticky="w")
        self.password_var = tk.StringVar()
        ttk.Entry(tab1, textvariable=self.password_var, show="*", width=30).grid(row=2, column=1, **pad)

        # selectors
        rows = [
            ("Selector نام کاربری:", "login_user_sel_var"),
            ("Selector رمز عبور:", "login_pass_sel_var"),
            ("Selector دکمه ورود:", "login_btn_sel_var"),
            ("Selector دکمه Dialer:", "dialer_btn_sel_var"),
            ("Selector ورودی شماره:", "phone_input_sel_var"),
            ("Selector دکمه تماس:", "call_btn_sel_var"),
            ("Selector دکمه قطع تماس:", "hangup_btn_sel_var"),
        ]
        for i, (lbl, varnm) in enumerate(rows, start=3):
            setattr(self, varnm, tk.StringVar())
            ttk.Label(tab1, text=lbl).grid(row=i, column=0, **pad, sticky="w")
            ttk.Entry(tab1, textvariable=getattr(self, varnm), width=40).grid(
                row=i, column=1, **pad, columnspan=3
            )

        ttk.Separator(tab1, orient="horizontal").grid(
            row=10, column=0, columnspan=4, sticky="ew", pady=10
        )
        ttk.Label(tab1, text="زمان‌بندی تماس‌ها (HH:MM)").grid(
            row=11, column=0, **pad, sticky="w"
        )
        self.schedule_start_var = tk.StringVar()
        self.schedule_end_var = tk.StringVar()
        sf = ttk.Frame(tab1)
        sf.grid(row=11, column=1, sticky="w", **pad)
        ttk.Entry(sf, textvariable=self.schedule_start_var, width=7).pack(side="left")
        ttk.Label(sf, text="تا").pack(side="left", padx=5)
        ttk.Entry(sf, textvariable=self.schedule_end_var, width=7).pack(side="left")

        bf = ttk.Frame(tab1)
        bf.grid(row=12, column=0, columnspan=4, pady=15)
        ttk.Button(bf, text="💾 ذخیره تنظیمات", command=self._save_config).pack(side="left", padx=6)
        ttk.Button(bf, text="🔑 تست ورود", command=self._test_login).pack(side="left", padx=6)

        # Tab2: تماس‌ها و فایل‌ها
        tab2 = ttk.Frame(nb)
        nb.add(tab2, text="تماس & فایل‌ها")
        ff = ttk.Frame(tab2)
        ff.pack(fill="x", pady=10)
        ttk.Button(ff, text="📄 بارگذاری Excel", command=self._load_excel).pack(side="left", padx=5)
        ttk.Button(ff, text="🗑️ پاک کردن لیست", command=self._clear_contacts).pack(side="left", padx=5)
        ttk.Button(ff, text="🔊 بارگذاری صدا", command=self._load_audio).pack(side="left", padx=5)

        # audio/play controls
        af = ttk.Frame(tab2)
        af.pack(fill="x", pady=6, padx=10)
        ttk.Label(af, text="تعداد دفعات پخش:").pack(side="left")
        self.repeat_var = tk.IntVar(value=self.config_data["audio"]["repeat"])
        ttk.Spinbox(af, from_=1, to=10, textvariable=self.repeat_var, width=5).pack(side="left", padx=6)
        ttk.Label(af, text="تاخیر قبل پخش (ث):").pack(side="left", padx=20)
        self.delay_var = tk.IntVar(value=self.config_data["audio"]["delay"])
        ttk.Spinbox(af, from_=0, to=60, textvariable=self.delay_var, width=5).pack(side="left")

        # play-audio checkbox + hangup button
        bf2 = ttk.Frame(tab2)
        bf2.pack(fill="x", pady=4, padx=10)
        ttk.Checkbutton(bf2,
                        text="تماس با فایل صوتی",
                        variable=self.play_audio_call_var).pack(side="left")
        ttk.Button(bf2,
                   text="🔌 قطع تماس",
                   command=self._on_hangup).pack(side="left", padx=8)

        ttk.Label(tab2, text="فیلتر دسته‌بندی:").pack(anchor="w", padx=8, pady=4)
        self.category_var = tk.StringVar()
        self.cat_cb = ttk.Combobox(tab2, textvariable=self.category_var, state="readonly")
        self.cat_cb.pack(fill="x", padx=10)
        self.cat_cb.bind("<<ComboboxSelected>>", lambda e: self._filter_contacts())

        ttk.Label(tab2, text="لیست مخاطبین:").pack(anchor="w", padx=8, pady=4)
        lf = ttk.Frame(tab2)
        lf.pack(fill="both", expand=True, padx=10)
        self.lb = tk.Listbox(lf, selectmode="extended")
        self.lb.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(lf, command=self.lb.yview)
        sb.pack(side="right", fill="y")
        self.lb.config(yscrollcommand=sb.set)

        act = ttk.Frame(tab2)
        act.pack(pady=12)
        ttk.Button(act, text="📞 تماس با انتخاب", command=lambda: self._start_calls(False)).pack(side="left", padx=8)
        ttk.Button(act, text="📞 تماس با همه", command=lambda: self._start_calls(True)).pack(side="left", padx=8)
        ttk.Button(act, text="📱 تماس دستی", command=self._open_manual_call_dialog).pack(side="left", padx=8)

        ttk.Label(tab2, text="لاگ تماس‌ها:").pack(anchor="w", padx=8, pady=4)
        self.log_txt = tk.Text(tab2, height=9, state="disabled")
        self.log_txt.pack(fill="x", padx=10, pady=5)

    def _save_config(self):
        c = self.config_data
        c["site_url"] = self.site_url_var.get().strip()
        c["username"] = self.username_var.get().strip()
        c["password"] = self.password_var.get().strip()

        sel = c["selectors"]
        sel["username"] = sanitize_selector(self.login_user_sel_var.get().strip())
        sel["password"] = sanitize_selector(self.login_pass_sel_var.get().strip())
        sel["login_button"] = sanitize_selector(self.login_btn_sel_var.get().strip())
        sel["dialer_button"] = sanitize_selector(self.dialer_btn_sel_var.get().strip())
        sel["phone_input"] = sanitize_selector(self.phone_input_sel_var.get().strip())
        sel["call_button"] = sanitize_selector(self.call_btn_sel_var.get().strip())
        sel["hangup_button"] = sanitize_selector(self.hangup_btn_sel_var.get().strip())

        c["schedule"]["start"] = self.schedule_start_var.get().strip()
        c["schedule"]["end"] = self.schedule_end_var.get().strip()

        out_name = self.output_cb.get()
        out_idx = next((i for i, n in self.output_devices if n == out_name), None)
        c["audio"]["output_index"] = out_idx

        c["audio"]["repeat"] = self.repeat_var.get()
        c["audio"]["delay"] = self.delay_var.get()

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False, indent=2)
        self._append_log("⚙️ تنظیمات ذخیره شد.")

    def _populate_settings(self):
        c = self.config_data
        self.site_url_var.set(c["site_url"])
        self.username_var.set(c["username"])
        self.password_var.set(c["password"])

        sel = c["selectors"]
        self.login_user_sel_var.set(sel["username"])
        self.login_pass_sel_var.set(sel["password"])
        self.login_btn_sel_var.set(sel["login_button"])
        self.dialer_btn_sel_var.set(sel["dialer_button"])
        self.phone_input_sel_var.set(sel["phone_input"])
        self.call_btn_sel_var.set(sel["call_button"])
        self.hangup_btn_sel_var.set(sel["hangup_button"])

        self.schedule_start_var.set(c["schedule"]["start"])
        self.schedule_end_var.set(c["schedule"]["end"])

        prev = c["audio"]
        if prev.get("output_index") is not None:
            name = next((n for i, n in self.output_devices if i == prev["output_index"]), None)
            if name:
                self.output_cb.set(name)

    def _append_log(self, msg):
        self.log_txt.config(state="normal")
        ts = time.strftime("%H:%M:%S")
        full_msg = f"[{ts}] {msg}"
        self.log_txt.insert(tk.END, full_msg + "\n")
        self.log_txt.see(tk.END)
        self.log_txt.config(state="disabled")
        logging.info(msg)  # Log to file without timestamp (since logging adds it)

    def _populate_audio_devices(self):
        self.output_devices = []
        for i in range(pygame.mixer.get_num_channels()):  # Simplified, since no pyaudio
            self.output_devices.append((i, f"Device {i}"))

        self.output_cb["values"] = [n for _, n in self.output_devices]

    def _init_firefox_driver(self):
        opts = Options()
        # opts.add_argument("--headless")  # Removed to show the browser window
        opts.set_preference("permissions.default.microphone", 1)
        opts.set_preference("media.navigator.permission.disabled", True)
        return webdriver.Firefox(options=opts)

    def _test_login(self):
        self._save_config()
        threading.Thread(target=self._do_test_login, daemon=True).start()

    def _do_test_login(self):
        cfg = self.config_data
        self._append_log(
            f"🛠️ تست ورود: "
            f"{cfg['selectors']['username']}, "
            f"{cfg['selectors']['password']}, "
            f"{cfg['selectors']['login_button']}"
        )
        try:
            dr = self._init_firefox_driver()
            dr.get(cfg["site_url"])
            WebDriverWait(dr, 5).until(  # Reduced from 10s
                EC.presence_of_element_located((By.CSS_SELECTOR, cfg["selectors"]["username"]))
            )
            dr.find_element(By.CSS_SELECTOR, cfg["selectors"]["username"]).send_keys(cfg["username"])
            dr.find_element(By.CSS_SELECTOR, cfg["selectors"]["password"]).send_keys(cfg["password"])
            dr.find_element(By.CSS_SELECTOR, cfg["selectors"]["login_button"]).click()
            time.sleep(1)  # Reduced from 3s
            self._append_log("✅ ورود با موفقیت انجام شد.")
            dr.quit()
        except Exception as e:
            self._append_log(f"❌ خطا در تست ورود: {e}")

    def _load_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xls")])
        if not path:
            return
        df = pd.read_excel(
            path,
            converters={"شماره موبایل": lambda x: str(x).strip().split('.')[0].zfill(11)}
        )
        need = {"نام", "دسته‌بندی", "شماره موبایل"}
        if not need.issubset(df.columns):
            messagebox.showerror("خطا", "ستون‌های لازم موجود نیست.")
            return

        if 'Called' not in df.columns:
            df['Called'] = False

        self.contacts_df = df
        self._persist_contacts()
        cats = ["همه"] + sorted(df["دسته‌بندی"].dropna().unique())
        self.cat_cb["values"] = cats
        self.cat_cb.set("همه")
        self._filter_contacts()
        self._append_log(f"📥 بارگذاری {len(df)} مخاطب.")

    def _load_persisted_contacts(self):
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, 'rb') as f:
                self.contacts_df = pickle.load(f)
            cats = ["همه"] + sorted(self.contacts_df["دسته‌بندی"].dropna().unique())
            self.cat_cb["values"] = cats
            self.cat_cb.set("همه")
            self._filter_contacts()
            self._append_log(f"📥 لیست مخاطبین از حافظه بارگذاری شد ({len(self.contacts_df)} مخاطب).")

    def _persist_contacts(self):
        with open(CONTACTS_FILE, 'wb') as f:
            pickle.dump(self.contacts_df, f)

    def _clear_contacts(self):
        if messagebox.askyesno("تأیید", "آیا مطمئن هستید که لیست مخاطبین پاک شود؟"):
            self.contacts_df = pd.DataFrame()
            self.filtered_df = pd.DataFrame()
            self.lb.delete(0, tk.END)
            self.cat_cb["values"] = []
            if os.path.exists(CONTACTS_FILE):
                os.remove(CONTACTS_FILE)
            self._append_log("🗑️ لیست مخاطبین پاک شد.")

    def _load_audio(self):
        p = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav")])
        if not p:
            return
        self.audio_path = p
        self._append_log(f"🔊 صوت بارگذاری شد: {os.path.basename(p)}")

    def _filter_contacts(self):
        if self.category_var.get() == "همه":
            self.filtered_df = self.contacts_df.copy()
        else:
            self.filtered_df = self.contacts_df[
                self.contacts_df["دسته‌بندی"] == self.category_var.get()
            ]
        self.lb.delete(0, tk.END)
        for _, r in self.filtered_df.iterrows():
            check = "☑️" if r['Called'] else "⬜"
            self.lb.insert(tk.END, f"{check} {r['نام']} — {r['شماره موبایل']}")

    def _start_calls(self, all_contacts):
        if self.filtered_df.empty:
            messagebox.showwarning("هشدار", "ابتدا اکسل بارگذاری شود.")
            return
        idxs = range(len(self.filtered_df)) if all_contacts else self.lb.curselection()
        if not idxs:
            messagebox.showwarning("هشدار", "حداقل یک مخاطب انتخاب کنید.")
            return

        self.config_data["audio"]["repeat"] = self.repeat_var.get()
        self.config_data["audio"]["delay"] = self.delay_var.get()
        self._save_config()
        threading.Thread(target=self._do_calls, args=(idxs,), daemon=True).start()

    def _is_present(self, sel) -> bool:
        try:
            return len(self.driver.find_elements(By.CSS_SELECTOR, sel)) > 0
        except:
            return False

    def _wait_for_pause_outcome(self):
        cfg = self.config_data["detect"]
        sel = self.config_data["selectors"]["pause_indicator"]
        ring_timeout = float(cfg["ring_timeout"])
        off_busy_threshold = float(cfg["off_busy_threshold"])
        answered_grace = float(cfg["answered_grace"])

        deadline = time.monotonic() + ring_timeout
        while time.monotonic() < deadline:
            if self._is_present(sel):
                t0 = time.monotonic()
                self._append_log("⏳ نشانگر تماس ظاهر شد.")
                break
            time.sleep(0.2)
        else:
            self._append_log("🕔 تماس بی‌پاسخ/خارج‌دسترس.")
            return {"status": "no_answer", "duration": 0.0}

        while True:
            elapsed = time.monotonic() - t0
            present = self._is_present(sel)
            if not present:
                self._append_log(f"🧭 نشانگر ناپدید شد در {elapsed:.1f}s.")
                if elapsed <= off_busy_threshold + 0.3:
                    return {"status": "powered_off_or_busy", "duration": elapsed}
                return {"status": "ended_after_answer", "duration": elapsed}
            if elapsed >= off_busy_threshold + answered_grace:
                self._append_log(f"✅ تماس برقرار شد ({elapsed:.1f}s).")
                return {"status": "answered", "duration": elapsed}
            time.sleep(0.2)

    def _do_calls(self, idxs):
        fmt = "%H:%M"
        st = datetime.datetime.strptime(
            self.config_data["schedule"]["start"], fmt
        ).time()
        ed = datetime.datetime.strptime(
            self.config_data["schedule"]["end"], fmt
        ).time()

        while True:
            now = datetime.datetime.now().time()
            if st <= now <= ed:
                break
            self._append_log("⌛ خارج از بازه تماس، منتظر آغاز...")
            time.sleep(30)

        self._append_log("🚀 آغاز تماس‌ها...")
        try:
            self._login_driver()
            for i in idxs:
                row = self.filtered_df.iloc[i]
                num = row["شماره موبایل"]
                name = row["نام"]
                self._append_log(f"📞 تماس: {name} ({num})")

                # dial
                success = False
                while not success:
                    try:
                        inp = self.driver.find_element(
                            By.CSS_SELECTOR, self.config_data["selectors"]["phone_input"]
                        )
                        inp.clear()
                        inp.send_keys(num)
                        time.sleep(0.5)
                        self.driver.find_element(
                            By.CSS_SELECTOR, self.config_data["selectors"]["call_button"]
                        ).click()
                        success = True
                    except Exception as ex:
                        self._append_log(f"⚠️ خطا در دیال: {ex}؛ تلاش مجدد...")
                        time.sleep(3)  # Reduced from 5s
                        self._login_driver()

                outcome = self._wait_for_pause_outcome()
                status, dur = outcome["status"], outcome["duration"]

                # Mark as called
                mask = self.contacts_df['شماره موبایل'] == num
                self.contacts_df.loc[mask, 'Called'] = True
                self._persist_contacts()
                self._filter_contacts()

                if status == "answered":
                    if self.play_audio_call_var.get() and self.audio_path:
                        if self.delay_var.get() > 0:
                            time.sleep(self.delay_var.get())
                        length = pygame.mixer.Sound(self.audio_path).get_length()
                        for _ in range(self.repeat_var.get()):
                            pygame.mixer.music.load(self.audio_path)
                            pygame.mixer.music.play()
                            time.sleep(length + 0.5)
                        self._append_log(f"🎯 نتیجه تماس: وصل شد (~{dur:.1f}s).")
                    else:
                        self.call_active = True
                        self.hangup_event.clear()
                        self._append_log("☎️ تماس برقرار شد؛ منتظر قطع توسط کاربر...")
                        self.hangup_event.wait()
                        self._append_log("🔌 تماس قطع شد توسط کاربر.")
                        self.call_active = False

                elif status == "ended_after_answer":
                    self._append_log(f"🟡 تماس وصل شد اما زود قطع شد (~{dur:.1f}s).")

                elif status == "powered_off_or_busy":
                    self._append_log(f"🔴 خاموش/مشغول (~{dur:.1f}s).")

                else:
                    self._append_log("⚫ بی‌پاسخ/خارج‌دسترس.")

                time.sleep(0.5)  # Reduced from 2s

            self._append_log("✅ تمام تماس‌ها انجام شد.")
        except Exception as e:
            self._append_log(f"❌ خطا در تماس‌ها: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def _login_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

        self.driver = self._init_firefox_driver()
        self.driver.get(self.config_data["site_url"])

        sel = self.config_data["selectors"]
        WebDriverWait(self.driver, 5).until(  # Reduced from 10s
            EC.presence_of_element_located((By.CSS_SELECTOR, sel["username"]))
        )
        self.driver.find_element(By.CSS_SELECTOR, sel["username"]).send_keys(
            self.config_data["username"]
        )
        self.driver.find_element(By.CSS_SELECTOR, sel["password"]).send_keys(
            self.config_data["password"]
        )
        self.driver.find_element(By.CSS_SELECTOR, sel["login_button"]).click()

        WebDriverWait(self.driver, 5).until(  # Reduced from 10s
            EC.element_to_be_clickable((By.CSS_SELECTOR, sel["dialer_button"]))
        )
        self.driver.find_element(By.CSS_SELECTOR, sel["dialer_button"]).click()
        time.sleep(1)  # Reduced from 2s

    def _open_manual_call_dialog(self, preset_number: str = ""):
        dlg = tk.Toplevel(self)
        dlg.title("📱 تماس دستی")
        dlg.resizable(False, False)
        pad = {"padx": 8, "pady": 6}

        ttk.Label(dlg, text="شماره موبایل:").grid(row=0, column=0, **pad, sticky="w")
        phone_var = tk.StringVar(value=preset_number)
        entry = ttk.Entry(dlg, textvariable=phone_var, width=30)
        entry.grid(row=0, column=1, **pad)
        entry.focus()

        ttk.Button(
            dlg, text="📞 تماس",
            command=lambda: threading.Thread(
                target=self._perform_manual_call,
                args=(phone_var.get().strip(), dlg),
                daemon=True
            ).start()
        ).grid(row=1, column=0, columnspan=2, pady=(0, 8))

    def _perform_manual_call(self, number: str, dialog: tk.Toplevel):
        if not number:
            messagebox.showwarning("هشدار", "لطفاً شماره موبایل را وارد کنید.", parent=dialog)
            return

        self._append_log(f"📞 تماس دستی: {number}")
        try:
            self._login_driver()
            inp = self.driver.find_element(
                By.CSS_SELECTOR, self.config_data["selectors"]["phone_input"]
            )
            inp.clear()
            inp.send_keys(number)
            time.sleep(0.5)
            self.driver.find_element(
                By.CSS_SELECTOR, self.config_data["selectors"]["call_button"]
            ).click()

            outcome = self._wait_for_pause_outcome()
            status, dur = outcome["status"], outcome["duration"]

            if status == "answered":
                if self.play_audio_call_var.get() and self.audio_path:
                    if self.delay_var.get() > 0:
                        time.sleep(self.delay_var.get())
                    length = pygame.mixer.Sound(self.audio_path).get_length()
                    for _ in range(self.repeat_var.get()):
                        pygame.mixer.music.load(self.audio_path)
                        pygame.mixer.music.play()
                        time.sleep(length + 0.5)
                    self._append_log(f"🎯 تماس دستی وصل شد (~{dur:.1f}s).")
                else:
                    self.call_active = True
                    self.hangup_event.clear()
                    self._append_log("☎️ تماس دستی برقرار شد؛ منتظر قطع توسط کاربر...")
                    self.hangup_event.wait()
                    self._append_log("🔌 تماس دستی قطع شد توسط کاربر.")
                    self.call_active = False

            elif status == "ended_after_answer":
                self._append_log(f"🟡 تماس دستی قطع زودهنگام (~{dur:.1f}s).")

            elif status == "powered_off_or_busy":
                self._append_log(f"🔴 تلفن مشغول/خاموش (~{dur:.1f}s).")

            else:
                self._append_log("⚫ تماس دستی بی‌پاسخ/خارج‌دسترس.")
        except Exception as e:
            self._append_log(f"❌ خطا در تماس دستی: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
            dialog.destroy()

    def _on_hangup(self):
        """User-triggered hang-up"""
        if not self.call_active:
            self._append_log("⚠️ هیچ تماسی برای قطع وجود ندارد.")
            return
        self._append_log("🔌 درخواست قطع تماس ارسال شد.")
        try:
            sel = self.config_data["selectors"]["hangup_button"]
            if sel and self.driver:
                btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                btn.click()
        except Exception as e:
            self._append_log(f"⚠️ خطا در اجرای قطع تماس: {e}")
        self.hangup_event.set()

    def _hotkey_manual_call(self):
        """میانبر Ctrl+Shift+C: کپی شماره منتخب و بازکردن دیالوگ تماس دستی"""
        text = pyperclip.paste().strip()
        if re.fullmatch(r'\d{5,}', text):
            self._open_manual_call_dialog(preset_number=text)
        else:
            self._append_log("⚠️ متن کلیپ‌بورد شماره موبایل معتبر نبود.")


if __name__ == "__main__":
    ContactDialerApp().mainloop()

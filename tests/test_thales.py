import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
import csv
import os
from datetime import datetime
import numpy as np

class CryocoolerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Thales Cryocooler Controller – Python Version")
        self.serial_obj = None
        self.log_file = None
        self.is_logging = True
        self.timer_thread = None
        self.stop_event = threading.Event()

        self.temp_data = []
        self.time_data = []
        self.volt_data = []
        self.set_point_K = None
        self.start_time = None
        self.file_to_save = ""

        self.update_interval = 1.0
        self.control_mode = tk.StringVar(value="temp")
        self.create_widgets()

    def create_widgets(self):
        self.tab_control = ttk.Notebook(self.root)
        self.main_tab = ttk.Frame(self.tab_control)
        self.slow_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.main_tab, text='Main Control')
        self.tab_control.add(self.slow_tab, text='Slow Start')
        self.tab_control.pack(expand=1, fill='both')

        self.port_var = tk.StringVar()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_menu = ttk.Combobox(self.main_tab, textvariable=self.port_var, values=ports)
        self.port_menu.set('Select')
        self.port_menu.place(relx=0.12, rely=0.93, relwidth=0.15)
        tk.Label(self.main_tab, text='Serial Port:').place(relx=0.03, rely=0.93)
        tk.Button(self.main_tab, text='Connect', command=self.connect_port).place(relx=0.28, rely=0.93)
        tk.Button(self.main_tab, text='Disconnect', command=self.disconnect_port).place(relx=0.37, rely=0.93)

        self.folder_path = tk.StringVar(value=os.getcwd())
        self.file_name = tk.StringVar(value='data.csv')
        tk.Label(self.main_tab, text='Folder (opt):').place(relx=0.03, rely=0.865)
        self.folder_entry = tk.Entry(self.main_tab, textvariable=self.folder_path, state='readonly')
        self.folder_entry.place(relx=0.16, rely=0.865, relwidth=0.20)
        tk.Button(self.main_tab, text='Choose Folder', command=self.choose_folder).place(relx=0.37, rely=0.865)

        tk.Label(self.main_tab, text='Data File (opt):').place(relx=0.03, rely=0.82)
        self.file_entry = tk.Entry(self.main_tab, textvariable=self.file_name)
        self.file_entry.place(relx=0.16, rely=0.82, relwidth=0.20)
        self.pause_btn = tk.Button(self.main_tab, text='Pause Logging', command=self.toggle_logging)
        self.pause_btn.place(relx=0.37, rely=0.82)

        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_tab)
        self.canvas.get_tk_widget().place(relx=0.50, rely=0.07, relwidth=0.45, relheight=0.57)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Temp (K)")
        self.ax.grid(True)

        tk.Label(self.main_tab, text='Update Interval (s):').place(relx=0.50, rely=0.75)
        self.interval_entry = tk.Entry(self.main_tab)
        self.interval_entry.insert(0, "1")
        self.interval_entry.place(relx=0.63, rely=0.75, relwidth=0.05)
        tk.Button(self.main_tab, text='Apply Interval', command=self.apply_interval).place(relx=0.69, rely=0.75)

        tk.Label(self.main_tab, text='Control Mode:').place(relx=0.03, rely=0.48)
        self.temp_radio = tk.Radiobutton(self.main_tab, text='Temp (K)', variable=self.control_mode, value='temp')
        self.temp_radio.place(relx=0.03, rely=0.52)
        self.temp_entry = tk.Entry(self.main_tab)
        self.temp_entry.insert(0, "293.15")
        self.temp_entry.place(relx=0.15, rely=0.52, relwidth=0.10)

        self.volt_radio = tk.Radiobutton(self.main_tab, text='Voltage (V)', variable=self.control_mode, value='voltage')
        self.volt_radio.place(relx=0.03, rely=0.56)
        self.volt_entry = tk.Entry(self.main_tab)
        self.volt_entry.insert(0, "0")
        self.volt_entry.place(relx=0.15, rely=0.56, relwidth=0.10)

        tk.Button(self.main_tab, text='Update Mode', command=self.update_mode).place(relx=0.28, rely=0.56)

        tk.Label(self.main_tab, text='Frequency (Hz):').place(relx=0.50, rely=0.92)
        self.freq_entry = tk.Entry(self.main_tab)
        self.freq_entry.insert(0, "50")
        self.freq_entry.place(relx=0.63, rely=0.92, relwidth=0.05)
        tk.Button(self.main_tab, text='Set Freq', command=self.set_frequency).place(relx=0.69, rely=0.92)

        tk.Label(self.main_tab, text='Read Freq (Hz):').place(relx=0.50, rely=0.85)
        self.read_freq = tk.StringVar(value="--")
        tk.Entry(self.main_tab, textvariable=self.read_freq, state='readonly').place(relx=0.63, rely=0.85, relwidth=0.05)
        tk.Button(self.main_tab, text='Read Freq', command=self.read_frequency).place(relx=0.69, rely=0.85)

        tk.Button(self.main_tab, text='Turn ON', command=self.start_control).place(relx=0.03, rely=0.42)
        tk.Button(self.main_tab, text='Turn OFF', command=self.stop_control).place(relx=0.15, rely=0.42)

        self.log_box = tk.Listbox(self.main_tab)
        self.log_box.place(relx=0.03, rely=0.07, relwidth=0.35, relheight=0.30)

        self.slow_labels = ['SSF (%)', 'SS1 (s)', 'SS2 (s)', 'SS3 (s)', 'SV1 (mV)', 'SV2 (mV)']
        self.slow_defaults = ['100', '5', '60', '81', '920', '1040']  # Add this line
        self.slow_entries = []
        y = 0.8
        for label, default in zip(self.slow_labels, self.slow_defaults):  # Use defaults
            tk.Label(self.slow_tab, text=label).place(relx=0.05, rely=y)
            entry = tk.Entry(self.slow_tab)
            entry.insert(0, default)  # Use default value
            entry.place(relx=0.35, rely=y, relwidth=0.10)
            self.slow_entries.append(entry)
            y -= 0.1
        tk.Button(self.slow_tab, text='Apply Slow-Start', command=self.apply_slow_start).place(relx=0.05, rely=0.15)
        tk.Button(self.slow_tab, text='End Slow-Start', command=self.end_slow_start).place(relx=0.35, rely=0.15)

    def connect_port(self):
        try:
            port = self.port_var.get()
            if port == 'Select': raise ValueError("No valid port selected")
            self.serial_obj = serial.Serial(port, baudrate=9600, timeout=1)
            self.log_message(f"Connected to {port}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def disconnect_port(self):
        if self.serial_obj:
            try:
                self.serial_obj.write(b'STP\r\n')
                self.serial_obj.close()
                self.serial_obj = None
                self.log_message("Disconnected")
            except: pass

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_path.get())
        if folder:
            self.folder_path.set(folder)
            self.log_message(f"Folder set: {folder}")

    def toggle_logging(self):
        self.is_logging = not self.is_logging
        self.pause_btn.config(text='Pause Logging' if self.is_logging else 'Resume Logging')

    def open_file(self):
        folder = self.folder_path.get()
        file_name = self.file_entry.get()
        ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        base, ext = os.path.splitext(file_name)
        if not ext: ext = '.csv'
        full_name = os.path.join(folder, f"{base}_{ts}{ext}")
        self.file_to_save = full_name
        self.log_message(f"Data file set: {full_name}")
        self.log_file = open(full_name, 'w', newline='')
        self.csv_writer = csv.writer(self.log_file)
        self.csv_writer.writerow(['DateTime', 'Time (s)', 'Temp (K)', 'Voltage (mV)'])

    def start_control(self):
        if not self.serial_obj:
            messagebox.showerror("Error", "Not connected to a serial port")
            return

        self.serial_obj.write(b'SRE 1\r\n')
        self.open_file()
        self.start_time = time.time()
        self.stop_event.clear()
        self.temp_data = []
        self.time_data = []
        self.volt_data = []
        self.timer_thread = threading.Thread(target=self.update_loop)
        self.timer_thread.start()
        self.log_message("Cryocooler ON")

    def stop_control(self):
        if self.serial_obj:
            self.serial_obj.write(b'SRE 0\r\n')
        self.stop_event.set()
        if self.timer_thread:
            self.timer_thread.join()
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        self.log_message("Cryocooler OFF")

    def update_loop(self):
        while not self.stop_event.is_set():
            try:
                t = time.time() - self.start_time

                self.serial_obj.reset_input_buffer()
                self.serial_obj.write(b'RVS\r\n')
                time.sleep(0.1)

                for _ in range(10):
                    raw = self.serial_obj.readline().decode(errors='ignore').strip()
                    try:
                        mV = float(raw)
                        K = self.voltage_to_kelvin(mV)
                        break
                    except ValueError:
                        pass
                else:
                    # No valid number found after 10 tries
                    time.sleep(self.update_interval)
                    continue
                self.temp_data.append(K)
                self.time_data.append(t)
                self.volt_data.append(mV)

                if self.is_logging and self.log_file:
                    self.csv_writer.writerow([datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), f"{t:.2f}", f"{K:.2f}", f"{mV:.2f}"])

                self.ax.clear()
                self.ax.plot(self.time_data, self.temp_data, '-ob')
                if self.set_point_K:
                    self.ax.axhline(self.set_point_K, color='r', linestyle='--', label='Setpoint')
                self.ax.set_xlabel("Time (s)")
                self.ax.set_ylabel("Temp (K)")
                self.ax.grid(True)
                self.canvas.draw()
                time.sleep(self.update_interval)
            except Exception as e:
                self.log_message(f"Error: {e}")

    def update_mode(self):
        mode = self.control_mode.get()
        if not self.serial_obj: return
        if mode == 'temp':
            K = float(self.temp_entry.get())
            mV = self.kelvin_to_voltage(K)
            cmd = f'SSP {mV:.2f}\r\n'
            self.serial_obj.write(cmd.encode())
            self.set_point_K = K
            self.log_message(f"SSP -> {mV:.2f} mV ({K:.2f} K)")
        else:
            V = float(self.volt_entry.get())
            self.serial_obj.write(b'SSK 706\r\n')
            cmd = f'SOV {V:.2f}\r\n'
            self.serial_obj.write(cmd.encode())
            self.log_message(f"SOV -> {V:.2f} Vac")

    def set_frequency(self):
        if not self.serial_obj: return
        f = float(self.freq_entry.get())
        if 30 <= f <= 100:
            cmd = f'SFR {f:.2f}\r\n'
            self.serial_obj.write(cmd.encode())
            self.log_message(f"Frequency set to {f:.2f} Hz")
        else:
            messagebox.showwarning("Input Error", "Frequency must be between 30 and 100 Hz")

    def read_frequency(self):
        if not self.serial_obj: return
        self.serial_obj.write(b'RFR\r\n')
        resp = self.serial_obj.readline().decode().strip()
        try:
            self.read_freq.set(f"{float(resp):.2f}")
            self.log_message(f"Read frequency: {resp} Hz")
        except:
            self.read_freq.set("ERR")
            self.log_message("Failed to read frequency")

    def apply_interval(self):
        try:
            interval = float(self.interval_entry.get())
            self.update_interval = max(0.1, interval)
            self.log_message(f"Interval -> {self.update_interval:.2f} s")
        except:
            self.interval_entry.delete(0, tk.END)
            self.interval_entry.insert(0, "1")

    def apply_slow_start(self):
        if not self.serial_obj: return
        for label, entry in zip(self.slow_labels, self.slow_entries):
            val = entry.get()
            cmd = f'{label} {val}\r\n'
            self.serial_obj.write(cmd.encode())
            time.sleep(0.1)
            self.log_message(cmd.strip())

    def end_slow_start(self):
        if not self.serial_obj: return
        self.serial_obj.write(b'ESS\r\n')
        self.log_message("ESS")

    def log_message(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_box.insert(tk.END, f"[{timestamp}] {msg}")
        self.log_box.yview(tk.END)

    def voltage_to_kelvin(self, mV):
        v = np.array([1624.302,1621.538,1568.453,1560.534,1392.006,1204.561,1196.144,
                     1120.642,1118.219,1102.003,1100.485,1087.711,1086.338,1060.346,
                     1032.082,994.930,955.920,915.333,873.513,830.647,786.902,742.370,
                     697.132,651.274])
        k = np.array([4.257,4.599,10.212,10.730,20.136,30.029,30.522,40.065,41.073,50.097,
                     51.100,60.062,61.056,79.936,99.809,124.666,149.504,174.339,199.155,
                     223.976,248.788,273.584,298.372,323.144])

        idx = np.argsort(v)
        v_sorted = v[idx]
        k_sorted = k[idx]
        return float(np.interp(mV, v_sorted, k_sorted))

    def kelvin_to_voltage(self, K):
        k = np.array([4.257,4.599,10.212,10.730,20.136,30.029,30.522,40.065,41.073,50.097,
                     51.100,60.062,61.056,79.936,99.809,124.666,149.504,174.339,199.155,
                     223.976,248.788,273.584,298.372,323.144])
        v = np.array([1624.302,1621.538,1568.453,1560.534,1392.006,1204.561,1196.144,
                      1120.642,1118.219,1102.003,1100.485,1087.711,1086.338,1060.346,
                      1032.082,994.930,955.920,915.333,873.513,830.647,786.902,742.370,
                      697.132,651.274])

        idx = np.argsort(v)
        v_sorted = v[idx]
        k_sorted = k[idx]
        return float(np.interp(K, k_sorted, v_sorted))

if __name__ == '__main__':
    root = tk.Tk()
    app = CryocoolerGUI(root)
    root.mainloop()

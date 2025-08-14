"""
Thales XPCDE4865 Cryocooler Controller Interface

This module provides a class to interface with the Thales XPCDE4865 cryocooler
over a serial port. Supports temperature setpoint, voltage setpoint, frequency control,
slow-start, and basic logging.

Example usage:
    from pyhkdlib.instruments.gpib.thales_XPCDE4865 import ThalesXPCDE4865
    cryo = ThalesXPCDE4865(port='/dev/ttyUSB1')
    cryo.connect()
    cryo.set_frequency(50)
    cryo.set_temperature(293.15)
    print(cryo.read_temperature())
    cryo.disconnect()
"""

import serial
import time
import logging
import numpy as np

from ..instrument import Instrument

class ThalesXPCDE4865(Instrument):
    """
    Interface for Thales XPCDE4865 cryocooler controller.
    """
    NUM_SENSORS = 2
    BOX_TYPE = 'THALES_XPCDE4865'

    def __init__(self, port='/dev/ttyUSB1', baudrate=9600, timeout=2.0, wait_time=1, channels=None, **kwargs):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.wait_time = wait_time
        self.serial = None
        # Ensure channels is always a list
        if channels is None:
            channels = [
                {"name": "Controller Temp", "type": "temperature"},
                {"name": "Controller Voltage", "type": "voltage"},
            ]
        elif not isinstance(channels, list):
            raise ValueError("channels must be a list or None")

        super().__init__(channels=channels, wait_time=wait_time, **kwargs)
        logging.info("ThalesXPCDE4865 initialized.")

    def connect(self):
        self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        self.serial.write(b'\r\n')
        time.sleep(0.1)
        self.flush()
        return self.serial.is_open

    def disconnect(self):
        if self.serial:
            self.write_cmd('STP')
            self.serial.close()
            self.serial = None

    def flush(self):
        if self.serial:
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

    def write_cmd(self, cmd):
        if self.serial:
            self.serial.write((cmd + '\r\n').encode())
            time.sleep(0.05)

    def read_line(self):
        if self.serial:
            return self.serial.readline().decode(errors='ignore').strip()
        return ""

    def enable(self, on=True):
        """Turn ON/OFF cryocooler output."""
        self.write_cmd(f"SRE {1 if on else 0}")

    def set_frequency(self, freq_hz):
        """Set cryocooler frequency (Hz)."""
        if not (30 <= freq_hz <= 100):
            raise ValueError("Frequency must be 30–100 Hz")
        self.write_cmd(f"SFR {freq_hz:.2f}")
        self.setpoint_freq = freq_hz

    def read_frequency(self):
        """Read current frequency (Hz)."""
        self.write_cmd("RFR")
        resp = self.read_line()
        try:
            return float(resp)
        except ValueError:
            return np.nan

    def set_temperature(self, kelvin):
        """Set temperature setpoint (K)."""
        mV = self.kelvin_to_voltage(kelvin)
        self.write_cmd(f"SSP {mV:.2f}")
        self.setpoint_K = kelvin

    def set_voltage(self, voltage):
        """Set output voltage (Vac)."""
        if voltage > 28:
            voltage = 28
        self.write_cmd("SSK 706")
        self.write_cmd(f"SOV {voltage:.2f}")
        self.setpoint_V = voltage

    def read_temperature(self):
        """Read temperature in Kelvin."""
        self.write_cmd("RVS")
        for _ in range(10):
            raw = self.read_line()
            try:
                mV = float(raw)
                return self.voltage_to_kelvin(mV)
            except ValueError:
                continue
        return np.nan

    def read_voltage(self):
        """Read output voltage (mV)."""
        self.write_cmd("RVS")
        for _ in range(10):
            raw = self.read_line()
            try:
                return float(raw)
            except ValueError:
                continue
        return np.nan

    def apply_slow_start(self, ssf=100, ss1=5, ss2=60, ss3=81, sv1=920, sv2=1040):
        """Apply slow-start parameters. Defaults match GUI/web."""
        tags = ['SSF', 'SS1', 'SS2', 'SS3', 'SV1', 'SV2']
        vals = [ssf, ss1, ss2, ss3, sv1, sv2]
        for tag, val in zip(tags, vals):
            self.write_cmd(f"{tag} {val}")
            time.sleep(0.1)

    def end_slow_start(self):
        self.write_cmd("ESS")

    @staticmethod
    def voltage_to_kelvin(mV):
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

    @staticmethod
    def kelvin_to_voltage(K):
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

# Example script usage
if __name__ == "__main__":
    cryo = ThalesXPCDE4865()
    cryo.connect()
    cryo.enable(True)
    cryo.set_frequency(50)
    cryo.set_temperature(293.15)
    print("Temperature:", cryo.read_temperature(), "K")
    cryo.set_voltage(10)
    print("Voltage:", cryo.read_voltage(), "mV")
    cryo.apply_slow_start()
    cryo.end_slow_start()
    cryo.enable(False)
    cryo.disconnect()
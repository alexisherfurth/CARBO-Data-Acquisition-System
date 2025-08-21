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

    def __init__(self, port='/dev/ttyUSB0', baudrate=9600, timeout=2.0, wait_time=1, channels=None, **kwargs):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.wait_time = wait_time
        self.serial = None
        # Ensure channels is always a list
        if channels is None:
            channels = [
                {"name": "Sensor 1", "type": "temperature"},
                {"name": "Voltage", "type": "voltage"},
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
        if not self.serial:
            return np.nan
        
        # Clear any pending data first
        self.flush()
        time.sleep(0.1)
        
        # Send the read frequency command
        self.write_cmd("RFR")
        
        # Try multiple times to read a valid response
        for attempt in range(5):
            resp = self.read_line()
            if resp:  # If we got a response
                try:
                    freq = float(resp.strip())
                    if 0 <= freq <= 200:  # Sanity check for reasonable frequency
                        return freq
                except ValueError:
                    pass
            time.sleep(0.05)  # Small delay between attempts
        
        logging.warning("Failed to read frequency after multiple attempts")
        return np.nanSet

    def set_temperature(self, kelvin, max_voltage=None, kp=1.0, ki=0.1):
        """Set temperature setpoint (K) with optional voltage limit and PID gains."""
        mV = self.kelvin_to_voltage(kelvin)
        
        # Set PID gains first
        try:
            self.set_pid_gains(kp, ki)
        except ValueError as e:
            logging.warning(f"Invalid PID gains, using defaults: {e}")
            kp, ki = 1.0, 0.1
            self.set_pid_gains(kp, ki)
        
        # If max_voltage is specified, check if the required voltage exceeds it
        if max_voltage is not None:
            required_voltage = mV / 1000.0  # Convert mV to V for comparison
            if required_voltage > max_voltage:
                # Cap the voltage and warns
                mV = max_voltage * 1000.0
                actual_temp = self.voltage_to_kelvin(mV)
                logging.warning(f"Temperature {kelvin}K requires {required_voltage:.2f}V, "
                              f"capped at {max_voltage}V (actual temp: {actual_temp:.2f}K)")
        
        # Set the temperature setpoint
        self.write_cmd(f"SSP {mV:.2f}")
        self.setpoint_K = kelvin
        
        logging.info(f"Temperature setpoint set to {kelvin}K with PID gains: Kp={kp}, Ki={ki}")
        return mV / 1000.0  # Return actual voltage set

    def set_voltage(self, voltage):
        """Set output voltage (Vac)."""
        original_voltage = voltage
        if voltage > 28:
            voltage = 28
            logging.warning(f"Voltage {original_voltage}V exceeds maximum limit, capped at 28V")
        self.write_cmd("SSK 706")
        self.write_cmd(f"SOV {voltage:.2f}")
        self.setpoint_V = voltage
        return voltage  # Return the actual voltage that was set

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

    def read(self):
        """Read data from all channels."""
        if not self.serial:
            return {}
        
        try:
            # Send RVS command once and get the response
            self.write_cmd("RVS")
            time.sleep(0.1)  # Give device time to respond
            
            # Try to read the response
            for attempt in range(5):
                raw = self.read_line()
                if raw:
                    try:
                        volt_mv = float(raw.strip())
                        temp_k = self.voltage_to_kelvin(volt_mv)
                        
                        # Add logging for debugging
                        logging.debug(f"Thales raw voltage: {volt_mv} mV, converted temp: {temp_k} K")
                        
                        break
                    except ValueError:
                        time.sleep(0.05)
                        continue
            else:
                logging.warning("Failed to read valid data from Thales")
                return {}
            
            # Return data for all configured channels
            data = {}
            for channel in self.channels:
                if channel['type'] == 'temperature':
                    data[channel['name']] = temp_k
                elif channel['type'] == 'voltage':
                    # Convert mV to V for voltage type
                    data[channel['name']] = volt_mv / 1000.0
            
            return data
            
        except Exception as e:
            logging.error(f"Error reading Thales data: {e}")
            return {}

    def update_periodic(self):
        """Update all sensor values - called by the data logging system"""
        data = self.read()
        for channel_id, channel_config in self._channels.items():
            for sensor_type in channel_config['types_processed']:
                sensor = self.get_sensor(channel_id, sensor_type, none_on_fail=True)
                if sensor is not None:
                    channel_name = channel_config['name']
                    if channel_name in data:
                        sensor.value = data[channel_name]

    def set_pid_gains(self, kp, ki):
        """Set PID gains. Valid ranges: P: 1.0-8.0, I: 0.1-0.85"""
        if not (1.0 <= kp <= 8.0):
            raise ValueError("Proportional gain must be between 1.0 and 8.0")
        if not (0.1 <= ki <= 0.85):
            raise ValueError("Integration gain must be between 0.1 and 0.85")
        
        self.write_cmd(f"SPG {kp:.2f}")
        time.sleep(0.1)
        self.write_cmd(f"SIG {ki:.2f}")
        
        logging.info(f"PID gains set: Kp={kp:.2f}, Ki={ki:.2f}")

    def read_pid_gains(self):
        """Read current PID gains"""
        try:
            # Read proportional gain
            self.write_cmd("RPG")
            time.sleep(0.1)
            kp_raw = self.read_line()
            kp = float(kp_raw) if kp_raw else np.nan
            
            # Read integration gain
            self.write_cmd("RIG")
            time.sleep(0.1)
            ki_raw = self.read_line()
            ki = float(ki_raw) if ki_raw else np.nan
            
            return kp, ki
        except Exception as e:
            logging.error(f"Failed to read PID gains: {e}")
            return np.nan, np.nan

    def set_ready_window(self, window_mv):
        """Set ready window in mV"""
        self.write_cmd(f"SRW {window_mv:.2f}")
        logging.info(f"Ready window set to {window_mv:.2f} mV")

    def read_ready_window(self):
        """Read ready window in mV"""
        try:
            self.write_cmd("RRW")
            time.sleep(0.1)
            raw = self.read_line()
            return float(raw) if raw else np.nan
        except:
            return np.nan

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

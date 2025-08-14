"""
MKS Pressure Sensor Interface via ADS1115 ADC with Digital Filter

This module provides a class to interface with an MKS pressure sensor
using an ADS1115 ADC over I2C. The sensor voltage is read, converted to
the actual sensor output voltage (accounting for a voltage divider), and
then converted to pressure in Torr. Includes digital filtering capabilities.

Example usage:
    from pyhkdlib.instruments.mks_ads1115 import MKSADS1115Pressure
    mks = MKSADS1115Pressure(i2c_bus=1, enable_filter=True, filter_cutoff=10)
    print(mks.get_pressure())
"""

import time
import logging
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import numpy as np
from scipy import signal

from ..instrument import Instrument
from pyhkdlib.sensor import Sensor

class MKSADS1115Pressure(Instrument):
    """
    Interface for an MKS pressure sensor read via ADS1115 ADC with digital filtering.
    """
    NUM_SENSORS = 2  # Raw and filtered pressure
    BOX_TYPE = 'MKSADS1115'

    def __init__(self, i2c_bus=None, gain=1, r1=100e3, r2=100e3, wait_time=1, channels=None, 
                 enable_filter=True, filter_cutoff=0.3, filter_order=2,
                 enable_spike_filter=True, spike_threshold=3.0, median_window=3, **kwargs):
        # Set up I2C
        if i2c_bus is None:
            self.i2c = busio.I2C(board.SCL, board.SDA)
        else:
            import sys
            import adafruit_blinka.microcontroller.generic_linux.i2c as blinka_i2c
            self.i2c = blinka_i2c.I2C(i2c_bus)
        self.ads = ADS.ADS1115(self.i2c)
        self.ads.gain = gain
        self.chan = AnalogIn(self.ads, ADS.P0)
        self.r1 = r1
        self.r2 = r2
        self.wait_time = wait_time

        # Filter parameters
        self.enable_filter = enable_filter
        self.filter_cutoff = filter_cutoff  # Hz
        self.filter_order = filter_order    # Filter order
        self.fs = 1.0 / wait_time  # Sampling frequency
        
        # Validate filter parameters
        nyquist_freq = self.fs / 2.0
        if self.enable_filter and self.filter_cutoff >= nyquist_freq:
            self.filter_cutoff = nyquist_freq * 0.8
            logging.warning(f"Filter cutoff adjusted to {self.filter_cutoff:.3f} Hz (Nyquist: {nyquist_freq:.3f} Hz)")
        
        # Filter state variables for higher order filter
        self.filter_initialized = False
        self.x_history = []  # Input history
        self.y_history = []  # Output history
        
        # Calculate filter coefficients
        if self.enable_filter:
            try:
                self.b, self.a = signal.butter(self.filter_order, self.filter_cutoff, fs=self.fs)
                logging.info(f"Digital Butterworth filter initialized: fc={self.filter_cutoff:.3f} Hz, order={self.filter_order}, fs={self.fs:.3f} Hz")
                
                # Initialize history arrays
                self.x_history = [0.0] * len(self.b)
                self.y_history = [0.0] * (len(self.a) - 1)
                
            except ValueError as e:
                logging.error(f"Failed to initialize filter: {e}")
                self.enable_filter = False
                logging.warning("Filter disabled due to invalid parameters")
        
        # Moving average filter parameters
        self.enable_moving_average = True
        self.moving_average_window = 5
        self.pressure_buffer = []
        
        # Spike filtering parameters
        self.enable_spike_filter = enable_spike_filter
        self.spike_threshold = spike_threshold  # Standard deviations
        self.median_window = median_window
        self.recent_values = []
        
        if channels is None:
            channels = [
                {"name": "Pressure", "type": "pressure"},
                {"name": "Filtered Pressure", "type": "pressure"}
            ]
        super().__init__(channels=channels, wait_time=wait_time, **kwargs)
        logging.info("MKSADS1115Pressure initialized with filtering capabilities.")

    def read_voltage(self):
        # Read the divided voltage from the ADC
        v_measured = self.chan.voltage
        # Undo the voltage divider
        v_sensor = 1.00301099 * v_measured * (self.r1 + self.r2) / self.r2
        return v_sensor

    def voltage_to_pressure(self, v_sensor):
        # Example conversion: P = 10^(2*V - 11)
        return 10 ** (2 * v_sensor - 11)

    def get_pressure_raw(self):
        v_sensor = self.read_voltage()
        pressure = self.voltage_to_pressure(v_sensor)
        return pressure

    def apply_moving_average(self, filtered_pressure):
        """Apply moving average filter as additional smoothing."""
        if not self.enable_moving_average:
            return filtered_pressure
            
        # Add to buffer
        self.pressure_buffer.append(filtered_pressure)
        
        # Keep buffer size limited
        if len(self.pressure_buffer) > self.moving_average_window:
            self.pressure_buffer.pop(0)
        
        # Return average
        return sum(self.pressure_buffer) / len(self.pressure_buffer)

    def apply_spike_filter(self, raw_pressure):
        """Remove spikes using median filter and statistical outlier detection."""
        if not self.enable_spike_filter:
            return raw_pressure
            
        self.recent_values.append(raw_pressure)
        
        # Keep window size limited
        if len(self.recent_values) > self.median_window * 3:
            self.recent_values.pop(0)
        
        if len(self.recent_values) < self.median_window:
            return raw_pressure
        
        # Calculate median and standard deviation of recent values
        import statistics
        recent_median = statistics.median(self.recent_values[-self.median_window:])
        recent_std = statistics.stdev(self.recent_values[-self.median_window:]) if len(self.recent_values) > 1 else 0
        
        # Check if current value is a spike
        if recent_std > 0 and abs(raw_pressure - recent_median) > self.spike_threshold * recent_std:
            logging.debug(f"Spike detected: {raw_pressure:.3e}, using median: {recent_median:.3e}")
            return recent_median
        
        return raw_pressure

    def apply_digital_filter(self, raw_pressure):
        """Apply complete filtering pipeline."""
        # 1. Remove spikes
        spike_filtered = self.apply_spike_filter(raw_pressure)
        
        # 2. Apply Butterworth filter
        butterworth_filtered = self.apply_butterworth_filter(spike_filtered)
        
        # 3. Apply moving average
        final_filtered = self.apply_moving_average(butterworth_filtered)
        
        return final_filtered

    def apply_butterworth_filter(self, raw_pressure):
        """Apply higher order digital Butterworth filter (renamed from apply_digital_filter)."""
        if not self.enable_filter:
            return raw_pressure
            
        if not self.filter_initialized:
            # Initialize filter with first reading
            for i in range(len(self.x_history)):
                self.x_history[i] = raw_pressure
            for i in range(len(self.y_history)):
                self.y_history[i] = raw_pressure
            self.filter_initialized = True
            return raw_pressure
        
        # Shift input history and add new input
        self.x_history[1:] = self.x_history[:-1]
        self.x_history[0] = raw_pressure
        
        # Apply filter equation: y[n] = sum(b[i]*x[n-i]) - sum(a[i]*y[n-i])
        filtered_output = 0.0
        
        # Feed-forward terms (b coefficients)
        for i in range(len(self.b)):
            filtered_output += self.b[i] * self.x_history[i]
        
        # Feedback terms (a coefficients, skip a[0] which is 1)
        for i in range(1, len(self.a)):
            if i <= len(self.y_history):
                filtered_output -= self.a[i] * self.y_history[i-1]
        
        # Shift output history and add new output
        self.y_history[1:] = self.y_history[:-1]
        self.y_history[0] = filtered_output
        
        return filtered_output

    def get_pressure_filtered(self):
        raw_pressure = self.get_pressure_raw()
        filtered_pressure = self.apply_digital_filter(raw_pressure)
        return filtered_pressure

    def get_pressure(self):
        """Return raw pressure (backwards compatibility)."""
        return self.get_pressure_raw()

    def update_periodic(self):
        raw_pressure = self.get_pressure_raw()
        filtered_pressure = self.apply_digital_filter(raw_pressure)
        
        # Update raw pressure sensor (index 0 - "Pressure")
        raw_sensor = self.get_sensor(0, Sensor.TYPE_PRESSURE, none_on_fail=True)
        if raw_sensor is not None:
            raw_sensor.value = raw_pressure
            
        # Update filtered pressure sensor (index 1 - "Filtered Pressure")
        filtered_sensor = self.get_sensor(1, Sensor.TYPE_PRESSURE, none_on_fail=True)
        if filtered_sensor is not None:
            filtered_sensor.value = filtered_pressure

# Example script usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mks = MKSADS1115Pressure(enable_filter=True, filter_cutoff=5, wait_time=1)
    
    print("Starting MKS pressure monitoring with digital filter...")
    for i in range(30):
        raw_p = mks.get_pressure_raw()
        filtered_p = mks.get_pressure_filtered()
        print(f"Time: {i}s, Raw: {raw_p:.3e} Torr, Filtered: {filtered_p:.3e} Torr")
        time.sleep(mks.wait_time)
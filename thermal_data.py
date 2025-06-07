import serial
import serial.tools.list_ports
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.colors import LinearSegmentedColormap
import time
import sys
import csv
import os
from datetime import datetime

class ThermalPlotter:
    def __init__(self, port='COM6', baudrate=115200, save_data=False, save_interval=1.0):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        
        self.width = 32
        self.height = 24
        
        self.thermal_data = np.zeros((self.height, self.width))
        
        self.save_data = save_data
        self.save_interval = save_interval
        self.last_save_time = time.time()
        self.csv_file = None
        self.csv_writer = None
        self.frame_count = 0
        
        colors = ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000', '#800000']
        self.cmap = LinearSegmentedColormap.from_list('thermal', colors)
        
        self.im = self.ax.imshow(self.thermal_data, cmap=self.cmap)
        title = 'Live Thermal Camera Feed - MLX90640'
        if self.save_data:
            title += ' (Recording)'
        self.ax.set_title(title, fontsize=16)
        self.ax.set_xlabel('X Position')
        self.ax.set_ylabel('Y Position')
        
        self.cbar = plt.colorbar(self.im, ax=self.ax)
        self.cbar.set_label('Temperature (°C)', rotation=270, labelpad=20)
        
        self.temp_text = self.ax.text(0.02, 0.98, '', transform=self.ax.transAxes, 
                                     verticalalignment='top', bbox=dict(boxstyle='round', 
                                     facecolor='white', alpha=0.8))
        
        if self.save_data:
            self.init_csv_file()

    def init_csv_file(self, custom_filename=None):
        if not os.path.exists('thermal_data'):
            os.makedirs('thermal_data')
        
        if custom_filename:
            if not custom_filename.endswith('.csv'):
                custom_filename += '.csv'
            filename = f"thermal_data/{custom_filename}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"thermal_data/thermal_data_{timestamp}.csv"
        
        try:
            self.csv_file = open(filename, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            
            header = ['Timestamp', 'Frame', 'Min_Temp', 'Max_Temp', 'Avg_Temp']
            for row in range(self.height):
                for col in range(self.width):
                    header.append(f'R{row:02d}_C{col:02d}')
            
            self.csv_writer.writerow(header)
            print(f"CSV logging initialized: {filename}")
            
        except Exception as e:
            print(f"Error initializing CSV file: {e}")
            self.save_data = False
    
    def save_to_csv(self, thermal_data):
        if not self.save_data or not self.csv_writer:
            return
        
        try:
            current_time = time.time()
            
            if current_time - self.last_save_time >= self.save_interval:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                min_temp = thermal_data.min()
                max_temp = thermal_data.max()
                avg_temp = thermal_data.mean()
                
                row = [timestamp, self.frame_count, f'{min_temp:.2f}', f'{max_temp:.2f}', f'{avg_temp:.2f}']
                row.extend([f'{temp:.2f}' for temp in thermal_data.flatten()])
                
                self.csv_writer.writerow(row)
                self.csv_file.flush()
                
                self.last_save_time = current_time
                self.frame_count += 1
                
        except Exception as e:
            print(f"Error saving to CSV: {e}")
    
    def save_current_frame_as_csv(self, filename=None):
        if self.thermal_data is None:
            print("No thermal data available to save")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"thermal_frame_{timestamp}.csv"
        
        try:
            if not os.path.exists('thermal_data'):
                os.makedirs('thermal_data')
            
            filepath = os.path.join('thermal_data', filename)
            
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                
                writer.writerow(['# MLX90640 Thermal Frame Data'])
                writer.writerow(['# Timestamp:', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow(['# Resolution:', f'{self.width}x{self.height}'])
                writer.writerow(['# Min Temperature:', f'{self.thermal_data.min():.2f}°C'])
                writer.writerow(['# Max Temperature:', f'{self.thermal_data.max():.2f}°C'])
                writer.writerow(['# Average Temperature:', f'{self.thermal_data.mean():.2f}°C'])
                writer.writerow([])
                
                col_headers = [f'Col_{i:02d}' for i in range(self.width)]
                writer.writerow(['Row'] + col_headers)
                
                for row_idx, row_data in enumerate(self.thermal_data):
                    row_label = f'Row_{row_idx:02d}'
                    formatted_row = [f'{temp:.2f}' for temp in row_data]
                    writer.writerow([row_label] + formatted_row)
            
            print(f"Current frame saved to: {filepath}")
            
        except Exception as e:
            print(f"Error saving frame to CSV: {e}")
    
    def close_csv_file(self):
        if self.csv_file:
            try:
                self.csv_file.close()
                print("CSV file closed")
            except Exception as e:
                print(f"Error closing CSV file: {e}")

    def list_available_ports(self):
        ports = serial.tools.list_ports.comports()
        print("\nAvailable serial ports:")
        for port in ports:
            print(f"  {port.device} - {port.description}")
        return [port.device for port in ports]
    
    def connect_serial(self):
        try:
            print(f"Attempting to connect to {self.port}...")
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Connected to {self.port} at {self.baudrate} baud")
            time.sleep(2)
            return True
            
        except (serial.SerialException, PermissionError) as e:
            print(f"Failed to connect to {self.port}: {e}")
            
            available_ports = self.list_available_ports()
            
            if not available_ports:
                print("No serial ports found!")
                return False
            
            print("\nTrying to auto-detect ESP32...")
            for port in available_ports:
                try:
                    print(f"Trying {port}...")
                    test_ser = serial.Serial(port, self.baudrate, timeout=1)
                    test_ser.close()
                    
                    self.port = port
                    self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
                    print(f"Successfully connected to {self.port}")
                    time.sleep(2)
                    return True
                    
                except (serial.SerialException, PermissionError):
                    continue
            
            print("Could not connect to any available port.")
            print("\nTroubleshooting tips:")
            print("1. Make sure no other programs (Arduino IDE, serial monitor) are using the port")
            print("2. Try running this script as Administrator")
            print("3. Unplug and replug your ESP32")
            print("4. Check if the ESP32 driver is properly installed")
            return False
    
    def read_thermal_data(self):
        if not self.ser or not self.ser.is_open:
            return None
        
        try:
            line = self.ser.readline().decode('utf-8').strip()
            
            if line:
                values = line.split(', ')
                
                cleaned_values = []
                for v in values:
                    v = v.strip().rstrip(',')
                    if v:
                        cleaned_values.append(v)
                
                if len(cleaned_values) >= 768:
                    try:
                        thermal_array = np.array([float(v) for v in cleaned_values[:768]])
                        thermal_2d = thermal_array.reshape(self.height, self.width)
                        return thermal_2d
                    except ValueError as e:
                        print(f"Error converting values to float: {e}")
                        for i, v in enumerate(cleaned_values[:10]):
                            try:
                                float(v)
                            except ValueError:
                                print(f"Problematic value at index {i}: '{v}'")
                        return None
                else:
                    print(f"Insufficient data points: got {len(cleaned_values)}, expected 768")
                    
        except (UnicodeDecodeError, Exception) as e:
            print(f"Error reading/parsing data: {e}")
            
        return None
    
    def update_plot(self, frame):
        thermal_data = self.read_thermal_data()
        
        if thermal_data is not None:
            self.thermal_data = thermal_data
            
            if self.save_data:
                self.save_to_csv(thermal_data)
            
            self.im.set_array(self.thermal_data)
            
            vmin, vmax = self.thermal_data.min(), self.thermal_data.max()
            self.im.set_clim(vmin=vmin, vmax=vmax)
            
            status_text = f'Min: {vmin:.1f}°C\nMax: {vmax:.1f}°C\nAvg: {self.thermal_data.mean():.1f}°C'
            if self.save_data:
                status_text += f'\nFrame: {self.frame_count}'
            self.temp_text.set_text(status_text)
        
        return [self.im, self.temp_text]
    
    def start_live_plot(self):
        if not self.connect_serial():
            return
        
        print("\nKeyboard shortcuts:")
        print("  Ctrl+C: Stop and exit")
        print("  S: Save current frame to CSV (press in terminal)")
        
        try:
            ani = animation.FuncAnimation(self.fig, self.update_plot, interval=500, 
                                        blit=False, cache_frame_data=False)
            
            plt.tight_layout()
            plt.show()
            
        except KeyboardInterrupt:
            print("\nStopping thermal camera...")
        finally:
            if self.save_data:
                self.close_csv_file()
            if self.ser and self.ser.is_open:
                self.ser.close()
                print("Serial connection closed")

def main():
    SERIAL_PORT = 'COM6'
    BAUD_RATE = 115200
    SAVE_DATA = True
    SAVE_INTERVAL = 2.0
    
    print("Starting MLX90640 Thermal Camera Viewer")
    print(f"Primary port: {SERIAL_PORT} at {BAUD_RATE} baud...")
    
    csv_filename = None
    if SAVE_DATA:
        print("\nCSV logging is enabled")
        csv_filename = input("Enter desired CSV filename (press Enter for automatic timestamp-based name): ").strip()
        print(f"CSV logging will save every {SAVE_INTERVAL} seconds")
    print("Press Ctrl+C to exit")
    
    plotter = ThermalPlotter(port=SERIAL_PORT, baudrate=BAUD_RATE, 
                           save_data=SAVE_DATA, save_interval=SAVE_INTERVAL)
    
    if SAVE_DATA and csv_filename:
        plotter.init_csv_file(csv_filename)
    else:
        plotter.init_csv_file()
        
    plotter.start_live_plot()

if __name__ == "__main__":
    main()
import serial
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import messagebox
import time
import threading
import queue

# Serial configuration
serial_port = 'COM6'
baud_rate = 9600

# Data storage
times = []
set_temps = []
actual_temps = []

# Thread communication
data_queue = queue.Queue()
stop_thread = False

# Initialize serial connection
try:
    ser = serial.Serial(serial_port, baud_rate, timeout=1)
    time.sleep(2)  # Wait for serial connection to stabilize
    print(f"Connected to {serial_port} at {baud_rate} baud")
except serial.SerialException as e:
    print(f"Failed to connect to serial port: {e}")
    exit()

# Create GUI
root = tk.Tk()
root.title("Temperature Control GUI")
root.geometry("900x700")

# Create matplotlib figure
fig, ax = plt.subplots(figsize=(10, 6))
ax.set_xlabel('Time (s)')
ax.set_ylabel('Temperature (°C)')
ax.set_title('Temperature vs Time')
line1, = ax.plot([], [], label='Actual Temperature', color='blue', linewidth=2)
line2, = ax.plot([], [], label='Setpoint Temperature', color='red', linestyle='--', linewidth=2)
ax.legend()
ax.grid(True, alpha=0.3)

# Embed plot in tkinter
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

# Control frame
frame = tk.Frame(root)
frame.pack(side=tk.BOTTOM, pady=10)

tk.Label(frame, text="Set Temperature (°C, 0-1000):").pack(side=tk.LEFT)
entry = tk.Entry(frame, width=10)
entry.pack(side=tk.LEFT, padx=5)

status_label = tk.Label(frame, text="Setpoint: N/A °C, Current: N/A °C", 
                       font=('Arial', 10), fg='blue')
status_label.pack(side=tk.LEFT, padx=10)

# View mode controls
view_frame = tk.Frame(root)
view_frame.pack(side=tk.BOTTOM, pady=5)

view_mode = tk.StringVar(value="rolling")
tk.Radiobutton(view_frame, text="Rolling View (30s)", variable=view_mode, value="rolling").pack(side=tk.LEFT, padx=5)
tk.Radiobutton(view_frame, text="Full View", variable=view_mode, value="full").pack(side=tk.LEFT, padx=5)
tk.Radiobutton(view_frame, text="Adaptive View", variable=view_mode, value="adaptive").pack(side=tk.LEFT, padx=5)

# Connection status
conn_label = tk.Label(root, text="Status: Connected", fg='green', font=('Arial', 9))
conn_label.pack(side=tk.BOTTOM)

start_time = time.time()

def read_serial():
    """Read data from serial port with error handling"""
    global stop_thread
    
    while not stop_thread:
        try:
            if ser.in_waiting > 0:
                # Read raw bytes first
                raw_line = ser.readline()
                
                # Try to decode with error handling
                try:
                    line = raw_line.decode('utf-8', errors='ignore').strip()
                except UnicodeDecodeError:
                    # Skip invalid lines
                    continue
                
                # Skip empty lines
                if not line:
                    continue
                
                # Process data lines (expecting: setpoint,actual_temp,pid_output)
                if ',' in line and len(line.split(',')) >= 3:
                    try:
                        parts = line.split(',')
                        setpoint = float(parts[0])
                        temp = float(parts[1])
                        pid_output = float(parts[2])
                        
                        # Validate reasonable temperature values
                        if -50 <= temp <= 1500 and 0 <= setpoint <= 1000:
                            current_time = time.time() - start_time
                            data_queue.put((current_time, setpoint, temp, pid_output))
                        else:
                            print(f"Invalid temperature values: {line}")
                            
                    except (ValueError, IndexError) as e:
                        print(f"Error parsing data '{line}': {e}")
                else:
                    # Print non-data messages from Arduino
                    if line.strip():
                        print(f"Arduino: {line}")
                        
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            root.after(0, lambda: conn_label.config(text="Status: Disconnected", fg='red'))
            break
        except Exception as e:
            print(f"Unexpected error in serial thread: {e}")
            time.sleep(0.1)
        
        time.sleep(0.01)  # Small delay to prevent excessive CPU usage

def process_data_queue():
    """Process data from the serial thread"""
    try:
        while not data_queue.empty():
            current_time, setpoint, temp, pid_output = data_queue.get_nowait()
            
            times.append(current_time)
            set_temps.append(setpoint)
            actual_temps.append(temp)
            
            # Limit data history to prevent memory issues
            max_points = 10000
            if len(times) > max_points:
                times.pop(0)
                set_temps.pop(0)
                actual_temps.pop(0)
            
            # Update status label
            status_label.config(text=f"Setpoint: {setpoint:.1f} °C, Current: {temp:.1f} °C")
            conn_label.config(text="Status: Connected", fg='green')
            
    except queue.Empty:
        pass

def update_plot():
    """Update the plot with new data"""
    if stop_thread:
        return
    
    # Process any new data
    process_data_queue()
    
    if times and len(times) > 1:
        # Update plot data
        line1.set_data(times, actual_temps)
        line2.set_data(times, set_temps)
        
        current_view = view_mode.get()
        current_time = times[-1]
        
        # Set axis limits based on view mode
        if current_view == "rolling":
            # Rolling 30-second window
            x_min = max(0, current_time - 30)
            x_max = current_time + 2
            ax.set_xlim(x_min, x_max)
            
            # Get data in current window for y-axis
            window_indices = [i for i, t in enumerate(times) if t >= x_min]
            if window_indices:
                window_actual = [actual_temps[i] for i in window_indices]
                window_set = [set_temps[i] for i in window_indices]
                y_min = min(min(window_actual), min(window_set)) - 5
                y_max = max(max(window_actual), max(window_set)) + 5
                ax.set_ylim(y_min, y_max)
                
        elif current_view == "full":
            # Show all data
            ax.set_xlim(0, max(times) + 1)
            y_min = min(min(actual_temps), min(set_temps)) - 5
            y_max = max(max(actual_temps), max(set_temps)) + 5
            ax.set_ylim(y_min, y_max)
            
        elif current_view == "adaptive":
            # Adaptive view
            if current_time <= 60:
                window_size = 30
            else:
                window_size = min(current_time, 120 + (current_time - 60) * 0.5)
            
            x_min = max(0, current_time - window_size)
            x_max = current_time + 2
            ax.set_xlim(x_min, x_max)
            
            # Get data in current window for y-axis
            window_indices = [i for i, t in enumerate(times) if t >= x_min]
            if window_indices:
                window_actual = [actual_temps[i] for i in window_indices]
                window_set = [set_temps[i] for i in window_indices]
                y_min = min(min(window_actual), min(window_set)) - 5
                y_max = max(max(window_actual), max(window_set)) + 5
                ax.set_ylim(y_min, y_max)
        
        # Redraw canvas
        canvas.draw_idle()
    
    # Schedule next update
    root.after(250, update_plot)

def set_temperature():
    """Send temperature setpoint to Arduino"""
    try:
        temp_str = entry.get().strip()
        if not temp_str:
            messagebox.showerror("Error", "Please enter a temperature value.")
            return
            
        temp_val = float(temp_str)
        if 0 <= temp_val <= 1000:
            command = f"{temp_val}\n"
            ser.write(command.encode('utf-8'))
            entry.delete(0, tk.END)
            print(f"Setpoint sent: {temp_val} °C")
        else:
            messagebox.showerror("Error", "Temperature must be between 0 and 1000 °C.")
    except ValueError:
        messagebox.showerror("Error", "Invalid input! Enter a numeric value.")
    except serial.SerialException as e:
        messagebox.showerror("Serial Error", f"Failed to send command: {e}")

def on_enter(event):
    """Handle Enter key press in temperature entry"""
    set_temperature()

def close_app():
    """Clean shutdown of the application"""
    global stop_thread
    print("Closing application...")
    stop_thread = True
    
    try:
        if ser.is_open:
            ser.close()
    except:
        pass
    
    root.quit()
    root.destroy()

# Bind Enter key to set temperature
entry.bind('<Return>', on_enter)

# Create buttons
set_button = tk.Button(frame, text="Set Temperature", command=set_temperature, 
                      bg='lightgreen', font=('Arial', 10))
set_button.pack(side=tk.LEFT, padx=5)

quit_button = tk.Button(frame, text="Quit", command=close_app, 
                       bg='lightcoral', font=('Arial', 10))
quit_button.pack(side=tk.LEFT, padx=5)

# Start serial reading thread
serial_thread = threading.Thread(target=read_serial, daemon=True)
serial_thread.start()

# Handle window closing
root.protocol("WM_DELETE_WINDOW", close_app)

# Start plot updates
root.after(500, update_plot)  # Start after a short delay

print("GUI started. Waiting for data...")
root.mainloop()
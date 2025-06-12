import serial
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import messagebox
import time
import threading


serial_port = 'COM6'
baud_rate = 9600

times = []
set_temps = []
actual_temps = []

try:
    ser = serial.Serial(serial_port, baud_rate, timeout=1)
    time.sleep(2)  # Wait for serial connection to stabilize
except serial.SerialException:
    print("Failed to connect to serial port. Check port and connection.")
    exit()

root = tk.Tk()
root.title("Temperature Control GUI")
root.geometry("800x600")

fig, ax = plt.subplots()
ax.set_xlabel('Time (s)')
ax.set_ylabel('Temperature (C)')
ax.set_title('Temperature vs Time')
line1, = ax.plot([], [], label='Actual Temperature', color='blue')
line2, = ax.plot([], [], label='Setpoint Temperature', color='red', linestyle='--')
ax.legend()
ax.grid(True)

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

frame = tk.Frame(root)
frame.pack(side=tk.BOTTOM, pady=10)

tk.Label(frame, text="Set Temperature (C, 0-1000):").pack(side=tk.LEFT)
entry = tk.Entry(frame, width=10)
entry.pack(side=tk.LEFT, padx=5)

status_label = tk.Label(frame, text="Setpoint: N/A C, Current: N/A C")
status_label.pack(side=tk.LEFT, padx=10)

start_time = time.time()

def read_serial():
    while not stop_thread:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if ',' in line:
                    try:
                        setpoint, temp, pid_output = map(float, line.split(','))
                        times.append(time.time() - start_time)
                        set_temps.append(setpoint)
                        actual_temps.append(temp)
                        # Update status label
                        root.after(0, lambda: status_label.config(
                            text=f"Setpoint: {setpoint:.1f} C, Current: {temp:.1f} C"))
                    except ValueError:
                        print(f"Invalid data received: {line}")
                else:
                    print(line)
        except serial.SerialException:
            root.after(0, lambda: messagebox.showerror("Error", "Serial error, check connection."))
            break

def update_plot():
    line1.set_data(times, actual_temps)
    line2.set_data(times, set_temps)
    
    if times:
        ax.relim()
        ax.autoscale_view()
        ax.set_xlim(max(0, times[-1] - 30), times[-1] + 1)  # Show last 30 seconds
        ax.set_ylim(min(min(actual_temps[-100:]), min(set_temps[-100:])) - 5,
                    max(max(actual_temps[-100:]), max(set_temps[-100:])) + 5)
    
    canvas.draw()
    root.after(250, update_plot)

def set_temperature():
    try:
        temp = entry.get()
        temp_val = float(temp)
        if 0 <= temp_val <= 1000:
            ser.write(f"{temp_val}\n".encode('utf-8'))
            entry.delete(0, tk.END)
            print(f"Setpoint sent: {temp_val} C")
        else:
            messagebox.showerror("Error", "Temperature must be between 0 and 1000 C.")
    except ValueError:
        messagebox.showerror("Error", "Invalid input! Enter a number.")

def close_app():
    global stop_thread
    stop_thread = True
    ser.close()
    root.destroy()

set_button = tk.Button(frame, text="Set", command=set_temperature)
set_button.pack(side=tk.LEFT, padx=5)

quit_button = tk.Button(frame, text="Quit", command=close_app)
quit_button.pack(side=tk.LEFT, padx=5)

stop_thread = False

serial_thread = threading.Thread(target=read_serial, daemon=True)
serial_thread.start()
root.after(250, update_plot)

root.mainloop()
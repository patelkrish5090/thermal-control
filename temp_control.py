import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

# --- CONFIGURATION ---
PORT = 'COM6'      # Change this to your serial port (e.g. '/dev/ttyUSB0' on Linux)
BAUD = 9600
BUFFER_SIZE = 100  # How many points to show on the graph at once

# --- SET UP DATA BUFFERS ---
times       = deque(maxlen=BUFFER_SIZE)
setpoints   = deque(maxlen=BUFFER_SIZE)
temps       = deque(maxlen=BUFFER_SIZE)
pwms        = deque(maxlen=BUFFER_SIZE)

# --- OPEN SERIAL ---
ser = serial.Serial(PORT, BAUD, timeout=1)

# --- SET UP PLOT ---
fig, ax = plt.subplots()
line_set, = ax.plot([], [], label='Setpoint (°C)')
line_temp, = ax.plot([], [], label='Current Temp (°C)')
line_pwm, = ax.plot([], [], label='PWM Output')
ax.legend(loc='upper left')
ax.set_xlabel('Time (ms)')
ax.set_ylabel('Value')
ax.set_title('Live Temperature Control Data')
ax.grid(True)

def init():
    ax.set_xlim(0, BUFFER_SIZE)
    ax.set_ylim(0, 255)  # adjust as needed
    return line_set, line_temp, line_pwm

def update(frame):
    # Read a line from serial
    raw = ser.readline().decode('utf-8').strip()
    if not raw:
        return line_set, line_temp, line_pwm

    try:
        t, sp, ct, pwm = raw.split(',')
        t   = float(t)
        sp  = float(sp)
        ct  = float(ct)
        pwm = float(pwm)
    except ValueError:
        # line not in expected format
        return line_set, line_temp, line_pwm

    # Append to buffers
    times.append(t)
    setpoints.append(sp)
    temps.append(ct)
    pwms.append(pwm)

    # Update plot data (use relative time or index)
    x = list(range(len(times)))
    line_set.set_data(x, setpoints)
    line_temp.set_data(x, temps)
    line_pwm.set_data(x, pwms)

    # Optionally adjust axes
    ax.set_xlim(0, max(BUFFER_SIZE, len(times)))
    ymin = min(min(setpoints, default=0), min(temps, default=0), min(pwms, default=0)) - 5
    ymax = max(max(setpoints, default=0), max(temps, default=0), max(pwms, default=0)) + 5
    ax.set_ylim(ymin, ymax)

    return line_set, line_temp, line_pwm

# --- RUN ANIMATION ---
ani = animation.FuncAnimation(fig, update, init_func=init, blit=True, interval=100)
plt.show()

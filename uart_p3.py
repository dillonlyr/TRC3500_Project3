import serial
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

#* ==================== CONFIGURATIONS ====================
PORT = '/dev/tty.usbmodem11103'
BAUDRATE = 115200

TOTAL_SAMPLES = 6000
SAMPLING_RATE = 100  # Hz
MOVING_AVG_WINDOW = 20
MIN_DISTANCE_SAMPLES = 40   # Minimum distance between peaks (~0.4 sec at 100Hz)
MIN_PROMINENCE = 100        # Minimum voltage difference to consider a peak (mV)
#* ==================== =============== ====================

# === SERIAL CONNECTION ===
ser = serial.Serial(PORT, BAUDRATE)
print(f"Connected to {PORT}")

# === PLOTTING SETUP ===
plt.ion()
fig, axs = plt.subplots(4, 1, figsize=(12, 8.5))

line_raw1, = axs[0].plot([], [], linewidth=2, label='Pressure V Raw')
line_raw2, = axs[1].plot([], [], linewidth=2, label='ADC2 Raw')
line_smooth1, = axs[2].plot([], [], linewidth=2, label='Pressure V (MAF)')
line_smooth2, = axs[3].plot([], [], linewidth=2, label='ADC2 Smoothed')
peak_dots1, = axs[2].plot([], [], 'ro', label='Peaks (Pressure)')    # Pressure peaks
peak_dots2, = axs[3].plot([], [], 'bs', label='Peaks (Rubber)')      # Rubber peaks

titles = [
    "Pressure Voltage (raw) vs Time",
    "ADC2 Raw Voltage vs Time",
    "Pressure Voltage (MAF) vs Time",
    "ADC2 Smoothed Voltage (Moving Average)"
]

for i, ax in enumerate(axs):
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Voltage (mV)', fontsize=12)
    ax.set_title(titles[i], fontsize=14)
    ax.set_ylim(0, 3300)
    ax.grid(True)

axs[2].legend()
axs[3].legend()
fig.tight_layout(pad=0.8)

def moving_average(signal, window_size):
    return np.convolve(signal, np.ones(window_size)/window_size, mode='valid')

def estimate_bpm(peaks, time_axis, label=""):
    peak_times = time_axis[peaks]
    print(f"{label} Detected peaks: {len(peaks)}")
    if len(peaks) >= 2:
        periods = np.diff(peak_times)
        bpm_values = 60 / periods
        avg_bpm = np.mean(bpm_values)
        print(f"{label} Estimated Breathing Rate: {avg_bpm:.2f} BPM\n")
    else:
        print(f"{label} Not enough peaks to estimate BPM.\n")

def acquire_and_plot_voltages():
    print("Waiting for signal...")

    # === Wait for "START" string ===
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line == "START":
            break

    print("Receiving data...")

    # === Read binary data ===
    total_bytes = TOTAL_SAMPLES * 2
    data = ser.read(total_bytes)
    adc_array = np.frombuffer(data, dtype=np.uint16)

    adc1 = adc_array[::2]  # Even indices: ADC1
    adc2 = adc_array[1::2] # Odd indices: ADC2

    # === Convert ADC to voltage (mV) ===
    v_adc1 = (adc1.astype(np.float32) * 3300) / 4095
    v_adc2 = (adc2.astype(np.float32) * 3300) / 4095
    v_adc2 = 2 * 1650 - v_adc2

    # === Time axes ===
    sample_count = TOTAL_SAMPLES // 2
    time_axis = np.linspace(0, sample_count / SAMPLING_RATE, sample_count)
    time_smooth = time_axis[:sample_count - MOVING_AVG_WINDOW + 1]

    # === Moving averages ===
    v_smooth1 = moving_average(v_adc1, MOVING_AVG_WINDOW)
    v_smooth2 = moving_average(v_adc2, MOVING_AVG_WINDOW)

    # === Detect Peaks for both signals ===
    peaks1, _ = find_peaks(v_smooth1, distance=MIN_DISTANCE_SAMPLES, prominence=MIN_PROMINENCE)
    peaks2, _ = find_peaks(v_smooth2, distance=MIN_DISTANCE_SAMPLES, prominence=MIN_PROMINENCE)

    # === Estimate BPMs ===
    estimate_bpm(peaks1, time_smooth, label="Pressure")
    estimate_bpm(peaks2, time_smooth, label="Rubber")

    # === Plotting ===
    line_raw1.set_data(time_axis, v_adc1)
    line_raw2.set_data(time_axis, v_adc2)
    line_smooth1.set_data(time_smooth, v_smooth1)
    line_smooth2.set_data(time_smooth, v_smooth2)
    peak_dots1.set_data(time_smooth[peaks1], v_smooth1[peaks1])
    peak_dots2.set_data(time_smooth[peaks2], v_smooth2[peaks2])

    for ax in axs:
        ax.set_xlim(0, time_axis[-1])

    # === Refresh plots ===
    fig.canvas.draw()
    fig.canvas.flush_events()

while True:
    acquire_and_plot_voltages()
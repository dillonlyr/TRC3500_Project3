import serial
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
import csv
import os

#* ==================== CONFIGURATIONS ====================
PORT = '/dev/tty.usbmodem11103'
BAUDRATE = 115200

TOTAL_SAMPLES = 6000
SAMPLING_RATE = 100  # Hz
SAVGOL_WINDOW = 101   # Must be odd and less than data length
SAVGOL_POLYORDER = 3
MIN_DISTANCE_SAMPLES = 40
MIN_PROMINENCE = 100
#* ==================== =============== ====================

# === SERIAL CONNECTION ===
ser = serial.Serial(PORT, BAUDRATE)
print(f"Connected to {PORT}")

# === PLOTTING SETUP ===
plt.ion()
fig, axs = plt.subplots(4, 1, figsize=(12, 8.5))

line_raw1, = axs[0].plot([], [], linewidth=2, label='Pressure V Raw')
line_raw2, = axs[1].plot([], [], linewidth=2, label='ADC2 Raw')
line_smooth1, = axs[2].plot([], [], linewidth=2, label='Pressure V (SG)')
line_smooth2, = axs[3].plot([], [], linewidth=2, label='ADC2 Smoothed')
peak_dots1, = axs[2].plot([], [], 'ro', label='Peaks (Pressure)')
peak_dots2, = axs[3].plot([], [], 'bs', label='Peaks (Rubber)')

titles = [
    "Pressure Voltage (raw) vs Time",
    "ADC2 Raw Voltage vs Time",
    "Pressure Voltage (Savitzky-Golay) vs Time",
    "ADC2 Smoothed Voltage (Savitzky-Golay)"
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

    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line == "START":
            break

    print("Receiving data...")
    print("--------------------------------------")

    total_bytes = TOTAL_SAMPLES * 2
    data = ser.read(total_bytes)
    adc_array = np.frombuffer(data, dtype=np.uint16)

    adc1 = adc_array[::2]
    adc2 = adc_array[1::2]

    v_adc1 = (adc1.astype(np.float32) * 3300) / 4095
    v_adc2 = (adc2.astype(np.float32) * 3300) / 4095
    v_adc2 = 2 * 1650 - v_adc2

    sample_count = TOTAL_SAMPLES // 2
    time_axis = np.linspace(0, sample_count / SAMPLING_RATE, sample_count)

    # === Savitzky-Golay Filtering ===
    if len(v_adc1) >= SAVGOL_WINDOW:
        v_smooth1 = savgol_filter(v_adc1, window_length=SAVGOL_WINDOW, polyorder=SAVGOL_POLYORDER)
        v_smooth2 = savgol_filter(v_adc2, window_length=SAVGOL_WINDOW, polyorder=SAVGOL_POLYORDER)
    else:
        print("ERROR: Signal too short for Savitzky-Golay filter")
        return
    
    # === Save to CSV ===
    csv_filename = "butterworth_2.csv"
    csv_path = os.path.join(os.getcwd(), csv_filename)

    with open(csv_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Raw_V1 (Pressure)', 'Raw_V2 (Rubber)', 'Filtered_V1', 'Filtered_V2'])
        for r1, r2, f1, f2 in zip(v_adc1, v_adc2, v_smooth1, v_smooth2):
            writer.writerow([f"{r1:.3f}", f"{r2:.3f}", f"{f1:.3f}", f"{f2:.3f}"])

    print(f"Saved data to {csv_filename}")

    # === Detect Peaks for both signals ===
    peaks1, _ = find_peaks(v_smooth1, distance=MIN_DISTANCE_SAMPLES, prominence=MIN_PROMINENCE)
    peaks2, _ = find_peaks(v_smooth2, distance=MIN_DISTANCE_SAMPLES, prominence=MIN_PROMINENCE)

    # === Estimate BPMs ===
    estimate_bpm(peaks1, time_axis, label="Pressure")
    estimate_bpm(peaks2, time_axis, label="Rubber")

    if len(peaks1) > 0:
        avg_peak_v1 = np.mean(v_smooth1[peaks1])
        print(f"Averaged Peak Voltage (Pressure): {avg_peak_v1:.2f} mV")
    if len(peaks2) > 0:
        avg_peak_v2 = np.mean(v_smooth2[peaks2])
        print(f"Averaged Peak Voltage (Rubber): {avg_peak_v2:.2f} mV")
    print("--------------------------------------\n")

    # === Plotting ===
    line_raw1.set_data(time_axis, v_adc1)
    line_raw2.set_data(time_axis, v_adc2)
    line_smooth1.set_data(time_axis, v_smooth1)
    line_smooth2.set_data(time_axis, v_smooth2)
    peak_dots1.set_data(time_axis[peaks1], v_smooth1[peaks1])
    peak_dots2.set_data(time_axis[peaks2], v_smooth2[peaks2])

    for ax in axs:
        ax.set_xlim(0, time_axis[-1])

    fig.canvas.draw()
    fig.canvas.flush_events()

while True:
    acquire_and_plot_voltages()

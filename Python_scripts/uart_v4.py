#!/usr/bin/env python3
# =============================================================================
# capture_four_bursts_named.py
# Acquire exactly four piezo bursts via UART
# Show a single 4 × 2 window:
#   Row 0  – Time  Burst-1 | Time  Burst-2
#   Row 1  – FFT   Burst-1 | FFT   Burst-2
#   Row 2  – Time  Burst-3 | Time  Burst-4
#   Row 3  – FFT   Burst-3 | FFT   Burst-4
# Legends appear bottom-left; FFT grid ON, time-grid OFF.
# =============================================================================

import serial, time
import numpy as np
import matplotlib.pyplot as plt

import matplotlib.pyplot as plt

# ---- GLOBAL FONT SETUP  ----------------------------------------------------
plt.rcParams.update({
    "font.family": "monospace",   # any installed font
    "font.size":   8,               # base size
    "axes.titlesize":   8,
    "axes.labelsize":    7,
    "xtick.labelsize":   7,
    "ytick.labelsize":   7,
    "legend.fontsize":   7,
})


#* ────────── USER SETTINGS ───────────────────────────────────────────────────
PORT, BAUDRATE   = "/dev/tty.usbmodem11103", 115200
TOTAL_SAMPLES    = 20_000        # 2 s @ 10 kS/s
SAMPLING_RATE    = 10_000        # Hz
CENTER_VOLTAGE   = 1650          # mV (signal bias)
VOLTAGE_RANGE    = 1650          # ± display span
NOISE_DEADBAND   = 100           # mV: flatten tiny ripples
N_CAPTURES       = 4
FIGSIZE          = (10, 6)       # inches (width, height)

# Give each burst a custom name (must match N_CAPTURES)
capture_labels = [
    "Coin (10,10)",   # capture 1
    "Coin (10,30)",   # capture 2
    "Eraser (10,10)", # capture 3
    "Eraser (10,30)"  # capture 4
]
assert len(capture_labels) == N_CAPTURES, "capture_labels length mismatch"
#* ────────────────────────────────────────────────────────────────────────────


def filter_voltage(v, thresh=NOISE_DEADBAND):
    """Dead-band filter: flatten everything within ±thresh of the mean."""
    mean = v.mean()
    v[np.abs(v - mean) <= thresh] = mean
    return v


def acquire_one_burst(ser):
    """Read one burst and return processed metrics."""
    # Wait for ASCII token “START”
    while ser.readline().decode("utf-8", "ignore").strip() != "START":
        pass

    # Pull EXACTLY TOTAL_SAMPLES*2 bytes (16-bit little-endian)
    need, buf = TOTAL_SAMPLES * 2, bytearray()
    while len(buf) < need:
        chunk = ser.read(need - len(buf))
        if not chunk:
            raise RuntimeError("UART timeout – burst truncated")
        buf.extend(chunk)
    adc = np.frombuffer(buf, dtype=np.uint16)

    # Voltage conversion & basic de-noising
    v_filt = filter_voltage(adc.astype(np.float32) * 3300 / 4095)
    x      = (v_filt - v_filt.mean()) * np.hanning(len(v_filt))

    # FFT, magnitude, dB normalised to 0-dB peak
    one         = np.fft.fft(x)[:len(x)//2]
    mag_lin     = np.abs(one) / len(x)
    f_axis      = np.fft.fftfreq(len(x), 1 / SAMPLING_RATE)[:len(one)]
    mag_dB      = 20 * np.log10(mag_lin + 1e-12)
    mag_dB     -= mag_dB.max()

    # Metrics
    total_E     = (np.abs(one) ** 2).sum()
    res_idx     = np.argmax(mag_lin)
    res_freq    = f_axis[res_idx]
    pp          = v_filt.max() - v_filt.min()
    peak_val    = v_filt[np.argmax(np.abs(v_filt))]
    peak_time   = np.argmax(np.abs(v_filt)) / SAMPLING_RATE

    return v_filt, f_axis, mag_dB, total_E, res_freq, pp, peak_val, peak_time


# ────────── SERIAL SET-UP & ACQUIRE FOUR BURSTS ─────────────────────────────
print(f"Opening {PORT} @ {BAUDRATE} …")
ser = serial.Serial(PORT, BAUDRATE, timeout=2)
time.sleep(0.5)

try:
    records = [acquire_one_burst(ser) for _ in range(N_CAPTURES)]
finally:
    ser.close()
    print("Serial port closed.")

# ────────── PLOTTING ────────────────────────────────────────────────────────
fig, axes = plt.subplots(4, 2, figsize=FIGSIZE, constrained_layout=True)
time_axis = np.arange(TOTAL_SAMPLES) / SAMPLING_RATE

for idx, rec in enumerate(records):
    v, f, mag_dB, tot_E, fres, pp, peak_v, peak_t = rec
    row_top, col = (idx // 2) * 2, idx % 2
    label        = capture_labels[idx]

    # Time-domain subplot
    ax_t = axes[row_top, col]
    ax_t.plot(time_axis, v, lw=.8, color='k')
    ax_t.scatter(peak_t, peak_v, marker='x', color='green', zorder=3,
                 label=f"Peak = {peak_v:.0f} mV\nP-P = {pp:.0f} mV")
    ax_t.set_ylim(CENTER_VOLTAGE - VOLTAGE_RANGE,
                  CENTER_VOLTAGE + VOLTAGE_RANGE)
    if row_top == 2:
        ax_t.set_xlabel("Time (s)")
    ax_t.set_ylabel("Voltage (mV)")
    ax_t.set_title(f"{label} – Time", fontweight="bold")
    ax_t.grid(False)
    ax_t.legend(fontsize=7, loc='lower left')

    # FFT subplot
    ax_f = axes[row_top + 1, col]
    ax_f.semilogx(f, mag_dB, lw=.8, color='b')
    ax_f.scatter(fres, 0, marker='x', color='red', zorder=3,
                 label=f"f₀ = {fres:.0f} Hz\nΣ|FFT|² = {tot_E:.1e}")
    ax_f.set_xlim(1, SAMPLING_RATE / 2)
    ax_f.set_ylim(mag_dB.min() - 5, 5)
    if row_top == 2:
        ax_f.set_xlabel("Frequency (Hz)")
    ax_f.set_ylabel("Mag (dB)")
    ax_f.set_title(f"{label} – FFT", fontweight="bold")
    ax_f.grid(True, which="both", ls=":")
    ax_f.legend(fontsize=7, loc='lower left')

plt.show()

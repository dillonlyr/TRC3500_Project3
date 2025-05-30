# 🫁 Breathing Rate Detection via Dual-Channel ADC (STM32 + Python 3.11.2)
Completed by: *Loo Yi Ren Dillon*

This project implements a real-time breathing rate monitoring system using an STM32 microcontroller and Python-based signal processing. Two analog signals (e.g., from a pressure sensor and a conductive rubber sensor) are sampled using dual ADC channels. The data is transmitted to a host computer over UART and analyzed to extract breathing patterns and estimate breaths per minute (BPM).

## 📁 Project Structure
```
/
├── .gitignore                 # Git ignore rules
├── ReadMe.md                  # Project documentation (you are here)
├── requirements_macOS.txt     # Python dependencies for macOS
├── requirements_winOS.txt     # Python dependencies for Windows
├── stm_final.zip              # STM32 project archive (HAL firmware with ADC & UART)
└──/ Python Scripts
   ├── plotting.ipynb     # Plotting Jupyter notebook for report
   ├── uart_p3.py         # Deployed DSP/signal filtering Python script
   ├── uart_p3_v2.py      # Further testings/enhancements
   ├── uart_p3_v3.py      # Further testings/enhancements
   ├── uart_pv4.py        # Further testings/enhancements
   ├──/ data            # Report demonstration datas
      ├── exercise_sample1.csv
      ├── exercise_sample2.csv
      ├── normal_sample1.csv
      ├── normal_sample2.csv         
   ├── output          # Report output graphs 
   ├── output_params   # Function parameter Gridtest results
```

## ⚙️ System Overview

### 🎯 Objective

- Monitor and analyze breathing rate using analog sensor signals.
- Capture and transmit data using STM32 with DMA-enabled ADC.
- Perform digital signal processing and real-time plotting in Python.

### 🧠 Core Components

- **STM32 Microcontroller**:
  - Samples analog input via dual ADC channels
  - Transmits data via UART (USART2 channel)
- **Python Script**:
  - Receives data
  - Converts ADC values to voltages (mV)
  - Smooths signals using moving average
  - Detects peaks
  - Estimates and displays breathing rate
  - Plots signals in real-time using `matplotlib`

---

## 🔌 STM32 Firmware Details

- **ADC**: Dual-channel DMA sampling (ADC1_IN5 and ADC2_IN6)
- **Sampling Rate**: 100 Hz total (per channel)
- **UART Transmission**:
  - Sends 6000 bytes (3000 samples/channel × 2 bytes/sample)
  - Transmission triggered after printing `"START\r\n"`

Key transmission code:

```c
printf("START\r\n");
HAL_UART_Transmit(&huart2, (uint8_t*)adc_dma_buf, ADC_BUFFER_SIZE * sizeof(uint16_t), HAL_MAX_DELAY);

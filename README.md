# CosBit AR v8.1

**CosBit AR (Amateur Radio)** is a robust digital mode software designed for acoustic data transmission over radio (HF/VHF/UHF). It uses AFSK modulation combined with strong Forward Error Correction (FEC) to ensure message integrity even in noisy environments.

![CosBit Interface](https://github.com/cosyfluf/Image-downhill/blob/e7fb21ef463b50f21667c529344103db3e15d85e/image.png?raw=true)

## Features

*   **Robust Protocol:** Uses **Reed-Solomon** Error Correction and **Matrix Interleaving** to survive burst noise and static.
*   **Ham Radio Friendly:**
    *   Click-to-Call functionality.
    *   Automated Macros (CQ, Reply, 73).
    *   Dark Mode GUI.
    *   Smart Shift-Key correction (automatically converts `Shift+1` to `1`).
*   **AFSK Modulation:** 
    *   Space: 1200 Hz
    *   Mark: 2000 Hz
    *   Baud Rate: 600
*   **Cross-Platform:** Written in Python (Works on Windows, Linux, macOS).

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/cosyfluf/CosBit-AR.git
    cd CosBit-AR
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the main application:
```bash
python main.py
Audio Setup: Go to "AUDIO SETUP" to select your input/output devices (Microphone/Speakers or Virtual Audio Cable for Radio).
Station Setup: Enter your Callsign in the "MY CALL" field.
Transmit: Type a message and click "TRANSMIT".
Receive: Signals are decoded automatically when "Live Audio Mode" is active, or by loading a WAV file.
Technical Details
Packet Size: Fixed 64 Bytes (48 Bytes Data + 16 Bytes ECC).
Sync: 16-Bit Sync Pattern.
Modulation: Continuous Phase AFSK.
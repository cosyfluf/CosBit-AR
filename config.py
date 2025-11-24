# config.py
# --- CosBit AR v8.1 Configuration ---

# Audio Settings
SAMPLE_RATE = 48000
BAUD_RATE = 600

# Frequencies (Optimized for SSB/FM voice bandwidth 300-2500Hz)
FREQ_SPACE = 1200.0  # Bit 0
FREQ_MARK  = 2000.0  # Bit 1
FREQ_THRESHOLD = 1600.0 # Decision threshold

# Protocol (Fixed Packet Size required for Matrix Interleaving)
TOTAL_PACKET_BYTES = 64 
ECC_BYTES = 16 # Strong Forward Error Correction (Reed-Solomon)
DATA_BYTES = TOTAL_PACKET_BYTES - ECC_BYTES # Available space for text

# Sync Marker (Bit pattern to wake up the receiver)
SYNC_PATTERN = "1010101000110011" 

# Colors (Dark Mode / Ham Radio Style)
COLORS = {
    "bg": "#121212",       # Deep dark grey background
    "panel": "#1e1e1e",    # Lighter panels
    "text_rx": "#ffb000",  # Amber for RX
    "text_tx": "#00ff00",  # Green for TX
    "alert": "#ff0000"     # Red for Alerts
}
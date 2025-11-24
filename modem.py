import numpy as np
import scipy.signal as signal
from reedsolo import RSCodec, ReedSolomonError
import config as cfg

class CosBitModem:
    def __init__(self):
        # Initialize Reed-Solomon Codec
        self.rsc = RSCodec(cfg.ECC_BYTES)

    def text_to_bits_robust(self, text):
        """Converts text to protected, interleaved bits."""
        # 1. Padding (Force fixed length)
        data_bytes = text.encode('utf-8')
        if len(data_bytes) > cfg.DATA_BYTES:
            data_bytes = data_bytes[:cfg.DATA_BYTES]
        else:
            padding = cfg.DATA_BYTES - len(data_bytes)
            data_bytes += b'\x00' * padding
        
        # 2. RS Encoding (Add Error Correction Codes)
        encoded_bytes = self.rsc.encode(data_bytes)
        
        # 3. Convert Bytes to Bits string
        bits = "".join(format(byte, '08b') for byte in encoded_bytes)
        
        # 4. Matrix Interleaving
        return self._interleave_bits(bits)

    def bits_to_text_robust(self, bits):
        """Decodes bits, de-interleaves, and repairs errors."""
        # 1. De-Interleaving
        deinterleaved = self._deinterleave_bits(bits)
        
        # 2. Bits to Bytes
        byte_array = bytearray()
        for i in range(0, len(deinterleaved), 8):
            chunk = deinterleaved[i:i+8]
            if len(chunk) < 8: break
            byte_array.append(int(chunk, 2))
            
        # 3. RS Decoding & Repair
        try:
            decoded_with_padding = self.rsc.decode(byte_array)[0]
            clean_bytes = decoded_with_padding.rstrip(b'\x00')
            return clean_bytes.decode('utf-8', errors='ignore'), True
        except (ReedSolomonError, ValueError):
            return "", False

    def modulate(self, text, amplitude=0.5):
        """Generates the AFSK audio signal."""
        preamble = "1010" * 20 
        payload_bits = self.text_to_bits_robust(text)
        full_bitstream = preamble + cfg.SYNC_PATTERN + payload_bits + "0" * 20 
        
        samples_per_bit = int(cfg.SAMPLE_RATE / cfg.BAUD_RATE)
        
        # Expand bits to audio samples
        bit_array = np.array([int(b) for b in full_bitstream])
        repeated_bits = np.repeat(bit_array, samples_per_bit)
        
        # Map frequencies
        freqs = np.where(repeated_bits == 1, cfg.FREQ_MARK, cfg.FREQ_SPACE)
        
        # Integrate phase (Continuous Phase Audio)
        phase = 2 * np.pi * np.cumsum(freqs) / cfg.SAMPLE_RATE
        audio = np.sin(phase) * amplitude 
        
        # Start-Chirp (Acoustic marker)
        chirp_len = int(cfg.SAMPLE_RATE * 0.1)
        t_chirp = np.linspace(0, 0.1, chirp_len)
        chirp = signal.chirp(t_chirp, 800, 0.1, 1500) * (amplitude * 0.8)
        
        return np.concatenate((chirp, np.zeros(1000), audio, np.zeros(2000)))

    def demodulate(self, audio_data, threshold_override=None):
        """Searches for signals and decodes them."""
        if len(audio_data) == 0: return None
        
        # 1. Hilbert Transform (Instantaneous Frequency)
        analytic_signal = signal.hilbert(audio_data)
        inst_phase = np.unwrap(np.angle(analytic_signal))
        inst_freq = (np.diff(inst_phase) / (2.0 * np.pi) * cfg.SAMPLE_RATE)
        
        # Filtering
        sos = signal.butter(4, cfg.BAUD_RATE*1.5, 'low', fs=cfg.SAMPLE_RATE, output='sos')
        freq_clean = signal.sosfilt(sos, inst_freq)
        
        # Digitization
        thresh = threshold_override if threshold_override is not None else cfg.FREQ_THRESHOLD
        digital_stream = np.where(freq_clean > thresh, 1, 0)
        
        # 2. Sampling (Read Bits)
        samples_per_bit = int(cfg.SAMPLE_RATE / cfg.BAUD_RATE)
        bits_list = []
        for i in range(samples_per_bit // 2, len(digital_stream), samples_per_bit):
            bits_list.append(str(int(digital_stream[i])))
        bits_str = "".join(bits_list)
            
        # 3. Sync Search
        idx = bits_str.find(cfg.SYNC_PATTERN)
        if idx != -1:
            payload_start = idx + len(cfg.SYNC_PATTERN)
            expected_bits = cfg.TOTAL_PACKET_BYTES * 8
            
            if payload_start + expected_bits <= len(bits_str):
                raw_payload_bits = bits_str[payload_start : payload_start + expected_bits]
                text, success = self.bits_to_text_robust(raw_payload_bits)
                
                return {
                    "text": text,
                    "success": success,
                    "freq_viz": freq_clean[idx*samples_per_bit : (idx+300)*samples_per_bit]
                }
        return None

    def _interleave_bits(self, bits):
        cols = 8 
        rows = len(bits) // cols
        interleaved = ""
        for c in range(cols):
            for r in range(rows):
                interleaved += bits[r * cols + c]
        return interleaved

    def _deinterleave_bits(self, bits):
        cols = 8
        rows = len(bits) // cols
        original = [""] * len(bits)
        idx = 0
        for c in range(cols):
            for r in range(rows):
                if idx < len(bits):
                    original[r * cols + c] = bits[idx]
                    idx += 1
        return "".join(original)
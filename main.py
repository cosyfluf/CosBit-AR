import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import scipy.io.wavfile as wav
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
import re
import json 
import os
import sys
import config as cfg
from modem import CosBitModem

# Audio Lib Check
HAS_AUDIO = False
try:
    import sounddevice as sd
    HAS_AUDIO = True
except ImportError:
    pass

# Smart Shift Mapping (Auto-correct numbers when Shift is held)
SHIFT_MAP = {
    '!': '1', '"': '2', '§': '3', '$': '4', '%': '5',
    '&': '6', '/': '7', '(': '8', ')': '9', '=': '0',
    '@': '2', '#': '3', '^': '6', '*': '8', '+': '1'
}

SETTINGS_FILE = "user_settings.json"

class CosBitApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"CosBit AR v8.1 - Ham Radio Digital Terminal")
        self.root.geometry("1200x850")
        self.root.configure(bg=cfg.COLORS["bg"])
        
        # Save on exit
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.modem = CosBitModem()
        
        # --- Variables ---
        self.var_my_call = tk.StringVar(value="N0CALL")
        self.var_dx_call = tk.StringVar(value="")
        self.var_rst = tk.StringVar(value="599")
        
        self.var_use_live = tk.BooleanVar(value=False)
        self.var_input_dev = tk.StringVar()  
        self.var_output_dev = tk.StringVar() 
        self.var_tx_vol = tk.DoubleVar(value=0.5) 
        self.var_rx_thresh = tk.DoubleVar(value=cfg.FREQ_THRESHOLD) 
        
        # --- Load Settings ---
        self.load_settings()
        
        self.setup_ui()
        
        if not HAS_AUDIO:
            self.log("SYS: 'sounddevice' library not found. File mode only.", "SYS")

    def load_settings(self):
        """Loads callsign and audio settings from JSON."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self.var_my_call.set(data.get("my_call", "N0CALL"))
                    self.var_use_live.set(data.get("live_mode", False))
                    self.var_input_dev.set(data.get("input_dev", ""))
                    self.var_output_dev.set(data.get("output_dev", ""))
                    self.var_tx_vol.set(data.get("tx_vol", 0.5))
            except Exception as e:
                print(f"Error loading settings: {e}")

    def on_close(self):
        """Saves settings on exit."""
        data = {
            "my_call": self.var_my_call.get(),
            "live_mode": self.var_use_live.get(),
            "input_dev": self.var_input_dev.get(),
            "output_dev": self.var_output_dev.get(),
            "tx_vol": self.var_tx_vol.get()
        }
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Could not save settings: {e}")
            
        self.root.destroy()
        sys.exit()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        col_bg = cfg.COLORS["bg"]
        col_panel = cfg.COLORS["panel"]
        col_btn = "#333333"
        
        style.configure("TFrame", background=col_bg)
        style.configure("Card.TFrame", background=col_panel, relief="flat", borderwidth=1)
        style.configure("TLabel", background=col_panel, foreground="#aaaaaa", font=("Verdana", 9))
        style.configure("Header.TLabel", background=col_bg, foreground="#ffffff", font=("Impact", 18))
        style.configure("Ham.TButton", background=col_btn, foreground="white", font=("Consolas", 10, "bold"), padding=6)
        style.map("Ham.TButton", background=[("active", "#555555")])

        # --- HEADER ---
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=15, pady=15)
        
        ttk.Label(top, text="CosBit AR // DIGITAL TERMINAL", style="Header.TLabel").pack(side="left")
        ttk.Button(top, text="⚙ AUDIO SETUP", style="Ham.TButton", command=self.open_settings_window).pack(side="right")

        # --- SPLIT VIEW ---
        main_split = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_split.pack(fill="both", expand=True, padx=10, pady=5)
        
        # === LEFT: RX ===
        frame_rx = ttk.Frame(main_split)
        main_split.add(frame_rx, weight=3)
        
        rx_container = ttk.LabelFrame(frame_rx, text=" RECEIVE STREAM (RX) ", padding=5)
        rx_container.pack(fill="both", expand=True, padx=(0,5))
        
        self.log_text = tk.Text(rx_container, bg="black", fg=cfg.COLORS["text_rx"], font=("Consolas", 12), bd=0, selectbackground="#444")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_config("SYS", foreground="#555555", font=("Consolas", 10, "italic"))
        self.log_text.tag_config("RX", foreground=cfg.COLORS["text_rx"])
        self.log_text.tag_config("MY_CALL", foreground="#ffffff", background="#aa0000") 
        self.log_text.tag_config("CLICKABLE", foreground="#00ffff", underline=True)
        self.log_text.tag_bind("CLICKABLE", "<Button-1>", self.on_callsign_click)
        self.log_text.tag_bind("CLICKABLE", "<Enter>", lambda e: self.log_text.config(cursor="hand2"))
        self.log_text.tag_bind("CLICKABLE", "<Leave>", lambda e: self.log_text.config(cursor=""))
        
        self.lbl_status = tk.Label(rx_container, text="SYSTEM READY", bg="#222", fg="#666", font=("Arial", 10, "bold"), anchor="w", padx=10)
        self.lbl_status.pack(fill="x", pady=2)
        
        ttk.Button(rx_container, text="OPEN WAV FILE", style="Ham.TButton", command=self.rx_file).pack(fill="x", pady=5)

        # === RIGHT: TX ===
        frame_tx = ttk.Frame(main_split)
        main_split.add(frame_tx, weight=2)
        
        tx_info = ttk.LabelFrame(frame_tx, text=" STATION CONTROL ", padding=10)
        tx_info.pack(fill="x", padx=(5,0), pady=(0, 10))
        
        grid_frame = ttk.Frame(tx_info, style="Card.TFrame")
        grid_frame.pack(fill="x")
        
        ttk.Label(grid_frame, text="MY CALL:").grid(row=0, column=0, sticky="w", pady=5)
        entry_my = tk.Entry(grid_frame, textvariable=self.var_my_call, bg="#333", fg="#00ff00", font=("Consolas", 12, "bold"), width=10)
        entry_my.grid(row=0, column=1, padx=5)
        entry_my.bind('<KeyRelease>', self.auto_upper_correction)

        ttk.Label(grid_frame, text="DX CALL:").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_dx = tk.Entry(grid_frame, textvariable=self.var_dx_call, bg="#333", fg="yellow", font=("Consolas", 12, "bold"), width=10)
        self.entry_dx.grid(row=1, column=1, padx=5)
        self.entry_dx.bind('<KeyRelease>', self.auto_upper_correction)

        ttk.Label(grid_frame, text="RST:").grid(row=1, column=2, sticky="w", padx=(10,2))
        tk.Entry(grid_frame, textvariable=self.var_rst, bg="#333", fg="white", font=("Consolas", 12), width=4).grid(row=1, column=3)
        tk.Button(grid_frame, text="CLR", bg="#440000", fg="white", font=("Arial", 8), command=lambda: self.var_dx_call.set("")).grid(row=1, column=4, padx=2)

        tx_macros = ttk.LabelFrame(frame_tx, text=" MACROS ", padding=10)
        tx_macros.pack(fill="x", padx=(5,0), pady=10)
        
        tk.Button(tx_macros, text="CALL / CQ", bg="#005500", fg="white", font=("Verdana", 9, "bold"), command=self.macro_cq).pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(tx_macros, text="ANSWER", bg="#004444", fg="white", font=("Verdana", 9, "bold"), command=self.macro_reply).pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(tx_macros, text="73 / BYE", bg="#550000", fg="white", font=("Verdana", 9, "bold"), command=self.macro_bye).pack(side="left", fill="x", expand=True, padx=2)

        tx_input_frame = ttk.LabelFrame(frame_tx, text=" TRANSMIT BUFFER ", padding=10)
        tx_input_frame.pack(fill="x", padx=(5,0), pady=10)
        
        self.txt_input = tk.Text(tx_input_frame, height=4, bg="#111", fg="white", font=("Consolas", 12), insertbackground="white")
        self.txt_input.pack(fill="x")
        self.txt_input.bind('<KeyRelease>', self.input_handler)
        
        self.lbl_chars = ttk.Label(tx_input_frame, text=f"0 / {cfg.DATA_BYTES}")
        self.lbl_chars.pack(anchor="e")
        
        self.btn_tx = ttk.Button(tx_input_frame, text=">>> TRANSMIT <<<", style="Ham.TButton", command=self.tx_process)
        self.btn_tx.pack(fill="x", pady=5)

        tx_scope = ttk.LabelFrame(frame_tx, text=" SCOPE ", padding=5)
        tx_scope.pack(fill="both", expand=True, padx=(5,0))
        
        self.fig = plt.Figure(figsize=(4, 2), dpi=100, facecolor=col_panel)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('black')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.grid(True, color="#333", linestyle="--", alpha=0.5)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=tx_scope)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # --- Logic: Input Correction ---
    def auto_upper_correction(self, event):
        widget = event.widget
        text = widget.get()
        new_text = text.upper()
        for char, num in SHIFT_MAP.items():
            new_text = new_text.replace(char, num)
        if text != new_text:
            pos = widget.index(tk.INSERT)
            widget.delete(0, tk.END)
            widget.insert(0, new_text)
            widget.icursor(pos)

    def input_handler(self, event):
        content = self.txt_input.get("1.0", tk.END)
        raw_content = content[:-1] 
        new_content = raw_content.upper()
        for char, num in SHIFT_MAP.items():
            new_content = new_content.replace(char, num)
        if raw_content != new_content:
            self.txt_input.delete("1.0", tk.END)
            self.txt_input.insert("1.0", new_content)
        
        l = len(new_content)
        col = "white" if l <= cfg.DATA_BYTES else "#ff5555"
        self.lbl_chars.config(text=f"{l} / {cfg.DATA_BYTES}", foreground=col)

    # --- Logic: Macros ---
    def macro_cq(self):
        my = self.var_my_call.get()
        dx = self.var_dx_call.get()
        if dx:
            self.insert_tx(f"CQ {dx} DE {my} K")
        else:
            self.insert_tx(f"CQ CQ DE {my} {my} K")

    def macro_reply(self):
        my = self.var_my_call.get()
        dx = self.var_dx_call.get()
        rst = self.var_rst.get()
        if not dx:
            messagebox.showinfo("Info", "No DX CALL selected!")
            return
        self.insert_tx(f"{dx} DE {my} R {rst} TNX K")

    def macro_bye(self):
        my = self.var_my_call.get()
        dx = self.var_dx_call.get()
        target = dx if dx else "CQ"
        self.insert_tx(f"{target} DE {my} 73 SK")

    def insert_tx(self, text):
        self.txt_input.delete("1.0", tk.END)
        self.txt_input.insert("1.0", text.upper())
        self.input_handler(None)

    # --- Logic: Core ---
    def on_callsign_click(self, event):
        try:
            index = self.log_text.index(f"@{event.x},{event.y}")
            line_start = f"{index} linestart"
            line_end = f"{index} lineend"
            word_start = self.log_text.search(r"\s|^", index, backwards=True, stopindex=line_start, regexp=True) 
            if not word_start: word_start = line_start
            else: word_start = f"{word_start}+1c"
            word_end = self.log_text.search(r"\s|$", index, stopindex=line_end, regexp=True)
            if not word_end: word_end = line_end
            
            clicked_word = self.log_text.get(word_start, word_end).strip()
            clicked_word = re.sub(r'[^A-Z0-9/]', '', clicked_word.upper())
            
            if len(clicked_word) > 2:
                self.var_dx_call.set(clicked_word)
                self.entry_dx.config(bg="#444400")
                self.root.after(200, lambda: self.entry_dx.config(bg="#333"))
        except Exception: pass

    def log(self, msg, tag="SYS"):
        t = time.strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"{t} ", "SYS")
        
        if tag == "RX":
            words = msg.split(" ")
            for word in words:
                clean = re.sub(r'[^A-Z0-9/]', '', word.upper())
                if re.match(r'[A-Z0-9/]{3,}', clean) and any(c.isdigit() for c in clean):
                    self.log_text.insert(tk.END, word + " ", "CLICKABLE")
                else:
                    self.log_text.insert(tk.END, word + " ", "RX")
            self.log_text.insert(tk.END, "\n")
            
            my_call = self.var_my_call.get().strip().upper()
            if my_call and my_call in msg.upper():
                self.trigger_alert()
                self.log_text.insert(tk.END, f"    < !!! CALL FOR {my_call} !!! >\n", "MY_CALL")
        else:
            self.log_text.insert(tk.END, f"{msg}\n", tag)
        self.log_text.see(tk.END)

    def trigger_alert(self):
        def flash():
            for _ in range(6):
                bg = "#aa0000" if _ % 2 == 0 else "#222"
                fg = "white" if _ % 2 == 0 else "#666"
                self.lbl_status.config(text="!!! INCOMING CALL !!!", bg=bg, fg=fg)
                time.sleep(0.15)
            self.lbl_status.config(text="SYSTEM READY", bg="#222", fg="#666")
        threading.Thread(target=flash).start()

    def tx_process(self):
        text = self.txt_input.get("1.0", tk.END).strip()
        if not text: return
        if len(text) > cfg.DATA_BYTES:
            messagebox.showerror("Overflow", f"Message too long ({len(text)}). Max {cfg.DATA_BYTES}.")
            return
        vol = self.var_tx_vol.get()
        self.log(f"TX > {text}", "SYS")
        try:
            audio = self.modem.modulate(text, amplitude=vol)
            
            self.ax.clear()
            self.ax.set_facecolor('black')
            self.ax.grid(True, color="#333", linestyle="--")
            self.ax.set_xticks([]); self.ax.set_yticks([])
            self.ax.plot(audio[:4000], color=cfg.COLORS["text_tx"], lw=1)
            self.canvas.draw()
            
            if self.var_use_live.get() and HAS_AUDIO:
                dev_id = self.get_device_id(self.var_output_dev.get(), 'output')
                if dev_id == -1: return
                sd.play(audio.astype(np.float32), samplerate=cfg.SAMPLE_RATE, device=dev_id)
            else:
                wav.write("tx_output.wav", cfg.SAMPLE_RATE, (audio * 32767).astype(np.int16))
                self.log("Saved 'tx_output.wav'", "SYS")
        except Exception as e:
            messagebox.showerror("TX Error", str(e))

    def rx_file(self):
        if self.var_use_live.get() and HAS_AUDIO:
            self.listen_live()
        else:
            path = filedialog.askopenfilename(filetypes=[("WAV", "*.wav")])
            if not path: return
            try:
                sr, data = wav.read(path)
                if data.dtype == np.int16: data = data / 32768.0
                if data.ndim > 1: data = data[:, 0]
                self.process_audio(data)
            except Exception as e:
                self.log(f"Err: {e}", "SYS")

    def listen_live(self):
        dev_id = self.get_device_id(self.var_input_dev.get(), 'input')
        if dev_id == -1:
            self.log("RX Device Error", "SYS")
            return
        self.lbl_status.config(text="LISTENING (10s)...", fg="yellow")
        self.root.update()
        def runner():
            rec = sd.rec(int(10 * cfg.SAMPLE_RATE), samplerate=cfg.SAMPLE_RATE, channels=1, device=dev_id, dtype='float32')
            sd.wait()
            self.root.after(0, lambda: self.process_audio(rec.flatten()))
        threading.Thread(target=runner).start()

    def process_audio(self, data):
        self.lbl_status.config(text="DECODING...", fg="cyan")
        self.root.update()
        thresh = self.var_rx_thresh.get()
        result = self.modem.demodulate(data, threshold_override=thresh)
        if result and result['success']:
            self.log(result['text'], "RX")
            self.lbl_status.config(text="CRC VALID", fg="#00ff00")
            self.ax.clear()
            self.ax.set_facecolor('black')
            self.ax.grid(True, color="#333", linestyle="--")
            self.ax.plot(result['freq_viz'], color=cfg.COLORS["text_rx"], lw=1)
            self.ax.axhline(y=thresh, color="red", alpha=0.5)
            self.canvas.draw()
        else:
            self.log("Signal Error / Noise", "SYS")
            self.lbl_status.config(text="SYNC ERROR", fg="red")

    def get_device_id(self, name, kind='input'):
        if not name: return -1
        try:
            devs = sd.query_devices()
            for i, d in enumerate(devs):
                if d['name'] == name:
                    if kind == 'input' and d['max_input_channels'] > 0: return i
                    if kind == 'output' and d['max_output_channels'] > 0: return i
        except: pass
        return -1

    def open_settings_window(self):
        if not HAS_AUDIO:
            messagebox.showerror("Error", "Sounddevice lib missing.")
            return
        win = tk.Toplevel(self.root)
        win.title("Audio Setup")
        win.geometry("500x500")
        win.configure(bg="#222")
        
        def lbl(txt): return tk.Label(win, text=txt, bg="#222", fg="white", font=("Arial", 10))
        
        lbl("AUDIO CONFIGURATION").pack(pady=10)
        frm = tk.Frame(win, bg="#333", padx=10, pady=10)
        frm.pack(fill="x", padx=10)
        tk.Checkbutton(frm, text="Live Audio Mode", variable=self.var_use_live, bg="#333", fg="white", selectcolor="black").pack(anchor="w")
        
        devs = sd.query_devices()
        ins = list(set([d['name'] for d in devs if d['max_input_channels'] > 0]))
        outs = list(set([d['name'] for d in devs if d['max_output_channels'] > 0]))
        
        lbl("Input Device:").pack()
        cb_in = ttk.Combobox(win, values=ins, textvariable=self.var_input_dev)
        cb_in.pack(fill="x", padx=20)
        lbl("Output Device:").pack()
        cb_out = ttk.Combobox(win, values=outs, textvariable=self.var_output_dev)
        cb_out.pack(fill="x", padx=20)
        
        if not self.var_input_dev.get() and ins: cb_in.current(0)
        if not self.var_output_dev.get() and outs: cb_out.current(0)
        
        lbl("TX Volume:").pack(pady=(10,0))
        tk.Scale(win, from_=0, to=1, resolution=0.1, orient="horizontal", variable=self.var_tx_vol, bg="#222", fg="white").pack(fill="x", padx=20)
        
        tk.Button(win, text="SAVE & CLOSE", bg="#008", fg="white", command=win.destroy).pack(pady=30)

if __name__ == "__main__":
    root = tk.Tk()
    app = CosBitApp(root)
    root.mainloop()
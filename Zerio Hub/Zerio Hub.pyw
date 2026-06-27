# Should be pretty easy to read!

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS & AUTO-INSTALL
# ═══════════════════════════════════════════════════════════════════════════════
import sys, os, json, subprocess, threading, time, platform, tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

def ensure_deps():
    deps = {"customtkinter": "customtkinter", "psutil": "psutil", "PIL": "Pillow"}
    missing = []
    for mod, pkg in deps.items():
        try: __import__(mod)
        except ImportError: missing.append(pkg)
    if missing:
        print(f"Installing: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing, "-q"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

ensure_deps()

import customtkinter as ctk
import psutil
from PIL import Image

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
BG_COLOR     = "#0D0D0D"
PANEL_COLOR  = "#1B1B1B"
SIDE_COLOR   = "#161616"
BORDER_COLOR = "#2A2A2A"
ACCENT       = "#8B5CF6"
HOVER_ACC    = "#A855F7"
TXT          = "#FFFFFF"
SUBTXT       = "#AAAAAA"
FONT         = "Segoe UI"
VERSION      = "2.4.0"
SETTINGS_FP  = Path.home() / ".zerio_hub_settings.json"
PROJECTS_DIR = Path.home() / "Documents" / "ZerioProjects"

ACCENT_PRESETS = {
    "Purple": "#8B5CF6", "Blue": "#3B82F6", "Green": "#10B981",
    "Red": "#EF4444", "Orange": "#F59E0B", "Pink": "#EC4899", "Cyan": "#06B6D4"
}

ctk.set_appearance_mode("dark")

# ═══════════════════════════════════════════════════════════════════════════════
# PREMIUM FULLSCREEN SPLASH SCREEN
# ═══════════════════════════════════════════════════════════════════════════════
class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#000000")
        
        # Force Fullscreen
        try: self.state("zoomed")
        except: self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

        # Center Frame
        frame = tk.Frame(self, bg="#000000")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        # Main Title
        tk.Label(frame, text="ZERIO HUB", font=(FONT, 72, "bold"), 
                 fg=ACCENT, bg="#000000").pack(pady=(0, 30))

        # Taglines
        tk.Label(frame, text="Launch all python scripts", font=(FONT, 18), 
                 fg="#444444", bg="#000000").pack(pady=(0, 5))
        tk.Label(frame, text="Make it easy for yourself", font=(FONT, 18), 
                 fg="#444444", bg="#000000").pack(pady=(0, 50))

        # Sleek Loading Bar Background
        self.canvas = tk.Canvas(frame, width=300, height=4, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack()
        self.bar = self.canvas.create_rectangle(0, 0, 0, 4, fill=ACCENT, width=0)
        
        self._animate_bar(0)

    def _animate_bar(self, width):
        if width <= 300:
            self.canvas.coords(self.bar, 0, 0, width, 4)
            self.after(12, self._animate_bar, width + 3)
        else:
            self.after(400, self._fade_out)

    def _fade_out(self):
        current = float(self.attributes("-alpha"))
        if current > 0.0:
            self.attributes("-alpha", current - 0.03)
            self.after(10, self._fade_out)
        else:
            self.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════
class ZerioHub(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.TRANSPARENT_COLOR = "#010101"
        self.configure(fg_color=self.TRANSPARENT_COLOR)
        self.overrideredirect(True)
        self.attributes("-transparentcolor", self.TRANSPARENT_COLOR)
        
        w, h = 1280, 780
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(1000, 600)

        self.target_opacity = 0.95
        self.is_overlay = False
        self.attributes("-alpha", 0.0)

        # -- State --
        self.page            = "scripts"
        self.script_folder   = ""
        self.scripts         = []
        self.filtered        = []
        self.sel_script      = None
        self.favorites       = []
        self.recent_projects = []
        self.process         = None
        self.running         = False
        self._drag           = {"x": 0, "y": 0}
        self.accent          = ACCENT
        self.font_size       = 13
        self.auto_refresh    = True
        self.auto_save       = False
        self.fav_filter      = False
        self._original_content = ""

        self._load_settings()
        
        self._build_mini_button()
        self.splash = SplashScreen(self)
        self._build_main_container()

        self._tick_time()
        self._tick_stats()
        self._tick_refresh()
        self._tick_process()

        self.after(3800, self._fade_in)

    # ──────────────────────────────────────────────────────────────────────────
    # SLEEK TRANSPARENT MINI OPEN BUTTON
    # ──────────────────────────────────────────────────────────────────────────
    def _build_mini_button(self):
        self.mini_btn = tk.Toplevel(self)
        self.mini_btn.overrideredirect(True)
        self.mini_btn.attributes("-topmost", True)
        self.mini_btn.configure(bg="#000000")
        self.mini_btn.attributes("-alpha", 0.85) # Semi-transparent glass effect

        btn_w, btn_h = 160, 34
        r = 12 # Corner radius
        sw = self.winfo_screenwidth()
        x = (sw - btn_w) // 2
        self.mini_btn.geometry(f"{btn_w}x{btn_h}+{x}+12")

        canvas = tk.Canvas(self.mini_btn, width=btn_w, height=btn_h, bg="#000000", highlightthickness=0)
        canvas.pack()

        # Helper to draw the button shape cleanly
        def draw_btn(fill_color, border_color, text_color):
            canvas.delete("all")
            # Draw 4 corners and 2 rectangles to make a perfect rounded rect
            canvas.create_arc(0, 0, 2*r, 2*r, start=90, extent=90, fill=fill_color, outline=border_color, width=1)
            canvas.create_arc(btn_w-2*r, 0, btn_w, 2*r, start=0, extent=90, fill=fill_color, outline=border_color, width=1)
            canvas.create_arc(0, btn_h-2*r, 2*r, btn_h, start=180, extent=90, fill=fill_color, outline=border_color, width=1)
            canvas.create_arc(btn_w-2*r, btn_h-2*r, btn_w, btn_h, start=270, extent=90, fill=fill_color, outline=border_color, width=1)
            canvas.create_rectangle(r, 0, btn_w-r, btn_h, fill=fill_color, outline="")
            canvas.create_rectangle(0, r, btn_w, btn_h-r, fill=fill_color, outline="")
            canvas.create_text(btn_w//2, btn_h//2, text="Open Zerio Hub", font=(FONT, 9, "bold"), fill=text_color)

        # Initial Draw
        draw_btn("#1a1a1a", "#333333", SUBTXT)

        # Hover Effects
        def on_enter(e): draw_btn(ACCENT, ACCENT, TXT)
        def on_leave(e): draw_btn("#1a1a1a", "#333333", SUBTXT)

        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
        canvas.bind("<Button-1>", lambda e: self._restore_from_minimize())
        canvas.configure(cursor="hand2")

        self.mini_btn.withdraw()

    def _minimize(self):
        self.withdraw()
        self.mini_btn.deiconify()

    def _restore_from_minimize(self):
        self.mini_btn.withdraw()
        self.deiconify()

    # ──────────────────────────────────────────────────────────────────────────
    # ANIMATIONS
    # ──────────────────────────────────────────────────────────────────────────
    def _fade_in(self):
        current = float(self.attributes("-alpha"))
        if current < self.target_opacity:
            self.attributes("-alpha", min(current + 0.05, self.target_opacity))
            self.after(20, self._fade_in)

    def _start_drag(self, e): self._drag = {"x": e.x, "y": e.y}
    def _on_drag(self, e): self.geometry(f"+{e.x_root - self._drag['x']}+{e.y_root - self._drag['y']}")
    
    def _quit(self):
        self._save_settings()
        if self.process:
            try: self.process.kill()
            except: pass
        try: self.mini_btn.destroy()
        except: pass
        self.destroy()

    def _toggle_overlay(self):
        self.is_overlay = not self.is_overlay
        if self.is_overlay:
            self.attributes("-topmost", True)
            self.overlay_btn.configure(text="Overlay On", text_color="#D8B4FE")
            self.opacity_frame.pack(fill="x", padx=(10, 60), pady=(0, 4))
        else:
            self.attributes("-topmost", False)
            self.overlay_btn.configure(text="Overlay Off", text_color=SUBTXT)
            self.opacity_frame.pack_forget()

    def _set_opacity(self, val):
        self.target_opacity = float(val)
        self.attributes("-alpha", self.target_opacity)

    # ──────────────────────────────────────────────────────────────────────────
    # MAIN FLOATING CONTAINER
    # ──────────────────────────────────────────────────────────────────────────
    def _build_main_container(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=BG_COLOR, corner_radius=24)
        self.main_frame.pack(fill="both", expand=True, padx=6, pady=6)

        self.main_frame.bind("<Button-1>", self._start_drag)
        self.main_frame.bind("<B1-Motion>", self._on_drag)

        self.main_frame.grid_rowconfigure(3, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

        self._build_titlebar()
        self._build_topnav()
        self._build_sidebar()
        self._build_content_area()
        self._build_statusbar()

    # ──────────────────────────────────────────────────────────────────────────
    # TITLE BAR
    # ──────────────────────────────────────────────────────────────────────────
    def _build_titlebar(self):
        bar = ctk.CTkFrame(self.main_frame, height=36, fg_color=PANEL_COLOR, corner_radius=14)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(6, 3))
        bar.grid_propagate(False)
        for w in [bar]: 
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

        lbl = ctk.CTkLabel(bar, text="ZERIO HUB", font=(FONT, 11, "bold"), text_color=self.accent)
        lbl.pack(side="left", padx=14)
        for w in [lbl]: 
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

        ctrl = ctk.CTkFrame(bar, fg_color="transparent")
        ctrl.pack(side="right", padx=4)
        
        self.overlay_btn = ctk.CTkButton(ctrl, text="Overlay Off", width=80, height=24, font=(FONT, 9),
                                         fg_color="transparent", text_color=SUBTXT, hover_color="#2a2a2a",
                                         corner_radius=6, command=self._toggle_overlay)
        self.overlay_btn.pack(side="left", padx=2, pady=6)

        self.opacity_frame = ctk.CTkFrame(bar, fg_color="transparent", height=24)
        self.opacity_slider = ctk.CTkSlider(self.opacity_frame, from_=0.7, to=1.0, number_of_steps=6,
                                           width=80, height=14, fg_color=BORDER_COLOR, progress_color=self.accent,
                                           command=self._set_opacity)
        self.opacity_slider.set(self.target_opacity)
        self.opacity_slider.pack(side="left", padx=(4,0), pady=6)
        ctk.CTkLabel(self.opacity_frame, text="Opacity", font=(FONT, 8), text_color=SUBTXT).pack(side="left", padx=4)

        bf = ctk.CTkFrame(ctrl, fg_color="transparent")
        bf.pack(side="right")
        for txt, cmd, hov in [("_", self._minimize, "#333"), ("X", self._quit, "#E81123")]:
            ctk.CTkButton(bf, text=txt, width=32, height=24, font=(FONT, 11, "bold" if txt=="X" else "normal"),
                          fg_color="transparent", text_color="#666666", hover_color=hov,
                          corner_radius=6, command=cmd).pack(side="left", padx=1, pady=6)

    # ──────────────────────────────────────────────────────────────────────────
    # TOP NAVIGATION
    # ──────────────────────────────────────────────────────────────────────────
    def _build_topnav(self):
        nav = ctk.CTkFrame(self.main_frame, height=40, fg_color=PANEL_COLOR, corner_radius=14)
        nav.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=3)
        nav.grid_propagate(False)

        holder = ctk.CTkFrame(nav, fg_color="transparent")
        holder.pack(side="left", padx=6, pady=5)

        items = [("Scripts", "scripts"), ("Settings", "settings"), ("Projects", "projects"), ("About", "about")]
        self.tab_btns = {}
        for text, pid in items:
            b = ctk.CTkButton(holder, text=text, height=28, width=85, font=(FONT, 11, "bold"),
                              fg_color="transparent", text_color=SUBTXT, hover_color="#2a2a2a",
                              corner_radius=8, command=lambda p=pid: self.show_page(p))
            b.pack(side="left", padx=2)
            self.tab_btns[pid] = b

        ctk.CTkButton(nav, text="Open Folder", height=28, width=110, font=(FONT, 10),
                      fg_color=BORDER_COLOR, text_color=SUBTXT, hover_color=HOVER_ACC,
                      corner_radius=8, command=self._select_folder).pack(side="right", padx=6, pady=5)

    # ──────────────────────────────────────────────────────────────────────────
    # SIDEBAR
    # ──────────────────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        side = ctk.CTkFrame(self.main_frame, width=220, fg_color=SIDE_COLOR, corner_radius=14)
        side.grid(row=2, column=0, rowspan=2, sticky="ns", padx=(6, 3), pady=3)
        side.grid_propagate(False)

        inf = ctk.CTkFrame(side, fg_color="transparent")
        inf.pack(fill="x", padx=14, pady=(14, 4))
        ctk.CTkLabel(inf, text="ZERIO HUB", font=(FONT, 16, "bold"), text_color=self.accent).pack(anchor="w")
        ctk.CTkLabel(inf, text="GUI Edition", font=(FONT, 8), text_color=SUBTXT).pack(anchor="w", pady=(0,8))
        
        for label, txt in [("User:", os.getlogin()), ("PC:", platform.node()), ("Py:", f"Python {sys.version.split()[0]}")]:
            row = ctk.CTkFrame(inf, fg_color="transparent"); row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=label, font=(FONT, 9), text_color="#555555", width=34, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=txt, font=(FONT, 9), text_color=SUBTXT, anchor="w").pack(side="left")
            
        self.time_lbl = ctk.CTkLabel(inf, text="Time: --:--:--", font=(FONT, 9), text_color=SUBTXT, anchor="w")
        self.time_lbl.pack(fill="x", pady=1)

        self._sep(side)

        self.side_btns = {}
        for text, pid in [("Scripts", "scripts"), ("Settings", "settings"), ("Projects", "projects"), ("About", "about")]:
            b = ctk.CTkButton(side, text=f"  {text}", height=28, font=(FONT, 10), fg_color="transparent",
                              text_color=SUBTXT, hover_color="#2a2a2a", corner_radius=8, anchor="w",
                              command=lambda p=pid: self.show_page(p))
            b.pack(fill="x", padx=10, pady=1)
            self.side_btns[pid] = b

        ctk.CTkFrame(side, fg_color="transparent").pack(fill="both", expand=True)
        self._sep(side)

        sf = ctk.CTkFrame(side, fg_color="transparent")
        sf.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkLabel(sf, text="SYSTEM", font=(FONT, 8, "bold"), text_color="#555").pack(anchor="w", pady=(0, 4))

        for label, bar_name, lbl_name in [("CPU", "cpu_bar", "cpu_lbl"), ("RAM", "ram_bar", "ram_lbl"), ("DISK", "disk_bar", "disk_lbl")]:
            row = ctk.CTkFrame(sf, fg_color="transparent"); row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=label, font=(FONT, 8), text_color=SUBTXT, width=30).pack(side="left")
            bar = ctk.CTkProgressBar(row, height=4, fg_color=BORDER_COLOR, progress_color=self.accent, corner_radius=2)
            bar.pack(side="left", fill="x", expand=True, padx=(4, 6))
            lbl = ctk.CTkLabel(row, text="0%", font=(FONT, 8), text_color=SUBTXT, width=30, anchor="e")
            lbl.pack(side="right")
            setattr(self, bar_name, bar)
            setattr(self, lbl_name, lbl)

    # ──────────────────────────────────────────────────────────────────────────
    # CONTENT AREA
    # ──────────────────────────────────────────────────────────────────────────
    def _build_content_area(self):
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color=PANEL_COLOR, corner_radius=14)
        self.content_frame.grid(row=3, column=1, sticky="nsew", padx=(3, 6), pady=3)
        
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.pages = {}
        self._build_scripts_page()
        self._build_settings_page()
        self._build_projects_page()
        self._build_about_page()

    # ──────────────────────────────────────────────────────────────────────────
    # STATUS BAR
    # ──────────────────────────────────────────────────────────────────────────
    def _build_statusbar(self):
        bar = ctk.CTkFrame(self.main_frame, height=26, fg_color=PANEL_COLOR, corner_radius=14)
        bar.grid(row=4, column=0, columnspan=2, sticky="ew", padx=6, pady=(3, 6))
        bar.grid_propagate(False)

        status_left = ctk.CTkFrame(bar, fg_color="transparent")
        status_left.pack(side="left", padx=12)
        self.status_dot = ctk.CTkLabel(status_left, text=">", font=(FONT, 10, "bold"), text_color=self.accent)
        self.status_dot.pack(side="left")
        self.status_lbl = ctk.CTkLabel(status_left, text="Ready", font=(FONT, 9), text_color=TXT)
        self.status_lbl.pack(side="left", padx=6)

        self.status_right = ctk.CTkLabel(bar, text="", font=(FONT, 8), text_color="#555")
        self.status_right.pack(side="right", padx=12)

    def _set_status(self, text): self.status_lbl.configure(text=text)

    @staticmethod
    def _sep(parent):
        ctk.CTkFrame(parent, height=1, fg_color=BORDER_COLOR).pack(fill="x", padx=14, pady=6)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE SWITCHING
    # ══════════════════════════════════════════════════════════════════════════
    def show_page(self, pid):
        self.page = pid
        for p, frame in self.pages.items():
            if p == pid: frame.grid(row=0, column=0, sticky="nsew")
            else: frame.grid_forget()

        for p, b in self.tab_btns.items():
            if p == pid: b.configure(fg_color=self.accent, text_color=TXT, hover_color=HOVER_ACC)
            else: b.configure(fg_color="transparent", text_color=SUBTXT, hover_color="#2a2a2a")

        for p, b in self.side_btns.items():
            if p == pid: b.configure(fg_color="#252525", text_color=self.accent, hover_color="#2a2a2a")
            else: b.configure(fg_color="transparent", text_color=SUBTXT, hover_color="#2a2a2a")

    # ══════════════════════════════════════════════════════════════════════════
    # SCRIPTS PAGE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_scripts_page(self):
        page = ctk.CTkFrame(self.content_frame, fg_color=PANEL_COLOR, corner_radius=0)
        self.pages["scripts"] = page

        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(page, width=240, fg_color="#151515", corner_radius=12)
        left.grid(row=0, column=0, sticky="ns", padx=(6,3), pady=6)
        left.grid_propagate(False)

        sf = ctk.CTkFrame(left, fg_color="transparent")
        sf.pack(fill="x", padx=6, pady=(6,3))
        self.search_entry = ctk.CTkEntry(sf, height=28, placeholder_text="Search...", fg_color=BORDER_COLOR,
                                         text_color=TXT, placeholder_text_color="#555", corner_radius=8, border_width=0, font=(FONT, 10))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0,3))
        self.search_entry.bind("<KeyRelease>", lambda e: self._filter_scripts())
        ctk.CTkButton(sf, text="R", width=28, height=28, font=(FONT, 12), fg_color=BORDER_COLOR, text_color=SUBTXT,
                      hover_color=HOVER_ACC, corner_radius=8, command=self._refresh_scripts).pack(side="right")

        tb = ctk.CTkFrame(left, fg_color="transparent"); tb.pack(fill="x", padx=6, pady=2)
        self.fav_btn = ctk.CTkButton(tb, text="Fav", width=30, height=22, font=(FONT, 9), fg_color="transparent",
                                     text_color=SUBTXT, hover_color="#2a2a2a", corner_radius=6, command=self._toggle_fav_filter)
        self.fav_btn.pack(side="left")
        self.folder_lbl = ctk.CTkLabel(tb, text="No folder", font=(FONT, 8), text_color="#555", anchor="w")
        self.folder_lbl.pack(side="left", fill="x", expand=True, padx=4)

        self.script_list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent", corner_radius=0, border_width=0)
        self.script_list_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.script_buttons = {}

        right = ctk.CTkFrame(page, fg_color="#111111", corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(3,6), pady=6)

        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        etb = ctk.CTkFrame(right, height=36, fg_color="#1a1a1a", corner_radius=8)
        etb.grid(row=0, column=0, sticky="ew", padx=4, pady=(4,0))
        etb.grid_propagate(False)
        self.file_lbl = ctk.CTkLabel(etb, text="No file selected", font=(FONT, 10), text_color=SUBTXT, anchor="w")
        self.file_lbl.pack(side="left", padx=10)

        ebf = ctk.CTkFrame(etb, fg_color="transparent"); ebf.pack(side="right", padx=4)
        for txt, cmd, w in [("Fav", self._toggle_favorite, 34), ("Save", self._save_script, 50), ("Run", self._run_script, 45), ("Stop", self._stop_script, 45)]:
            ctk.CTkButton(ebf, text=txt, width=w, height=24, font=(FONT, 9), fg_color=BORDER_COLOR, text_color=TXT,
                          hover_color=HOVER_ACC, corner_radius=6, command=cmd).pack(side="left", padx=2, pady=5)

        self.editor = ctk.CTkTextbox(right, fg_color="#111111", text_color="#d4d4d4",
                                     font=("Cascadia Code", self.font_size) if sys.platform == "win32" else (FONT, self.font_size),
                                     corner_radius=0, border_width=0, spacing3=2, activate_scrollbars=True)
        self.editor.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

    # ══════════════════════════════════════════════════════════════════════════
    # REAL TERMINAL EXECUTION
    # ══════════════════════════════════════════════════════════════════════════
    def _run_script(self):
        if not self.sel_script: self._set_status("No script selected"); return
        if self.running: self._set_status("Already running a script"); return
        self._save_script(silent=True)
        
        self.running = True
        self._set_status(f"Opened terminal for {self.sel_script.name}")
        
        try:
            flags = subprocess.CREATE_NEW_CONSOLE
            self.process = subprocess.Popen(
                [sys.executable, str(self.sel_script)],
                cwd=str(self.sel_script.parent),
                creationflags=flags
            )
        except Exception as e:
            self.running = False
            self._set_status(f"Run error: {e}")

    def _stop_script(self):
        if self.process and self.running:
            try: self.process.kill()
            except: pass
            self.running = False
            self._set_status("Process killed")

    def _tick_process(self):
        if self.process and self.running:
            if self.process.poll() is not None:
                self.running = False
                self._set_status("Ready")
        self.after(1000, self._tick_process)

    # ══════════════════════════════════════════════════════════════════════════
    # SETTINGS, PROJECTS, ABOUT PAGES
    # ══════════════════════════════════════════════════════════════════════════
    def _build_settings_page(self):
        page = ctk.CTkFrame(self.content_frame, fg_color=PANEL_COLOR, corner_radius=0)
        self.pages["settings"] = page
        scroll = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=30, pady=20)

        ctk.CTkLabel(scroll, text="Settings", font=(FONT, 22, "bold"), text_color=TXT).pack(anchor="w", pady=(0, 16))

        self._section_label(scroll, "Accent Color")
        acf = ctk.CTkFrame(scroll, fg_color="transparent"); acf.pack(fill="x", pady=(0, 16))
        self.accent_btns = {}
        for name, color in ACCENT_PRESETS.items():
            b = ctk.CTkButton(acf, text="", width=34, height=34, fg_color=color, hover_color=color, corner_radius=10,
                              border_width=2 if color == self.accent else 0, border_color=TXT,
                              command=lambda c=color, n=name: self._set_accent(c, n))
            b.pack(side="left", padx=4); self.accent_btns[name] = b

        self._section_label(scroll, "Font Size")
        fsf = ctk.CTkFrame(scroll, fg_color="transparent"); fsf.pack(fill="x", pady=(0, 16))
        self.font_slider = ctk.CTkSlider(fsf, from_=9, to=20, number_of_steps=11, fg_color=BORDER_COLOR,
                                         progress_color=self.accent, command=self._on_font_change)
        self.font_slider.set(self.font_size); self.font_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.font_size_lbl = ctk.CTkLabel(fsf, text=f"{self.font_size}px", font=(FONT, 11), text_color=TXT, width=50)
        self.font_size_lbl.pack(side="right")

        self._section_label(scroll, "Startup Folder")
        sff = ctk.CTkFrame(scroll, fg_color="transparent"); sff.pack(fill="x", pady=(0, 16))
        self.startup_folder_lbl = ctk.CTkLabel(sff, text=self.script_folder or "None", font=(FONT, 10), text_color=SUBTXT, anchor="w")
        self.startup_folder_lbl.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(sff, text="Change", width=70, height=28, font=(FONT, 10), fg_color=BORDER_COLOR, text_color=TXT,
                      hover_color=HOVER_ACC, corner_radius=6, command=self._change_startup_folder).pack(side="right")

        self._section_label(scroll, "Behavior")
        self.auto_refresh_var = ctk.BooleanVar(value=self.auto_refresh)
        self.auto_save_var = ctk.BooleanVar(value=self.auto_save)
        for text, var, cmd in [("Auto-refresh script list", self.auto_refresh_var, lambda: setattr(self, 'auto_refresh', self.auto_refresh_var.get())),
                                ("Auto-save on script switch", self.auto_save_var, lambda: setattr(self, 'auto_save', self.auto_save_var.get()))]:
            row = ctk.CTkFrame(scroll, fg_color="transparent"); row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=text, font=(FONT, 11), text_color=TXT, anchor="w").pack(side="left")
            ctk.CTkSwitch(row, variable=var, fg_color=BORDER_COLOR, progress_color=self.accent, command=cmd, width=44, height=22).pack(side="right")

    def _build_projects_page(self):
        page = ctk.CTkFrame(self.content_frame, fg_color=PANEL_COLOR, corner_radius=0)
        self.pages["projects"] = page
        ctk.CTkLabel(page, text="Projects", font=(FONT, 22, "bold"), text_color=TXT).pack(anchor="w", padx=30, pady=(24, 4))
        ctk.CTkLabel(page, text="Create and manage your script projects", font=(FONT, 10), text_color=SUBTXT).pack(anchor="w", padx=30, pady=(0, 16))
        af = ctk.CTkFrame(page, fg_color="transparent"); af.pack(fill="x", padx=30, pady=(0, 16))
        ctk.CTkButton(af, text="+ New Project", height=36, font=(FONT, 11), fg_color=self.accent, text_color=TXT,
                      hover_color=HOVER_ACC, corner_radius=10, width=140, command=self._create_project).pack(side="left", padx=(0, 10))
        ctk.CTkButton(af, text="Open Project", height=36, font=(FONT, 11), fg_color=BORDER_COLOR, text_color=TXT,
                      hover_color=HOVER_ACC, corner_radius=10, width=140, command=self._open_project).pack(side="left")
        ctk.CTkLabel(page, text="Recent Projects", font=(FONT, 12, "bold"), text_color=SUBTXT).pack(anchor="w", padx=30, pady=(10, 6))
        self.projects_list = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
        self.projects_list.pack(fill="both", expand=True, padx=30, pady=(0, 24))

    def _build_about_page(self):
        page = ctk.CTkFrame(self.content_frame, fg_color=PANEL_COLOR, corner_radius=0)
        self.pages["about"] = page
        center = ctk.CTkFrame(page, fg_color="transparent"); center.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(center, text="ZERIO HUB", font=(FONT, 30, "bold"), text_color=self.accent).pack(pady=(0, 4))
        ctk.CTkLabel(center, text=f"Version {VERSION}", font=(FONT, 12), text_color=SUBTXT).pack(pady=(0, 20))
        card = ctk.CTkFrame(center, fg_color="#151515", corner_radius=14, width=360)
        card.pack(padx=20, pady=4); card.pack_propagate(False)
        infos = [("Python", sys.version.split()[0]), ("Platform", f"{platform.system()} {platform.release()}"),
                 ("Architecture", platform.machine()), ("CustomTkinter", ctk.__version__),
                 ("psutil", psutil.__version__), ("Pillow", __import__("PIL").__version__), ("Author", "Zerio")]
        for label, value in infos:
            row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=18, pady=4)
            ctk.CTkLabel(row, text=label, font=(FONT, 10), text_color=SUBTXT, anchor="w", width=110).pack(side="left")
            ctk.CTkLabel(row, text=value, font=(FONT, 10), text_color=TXT, anchor="e").pack(side="right")
        ctk.CTkLabel(center, text="Built with Python & CustomTkinter", font=(FONT, 9), text_color="#444").pack(pady=(20, 0))

    def _section_label(self, parent, text): ctk.CTkLabel(parent, text=text, font=(FONT, 12, "bold"), text_color=SUBTXT).pack(anchor="w", pady=(8, 6))

    # ══════════════════════════════════════════════════════════════════════════
    # LOGIC FUNCTIONS
    # ══════════════════════════════════════════════════════════════════════════
    def _select_folder(self):
        path = filedialog.askdirectory(title="Select Script Folder")
        if path: self.script_folder = path; self.folder_lbl.configure(text=os.path.basename(path)); self._scan_folder(); self._save_settings()

    def _scan_folder(self):
        if not self.script_folder or not os.path.isdir(self.script_folder): return
        self.scripts = sorted([p for p in Path(self.script_folder).rglob("*") if p.suffix in (".py", ".pyw")], key=lambda p: p.name.lower())
        self._filter_scripts(); self._set_status(f"Found {len(self.scripts)} scripts")

    def _filter_scripts(self):
        q = self.search_entry.get().lower()
        self.filtered = [s for s in self.scripts if q in s.name.lower() and (not self.fav_filter or str(s) in self.favorites)]
        self._render_script_list()

    def _render_script_list(self):
        for w in self.script_list_frame.winfo_children(): w.destroy()
        self.script_buttons.clear()
        if not self.script_folder: ctk.CTkLabel(self.script_list_frame, text="Open a folder\nto begin", font=(FONT, 10), text_color=SUBTXT).pack(pady=40); return
        if not self.filtered: ctk.CTkLabel(self.script_list_frame, text="No scripts found", font=(FONT, 10), text_color=SUBTXT).pack(pady=40); return
        for sp in self.filtered:
            is_fav = str(sp) in self.favorites; prefix = "[Fav] " if is_fav else "      "
            is_sel = self.sel_script and sp == self.sel_script
            btn = ctk.CTkButton(self.script_list_frame, text=f"{prefix}{sp.name}", height=28, font=(FONT, 10),
                                fg_color=self.accent if is_sel else "#1e1e1e", text_color=TXT,
                                hover_color="#2a2a2a" if not is_sel else HOVER_ACC, corner_radius=6, anchor="w",
                                command=lambda s=sp: self._on_script_select(s))
            btn.pack(fill="x", pady=1); self.script_buttons[sp] = btn

    def _on_script_select(self, sp):
        if self.auto_save and self.sel_script and self.editor.get("1.0", "end").strip(): self._save_script(silent=True)
        self.sel_script = sp; self._original_content = ""
        try:
            self._original_content = sp.read_text(encoding="utf-8", errors="replace")
            self.editor.configure(state="normal"); self.editor.delete("1.0", "end"); self.editor.insert("1.0", self._original_content)
        except Exception as e: self.editor.delete("1.0", "end"); self.editor.insert("1.0", f"Error reading file:\n{e}")
        self.file_lbl.configure(text=f"File: {sp.name}"); self._set_status(f"Opened {sp.name}"); self._render_script_list()

    def _save_script(self, silent=False):
        if not self.sel_script:
            if not silent: self._set_status("No file to save"); return
        try:
            content = self.editor.get("1.0", "end")
            if not content.endswith("\n"): content += "\n"
            self.sel_script.write_text(content, encoding="utf-8"); self._original_content = content
            self._set_status(f"Saved {self.sel_script.name}")
        except Exception as e:
            self._set_status(f"Save error: {e}")

    def _toggle_favorite(self):
        if not self.sel_script: return
        key = str(self.sel_script)
        if key in self.favorites: self.favorites.remove(key); self._set_status(f"Removed favorite")
        else: self.favorites.append(key); self._set_status(f"Added favorite")
        self._save_settings(); self._filter_scripts()

    def _toggle_fav_filter(self):
        self.fav_filter = not self.fav_filter; self.fav_btn.configure(text_color=self.accent if self.fav_filter else SUBTXT)
        self._filter_scripts()

    def _refresh_scripts(self): self._scan_folder(); self._set_status("Refreshed")
    def _tick_refresh(self):
        if self.auto_refresh and self.script_folder and self.page == "scripts": self._scan_folder()
        self.after(5000, self._tick_refresh)

    def _set_accent(self, color, name):
        self.accent = color
        for n, b in self.accent_btns.items(): b.configure(border_width=2 if n == name else 0, border_color=TXT)
        self._apply_accent(); self._save_settings()

    def _apply_accent(self):
        for bar in [self.cpu_bar, self.ram_bar, self.disk_bar]: bar.configure(progress_color=self.accent)
        self.font_slider.configure(progress_color=self.accent)
        self.time_lbl.configure(text_color=self.accent)
        self.show_page(self.page)

    def _on_font_change(self, val):
        self.font_size = int(float(val)); self.font_size_lbl.configure(text=f"{self.font_size}px")
        self.editor.configure(font=("Cascadia Code" if sys.platform=="win32" else FONT, self.font_size))
        self._save_settings()

    def _change_startup_folder(self):
        path = filedialog.askdirectory(title="Select Startup Folder")
        if path: self.script_folder = path; self.startup_folder_lbl.configure(text=path); self.folder_lbl.configure(text=os.path.basename(path)); self._save_settings(); self._scan_folder()

    def _create_project(self):
        dialog = ctk.CTkInputDialog(text="Enter project name:", title="New Project"); name = dialog.get_input()
        if not name or not name.strip(): return
        name = name.strip().replace(" ", "_").replace("/", ""); PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        proj_path = PROJECTS_DIR / name
        if proj_path.exists(): self._set_status("Project already exists"); return
        proj_path.mkdir(); (proj_path / "main.py").write_text(f'# {name} Project\nprint("Hello from {name}!")\n', encoding="utf-8")
        self._add_recent(str(proj_path)); self._open_project_path(str(proj_path)); self._set_status(f"Created project: {name}")

    def _open_project(self):
        path = filedialog.askdirectory(title="Open Project Folder")
        if path: self._open_project_path(path)

    def _open_project_path(self, path):
        self.script_folder = path; self.folder_lbl.configure(text=os.path.basename(path))
        self.startup_folder_lbl.configure(text=path); self._add_recent(path)
        self._save_settings(); self._scan_folder(); self.show_page("scripts"); self._set_status(f"Opened project: {os.path.basename(path)}")

    def _add_recent(self, path):
        path = str(path)
        if path in self.recent_projects: self.recent_projects.remove(path)
        self.recent_projects.insert(0, path); self.recent_projects = self.recent_projects[:10]; self._render_projects()

    def _render_projects(self):
        for w in self.projects_list.winfo_children(): w.destroy()
        if not self.recent_projects: ctk.CTkLabel(self.projects_list, text="No recent projects", font=(FONT, 10), text_color=SUBTXT).pack(pady=20); return
        for p in self.recent_projects:
            if not os.path.isdir(p): continue
            row = ctk.CTkFrame(self.projects_list, fg_color="#151515", corner_radius=10, height=46)
            row.pack(fill="x", pady=2); row.pack_propagate(False)
            ctk.CTkLabel(row, text=f"> {os.path.basename(p)}", font=(FONT, 11), text_color=TXT, anchor="w").pack(side="left", padx=14, fill="y")
            ctk.CTkButton(row, text="Open", width=60, height=26, font=(FONT, 9), fg_color=self.accent, text_color=TXT,
                          hover_color=HOVER_ACC, corner_radius=6, command=lambda pp=p: self._open_project_path(pp)).pack(side="right", padx=10, pady=10)

    # ══════════════════════════════════════════════════════════════════════════
    # SETTINGS PERSISTENCE & TICKS
    # ══════════════════════════════════════════════════════════════════════════
    def _load_settings(self):
        try:
            if SETTINGS_FP.exists():
                d = json.loads(SETTINGS_FP.read_text(encoding="utf-8"))
                self.accent = d.get("accent", ACCENT); self.font_size = d.get("font_size", 13)
                self.script_folder = d.get("script_folder", ""); self.auto_refresh = d.get("auto_refresh", True)
                self.auto_save = d.get("auto_save", False); self.favorites = d.get("favorites", [])
                self.recent_projects = d.get("recent_projects", [])
        except: pass

    def _save_settings(self):
        try:
            SETTINGS_FP.write_text(json.dumps({"accent": self.accent, "font_size": self.font_size, "script_folder": self.script_folder,
                "auto_refresh": self.auto_refresh, "auto_save": self.auto_save, "favorites": self.favorites,
                "recent_projects": self.recent_projects}, indent=2), encoding="utf-8")
        except: pass

    def _tick_time(self):
        self.time_lbl.configure(text=f"Time: {datetime.now().strftime('%H:%M:%S')}"); self.after(1000, self._tick_time)

    def _tick_stats(self):
        try:
            cpu = psutil.cpu_percent(interval=0.5); mem = psutil.virtual_memory(); disk = psutil.disk_usage('/')
            self.cpu_bar.set(cpu / 100); self.cpu_lbl.configure(text=f"{cpu:.0f}%")
            self.ram_bar.set(mem.percent / 100); self.ram_lbl.configure(text=f"{mem.percent:.0f}%")
            self.disk_bar.set(disk.percent / 100); self.disk_lbl.configure(text=f"{disk.percent:.0f}%")
            self.status_right.configure(text=f"CPU {cpu:.0f}%  |  RAM {mem.percent:.0f}%")
        except: pass
        self.after(2000, self._tick_stats)

if __name__ == "__main__":
    app = ZerioHub()
    app.mainloop()
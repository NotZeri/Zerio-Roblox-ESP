# Debug
DEBUG_MODE = True
ENABLE_ESP = True
# ====================================
# AIMBOT SETTINGS
# ====================================
ENABLE_AIMBOT = False          # Starts OFF. Press V to toggle.
AIMBOT_FOV_SIZE = 80.0        # Radius in pixels from crosshair
AIMBOT_SMOOTHING = 3.5         # Lower = faster/snappier.
AIMBOT_PREDICTION = False      # Leave False until base aimbot is verified
# Colors [R, G, B, A]
ESP_BOX_COLOR = [0, 255, 0, 255]
ESP_TRACER_COLOR = [255, 255, 255, 255]
ESP_NAME_COLOR = [255, 255, 255, 255]
ESP_DISTANCE_COLOR = [255, 255, 255, 255]
ESP_HEALTH_COLOR = [0, 255, 0, 255]
AIMBOT_FOV_COLOR = [255, 255, 255, 100] # Color of the FOV circle
# Visual settings
ESP_SHOW_BOX = True
ESP_SHOW_TRACER = False
ESP_SHOW_NAME = False
ESP_SHOW_DISTANCE = True
ESP_SHOW_HEALTH = True
ESP_CORNER_BOX = True
ESP_3D_BOX = False
ESP_DYNAMIC_HEALTH_COLOR = True
ESP_TEXT_SIZE = 14
ESP_BOX_THICKNESS = 1
# Filters
IGNORE_TEAM = True
IGNORE_DEAD = True
HIDE_DISTANCE = False
MAX_DISTANCE = 500
# ====================================
# HARDCODED OFFSETS
# ====================================
HARDCODED_OFFSETS = {
"FakeDataModelPointer": 0x7BE9278,
"FakeDataModelToDataModel": 0x1D0,
"Workspace": 0x178,
"VisualEnginePointer": 0x8306B58,
"viewmatrix": 0x150,
"Children": 0x78,
"Name": 0xB0,
"LocalPlayer": 0x148,
"ModelInstance": 0x3D8,
"Team": 0x2D0,
"Health": 0x194,
"Primitive": 0x148,
"Position": 0xEC,
"Velocity": 0xF8,
}
# ====================================
# IMPORTS
# ====================================
import sys
import os
import math
import random
from ctypes import *
from ctypes.wintypes import DWORD, LONG, BYTE, HMODULE
from struct import unpack
from numpy import array, float32, dot
from time import time, sleep
from threading import Thread
from psutil import Process, HIGH_PRIORITY_CLASS, process_iter, NoSuchProcess
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QBrush
if not DEBUG_MODE:
    hwnd = windll.kernel32.GetConsoleWindow()
    if hwnd: windll.user32.ShowWindow(hwnd, 0)
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFO = 0x0400
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008 | 0x00000010
class PROCESSENTRY32(Structure):
    _fields_ = [
        ("dwSize", DWORD), ("cntUsage", DWORD), ("th32ProcessID", DWORD),
        ("th32DefaultHeapID", c_void_p), ("th32ModuleID", DWORD), ("th32Threads", DWORD),
        ("th32ParentProcessID", DWORD), ("pcPriClassBase", c_ulong), ("dwFlags", DWORD),
        ("szExeFile", c_wchar * 260),
    ]
class MODULEENTRY32(Structure):
    _fields_ = [
        ("dwSize", DWORD), ("th32ModuleID", DWORD), ("th32ProcessID", DWORD),
        ("GlblcntUsage", DWORD), ("ProccntUsage", DWORD), ("modBaseAddr", c_void_p),
        ("modBaseSize", DWORD), ("hModule", HMODULE), ("szModule", c_char * 256),
        ("szExePath", c_char * 260),
    ]
class RECT(Structure):
    _fields_ = [('left', LONG), ('top', LONG), ('right', LONG), ('bottom', LONG)]
class POINT(Structure):
    _fields_ = [('x', LONG), ('y', LONG)]
# ====================================
# MEMORY CLASS
# ====================================
class Memory:
    def __init__(self):
        self.process_handle = None
        self.process_id = 0
    def _is_valid_ptr(self, address):
        return isinstance(address, int) and 0x10000 < address < 0x7FFFFFFFFFFF
    def get_pid_by_name(self, process_name):
        try:
            for proc in process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                        log(f'[+] Process found: {proc.info["name"]} (PID: {proc.info["pid"]})')
                        return proc.info['pid']
                except: pass
        except: pass
        return None
    def open_process(self, pid):
        try:
            self.process_id = pid
            self.process_handle = windll.kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFO, False, pid)
            if self.process_handle and self.process_handle != 0:
                log(f'[+] Process opened! Handle: {self.process_handle}')
                return True
            log(f'[!] Failed to open process. Error: {windll.kernel32.GetLastError()}')
            return False
        except Exception as e: log(f'[!] Exception: {e}'); return False
    def get_module_base(self, module_name="RobloxPlayerBeta.exe"):
        try:
            snapshot = windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, self.process_id)
            if snapshot == -1: return 0
            entry = MODULEENTRY32()
            entry.dwSize = sizeof(MODULEENTRY32)
            if windll.kernel32.Module32First(snapshot, byref(entry)):
                while True:
                    try:
                        mod_name = entry.szModule.decode('utf-8', errors='ignore')
                        if mod_name.lower() == module_name.lower():
                            base = entry.modBaseAddr
                            windll.kernel32.CloseHandle(snapshot)
                            log(f'[+] Module {mod_name} - Base: {hex(base)}')
                            return base
                    except: pass
                    if not windll.kernel32.Module32Next(snapshot, byref(entry)): break
            windll.kernel32.CloseHandle(snapshot)
        except Exception as e: log(f'[!] Error: {e}')
        return 0
    def read(self, address, size):
        if not self.process_handle or not self._is_valid_ptr(address): return b'\x00' * size
        try:
            buffer = (BYTE * size)()
            bytes_read = c_size_t(0)
            if windll.kernel32.ReadProcessMemory(self.process_handle, c_void_p(address), buffer, size, byref(bytes_read)):
                return bytes(buffer)
        except: pass
        return b'\x00' * size
    def read_int8(self, address):
        if not self._is_valid_ptr(address): return 0
        data = self.read(address, 8)
        return unpack("<Q", data)[0] if len(data) == 8 else 0
    def read_int4(self, address):
        if not self._is_valid_ptr(address): return 0
        data = self.read(address, 4)
        return unpack("<I", data)[0] if len(data) == 4 else 0
    def read_float(self, address):
        if not self._is_valid_ptr(address): return 0.0
        data = self.read(address, 4)
        return unpack("<f", data)[0] if len(data) == 4 else 0.0
    def close(self):
        if self.process_handle: windll.kernel32.CloseHandle(self.process_handle)
mem = Memory()
lpAddr = 0
plrsAddr = 0
matrixAddr = 0
features_enabled = False
aimbot_enabled = False
offsets = {}
def log(msg):
    if DEBUG_MODE: print(msg)
# ====================================
# ROBLOX HELPERS
# ====================================
def read_roblox_string(address):
    try:
        raw_count = mem.read_int4(address + 0x10)
        string_count = min(max(0, raw_count), 128)
        if string_count == 0: return ""
        if raw_count > 15:
            ptr = mem.read_int8(address)
            if not mem._is_valid_ptr(ptr): return ""
            data = mem.read(ptr, string_count)
        else:
            data = mem.read(address, string_count)
        return data.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
    except: return ""
def get_class_name(instance):
    try:
        class_desc = mem.read_int8(instance + 0x18)
        if not class_desc: return ""
        class_name_ptr = mem.read_int8(class_desc + 0x8)
        if not mem._is_valid_ptr(class_name_ptr): return ""
        return read_roblox_string(class_name_ptr)
    except: return ""
def get_name(instance, name_offset):
    try:
        ptr = mem.read_int8(instance + name_offset)
        if not mem._is_valid_ptr(ptr): return ""
        return read_roblox_string(ptr)
    except: return ""
def get_children(instance, children_offset):
    try:
        vector_ptr = mem.read_int8(instance + children_offset)
        if not vector_ptr: return []
        begin = mem.read_int8(vector_ptr)
        end = mem.read_int8(vector_ptr + 8)
        children = []
        current = begin
        for _ in range(9000):
            if current >= end: break
            child = mem.read_int8(current)
            if child: children.append(child)
            current += 0x08
        return children
    except: return []
def find_first_child(instance, child_name, name_offset, children_offset):
    try:
        for child in get_children(instance, children_offset):
            if get_name(child, name_offset) == child_name: return child
    except: pass
    return 0
def find_first_child_of_class(instance, class_name, children_offset):
    try:
        for child in get_children(instance, children_offset):
            if get_class_name(child) == class_name: return child
    except: pass
    return 0
# ====================================
# MATH HELPERS
# ====================================
_IDENTITY_4X4 = array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=float32)
def world_to_screen(pos, view_proj_matrix, width, height):
    try:
        vec = array([pos[0], pos[1], pos[2], 1.0], dtype=float32)
        clip = dot(view_proj_matrix, vec)
        if clip[3] <= 0: return None
        ndc = clip[:3] / clip[3]
        if not (-1 <= ndc[0] <= 1 and -1 <= ndc[1] <= 1 and 0 <= ndc[2] <= 1): return None
        x = int((ndc[0] + 1) * 0.5 * width)
        y = int((1 - ndc[1]) * 0.5 * height)
        return (x, y)
    except: return None
def world_to_screen_float(pos, view_proj_matrix, width, height):
    try:
        vec = array([pos[0], pos[1], pos[2], 1.0], dtype=float32)
        clip = dot(view_proj_matrix, vec)
        if clip[3] <= 0: return None
        ndc = clip[:3] / clip[3]
        if not (-1 <= ndc[0] <= 1 and -1 <= ndc[1] <= 1 and 0 <= ndc[2] <= 1): return None
        x = (ndc[0] + 1) * 0.5 * width
        y = (1 - ndc[1]) * 0.5 * height
        return (float(x), float(y))
    except: return None
def find_window_by_title(title): return windll.user32.FindWindowW(None, title)
def get_client_rect_on_screen(hwnd):
    rect = RECT()
    if windll.user32.GetClientRect(hwnd, byref(rect)) == 0: return 0, 0, 0, 0
    top_left, bot_right = POINT(rect.left, rect.top), POINT(rect.right, rect.bottom)
    windll.user32.ClientToScreen(hwnd, byref(top_left))
    windll.user32.ClientToScreen(hwnd, byref(bot_right))
    return top_left.x, top_left.y, bot_right.x, bot_right.y
def get_window_rect(hwnd):
    rect = RECT()
    windll.user32.GetWindowRect(hwnd, byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom
def get_roblox_version(pid):
    try:
        exe_path = Process(pid).exe()
        folder = os.path.basename(os.path.dirname(exe_path))
        if folder.startswith("version-"): return folder
    except: pass
    return "Unknown"
# ====================================
# INIT INJECTION
# ====================================
def init_injection():
    global lpAddr, plrsAddr, matrixAddr, offsets
    while True:
        log('[*] Waiting for Roblox...')
        while True:
            pid = mem.get_pid_by_name("RobloxPlayerBeta.exe")
            if pid and mem.open_process(pid): break
            sleep(1)
        offsets = HARDCODED_OFFSETS
        local_version = get_roblox_version(pid)
        target_version = "version-1a951716f19e4638"
        log('----------------------------------------------')
        log(f' Your Roblox Version : {local_version}')
        log(f' Offsets Target Ver. : {target_version}')
        if local_version != target_version:
            log(' Status : MISMATCH! Waiting for update...')
            sleep(15); continue
        else:
            log(' Status : MATCH!')
            log('----------------------------------------------')
        try:
            baseAddr = mem.get_module_base()
            if not baseAddr: sleep(5); continue
            log('[*] Step 1: Reading FakeDataModel...')
            fakeDatamodel = mem.read_int8(baseAddr + offsets['FakeDataModelPointer'])
            if not fakeDatamodel: log('[!] Failed at FakeDataModel.'); sleep(5); continue
            log('[*] Step 2: Reading DataModel...')
            dataModel = mem.read_int8(fakeDatamodel + offsets['FakeDataModelToDataModel'])
            if not dataModel: log('[!] Failed at DataModel.'); sleep(5); continue
            log('[*] Step 3: Reading Workspace...')
            wsAddr = mem.read_int8(dataModel + offsets['Workspace'])
            if not wsAddr: log('[!] Failed at Workspace.'); sleep(5); continue
            log('[*] Step 4: Finding Players...')
            plrsAddr = 0
            for _ in range(30):
                plrsAddr = find_first_child_of_class(dataModel, 'Players', offsets['Children'])
                if plrsAddr: break
                sleep(1)
            if not plrsAddr: log('[!] Failed to find Players.'); sleep(5); continue
            log('[*] Step 5: Finding LocalPlayer...')
            lpAddr = 0
            for _ in range(30):
                lpAddr = mem.read_int8(plrsAddr + offsets['LocalPlayer'])
                if lpAddr: break
                sleep(1)
            if not lpAddr: log('[!] Failed to find LocalPlayer.'); sleep(5); continue
            log('[*] Step 6: Finding ViewMatrix...')
            visualEngine = mem.read_int8(baseAddr + offsets['VisualEnginePointer'])
            if visualEngine:
                matrixAddr = visualEngine + offsets['viewmatrix']
                log(f'[+] ViewMatrix mapped to {hex(matrixAddr)}')
            else:
                log('[!] Failed to read VisualEngine.')
            log('[+] Injection completed successfully!')
            return True
        except Exception as e:
            log(f'[!!!] CRASH PREVENTED: {e}')
            sleep(5)
# ====================================
# ESP OVERLAY & ISOLATED AIMBOT
# ====================================
class ESPOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.resize(10, 10)
        self.esp_data = []
        self.prev_geometry = (0, 0, 0, 0)
        self.last_geom_check = 0.0
        self.startLineX = 0
        self.startLineY = 0
        self.matrix_cache = None
        self.matrix_cache_time = 0.0
        self._entity_cache = {}
        self._entity_cache_ttl = 2.0
        self._font = QFont("Arial", ESP_TEXT_SIZE)
        self._font.setBold(False)
        sleep(0.1)
        self.show()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(8)
    def _tick(self):
        self.update_players()
        self.timer.setInterval(max(4, 8 + random.randint(-2, 2)))
    def _get_cached_entity(self, player_addr, now):
        cached = self._entity_cache.get(player_addr)
        if cached and now < cached['expires']: return cached
        return None
    def _set_cached_entity(self, player_addr, data, now):
        data['expires'] = now + self._entity_cache_ttl
        self._entity_cache[player_addr] = data
    def _update_geometry(self):
        hwnd_roblox = find_window_by_title("Roblox")
        if not hwnd_roblox: return
        x, y, r, b = get_client_rect_on_screen(hwnd_roblox)
        w, h = r - x, b - y
        if w <= 0 or h <= 0: x, y, r, b = get_window_rect(hwnd_roblox); w, h = r - x, b - y
        if w <= 0 or h <= 0: return
        new_geom = (x, y, w, h)
        if new_geom != self.prev_geometry:
            self.setGeometry(*new_geom)
            self.prev_geometry = new_geom
            self.startLineX = w / 2
            self.startLineY = h - h / 20
    def run_aimbot(self, target_float_screen):
        try:
            if not aimbot_enabled or not features_enabled: return
            cursor_global = POINT()
            windll.user32.GetCursorPos(byref(cursor_global))
            cursor_local = self.mapFromGlobal(QPoint(cursor_global.x, cursor_global.y))
            cur_x, cur_y = float(cursor_local.x()), float(cursor_local.y())
            final_dx = target_float_screen[0] - cur_x
            final_dy = target_float_screen[1] - cur_y
            smooth_factor = 1.0 / AIMBOT_SMOOTHING
            if smooth_factor > 1.0: smooth_factor = 1.0
            move_x = int(final_dx * smooth_factor)
            move_y = int(final_dy * smooth_factor)
            if move_x != 0 or move_y != 0:
                # Uses the most reliable mouse moving function for games
                windll.user32.mouse_event(0x0001, move_x, move_y, 0, 0)
        except Exception as e:
            if DEBUG_MODE: print(f"[AIMBOT ERROR] {e}")
    def update_players(self):
        if not ENABLE_ESP or not features_enabled or lpAddr == 0 or plrsAddr == 0 or matrixAddr == 0:
            if self.esp_data: self.esp_data.clear(); self.update()
            return
        self.esp_data.clear()
        now = time()
        if now - self.last_geom_check > 2.0:
            self._update_geometry()
            self.last_geom_check = now
        try:
            if now - self.matrix_cache_time > 0.016:
                raw = mem.read(matrixAddr, 64)
                self.matrix_cache = array(unpack("<16f", raw), dtype=float32).reshape(4, 4)
                self.matrix_cache_time = now
            view_proj = self.matrix_cache if self.matrix_cache is not None else _IDENTITY_4X4.copy()
            lpTeam = mem.read_int8(lpAddr + offsets['Team'])
            lpChar = mem.read_int8(lpAddr + offsets['ModelInstance'])
            lpHead = find_first_child(lpChar, 'Head', offsets['Name'], offsets['Children']) if lpChar else 0
            if lpHead:
                lpPrim = mem.read_int8(lpHead + offsets['Primitive'])
                lpHeadPos = array(unpack("<fff", mem.read(lpPrim + offsets['Position'], 12)), dtype=float32) if lpPrim else array([0,0,0], dtype=float32)
            else:
                lpHeadPos = array([0, 0, 0], dtype=float32)
            if now % 10 < 0.1:
                self._entity_cache = {k: v for k, v in self._entity_cache.items() if now < v['expires']}
            closest_dist = float('inf')
            closest_screen = None
            for child in get_children(plrsAddr, offsets['Children']):
                try:
                    if child == lpAddr: continue
                    if IGNORE_TEAM:
                        team = mem.read_int8(child + offsets['Team'])
                        if team == lpTeam and team > 0: continue
                    cached = self._get_cached_entity(child, now)
                    if cached:
                        char, hum, head, hrp = cached['char'], cached['hum'], cached['head'], cached['hrp']
                    else:
                        char = mem.read_int8(child + offsets['ModelInstance'])
                        if not char: continue
                        hum = find_first_child_of_class(char, 'Humanoid', offsets['Children'])
                        head = find_first_child(char, 'Head', offsets['Name'], offsets['Children'])
                        hrp = find_first_child(char, 'HumanoidRootPart', offsets['Name'], offsets['Children'])
                        self._set_cached_entity(child, {'char': char, 'hum': hum, 'head': head, 'hrp': hrp}, now)
                    if not char or not hum: continue
                    health = mem.read_float(hum + offsets['Health'])
                    if IGNORE_DEAD and health <= 0: continue
                    health = max(0.0, min(100.0, health))
                    if not head: continue
                    head_prim = mem.read_int8(head + offsets['Primitive'])
                    if not head_prim: continue
                    head_pos = array(unpack("<fff", mem.read(head_prim + offsets['Position'], 12)), dtype=float32)
                    distance = int(math.sqrt(sum((head_pos - lpHeadPos) ** 2)))
                    if HIDE_DISTANCE and distance > MAX_DISTANCE: continue
                    screen_head = world_to_screen(head_pos, view_proj, self.width(), self.height())
                    if not screen_head: continue
                    try:
                        if aimbot_enabled and features_enabled:
                            float_screen = world_to_screen_float(head_pos, view_proj, self.width(), self.height())
                            if float_screen:
                                cursor_global = POINT()
                                windll.user32.GetCursorPos(byref(cursor_global))
                                cursor_local = self.mapFromGlobal(QPoint(cursor_global.x, cursor_global.y))
                                dx = float_screen[0] - cursor_local.x()
                                dy = float_screen[1] - cursor_local.y()
                                dist = math.hypot(dx, dy)
                                if dist < closest_dist and dist <= AIMBOT_FOV_SIZE:
                                    closest_dist = dist
                                    closest_screen = float_screen
                    except Exception:
                        pass
                    hrp_pos = None
                    parts = [screen_head]
                    if hrp:
                        hrp_prim = mem.read_int8(hrp + offsets['Primitive'])
                        if hrp_prim:
                            hrp_pos = array(unpack("<fff", mem.read(hrp_prim + offsets['Position'], 12)), dtype=float32)
                            hrp_screen = world_to_screen(hrp_pos, view_proj, self.width(), self.height())
                            if hrp_screen: parts.append(hrp_screen)
                    if len(parts) < 2: continue
                    box3d_pts = None
                    if ESP_3D_BOX and hrp_pos is not None:
                        cx, cy_hrp, cz = float(hrp_pos[0]), float(hrp_pos[1]), float(hrp_pos[2])
                        top_y = float(head_pos[1]) + 0.6
                        bot_y = cy_hrp - 3.2
                        hw, hd = 1.5, 1.0
                        corners_3d = [
                            [cx-hw, top_y, cz-hd], [cx+hw, top_y, cz-hd],
                            [cx+hw, top_y, cz+hd], [cx-hw, top_y, cz+hd],
                            [cx-hw, bot_y, cz-hd], [cx+hw, bot_y, cz-hd],
                            [cx+hw, bot_y, cz+hd], [cx-hw, bot_y, cz+hd],
                        ]
                        projected = [world_to_screen(c, view_proj, self.width(), self.height()) for c in corners_3d]
                        if all(p is not None for p in projected): box3d_pts = projected
                    pad = 5
                    min_x = min(p[0] for p in parts) - pad
                    min_y = min(p[1] for p in parts) - pad
                    max_x = max(p[0] for p in parts) + pad
                    max_y = max(p[1] for p in parts) + pad
                    self.esp_data.append({
                        'box': [int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y)],
                        'box3d': box3d_pts,
                        'name': get_name(child, offsets['Name']),
                        'health': health,
                        'distance': distance,
                        'screen_pos': screen_head,
                    })
                except: continue
            if closest_screen:
                self.run_aimbot(closest_screen)
        except: pass
        self.update()
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        if not ENABLE_ESP or not features_enabled: painter.end(); return
        # ==========================================
        # DRAW FOV CIRCLE
        # ==========================================
        if aimbot_enabled:
            try:
                cursor_global = POINT()
                windll.user32.GetCursorPos(byref(cursor_global))
                cursor_local = self.mapFromGlobal(QPoint(cursor_global.x, cursor_global.y))
                # MAKE SURE YOU UNPACK THE LIST LIKE THIS! DO NOT PASS THE LIST TO QColor!
                r, g, b, a = AIMBOT_FOV_COLOR
                pen = QPen(QColor(r, g, b, a))
                pen.setWidth(1)
                pen.setStyle(Qt.DashLine)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                radius = int(AIMBOT_FOV_SIZE)
                painter.drawEllipse(
                    int(cursor_local.x() - radius), int(cursor_local.y() - radius),
                    radius * 2, radius * 2
                )
            except Exception:
                pass
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(self._font)
        pen = QPen()
        pen.setWidth(ESP_BOX_THICKNESS)
        for entry in self.esp_data:
            box = entry.get('box')
            if not box: continue
            x, y, w, h = box
            name, health, distance, screen_pos = entry.get('name', ''), entry.get('health', 100), entry.get('distance', 0), entry.get('screen_pos')
            if not screen_pos: continue
            if ESP_SHOW_BOX:
                r, g, b, a = ESP_BOX_COLOR
                pen.setColor(QColor(r, g, b, a)); painter.setPen(pen); painter.setBrush(Qt.NoBrush)
                if ESP_CORNER_BOX:
                    corner = max(6, int(h * 0.2))
                    # top-left
                    painter.drawLine(int(x), int(y), int(x + corner), int(y)); painter.drawLine(int(x), int(y), int(x), int(y + corner))
                    # top-right
                    painter.drawLine(int(x + w - corner), int(y), int(x + w), int(y)); painter.drawLine(int(x + w), int(y), int(x + w), int(y + corner))
                    # bottom-left
                    painter.drawLine(int(x), int(y + h - corner), int(x), int(y + h)); painter.drawLine(int(x), int(y + h), int(x + corner), int(y + h))
                    # bottom-right
                    painter.drawLine(int(x + w - corner), int(y + h), int(x + w), int(y + h)); painter.drawLine(int(x + w), int(y + h - corner), int(x + w), int(y + h))
                else:
                    painter.drawRect(int(x), int(y), int(w), int(h))
            if ESP_SHOW_TRACER:
                r, g, b, a = ESP_TRACER_COLOR
                pen.setWidth(1); pen.setColor(QColor(r, g, b, a)); painter.setPen(pen)
                painter.drawLine(int(self.startLineX), int(self.startLineY), int(screen_pos[0]), int(screen_pos[1]))
                pen.setWidth(ESP_BOX_THICKNESS)
            if ESP_SHOW_HEALTH:
                bar_w, bar_x, bar_y = 4, x - 6, y
                filled = int((health / 100.0) * h)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(20, 20, 20, 200)))
                painter.drawRect(bar_x, bar_y, bar_w, h)
                if ESP_DYNAMIC_HEALTH_COLOR:
                    green, red = int(health * 2.55), 255 - int(health * 2.55)
                    fill_color = QColor(red, green, 0, 255)
                else:
                    r, g, b, a = ESP_HEALTH_COLOR; fill_color = QColor(r, g, b, a)
                painter.setBrush(QBrush(fill_color))
                painter.drawRect(bar_x, bar_y + h - filled, bar_w, filled)
                painter.setBrush(Qt.NoBrush)
            if ESP_SHOW_NAME and name:
                r, g, b, a = ESP_NAME_COLOR
                pen.setWidth(1); pen.setColor(QColor(r, g, b, a)); painter.setPen(pen)
                painter.drawText(int(x + w / 2), int(y - 5), name)
            if ESP_SHOW_DISTANCE:
                r, g, b, a = ESP_DISTANCE_COLOR
                pen.setColor(QColor(r, g, b, a)); painter.setPen(pen)
                painter.drawText(int(x + w / 2), int(y + h + 15), f"{distance}m")
        painter.end()
# ====================================
# HOTKEY HANDLER
# ====================================
def hotkey_listener():
    global features_enabled, aimbot_enabled
    P_KEY = 0x50
    V_KEY = 0x56
    INSERT_KEY = 0x2D
    last_p = False
    last_v = False
    last_ins = False
    check_cnt = 0
    while mem.process_id == 0: sleep(0.1)
    roblox_pid = mem.process_id
    log(f'[+] Hotkey listener started (PID: {roblox_pid})')
    log('[*] P = toggle ESP | V = toggle Aimbot | INSERT to quit')
    while True:
        try:
            check_cnt += 1
            if check_cnt >= 20:
                check_cnt = 0
                try:
                    proc = Process(roblox_pid)
                    if not proc.is_running(): raise NoSuchProcess(roblox_pid)
                except (NoSuchProcess, Exception):
                    log('[!] Roblox was closed - exiting...')
                    sleep(1)
                    sys.exit(0)
            cur_p   = (windll.user32.GetAsyncKeyState(P_KEY)      & 0x8000) != 0
            cur_v   = (windll.user32.GetAsyncKeyState(V_KEY)      & 0x8000) != 0
            cur_ins = (windll.user32.GetAsyncKeyState(INSERT_KEY) & 0x8000) != 0
            if cur_p and not last_p:
                features_enabled = not features_enabled
                log(f'[*] Features {"ENABLED" if features_enabled else "DISABLED"}')
            if cur_v and not last_v:
                aimbot_enabled = not aimbot_enabled
                log(f'[*] Aimbot {"ENABLED" if aimbot_enabled else "DISABLED"}')
            if cur_ins and not last_ins:
                log('[*] INSERT pressed - closing...')
                sys.exit(0)
            last_p   = cur_p
            last_v   = cur_v
            last_ins = cur_ins
        except SystemExit: raise
        except: pass
        sleep(0.05)
# ====================================
# MAIN
# ====================================
if __name__ == "__main__":
    try:
        Process(os.getpid()).nice(HIGH_PRIORITY_CLASS)
    except: pass
    log('================')
    log('     OMEGA')
    log('================')
    log(f'ESP: {"✓" if ENABLE_ESP else "✗"}')
    log('================')
    init_injection()
    Thread(target=hotkey_listener, daemon=True).start()
    app = QApplication([])
    esp_overlay = None
    if ENABLE_ESP:
        esp_overlay = ESPOverlay()
        log('[+] ESP Overlay Active')
        log('[*] Press P to toggle ESP | E to toggle Aimbot | INSERT to quit')
    sys.exit(app.exec_())

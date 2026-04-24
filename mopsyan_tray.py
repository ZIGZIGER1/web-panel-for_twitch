from __future__ import annotations

import ctypes
import time
import webbrowser
from ctypes import wintypes
from pathlib import Path

from constants import APP_TITLE
from utils import user_data_dir
from web_runtime import WebRuntime


ERROR_ALREADY_EXISTS = 183

WM_DESTROY = 0x0002
WM_TIMER = 0x0113
WM_CLOSE = 0x0010
WM_CONTEXTMENU = 0x007B
WM_DRAWITEM = 0x002B
WM_MEASUREITEM = 0x002C
WM_USER = 0x0400
WM_NULL = 0x0000
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205

IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIM_SETVERSION = 0x00000004

NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_INFO = 0x00000010

NOTIFYICON_VERSION_4 = 4
NIIF_NONE = 0x00000000

TPM_LEFTALIGN = 0x0000
TPM_BOTTOMALIGN = 0x0020
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100

MF_STRING = 0x0000
MF_OWNERDRAW = 0x0100
MF_SEPARATOR = 0x0800

IDI_APPLICATION = 32512

TRAY_CALLBACK = WM_USER + 20
TIMER_ID = 1
TIMER_MS = 1200

MENU_OPEN_BROWSER = 101
MENU_EXIT = 102

ODT_MENU = 1
ODS_SELECTED = 0x0001

COLOR_MENU = 4
COLOR_MENUTEXT = 7
COLOR_HIGHLIGHT = 13
COLOR_HIGHLIGHTTEXT = 14

DT_LEFT = 0x0000
DT_VCENTER = 0x0004
DT_SINGLELINE = 0x0020
DT_NOPREFIX = 0x0800

TRANSPARENT = 1


user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

user32.CreatePopupMenu.restype = wintypes.HMENU
user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
user32.AppendMenuW.restype = wintypes.BOOL
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.DestroyMenu.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    ctypes.c_void_p,
]
user32.TrackPopupMenu.restype = wintypes.UINT
user32.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH]
user32.FillRect.restype = ctypes.c_int
user32.DrawTextW.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.RECT), wintypes.UINT]
user32.DrawTextW.restype = ctypes.c_int
user32.GetSysColorBrush.argtypes = [ctypes.c_int]
user32.GetSysColorBrush.restype = wintypes.HBRUSH
user32.GetSysColor.argtypes = [ctypes.c_int]
user32.GetSysColor.restype = wintypes.DWORD
gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
gdi32.SetTextColor.restype = wintypes.COLORREF
gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.SetBkMode.restype = ctypes.c_int


WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
        ("lPrivate", wintypes.DWORD),
    ]


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class MEASUREITEMSTRUCT(ctypes.Structure):
    _fields_ = [
        ("CtlType", wintypes.UINT),
        ("CtlID", wintypes.UINT),
        ("itemID", wintypes.UINT),
        ("itemWidth", wintypes.UINT),
        ("itemHeight", wintypes.UINT),
        ("itemData", ctypes.c_size_t),
    ]


class DRAWITEMSTRUCT(ctypes.Structure):
    _fields_ = [
        ("CtlType", wintypes.UINT),
        ("CtlID", wintypes.UINT),
        ("itemID", wintypes.UINT),
        ("itemAction", wintypes.UINT),
        ("itemState", wintypes.UINT),
        ("hwndItem", wintypes.HWND),
        ("hDC", wintypes.HDC),
        ("rcItem", wintypes.RECT),
        ("itemData", ctypes.c_size_t),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", GUID),
        ("hBalloonIcon", wintypes.HICON),
    ]


class TrayController:
    def __init__(self) -> None:
        self.base_dir = Path(__file__).resolve().parent
        self.icon_path = self.base_dir / "z_icon.ico"
        self.log_path = user_data_dir(APP_TITLE) / "tray.log"
        self.runtime = WebRuntime()
        self.hinstance = kernel32.GetModuleHandleW(None)
        self.class_name = "ZigZigerWebPanelTray"
        self.hwnd: wintypes.HWND | None = None
        self.hicon: wintypes.HICON | None = None
        self.nid = NOTIFYICONDATAW()
        self.wndproc = WNDPROC(self._window_proc)
        self.running = False
        self.menu_labels = {
            MENU_OPEN_BROWSER: "Открыть в браузере",
            MENU_EXIT: "Закрыть",
        }
        self.log("tray controller initialized")

    def log(self, message: str) -> None:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            current = self.log_path.read_text(encoding="utf-8") if self.log_path.exists() else ""
            self.log_path.write_text(current + f"[{stamp}] {message}\n", encoding="utf-8")
        except OSError:
            pass

    def tooltip_text(self) -> str:
        with self.runtime.lock:
            level = max(0.0, min(100.0, float(self.runtime.last_level_value)))
            mic_running = self.runtime.monitor.running
            chat_ready = bool(self.runtime.chat_twitch_channel)
            server_ready = bool(self.runtime.overlay_port)

        mic_text = f"Мик {level:.0f}%" if mic_running else "Мик выкл"
        chat_text = "Чат подключен" if chat_ready else "Чат не подключен"
        server_text = "Панель онлайн" if server_ready else "Панель запускается"
        return f"Web панель by ZigZiger | {server_text} | {mic_text} | {chat_text}"[:127]

    def load_icon_handle(self) -> wintypes.HICON:
        if self.icon_path.exists():
            handle = user32.LoadImageW(
                None,
                str(self.icon_path),
                IMAGE_ICON,
                0,
                0,
                LR_LOADFROMFILE | LR_DEFAULTSIZE,
            )
            if handle:
                return handle
        return user32.LoadIconW(None, ctypes.c_wchar_p(IDI_APPLICATION))

    def register_window(self) -> None:
        window_class = WNDCLASSW()
        window_class.style = 0
        window_class.lpfnWndProc = self.wndproc
        window_class.cbClsExtra = 0
        window_class.cbWndExtra = 0
        window_class.hInstance = self.hinstance
        window_class.hIcon = self.load_icon_handle()
        window_class.hCursor = None
        window_class.hbrBackground = None
        window_class.lpszMenuName = None
        window_class.lpszClassName = self.class_name
        user32.RegisterClassW(ctypes.byref(window_class))

        self.hwnd = user32.CreateWindowExW(
            0,
            self.class_name,
            self.class_name,
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            self.hinstance,
            None,
        )
        if not self.hwnd:
            raise RuntimeError("Не удалось создать скрытое окно трея.")

    def init_tray_icon(self) -> None:
        if not self.hwnd:
            raise RuntimeError("Окно трея не создано.")

        self.hicon = self.load_icon_handle()
        self.nid = NOTIFYICONDATAW()
        self.nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self.nid.hWnd = self.hwnd
        self.nid.uID = 1
        self.nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self.nid.uCallbackMessage = TRAY_CALLBACK
        self.nid.hIcon = self.hicon
        self.nid.szTip = self.tooltip_text()

        if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.nid)):
            raise RuntimeError("Не удалось добавить иконку в трей.")

        self.nid.uVersion = NOTIFYICON_VERSION_4
        shell32.Shell_NotifyIconW(NIM_SETVERSION, ctypes.byref(self.nid))
        user32.SetTimer(self.hwnd, TIMER_ID, TIMER_MS, None)
        self.log("tray icon added")

    def update_tray_tooltip(self) -> None:
        if not self.hwnd:
            return
        self.nid.uFlags = NIF_TIP | NIF_ICON
        self.nid.szTip = self.tooltip_text()
        self.nid.hIcon = self.hicon
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.nid))

    def show_balloon(self, title: str, message: str) -> None:
        if not self.hwnd:
            return
        self.nid.uFlags = NIF_INFO
        self.nid.szInfo = message[:255]
        self.nid.szInfoTitle = title[:63]
        self.nid.dwInfoFlags = NIIF_NONE
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.nid))

    def open_dashboard(self) -> None:
        webbrowser.open_new(self.runtime.dashboard_url)

    def stop(self) -> None:
        self.log("tray exit requested")
        self.running = False
        if self.hwnd:
            user32.DestroyWindow(self.hwnd)

    def handle_menu_command(self, command: int) -> None:
        if command == MENU_OPEN_BROWSER:
            self.open_dashboard()
        elif command == MENU_EXIT:
            self.stop()

    @staticmethod
    def tray_event_code(value: wintypes.LPARAM) -> int:
        return int(value) & 0xFFFF

    def show_menu(self) -> None:
        if not self.hwnd:
            return

        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, MF_OWNERDRAW, MENU_OPEN_BROWSER, None)
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_OWNERDRAW, MENU_EXIT, None)

        point = POINT()
        user32.GetCursorPos(ctypes.byref(point))
        user32.SetForegroundWindow(self.hwnd)
        command = user32.TrackPopupMenu(
            menu,
            TPM_LEFTALIGN | TPM_BOTTOMALIGN | TPM_RIGHTBUTTON | TPM_RETURNCMD,
            point.x,
            point.y,
            0,
            self.hwnd,
            None,
        )
        user32.DestroyMenu(menu)
        user32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        if command:
            self.handle_menu_command(command)

    def draw_menu_item(self, draw_struct: DRAWITEMSTRUCT) -> int:
        label = self.menu_labels.get(draw_struct.itemID, "")
        if not label:
            return 0

        selected = bool(draw_struct.itemState & ODS_SELECTED)
        brush = user32.GetSysColorBrush(COLOR_HIGHLIGHT if selected else COLOR_MENU)
        user32.FillRect(draw_struct.hDC, ctypes.byref(draw_struct.rcItem), brush)

        text_rect = wintypes.RECT(
            draw_struct.rcItem.left + 14,
            draw_struct.rcItem.top,
            draw_struct.rcItem.right - 10,
            draw_struct.rcItem.bottom,
        )
        gdi32.SetBkMode(draw_struct.hDC, TRANSPARENT)
        gdi32.SetTextColor(
            draw_struct.hDC,
            user32.GetSysColor(COLOR_HIGHLIGHTTEXT if selected else COLOR_MENUTEXT),
        )
        user32.DrawTextW(
            draw_struct.hDC,
            label,
            -1,
            ctypes.byref(text_rect),
            DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX,
        )
        return 1

    def measure_menu_item(self, measure_struct: MEASUREITEMSTRUCT) -> int:
        if measure_struct.itemID not in self.menu_labels:
            return 0
        measure_struct.itemWidth = 196
        measure_struct.itemHeight = 30
        return 1

    def cleanup(self) -> None:
        try:
            self.runtime.shutdown()
        except Exception:
            pass

        try:
            if self.hwnd:
                user32.KillTimer(self.hwnd, TIMER_ID)
        except Exception:
            pass

        try:
            if self.nid.hWnd:
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.nid))
        except Exception:
            pass

        try:
            if self.hicon:
                user32.DestroyIcon(self.hicon)
        except Exception:
            pass

    def _window_proc(
        self,
        hwnd: wintypes.HWND,
        msg: wintypes.UINT,
        wparam: wintypes.WPARAM,
        lparam: wintypes.LPARAM,
    ) -> int:
        if msg == WM_MEASUREITEM:
            measure_struct = ctypes.cast(lparam, ctypes.POINTER(MEASUREITEMSTRUCT)).contents
            if measure_struct.CtlType == ODT_MENU:
                return self.measure_menu_item(measure_struct)

        if msg == WM_DRAWITEM:
            draw_struct = ctypes.cast(lparam, ctypes.POINTER(DRAWITEMSTRUCT)).contents
            if draw_struct.CtlType == ODT_MENU:
                return self.draw_menu_item(draw_struct)

        if msg == TRAY_CALLBACK:
            event = self.tray_event_code(lparam)
            if event in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                self.open_dashboard()
                return 0
            if event in (WM_RBUTTONUP, WM_CONTEXTMENU):
                self.show_menu()
                return 0

        if msg == WM_TIMER and wparam == TIMER_ID:
            self.update_tray_tooltip()
            return 0

        if msg == WM_CLOSE:
            self.stop()
            return 0

        if msg == WM_DESTROY:
            self.running = False
            user32.PostQuitMessage(0)
            return 0

        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def run(self) -> None:
        self.log("tray setup start")
        self.register_window()
        self.init_tray_icon()
        self.runtime.start(open_browser_on_start=False)
        self.update_tray_tooltip()
        self.log(f"runtime online at {self.runtime.dashboard_url}")
        self.show_balloon("Web панель by ZigZiger", "Панель запущена и доступна из трея")
        self.open_dashboard()
        self.running = True

        msg = MSG()
        try:
            while self.running and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            self.cleanup()


def main() -> None:
    try:
        shell32.SetCurrentProcessExplicitAppUserModelID("ZigZiger.WebPanel")
    except Exception:
        pass

    mutex_handle = None
    try:
        mutex_handle = kernel32.CreateMutexW(None, False, "Local\\ZigZigerWebPanel")
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            webbrowser.open_new("http://127.0.0.1:8765/")
            return
    except Exception:
        mutex_handle = None

    try:
        TrayController().run()
    finally:
        if mutex_handle:
            try:
                kernel32.ReleaseMutex(mutex_handle)
                kernel32.CloseHandle(mutex_handle)
            except Exception:
                pass


if __name__ == "__main__":
    main()

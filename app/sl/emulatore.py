"""Funzioni di Windows per trovare le finestre di un processo e incastrarle nell'app (usate da melon.py)."""
import ctypes
import sys

WIN = sys.platform == "win32"
if WIN:
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
    user32.SetParent.restype = wintypes.HWND
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    GWL_STYLE = -16
    WS_CAPTION, WS_THICKFRAME, WS_SYSMENU = 0x00C00000, 0x00040000, 0x00080000
    WS_MINIMIZEBOX, WS_MAXIMIZEBOX, WS_POPUP, WS_CHILD = 0x00020000, 0x00010000, 0x80000000, 0x40000000
    WM_CLOSE = 0x0010
    SWP_NOZORDER, SWP_NOACTIVATE, SWP_FRAMECHANGED, SWP_SHOWWINDOW = 0x0004, 0x0010, 0x0020, 0x0040
    SW_HIDE, SW_SHOW = 0, 5


def finestre_del_processo(pid: int) -> list:
    """[(hwnd, titolo, area)] delle finestre visibili del processo."""
    out = []
    if not WIN:
        return out

    def cb(hwnd, _):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            r = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            out.append((hwnd, buf.value, (r.right - r.left) * (r.bottom - r.top)))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def incastra(hwnd, ospite_hwnd, w, h):
    """Rende la finestra figlia del riquadro nativo dell'app (coordinate relative al riquadro)."""
    if not WIN:
        return
    st = user32.GetWindowLongPtrW(hwnd, GWL_STYLE)
    st &= ~(WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_POPUP)
    st |= WS_CHILD
    user32.SetWindowLongPtrW(hwnd, GWL_STYLE, st)
    user32.SetParent(hwnd, ospite_hwnd)
    user32.SetWindowPos(hwnd, 0, 0, 0, w, h, SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW)


def adatta(hwnd, w, h):
    if WIN and hwnd:
        user32.SetWindowPos(hwnd, 0, 0, 0, w, h, SWP_NOZORDER | SWP_NOACTIVATE)


def sgancia(hwnd):
    if WIN and hwnd:
        user32.SetParent(hwnd, 0)

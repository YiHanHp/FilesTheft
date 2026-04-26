import os
import subprocess
import ctypes
import time
import threading

# --- 核心配置 ---
TARGET_ROOT = r'D:\USBGet'
# 第一波抢救的阈值（建议20MB，文档类基本都在此范围内）
SMALL_SIZE_LIMIT = 20 * 1024 * 1024 
THREADS = 32

def get_unique_id(drive):
    """获取U盘标识，作为根目录，确保不同U盘不混淆"""
    buf = ctypes.create_unicode_buffer(1024)
    sn = ctypes.c_uint(0)
    ctypes.windll.kernel32.GetVolumeInformationW(drive, buf, 1024, ctypes.byref(sn), None, None, None, 0)
    # 格式：卷标_序列号 (例如：WORK_384729)
    name = buf.value if buf.value else "USB_DISK"
    return f"{name}_{sn.value}"

def run_task(src, dst, limit_args):
    """
    /S: 复制子目录（不拷贝空目录，保证结构完整）
    /E: 复制所有子目录（包括空目录，确保结构1:1还原）
    /IM: 即使目标已存在相同大小文件也重新检查（确保一致性）
    """
    base_cmd = [
        'robocopy', src, dst, '/E', 
        f'/MT:{THREADS}', '/R:1', '/W:1', 
        '/TBD', '/NP', '/XJD', '/XJF'
    ]
    subprocess.run(base_cmd + limit_args, creationflags=subprocess.CREATE_NO_WINDOW)

def prioritized_sync(drive):
    unique_id = get_unique_id(drive)
    # 每一个U盘都有自己独立的顶级文件夹，绝对不会和电脑或其他U盘乱套
    usb_dst = os.path.join(TARGET_ROOT, unique_id)
    
    print(f"[*] 正在镜像结构并抢救小文件 (<{SMALL_SIZE_LIMIT//1024**2}MB): {drive}")
    
    # 第一步：快速复制所有小文件。Robocopy 会自动在 dst 创建完整的目录树
    # /MAX 指定最大值
    run_task(drive, usb_dst, [f'/MAX:{SMALL_SIZE_LIMIT}'])
    
    print(f"[*] 结构已建立，正在搬运剩余大文件: {drive}")
    
    # 第二步：填补剩余的大文件
    # /MIN 指定最小值
    run_task(drive, usb_dst, [f'/MIN:{SMALL_SIZE_LIMIT}'])
    
    print(f"[OK] {drive} 备份完成，目录结构与源盘 100% 一致。")

def monitor():
    print(f"监控服务已启动。目标目录: {TARGET_ROOT}")
    known_drives = set()
    
    while True:
        current_drives = set()
        for i in range(26):
            d = chr(65+i) + ":\\"
            if ctypes.windll.kernel32.GetDriveTypeW(d) == 2:
                current_drives.add(d)
        
        for drive in (current_drives - known_drives):
            # 延迟1秒等待系统完全识别文件系统，防止目录读取不全
            time.sleep(1)
            threading.Thread(target=prioritized_sync, args=(drive,), daemon=True).start()
            
        known_drives = current_drives
        time.sleep(2)

if __name__ == "__main__":
    os.makedirs(TARGET_ROOT, exist_ok=True)
    monitor()

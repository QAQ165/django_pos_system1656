import os
import sys
import time
import socket
import webbrowser
import threading
from django.core.management import execute_from_command_line

# ===================== 配置项 =====================
PROJECT_SETTINGS = "pos_system.settings"  # 这里改成你的Django项目名
HOST = "0.0.0.0"
PORT = 8000
URL = f"http://127.0.0.1:{PORT}"
# ===================================================

# 单例运行：防止重复启动
def is_running():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        result = sock.connect_ex(("127.0.0.1", PORT))
        sock.close()
        return result == 0
    except:
        return False

# 只打开一次浏览器
def open_browser_once():
    try:
        webbrowser.open(URL, new=1, autoraise=True)
        print(f" 浏览器已打开，系统访问地址：{URL}")
    except Exception as e:
        print(f"  浏览器自动打开失败，请手动访问：{URL}")

# 启动服务器
def start_server():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", PROJECT_SETTINGS)
    print("=" * 50)
    print(" POS零售管理系统 正在启动...")
    print(f" 服务地址：{URL}")
    print("=" * 50)

    # 启动备份调度器（延迟导入，在Django设置加载后）
    try:
        import django
        django.setup()  # 确保Django应用完全加载
        from system.backup_scheduler import backup_scheduler
        backup_scheduler.start()
        print(" 定时备份调度器已启动")
    except Exception as e:
        print(f" 启动备份调度器失败: {str(e)}")

    try:
        # 启动 Django 服务器（关键：--noreload 必须加）
        execute_from_command_line([
            "run.py", "runserver",
            f"{HOST}:{PORT}",
            "--noreload",
            "--insecure"
        ])
    except KeyboardInterrupt:
        print("\n 服务已手动停止")
    except Exception as e:
        print(f"\n 服务启动失败：{str(e)}")
        input("按回车键退出...")

# 主程序
def main():
    # 判断是否重复启动
    if is_running():
        print(" 系统已在运行中，请勿重复启动！")
        time.sleep(2)
        return

    print(" 启动检查完成，未发现重复进程")

    # 延迟打开浏览器（确保服务先启动）
    threading.Timer(1.8, open_browser_once).start()

    # 启动服务
    start_server()

if __name__ == "__main__":
    main()

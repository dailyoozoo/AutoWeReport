import os
import sys
import time
import socket
import webbrowser
import subprocess
from pathlib import Path

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def main():
    print("="*50)
    print(" 🚀 AI Work Assistant Dashboard - 启动程序 ")
    print("="*50)
    
    port = 8080
    
    # 强制清理可能的旧进程
    if is_port_in_use(port):
        print(f"[Warning] 端口 {port} 已被占用。此服务可能已经在运行中。")
        print(" -> 正在尝试直接打开浏览器...")
    else:
        print("[System] 正在启动后台 Web 核心加速引擎...")
        
        # 使用 uvicorn 启动 src.web_server:app
        script_dir = Path(__file__).parent.absolute()
        src_dir = script_dir / 'src'
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(src_dir)
        
        # 以子进程不阻塞地方式启动服务器
        server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.web_server:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=str(script_dir),
            env=env
        )
        
        # 等待服务器初始化
        print("[System] 等待服务预热响应中...")
        for _ in range(15):
            time.sleep(1)
            if is_port_in_use(port):
                break
        
        if not is_port_in_use(port):
            print("[Error] 致命错误：FastAPI Web 服务未能成功启动，引流失败！")
            server_process.kill()
            sys.exit(1)
            
    # 启动浏览器
    url = f"http://127.0.0.1:{port}/web/index.html"
    print(f"\n[Success] 系统启动成功！正在为您自动打开浏览器控制面板：\n {url}")
    webbrowser.open(url)
    
    print("\n⚠️ 请保持这个黑色控制台窗口开启。若要关闭系统，请随时按 Ctrl+C。")
    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        print("\n[Exit] 接收到退出信号，正在关闭系统核心进程...")
        if 'server_process' in locals():
            server_process.terminate()

if __name__ == "__main__":
    main()

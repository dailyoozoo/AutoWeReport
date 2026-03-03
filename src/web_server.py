import os
import sys
import json
import asyncio
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv, set_key

PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / '.env'
sys.path.append(str(PROJECT_ROOT / 'src'))

app = FastAPI(title="AI Work Assistant API")

# 挂载前端静态文件
app.mount("/web", StaticFiles(directory=str(PROJECT_ROOT / "web"), html=True), name="web")

# 全局队列
log_queue = asyncio.Queue()

class ConfigModel(BaseModel):
    USER_REAL_NAME: Optional[str] = ""
    USER_WX_NICKNAME: Optional[str] = ""
    NVIDIA_BASE_URL: Optional[str] = ""
    NVIDIA_API_KEY: Optional[str] = ""
    NVIDIA_MODEL: Optional[str] = ""
    WECHAT_SOURCE_DIR: Optional[str] = ""

async def push_log(message: str, is_error=False):
    data = { "type": "error" if is_error else "log", "content": message }
    await log_queue.put(data)

async def push_report(md_content: str):
    data = { "type": "report_done", "content": md_content }
    await log_queue.put(data)

@app.get("/api/config")
async def get_config():
    load_dotenv(ENV_PATH)
    return {
        "USER_REAL_NAME": os.getenv("USER_REAL_NAME", "宋代立"),
        "USER_WX_NICKNAME": os.getenv("USER_WX_NICKNAME", "小兄弟"),
        "NVIDIA_BASE_URL": os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        "NVIDIA_API_KEY": os.getenv("NVIDIA_API_KEY", ""),
        "NVIDIA_MODEL": os.getenv("NVIDIA_MODEL", "moonshotai/kimi-k2.5"),
        "WECHAT_SOURCE_DIR": os.getenv("WECHAT_SOURCE_DIR", ""),
    }

@app.post("/api/config")
async def save_config(config: ConfigModel):
    if not ENV_PATH.exists():
        ENV_PATH.touch()
    
    config_dict = config.dict(exclude_unset=True)
    for key, value in config_dict.items():
        set_key(str(ENV_PATH), key, value)
        os.environ[key] = value
        
    return {"message": "Config saved"}

@app.get("/api/stream")
async def sse_logs(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                data = await asyncio.wait_for(log_queue.get(), timeout=1.0)
                yield f"data: {json.dumps(data)}\n\n"
            except asyncio.TimeoutError:
                yield f": heartbeat\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/open_dir")
async def open_dir():
    reports_dir = PROJECT_ROOT / 'workspace' / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)
    os.startfile(str(reports_dir))
    return {"message": "opened"}

@app.get("/api/browse")
async def browse_folder():
    """唤起 Windows 原生物理文件夹选择器"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # 必须在主线程外跑防止阻塞 FastAPI，或者简单的使用新进行程/隐藏根窗口
        root = tk.Tk()
        root.attributes('-topmost', True)
        root.withdraw() # 隐藏主窗口
        
        folder_path = filedialog.askdirectory(title="选择微信原始资料目录(包含 Msg_XXX.db 的上级目录)")
        root.destroy()
        
        if folder_path:
            return {"path": folder_path.replace('/', '\\')}
        return {"path": ""}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/extract")
async def trigger_extract():
    async def background_task():
        await push_log("[System] 初始化合并引擎流水线...")
        
        old_stdout = sys.stdout
        class LogInterceptor:
            def write(self, s):
                if s.strip():
                    asyncio.create_task(push_log(s.strip()))
            def flush(self): pass

        sys.stdout = LogInterceptor()
        
        try:
            source_dir = os.getenv("WECHAT_SOURCE_DIR", "").strip()
            # 硬编码默认的解密结果保存地，不暴露给用户
            wechat_dir = str(PROJECT_ROOT / 'data' / 'wechat' / 'decrypted')
            output_file = PROJECT_ROOT / 'data' / 'merged_chat_data.json'
            
            # 第一阶段：活体提取与解密
            if source_dir and os.path.exists(source_dir):
                await push_log(f"\n[Decrypting] 发现原址寄生数据配置 ({source_dir})，尝试提取...")
                from extractors.wechat_extractor import create_config, extract_keys, decrypt_databases
                
                # 配置解密器
                create_config(source_dir)
                
                # 尝试注入读取秘钥
                if extract_keys():
                    await push_log("\n[Decrypting] 内存注入拿取微信密钥成功，开始后台还原 sqlite...")
                    if decrypt_databases():
                        await push_log("\n[Success] 数据库物理文件全量解密成功！\n")
                    else:
                        await push_log("\n[Error] 本地微信数据还原失败。", is_error=True)
                        return
                else:
                    await push_log("\n[Failed] 嗅探活体微信密钥失败。请确认微信目前是否保持前台登录状态、或者您是否以 Administrator 管理员最高权限运行本脚本！", is_error=True)
                    return
            else:
                await push_log("[Skip] 未检测到物理原始微信配置参数，路过解密环节...")

            # 第二阶段：格式清洗与重组
            from formatters.data_formatter import DataFormatter
            await push_log(f"\n[DB Mount] 开始从已解密的数据点 {wechat_dir} 转储最新业务数据...")
            conversations = DataFormatter.merge_all(wechat_db_dir=wechat_dir, days_limit=7)
            DataFormatter.save_merged(conversations, str(output_file))
            
            await push_log(f"\n[Success] SQLite 表结构降层处理并聚合完毕.")
            await push_report("✅ **原生数据挂载及同步完毕**\n数据源提取已完成（包含了活体进程的提取及格式化重组），暂无报告内容，请点击生成报告。")
        except Exception as e:
            await push_log(f"\n[Fatal Error] 提取链路发生崩溃: {e}", is_error=True)
            import traceback
            traceback.print_exc()
        finally:
            sys.stdout = old_stdout
            
    asyncio.create_task(background_task())
    return {"status": "started"}

@app.post("/api/generate")
async def trigger_generate(range: str = '1d'):
    async def background_task():
        import io
        from ai_planner.data_cleaner import filter_messages
        from ai_planner.prompts import GENERAL_REPORT_PROMPT
        from ai_planner.llm_client import generate_plan
        from main_agent import load_data, save_report
        
        await push_log(f"[Scheduler] 开始分析... 选定范围: {range}")
        
        old_stdout = sys.stdout
        class LogInterceptor:
            def write(self, s):
                if s.strip():
                    asyncio.create_task(push_log(s.strip()))
            def flush(self): pass
        sys.stdout = LogInterceptor()
        
        try:
            DATA_FILE_PATH = Path('D:/其他/gmini/工作安排工具/data/merged_chat_data.json')
            now = datetime.now()
            
            days = 1
            if range == '3d': days = 3
            elif range == '7d': days = 7
                
            start_time = now - timedelta(days=days)
            
            await push_log("[Filter] 加载并清洗聊天数据...")
            conversations = load_data(DATA_FILE_PATH)
            clean_text = filter_messages(conversations, start_time, now)
            
            if not clean_text:
                await push_log("[Warning] 空管道：在此过滤时间段内没有记录。")
                await push_report(f"⚠️ 在过去的 {days} 天内，没有找到任何有效的聊天记录。")
                sys.stdout = old_stdout
                return
            
            await push_log(f"[LLM] 请求远端大模型进行深度逻辑梳理 (Token: {len(clean_text)})")
            
            real_name = os.getenv("USER_REAL_NAME", "未知")
            wx_nick = os.getenv("USER_WX_NICKNAME", "未知")
            
            # 使用统一通用汇报 Prompt
            final_prompt = GENERAL_REPORT_PROMPT.replace("[时间范围]", f"过去 {days} 天")
            final_prompt = final_prompt.replace("[真实姓名]", real_name)
            final_prompt = final_prompt.replace("[微信昵称]", wx_nick)
            
            # 临时将单模型环境变量映射到脚本现有的环境键上，以便 llm_client 跑通
            os.environ["NVIDIA_MODEL_WEEKLY"] = os.getenv("NVIDIA_MODEL", "moonshotai/kimi-k2.5")
            
            report_content = generate_plan(prompt=final_prompt, content=clean_text, is_weekly=True)
            
            if report_content:
                # 依然复用 save_report 将报告存入 weekly 目录或者按范围命名
                save_report(report_content, is_weekly=(days>1))
                await push_report(report_content)
                
        except Exception as e:
            await push_log(f"错误: {str(e)}", is_error=True)
        finally:
            sys.stdout = old_stdout
            await push_log("[System] 处理完成。")
            
    asyncio.create_task(background_task())
    return {"status": "started"}

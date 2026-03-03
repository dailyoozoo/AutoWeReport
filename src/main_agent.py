"""
工作安排工具 - AI 工作规划与总结入口
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到 sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from ai_planner.data_cleaner import filter_messages
from ai_planner.prompts import DAILY_PROMPT, WEEKLY_PROMPT
from ai_planner.llm_client import generate_plan

DATA_FILE_PATH = Path('D:/其他/gmini/工作安排工具/data/merged_chat_data.json')
REPORTS_DIR = Path('D:/其他/gmini/工作安排工具/workspace/reports')

def load_data(file_path: Path):
    if not file_path.exists():
        print(f"❌ 数据文件不存在: {file_path}")
        print("请先通过微信数据提取和 data_formatter.py 生成合并数据。")
        sys.exit(1)
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('conversations', [])
    except Exception as e:
        print(f"❌ 读取数据失败: {e}")
        sys.exit(1)

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def save_report(content: str, is_weekly: bool):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    now = datetime.now()
    if is_weekly:
        filename = f"weekly_report_{now.strftime('%Y_W%W')}.md" # 比如 2026_W09.md
    else:
        filename = f"daily_plan_{now.strftime('%Y%m%d')}.md"
        
    filepath = REPORTS_DIR / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
    return filepath

def main():
    parser = argparse.ArgumentParser(description='AI 工作安排与总结生成工具')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--daily', action='store_true', help='生成每日工作规划')
    group.add_argument('--weekly', action='store_true', help='生成每周工作总结')
    
    args = parser.parse_args()
    
    print("="*50)
    print("  AI 工作助手启动")
    print("="*50)
    
    # 1. 确定时间范围
    now = datetime.now()
    if args.daily:
        # 每日计划：看过去 24 小时（昨天此时到现在）的消息
        start_time = now - timedelta(days=1)
        prompt_template = DAILY_PROMPT
        print(f"模式: [每日工作规划]")
        print(f"数据范围: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {now.strftime('%H:%M')}")
    else:
        # 每周总结：看过去 7 天的消息
        start_time = now - timedelta(days=7)
        prompt_template = WEEKLY_PROMPT
        print(f"模式: [每周工作总结]")
        print(f"数据范围: {start_time.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}")
        
    # 2. 读取并清洗数据
    print("\n⏳ 正在读取并清洗聊天记录...")
    conversations = load_data(DATA_FILE_PATH)
    clean_text = filter_messages(conversations, start_time, now)
    
    if not clean_text:
        print("\n⚠️ 在这期间没有找到任何相关的聊天记录。")
        sys.exit(0)
        
    print(f"✅ 清洗完成。提取出有效字符数: {len(clean_text)}")
    if len(clean_text) > 100000:
        print("⚠️ 警告: 提取的文字量非常大，大模型可能会丢失焦点或达到 Token 限制。")
        print("   建议：在 .env 文件中优化 FILTER_KEYWORDS 以过滤无关人员/水群。")
        
    # 3. 请求大模型
    print("\n🚀 正在请求 AI 大语言模型进行分析...")
    
    real_name = os.getenv("USER_REAL_NAME", "未知")
    wx_nick = os.getenv("USER_WX_NICKNAME", "未知")
    
    # 替换 Prompt 中的占位符
    final_prompt = prompt_template.replace("[今天日期]", now.strftime('%Y-%m-%d'))
    final_prompt = final_prompt.replace("[真实姓名]", real_name)
    final_prompt = final_prompt.replace("[微信昵称]", wx_nick)
    
    report_content = generate_plan(prompt=final_prompt, content=clean_text, is_weekly=args.weekly)
    
    if report_content:
        # 4. 保存报告
        report_path = save_report(report_content, is_weekly=args.weekly)
        print(f"\n🎉 报告生成成功！\n📂 已保存至: {report_path}")

if __name__ == '__main__':
    main()

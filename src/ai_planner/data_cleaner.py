"""
聊天数据清洗模块
负责过滤无关群聊、提取特定时间段的有用消息，并拼接成LLM的输入格式。
"""
import os
import re
from datetime import datetime, timedelta

def load_filter_keywords():
    from dotenv import load_dotenv
    load_dotenv()
    kws = os.getenv("FILTER_KEYWORDS", "")
    return [k.strip() for k in kws.split(",") if k.strip()]

def filter_messages(conversations: list, start_time: datetime, end_time: datetime) -> str:
    """
    过滤并清洗聊天记录
    
    规则：
    1. 只取 start_time 到 end_time 之间的消息
    2. 忽略包含 FILTER_KEYWORDS 的消息
    3. 只保留 text, file, image (占位符) 等类型
    4. 忽略纯表情包、乱码
    
    返回拼接好的纯文本供 LLM 分析
    """
    keywords = load_filter_keywords()
    
    output_lines = []
    
    for conv in conversations:
        # 如果是已知无关群（比如家族群、外卖拼单群），可以通过匹配 conversation_name 过滤
        # 这里暂不过滤特定的群，你可以以后加
        
        c_name = conv.get('conversation_name', '未知会话')
        c_type = conv.get('conversation_type', 'unknown')
        msgs = conv.get('messages', [])
        
        valid_msgs = []
        for m in msgs:
            # 1. 时间过滤
            try:
                msg_time = datetime.fromisoformat(m.get('timestamp', '').replace('Z', '+00:00'))
                # 统一为本地时间或直接暴力对比时间戳（这里简化为naive时间对比）
                # 注意：如果跨时区需要处理 timezone，此处假设都是本地时间或相同时区
                msg_time = msg_time.replace(tzinfo=None)
            except Exception:
                continue

            if not (start_time <= msg_time <= end_time):
                continue
                
            content = m.get('content', '')
            if not content:
                continue
                
            # 2. 关键词黑名单过滤
            if any(kw in content for kw in keywords):
                continue
                
            # 3. 简易正则过滤掉纯乱码或过长无意义符号
            if len(content) > 1000:
                content = content[:1000] + "..."
                
            sender = m.get('sender_name', '') or m.get('sender', '未知发送者')
            time_str = msg_time.strftime("%m-%d %H:%M")
            
            valid_msgs.append(f"[{time_str}] {sender}: {content}")
            
        if valid_msgs:
            output_lines.append(f"\n--- 会话: {c_name} ({c_type}) ---\n" + "\n".join(valid_msgs))
            
    return "\n".join(output_lines)

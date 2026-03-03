"""
AI 大模型调用客户端
封装对 NVIDIA API 的请求
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 读取配置
API_KEY = os.getenv("NVIDIA_API_KEY")
BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL_DAILY = os.getenv("NVIDIA_MODEL_DAILY", "moonshotai/kimi-k2.5")
MODEL_WEEKLY = os.getenv("NVIDIA_MODEL_WEEKLY", "z-ai/glm4.7")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)

def generate_plan(prompt: str, content: str, is_weekly: bool = False) -> str:
    """调用大模型生成内容 (原生存取)"""
    model_name = MODEL_WEEKLY if is_weekly else MODEL_DAILY
    
    url = f"{BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"=== 聊天记录开始 ===\n{content}\n=== 聊天记录结束 ===\n请基于上述记录提取任务。"}
        ],
        "temperature": 0.2,
        "max_tokens": 8192,
        "stream": True
    }
    
    try:
        import requests
        import json
        print("\n⏳ 正在思考...\n" + "-"*50)
        
        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()
        
        full_result = ""
        reasoning_result = ""
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            
                            reasoning = delta.get("reasoning_content") or ""
                            content = delta.get("content") or ""
                            
                            if reasoning:
                                print(reasoning, end="", flush=True)
                                reasoning_result += reasoning
                                
                            if content:
                                print(content, end="", flush=True)
                                full_result += content
                    except Exception:
                        pass
                        
        print("\n" + "-"*50)
        
        final_output = ""
        if reasoning_result:
            # 使用 HTML 折叠标签包装思考过程
            final_output += "<details>\n<summary>💡 点击展开 AI 深度思考过程</summary>\n\n"
            # 为了在 details 内正确渲染 markdown，加一级引用或代码块，这里直接输出
            final_output += reasoning_result + "\n\n</details>\n\n---\n\n"
            
        final_output += full_result
        return final_output
        
    except Exception as e:
        print(f"\n❌ API 请求失败: {e}")
        return ""

"""
统一数据格式化器
将 360Teams 和微信的聊天数据转换为统一格式
"""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class DataFormatter:
    """统一格式化两个数据源的消息"""

    # 已移除 360teams 处理逻辑

    @staticmethod
    def format_wechat_data(decrypted_db_dir: str, 
                           contact_db_path: Optional[str] = None,
                           days_limit: int = 7) -> list[dict]:
        """
        格式化微信解密后的数据库

        Args:
            decrypted_db_dir: wechat-decrypt 解密后的数据库目录
            contact_db_path: 联系人数据库路径（可选）
            days_limit: 只获取最近N天的消息

        Returns:
            统一格式的会话列表
        """
        decrypted_dir = Path(decrypted_db_dir)
        result = []

        # 加载联系人映射
        contacts = {}
        if contact_db_path and os.path.exists(contact_db_path):
            try:
                conn = sqlite3.connect(contact_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT UserName, NickName, Remark FROM Contact")
                for row in cursor.fetchall():
                    username, nickname, remark = row
                    contacts[username] = remark if remark else nickname
                conn.close()
            except Exception as e:
                print(f'⚠️ 加载联系人数据库失败: {e}')

        msg_dbs = sorted(decrypted_dir.glob('message/message_*.db'))
        if not msg_dbs:
            msg_dbs = sorted(decrypted_dir.glob('**/MSG*.db'))

        # 预加载 Name2Id 映射 (微信4.x)
        name2id = {}
        for db_path in msg_dbs:
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Name2Id'")
                if cursor.fetchone():
                    cursor.execute("SELECT Id, UsrName FROM Name2Id")
                    for r in cursor.fetchall():
                        name2id[r[0]] = r[1]
                conn.close()
            except Exception:
                pass

        # 计算时间截止点
        cutoff_ts = 0
        if days_limit > 0:
            cutoff_ts = int((datetime.now().timestamp() - days_limit * 86400))

        # 遍历消息数据库
        msg_dbs = sorted(decrypted_dir.glob('message/message_*.db'))
        if not msg_dbs:
            # 也尝试直接在目录下查找
            msg_dbs = sorted(decrypted_dir.glob('**/MSG*.db'))

        conversations_map = {}

        for db_path in msg_dbs:
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                # 获取表列表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [t[0] for t in cursor.fetchall()]

                # 查找消息表
                for table in tables:
                    t_lower = table.lower()
                    if not (t_lower.startswith('msg') or t_lower.startswith('message') or t_lower.startswith('chat')):
                        continue

                    try:
                        # 获取列名
                        cursor.execute(f"PRAGMA table_info([{table}])")
                        columns = {c[1].lower(): c[1] for c in cursor.fetchall()}

                        # 确定列名映射
                        sender_col = columns.get('strtalker', columns.get('talker', columns.get('sender', columns.get('real_sender_id', None))))
                        content_col = columns.get('strcontent', columns.get('content', columns.get('message', columns.get('message_content', None))))
                        time_col = columns.get('ncreatetime', columns.get('createtime',
                                    columns.get('createtime', columns.get('timestamp', columns.get('create_time', None)))))
                        type_col = columns.get('ntype', columns.get('type', columns.get('msgtype', None)))

                        if not (content_col and time_col):
                            continue

                        # 构建查询
                        select_cols = []
                        if sender_col:
                            select_cols.append(sender_col)
                        select_cols.extend([content_col, time_col])
                        if type_col:
                            select_cols.append(type_col)

                        query = f"SELECT {', '.join(select_cols)} FROM [{table}]"
                        if cutoff_ts > 0:
                            query += f" WHERE {time_col} > {cutoff_ts}"
                        query += f" ORDER BY {time_col}"

                        cursor.execute(query)
                        rows = cursor.fetchall()

                        for row in rows:
                            idx = 0
                            sender_val = row[idx] if sender_col else ''; idx += (1 if sender_col else 0)
                            content = row[idx] or ''; idx += 1
                            timestamp = row[idx] or 0; idx += 1
                            msg_type = row[idx] if type_col else 1
                            
                            if isinstance(content, bytes):
                                continue # 忽略二进制消息

                            sender = sender_val
                            if sender_col == 'real_sender_id':
                                # 微信4.x处理
                                if sender_val == 0:
                                    sender = "宋代立(我)"
                                else:
                                    sender = name2id.get(sender_val, str(sender_val))
                                
                                # 解析群聊消息前缀
                                if isinstance(content, str) and ':\n' in content[:50] and table.startswith('Msg_'):
                                    parts = content.split(':\n', 1)
                                    if len(parts) == 2 and not parts[0].isspace():
                                        sender = parts[0]
                                        content = parts[1]

                            # 跳过系统消息
                            if msg_type == 10000 or msg_type == 10002:
                                continue

                            # 确定会话ID
                            conv_id = table
                            if sender_col != 'real_sender_id':
                                conv_id = sender if sender else table
                            else:
                                # 对于Msg_表，表名就是联系人哈希
                                pass

                            if conv_id not in conversations_map:
                                conversations_map[conv_id] = {
                                    'source': 'wechat',
                                    'conversation_id': conv_id,
                                    'conversation_name': contacts.get(sender, conv_id) if sender else conv_id,
                                    'conversation_type': 'unknown',
                                    'messages': []
                                }

                            # 格式化时间
                            try:
                                ts_str = datetime.fromtimestamp(timestamp).isoformat()
                            except (ValueError, OSError):
                                ts_str = str(timestamp)

                            # 消息类型
                            type_name = 'text'
                            if msg_type == 3:
                                type_name = 'image'
                            elif msg_type == 43:
                                type_name = 'video'
                            elif msg_type == 34:
                                type_name = 'voice'
                            elif msg_type == 49:
                                type_name = 'file'
                            elif msg_type == 47:
                                type_name = 'emoji'

                            s_name = '我' if sender_val == 0 else contacts.get(sender, '')
                            conversations_map[conv_id]['messages'].append({
                                'sender': sender,
                                'sender_name': s_name,
                                'content': content,
                                'timestamp': ts_str,
                                'type': type_name
                            })

                    except Exception as e:
                        pass  # 跳过无法解析的表

                conn.close()

            except Exception as e:
                print(f'⚠️ 处理数据库 {db_path} 失败: {e}')

        result = list(conversations_map.values())
        return result

    @staticmethod
    def merge_all(wechat_db_dir: Optional[str] = None,
                  days_limit: int = 7) -> list[dict]:
        """
        提取并合并微信数据

        Args:
            wechat_db_dir: 微信解密数据库目录
            days_limit: 天数限制

        Returns:
            合并后的统一格式数据
        """
        all_conversations = []

        # 处理微信数据
        if wechat_db_dir and os.path.exists(wechat_db_dir):
            convs = DataFormatter.format_wechat_data(wechat_db_dir, days_limit=days_limit)
            all_conversations.extend(convs)
            print(f'✅ WeChat: 加载 {len(convs)} 个会话')

        return all_conversations

    @staticmethod
    def save_merged(conversations: list[dict], output_path: str):
        """保存合并后的数据"""
        output = {
            'merged_at': datetime.now().isoformat(),
            'total_conversations': len(conversations),
            'total_messages': sum(len(c.get('messages', [])) for c in conversations),
            'conversations': conversations
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f'✅ 合并数据已保存: {output_path}')
        print(f'   总会话数: {output["total_conversations"]}')
        print(f'   总消息数: {output["total_messages"]}')


if __name__ == '__main__':
    import sys

    project_root = Path(__file__).parent.parent.parent
    wechat_dir = project_root / 'data' / 'wechat' / 'decrypted'
    output_file = project_root / 'data' / 'merged_chat_data.json'

    if not wechat_dir.exists():
        print('⚠️ 未找到任何数据文件')
        print(f'   微信解密目录: {wechat_dir}')
        sys.exit(1)

    conversations = DataFormatter.merge_all(
        wechat_db_dir=str(wechat_dir) if wechat_dir.exists() else None,
        days_limit=7
    )

    DataFormatter.save_merged(conversations, str(output_file))

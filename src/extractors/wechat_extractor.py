"""
微信数据提取配置和启动脚本
封装 wechat-decrypt 工具的使用流程
"""
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
WECHAT_DECRYPT_DIR = PROJECT_ROOT / 'wechat-decrypt'
DATA_DIR = PROJECT_ROOT / 'data' / 'wechat'


def check_prerequisites():
    """检查前置条件"""
    print('=== 微信数据提取工具 ===\n')

    # 检查 wechat-decrypt 是否存在
    if not WECHAT_DECRYPT_DIR.exists():
        print('❌ 未找到 wechat-decrypt 目录')
        print(f'   请先运行: git clone https://github.com/ylytdeng/wechat-decrypt.git')
        return False

    # 检查依赖
    try:
        import Crypto
        print('✅ pycryptodome 已安装')
    except ImportError:
        print('⚠️ 正在安装 pycryptodome...')
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pycryptodome'],
                       capture_output=True)
        print('✅ pycryptodome 安装完成')

    # 检查管理员权限
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not is_admin:
            print('⚠️ 未以管理员权限运行')
            print('   提取微信密钥需要管理员权限')
            print('   请右键 -> 以管理员身份运行')
            return False
        print('✅ 管理员权限')
    except Exception:
        print('⚠️ 无法检测管理员权限')

    return True


def find_wechat_data_dir():
    """查找微信数据目录（需要精确到 wxid 子目录）"""
    # 常见的 xwechat_files 根目录位置
    common_roots = [
        Path(os.environ.get('APPDATA', '')) / 'Tencent' / 'xwechat_files',
        Path(os.environ.get('USERPROFILE', '')) / 'Documents' / 'xwechat_files',
    ]
    # 搜索各个盘符
    for drive in 'CDEFG':
        common_roots.append(Path(f'{drive}:/xwechat_files'))
        common_roots.append(Path(f'{drive}:/Program Files/xwechat_files'))
        common_roots.append(Path(f'{drive}:/Program Files (x86)/xwechat_files'))

    # 找到存在的根目录
    xwechat_root = None
    for p in common_roots:
        if p.exists():
            xwechat_root = p
            break

    if not xwechat_root:
        print('\n⚠️ 未自动找到 xwechat_files 目录')
        manual = input('请手动输入微信数据根目录路径（xwechat_files 所在目录）: ').strip()
        if manual and os.path.exists(manual):
            xwechat_root = Path(manual)
        else:
            print('路径无效')
            return []

    print(f'\n找到微信数据根目录: {xwechat_root}')

    # 列出有 db_storage 子目录的 wxid 目录
    found = []
    for sub in xwechat_root.iterdir():
        if sub.is_dir() and (sub / 'db_storage').exists():
            found.append(sub)

    if found:
        print(f'发现 {len(found)} 个微信账号目录:')
        for i, p in enumerate(found):
            db_dir = p / 'db_storage'
            db_count = len(list(db_dir.rglob('*.db'))) if db_dir.exists() else 0
            print(f'  [{i + 1}] {p.name} ({db_count} 个数据库)')
    else:
        print('⚠️ 未找到包含 db_storage 的微信账号目录')

    return found


def create_config(wechat_data_dir: str):
    """创建 wechat-decrypt 的配置文件"""
    config = {
        "db_dir": os.path.join(wechat_data_dir, "db_storage"),
        "keys_file": str(DATA_DIR / "all_keys.json"),
        "decrypted_dir": str(DATA_DIR / "decrypted"),
        "wechat_process": "Weixin.exe"
    }

    config_path = WECHAT_DECRYPT_DIR / 'config.json'
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f'\n✅ 配置已写入: {config_path}')
    print(f'   数据库目录: {config["db_dir"]}')
    print(f'   密钥文件: {config["keys_file"]}')
    print(f'   解密输出: {config["decrypted_dir"]}')

    return config_path


def extract_keys():
    """提取微信数据库密钥"""
    print('\n=== 步骤1: 提取密钥 ===')
    print('请确保微信正在运行并已登录...\n')

    script = WECHAT_DECRYPT_DIR / 'find_all_keys.py'
    if not script.exists():
        print(f'❌ 未找到密钥提取脚本: {script}')
        return False

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(WECHAT_DECRYPT_DIR),
        capture_output=False
    )

    return result.returncode == 0


def decrypt_databases():
    """解密数据库"""
    print('\n=== 步骤2: 解密数据库 ===\n')

    script = WECHAT_DECRYPT_DIR / 'decrypt_db.py'
    if not script.exists():
        print(f'❌ 未找到解密脚本: {script}')
        return False

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(WECHAT_DECRYPT_DIR),
        capture_output=False
    )

    return result.returncode == 0


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not check_prerequisites():
        return

    # 查找数据目录
    data_dirs = find_wechat_data_dir()

    if not data_dirs:
        return

    if len(data_dirs) == 1:
        chosen = data_dirs[0]
    else:
        choice = input(f'\n请选择微信账号 [1-{len(data_dirs)}]: ').strip()
        try:
            chosen = data_dirs[int(choice) - 1]
        except (ValueError, IndexError):
            print('无效选择')
            return

    print(f'\n选择的数据目录: {chosen}')

    # 创建配置
    create_config(str(chosen))

    # 提取密钥
    if not extract_keys():
        print('\n❌ 密钥提取失败')
        print('   可能原因:')
        print('   1. 微信未运行或未登录')
        print('   2. 未以管理员权限运行')
        print('   3. 微信版本不兼容')
        return

    # 解密数据库
    if not decrypt_databases():
        print('\n❌ 数据库解密失败')
        return

    decrypted_dir = DATA_DIR / 'decrypted'
    if decrypted_dir.exists():
        db_count = len(list(decrypted_dir.rglob('*.db')))
        print(f'\n🎉 解密完成！共 {db_count} 个数据库文件')
        print(f'   输出目录: {decrypted_dir}')
    else:
        print('\n⚠️ 未找到解密输出')


if __name__ == '__main__':
    main()

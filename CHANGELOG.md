# 变更记录

## 2026-03-18 v0.1.1 - 配置生效与同步稳定性修复

### 修复
- **网页配置保存后立即生效**
  - `src/ai_planner/llm_client.py` 改为每次请求时重新读取 `.env`
  - 修复 Web 面板修改模型、API Key、Base URL 后仍沿用旧配置的问题

- **重新同步前清理旧解密产物**
  - `src/extractors/wechat_extractor.py` 新增 `reset_extraction_output()`
  - `src/web_server.py` 在重新解密前删除旧的 `data/wechat/decrypted` 和 `all_keys.json`
  - 避免旧数据库残留混入本次同步结果

- **移除硬编码绝对路径**
  - `src/web_server.py` 和 `src/main_agent.py` 改为基于项目根目录拼接路径
  - 修复换目录或换机器后找不到 `data/`、`workspace/reports/` 的问题

- **统一运行时配置加载**
  - `src/web_server.py`、`src/main_agent.py`、`src/ai_planner/data_cleaner.py`、`src/ai_planner/llm_client.py` 统一显式读取仓库根目录 `.env`
  - 修复 CLI 与 Web 对配置读取行为不一致的问题

- **修正 Web 报告生成分支**
  - `src/web_server.py` 按 `1d / 3d / 7d` 选择正确的报告类型
  - 修复原先无论选择什么范围都按多日分支调用模型的问题

- **修正报告文件命名**
  - `src/main_agent.py` 的 `save_report()` 改为按 `daily / 3d / weekly` 区分文件名
  - 避免 3 天报告与周报共用命名规则导致覆盖

### 验证
- 通过 `python -m compileall src`

## 2026-03-02 v0.1.0 - 数据采集模块初版

### 新增
- **360Teams 数据提取** (`src/extractors/teams_extractor.js`)
  - DevTools Console 注入脚本
  - 通过融云 SDK API 提取聊天记录
  - 支持发送到本地服务器或复制到剪贴板
  - 支持按时间范围过滤、分页获取、多版本API兼容
  - 备选方案：自动探测 IndexedDB 数据

- **微信数据提取** (`src/extractors/wechat_extractor.py`)
  - 封装 [wechat-decrypt](https://github.com/ylytdeng/wechat-decrypt) 工具
  - 自动查找微信数据目录
  - 一键完成密钥提取和数据库解密
  - 支持微信 4.x 版本

- **本地数据接收服务器** (`src/server/local_server.py`)
  - 监听 localhost:8899
  - 接收 360Teams 导出的 JSON 数据
  - 支持 CORS 跨域

- **统一数据格式化器** (`src/formatters/data_formatter.py`)
  - 统一两个数据源的消息格式
  - 支持按时间过滤
  - 合并输出为单一 JSON 文件

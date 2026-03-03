# 变更记录

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

# easyPlayWright 架构参考

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI + uvicorn（ASGI 异步） |
| 浏览器自动化 | Playwright async API |
| 配置 | config.yaml + pkg/config.py |
| 日志 | loguru（pkg/logger.py） |
| 数据模型 | Python dataclass（pkg/models.py） |
| HTTP 数据验证 | Pydantic v2（FastAPI 路由层） |

## BrowserAdapter 三级缓存架构

```
Playwright（全局唯一）
  └── Browser（全局唯一）
        └── BrowserContext（按 storage_state 缓存）
              └── Page（按 provider/page_key 缓存）
```

- `_playwright` / `_browser`：类变量，进程内唯一
- `_instances`：`Dict[storage_state, BrowserAdapter]`，每个登录态对应一个 Context
- `_pages`：`Dict[page_key, Page]`，每个 provider 对应一个缓存 Page
- `_page_locks`：`Dict[page_key, asyncio.Lock]`，Page 级并发控制

## 并发模型

- 不同 provider（page_key）的请求**可并发**执行
- 同一 provider 的请求通过 `asyncio.Lock` **串行**执行
- 锁在 `api/chat_api.py` 的 `_chat_singleton` 中获取

## ChatApi 调用链

```
POST /api/chat
  → chat_controller.py (FastAPI 路由)
  → ChatApi.chat()
  → ChatApi._chat_singleton() / _chat_disposable()
  → ChatDomain.chat()
  → ChatComponent.send_in_session()
  → BaseLLMAdapter.chat()（模板方法）
      → upload_attachments()
      → type_message()
      → send()
      → wait_for_response()
```

## 多模型注册机制

```python
# domain/llm/chat_domain.py
MODEL_REGISTRY: Dict[str, Type[BaseLLMAdapter]] = {
    "qwen": QwenAdapter,
    "doubao": DoubaoAdapter,
}
```

新增模型只需：实现 `BaseLLMAdapter` → 注册到 `MODEL_REGISTRY` → 在 `PROVIDER_CONFIG` 中添加登录态配置。

## 反自动化检测

所有浏览器实例均启用：
- 启动参数：`--disable-blink-features=AutomationControlled`、`--start-maximized` 等
- JS 注入：隐藏 `navigator.webdriver`、伪造 `chrome` 对象、`plugins`、`languages` 等
- Context：`no_viewport=True`、`locale="zh-CN"`、`timezone_id="Asia/Shanghai"`
- 可选：`channel: chrome`（使用系统 Chrome，绕过 Playwright Chromium 指纹）

## HTTP 接口

### POST /api/chat

请求体：
```json
{
  "message": "你好",
  "model": "Qwen3.5-Omni-Plus",
  "provider": "qwen",
  "session_id": "",
  "attachments": [],
  "timeout": 60.0
}
```

响应体：
```json
{
  "success": true,
  "data": {
    "answer": "...",
    "question": "你好",
    "session_id": "abc123",
    "timestamp": "2026-04-01 12:00:00",
    "model": "Qwen3.5-Omni-Plus",
    "provider": "qwen"
  },
  "error": null
}
```

### GET /health

响应：`{"status": "ok", "service": "easyPlayWright Chat API"}`

## 配置文件（config.yaml）

```yaml
browser:
  type: chromium
  channel: chrome       # 留空使用内置 Chromium
  headless: false
  slow_mo: 0
  timeout: 30000
  storage_state: ""     # 单个 provider 时可在此设置，多 provider 由代码决定
```

## 登录态管理

```bash
# 保存千问登录态
python tools/save_login_state.py qwen

# 保存豆包登录态
python tools/save_login_state.py doubao
```

登录态文件存储于 `output/state/{provider}_state.json`。

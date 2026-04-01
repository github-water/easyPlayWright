# easyPlayWright

基于 Playwright + Python 的网页自动化框架，支持网页数据抓取与大模型对话自动化。

## 架构说明

```
easyPlayWright/
├── api/                            # C4 System Interface：对外暴露的系统接口层
│   ├── http/
│   │   └── http_server.py          # FastAPI HTTP 服务（REST API 入口）
│   ├── chat_api.py                 # 大模型对话接口（单轮/多轮对话）
│   ├── newsflash_api.py            # 快讯抓取接口
│   └── init.py                     # FastAPI 应用初始化与路由注册
│
├── domain/                         # C4 System Context：业务域，定义"做什么"
│   ├── kr36/
│   │   └── newsflash.py            # 36kr 快讯业务用例
│   └── llm/
│       └── chat_domain.py          # 大模型对话业务域（多模型注册/切换）
│
├── component/                      # C4 Component：系统内部编排，主动调用外部
│   ├── chat.py                     # 对话编排组件（单轮/多轮/会话管理）
│   ├── navigator.py                # 导航组件
│   ├── scraper.py                  # 数据抓取组件
│   └── exporter.py                 # 数据导出组件
│
├── adapter/                        # C4 External System Adapter：对接外部系统
│   ├── llm/
│   │   ├── base.py                 # 大模型页面适配器抽象基类
│   │   └── qwen.py                 # 通义千问适配器实现
│   ├── browser.py                  # 浏览器生命周期适配（单例 + 异步）
│   ├── page.py                     # 页面操作适配
│   └── element.py                  # 元素操作适配
│
├── pkg/                            # 横切关注点：配置 / 日志 / 模型 / 工具
│   ├── config.py                   # YAML 配置单例
│   ├── logger.py                   # loguru 日志
│   ├── models.py                   # 公共数据模型（ChatRequest/Attachment 等）
│   └── utils.py                    # 截图、目录等工具
│
├── tools/                          # 辅助工具脚本
│   └── save_login_state.py         # 手动登录并保存浏览器登录态
│
├── examples/                       # 示例脚本
│   ├── example_36kr_newsflash.py   # 36kr 快讯抓取示例
│   └── example_llm_chat.py         # 大模型对话示例
│
├── output/                         # 输出目录（数据、状态、日志）
│   ├── state/                      # 浏览器登录态存储
│   │   └── qwen_state.json         # 千问登录态
│   └── 36kr_newsflash.json         # 抓取数据
│
├── config.yaml                     # 全局配置
├── requirements.txt                # 依赖清单
└── main.py                         # 主入口（uvicorn 启动）
```

## 层次职责与调用方向

```
外部调用者（测试 / 脚本 / CI / HTTP 客户端）
        │
        ▼
  ┌─────────────┐
  │   api/      │  ← System Interface：唯一对外入口，被外部调用
  │             │     - chat_api.py：Python 异步调用入口
  │             │     - http/：REST API 入口（FastAPI）
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  domain/    │  ← System Context：业务语义，描述用例意图
  │             │     - llm/：大模型对话（多模型注册/切换）
  │             │     - kr36/：36kr 快讯抓取
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ component/  │  ← Component：系统内编排，主动驱动外部交互
  │             │     - chat：对话流程编排
  │             │     - navigator/scraper/exporter：抓取流程编排
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  adapter/   │  ← External Adapter：对接外部系统
  │             │     - llm/：大模型页面适配（Qwen 等）
  │             │     - browser/page/element：Playwright 异步适配
  └──────┬──────┘
         │
         ▼
  Playwright / 浏览器
         │
        pkg/ （横切，各层均可使用）
```

| 层 | C4 对应 | 方向 | 职责 |
|----|---------|------|------|
| `api/` | System Interface | **被外部调用** | 暴露系统能力，屏蔽内部实现（Python API + HTTP） |
| `domain/` | System Context | 编排 component | 定义业务用例，表达"做什么"，支持多模型切换 |
| `component/` | Component | **主动调用外部** | 系统内编排，驱动 adapter 完成具体流程 |
| `adapter/` | External Adapter | 对接外部系统 | 封装 Playwright 与大模型页面交互细节 |
| `pkg/` | Cross-cutting | 横向支撑 | 配置、日志、公共数据模型、工具函数 |
| `tools/` | Utility Scripts | 独立运行 | 辅助脚本（如保存登录态） |

## 异步设计原则

### 为什么选择异步架构

Playwright 同步 API 在等待大模型回复时会**阻塞整个线程**（`time.sleep` 轮询），导致 HTTP 服务无法并发处理请求。异步架构通过 `asyncio.sleep` 在等待期间**释放事件循环控制权**，让其他请求得以同时执行。

### 并发模型

```
uvicorn 事件循环（单进程单线程）
  │
  ├─ 请求 A: await chat()    ── asyncio.sleep（等待 AI 回复）──→ 释放控制权
  │                                                              │
  ├─ 请求 B: await chat()  ◄─────────────────────────────────────┘ 获得控制权
  │                           ── asyncio.sleep（等待 AI 回复）──→ 释放控制权
  │                                                              │
  └─ 请求 A: 回复到达       ◄─────────────────────────────────────┘ 继续执行
```

每个请求使用独立的 Page（浏览器 Tab），彼此互不干扰。

### 三级资源缓存

```
┌──────────────────────────────────────────────────┐
│           Playwright（全局唯一）                    │
│  ┌────────────────────────────────────────────┐  │
│  │         Browser（全局唯一进程）               │  │
│  │                                            │  │
│  │  ┌──────────────────┐ ┌─────────────────┐  │  │
│  │  │ Context A         │ │ Context B       │  │  │
│  │  │ qwen_state.json   │ │ gpt_state.json  │  │  │
│  │  │ (Cookie 隔离)     │ │ (Cookie 隔离)   │  │  │
│  │  │                   │ │                 │  │  │
│  │  │ Pages 缓存:       │ │ Pages 缓存:     │  │  │
│  │  │  "qwen" → Page    │ │  "chatgpt" → …  │  │  │
│  │  └──────────────────┘ └─────────────────┘  │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

| 层级 | 缓存粒度 | 生命周期 | 作用 |
|------|---------|---------|------|
| Playwright + Browser | 全局单例 | 应用生命周期 | 避免重复启动浏览器进程 |
| BrowserContext | 按 `storage_state` 缓存 | 应用生命周期 | Cookie 隔离，不同登录态独立 |
| Page | 按 `provider` 缓存 | 应用生命周期 | 避免重复导航和页面创建 |

### 关键设计约束

1. **全异步链路**：从 FastAPI 路由到 Playwright 操作，全链路 `async/await`，无 `time.sleep` 阻塞
2. **单事件循环**：所有 Playwright 操作在同一 asyncio 事件循环中执行，避免跨线程问题
3. **资源隔离**：不同 `storage_state` 使用独立 Context（Cookie 隔离），不同 `provider` 使用独立 Page
4. **优雅退出**：FastAPI `lifespan` 机制在应用关闭时自动调用 `BrowserAdapter.close_all()` 清理所有资源
5. **双模式兼容**：
   - **单例模式**（`singleton=True`）：HTTP 服务场景，复用浏览器/Context/Page
   - **一次性模式**（`async with`）：脚本场景，每次创建/销毁，互不影响

## 业务能力

### 🤖 大模型对话自动化

通过 Playwright 驱动浏览器与大模型网页交互，支持：
- **单轮对话**：发送消息并获取回复（支持文本 + 图片/视频/文件附件）
- **多轮对话**：基于 session_id 的会话管理，浏览器页面侧天然维护上下文记忆
- **多模型切换**：通过 `MODEL_REGISTRY` 注册表扩展新模型适配器
- **HTTP API**：FastAPI REST 接口，支持并发调用，自动生成 API 文档
- **登录态复用**：保存浏览器登录态，免重复登录

### 📰 网页数据抓取

- 36kr 快讯自动抓取与导出（JSON/CSV）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 保存登录态（大模型对话需要）

```bash
python tools/save_login_state.py
# 在打开的浏览器中手动完成登录，回到终端按 Enter 保存
```

### 3. 运行示例

```bash
# 大模型对话示例
python examples/example_llm_chat.py

# 36kr 快讯抓取
python examples/example_36kr_newsflash.py

# 主入口（启动 HTTP 服务）
python main.py
```

### 4. HTTP API 方式

```bash
# 启动服务
python main.py

# 调用对话接口
curl -X POST http://localhost:8009/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "model": "Qwen3.5-Omni-Plus", "provider": "qwen"}'

# 健康检查
curl http://localhost:8009/health

# 交互式 API 文档
# http://localhost:8009/docs
```

### 5. 查看结果

```
output/
├── state/                    # 登录态
│   └── qwen_state.json
├── 36kr_newsflash.json       # 抓取数据（JSON）
├── 36kr_newsflash.csv        # 抓取数据（CSV）
├── logs/                     # 运行日志
└── screenshots/              # 截图（如启用）
```

## 配置说明

编辑 `config.yaml`：

```yaml
browser:
  type: chromium      # chromium | firefox | webkit
  headless: false     # true 为无头模式
  slow_mo: 0          # 操作间隔毫秒（调试时可设 500）
  timeout: 30000      # 默认超时（毫秒）
```

## 扩展新模型

1. 在 `adapter/llm/` 下新建适配器类，继承 `BaseLLMAdapter`（所有方法为 `async`）
2. 在 `domain/llm/chat_domain.py` 的 `MODEL_REGISTRY` 中注册
3. 调用时指定 `provider` 参数即可


## 技术栈

| 组��� | 技术 | 作用 |
|------|------|------|
| 浏览器自动化 | Playwright (async API) | 驱动浏览器与网页交互 |
| Web 框架 | FastAPI + uvicorn | 异步 HTTP 服务 |
| 数据校验 | Pydantic | 请求/响应模型校验 |
| 配置管理 | PyYAML | YAML 配置文件解析 |
| 日志 | loguru | 结构化日志 |
| 测试 | pytest + pytest-asyncio | 异步测试支持 |

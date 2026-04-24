---
name: project_code
description: easyPlayWright 项目编码指导技能。当需要在本项目中编写代码、新增功能、修改模块、重构代码时使用。提供项目架构规范、目录结构、分层职责、编码约定，确保 AI 编写的代码符合项目规范并与现有架构保持一致。
---

# easyPlayWright 项目编码指南

## 项目概述

基于 Playwright 的 Web 自动化框架，采用 C4 架构分层设计，支持多模型 LLM 页面交互。异步架构（FastAPI + Playwright async API）。

## 目录结构

```
easyPlayWright/
├── adapter/                  # 外部系统适配器层
│   ├── llm/
│   │   ├── base.py           # LLM 适配器抽象基类（必须继承）
│   │   ├── qwen.py           # 千问适配器
│   │   └── doubao.py         # 豆包适配器
│   ├── browser.py            # 浏览器生命周期管理（单例+一次性模式）
│   ├── element.py            # 元素操作封装
│   └── page.py               # 页面操作封装
├── api/                      # 对外接口层
│   ├── http/
│   │   └── chat_controller.py  # FastAPI 路由
│   ├── chat_api.py           # 统一对话入口（ChatApi）
│   ├── newsflash_api.py      # 快讯接口
│   └── init.py               # FastAPI app + lifespan
├── component/                # 编排组件层
│   ├── chat.py               # 对话流程编排
│   ├── scraper.py            # 页面抓取组件
│   ├── navigator.py          # 导航组件
│   └── exporter.py           # 数据导出组件
├── domain/                   # 业务域层
│   ├── llm/
│   │   └── chat_domain.py    # 对话业务域 + MODEL_REGISTRY
│   └── kr36/
│       └── newsflash.py      # 36kr 快讯业务域
├── pkg/                      # 公共基础包
│   ├── config.py             # 配置管理（读 config.yaml）
│   ├── logger.py             # 日志
│   ├── models.py             # 公共数据模型（ChatRequest/ChatResponse 等）
│   └── utils.py              # 工具函数
├── tools/                    # 独立工具脚本
│   └── save_login_state.py   # 保存登录态（支持多 provider）
├── examples/                 # 使用示例
├── output/state/             # 登录态文件（*.json）
├── config.yaml               # 全局配置
└── main.py                   # 服务启动入口（uvicorn）
```

## 分层职责（C4 架构）

| 层 | 职责 | 禁止 |
|----|------|------|
| `adapter` | 对接外部系统（浏览器/页面），封装原子操作 | 不含业务逻辑 |
| `component` | 编排 adapter，实现多步流程 | 不直接调用外部系统 |
| `domain` | 定义业务用例语义，屏蔽模型差异 | 不含页面操作细节 |
| `api` | 系统唯一入口，屏蔽内部实现 | 不含业务逻辑 |
| `pkg` | 公共基础，跨层复用 | 不依赖其他层 |

**调用方向（单向）**：`api` → `domain` → `component` → `adapter`

## 编码规范

### 通用
- 全部使用 **异步**：`async def` + `await`，禁止 `time.sleep`（用 `asyncio.sleep`）
- 日志格式：`[层][模块] 描述`，如 `[Adapter][Qwen] 打开页面`
- 配置读取统一通过 `pkg.config.Config`，不硬编码
- 公共数据模型定义在 `pkg/models.py`

### 新增 LLM 适配器
1. 继承 `BaseLLMAdapter`，实现所有 `@abstractmethod`
2. 在文件顶部定义 `SELECTORS` 字典（所有选择器集中管理）
3. 提供 `update_selectors(**kwargs)` 方法支持动态覆盖
4. 在 `domain/llm/chat_domain.py` 的 `MODEL_REGISTRY` 中注册
5. 在 `tools/save_login_state.py` 的 `PROVIDER_CONFIG` 中注册
6. 登录态文件命名：`output/state/{provider}_state.json`

### BrowserAdapter 使用
- **HTTP 服务**：`BrowserAdapter.get_instance(storage_state=...)` 单例模式
- **脚本/示例**：`async with BrowserAdapter(...) as context:` 一次性模式
- Page 级别锁：`adapter.get_page_lock(page_key)` 保证同一页面串行操作


## 参考文件

- 项目架构详情：参见 `references/architecture.md`
- 现有适配器实现参考：`adapter/llm/qwen.py`

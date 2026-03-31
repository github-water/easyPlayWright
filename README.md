# easyPlayWright

基于 Playwright + Python 的网页自动化框架，采用 **C4 架构**四层设计。

## C4 架构说明

```
easyPlayWright/
├── api/                        # C4 System Interface：对外暴露的系统接口层
│   ├── newsflash_api.py        # 快讯抓取接口（外部调用入口）
│   └── ...                     # 可扩展其他业务接口
│
├── domain/                     # C4 System Context：业务域，定义"做什么"
│   └── kr36/
│       └── newsflash.py        # 36kr 快讯业务用例
│
├── component/                  # C4 Component：系统内部编排，主动调用外部
│   ├── navigator.py            # 导航组件
│   ├── scraper.py              # 数据抓取组件
│   └── exporter.py             # 数据导出组件
│
├── adapter/                    # C4 External System Adapter：对接 Playwright 外部系统
│   ├── browser.py              # 浏览器生命周期适配
│   ├── page.py                 # 页面操作适配
│   └── element.py              # 元素操作适配
│
├── pkg/                        # 横切关注点：配置 / 日志 / 工具
│   ├── config.py               # YAML 配置单例
│   ├── logger.py               # loguru 日志
│   └── utils.py                # 截图、目录等工具
│
├── examples/                   # 示例脚本
│   └── example_36kr_newsflash.py
│
├── tests/                      # 测试目录
├── output/                     # 输出目录（截图、日志、数据）
├── config.yaml                 # 全局配置
├── requirements.txt            # 依赖清单
└── main.py                     # 主入口
```

## C4 层次职责与调用方向

```
外部调用者（测试 / 脚本 / CI）
        │
        ▼
  ┌─────────────┐
  │   api/      │  ← System Interface：唯一对外入口，被外部调用
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  domain/    │  ← System Context：业务语义，描述用例意图
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ component/  │  ← Component：系统内编排，主动驱动外部交互
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  adapter/   │  ← External Adapter：对接 Playwright 外部系统
  └──────┬──────┘
         │
         ▼
    Playwright
         │
        pkg/ （横切，各层均可使用）
```

| 层 | C4 对应 | 方向 | 职责 |
|----|---------|------|------|
| `api/` | System Interface | **被外部调用** | 暴露系统能力，屏蔽内部实现 |
| `domain/` | System Context | 编排 component | 定义业务用例，表达"做什么" |
| `component/` | Component | **主动调用外部** | 系统内编排，驱动 adapter |
| `adapter/` | External Adapter | 对接 Playwright | 封装外部系统交互细节 |
| `pkg/` | Cross-cutting | 横向支撑 | 配置、日志、工具 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 运行示例

```bash
# 方式一：主入口
python main.py

# 方式二：示例脚本
python examples/example_36kr_newsflash.py
```

### 3. 查看结果

```
output/
├── 36kr_newsflash.json   # 抓取数据（JSON）
├── 36kr_newsflash.csv    # 抓取数据（CSV）
├── logs/                 # 运行日志
└── screenshots/          # 截图（如启用）
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

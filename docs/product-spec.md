# ClaudePilot 产品文档

## 1. 产品定位

ClaudePilot 是 Claude Code CLI 的 Web 可视化控制面板。

**核心理念**：Claude CLI 能做的所有事情，都在浏览器里可操作、可可视化。

- Claude CLI 是引擎，ClaudePilot 是方向盘和仪表盘
- 不替代 CLI，只做控制和展示
- 每一个 CLI 参数、交互、输出，都应该有对应的前端表达

## 2. Claude CLI 功能全景 → ClaudePilot 映射

### 2.1 启动参数（Session 配置）

| CLI 参数                 | 说明                                                                | ClaudePilot 控件        | 优先级 |
| ------------------------ | ------------------------------------------------------------------- | ----------------------- | ------ |
| `--model`                | 选择模型                                                            | 模型选择下拉            | P0     |
| `--permission-mode`      | 权限模式（default/plan/acceptEdits/auto/bypassPermissions/dontAsk） | 权限模式选择            | P0     |
| `--session-id`           | 会话 ID                                                             | 自动生成，不可编辑      | -      |
| `-r, --resume`           | 恢复会话                                                            | 点击历史会话自动 resume | P0     |
| `-c, --continue`         | 继续最近对话                                                        | "继续上次"按钮          | P1     |
| `--append-system-prompt` | 追加系统提示                                                        | 语言偏好 + 自定义提示   | P0     |
| `--system-prompt`        | 完全替换系统提示                                                    | 高级设置                | P2     |
| `--max-turns`            | 最大轮次                                                            | 数字输入                | P1     |
| `--effort`               | 思考深度（low/medium/high/xhigh/max）                               | Effort 选择器           | P1     |
| `--fallback-model`       | 备用模型                                                            | 备用模型选择            | P2     |
| `--tools`                | 可用工具列表                                                        | 工具开关面板            | P1     |
| `--allowedTools`         | 允许的工具                                                          | 工具白名单              | P1     |
| `--disallowedTools`      | 禁止的工具                                                          | 工具黑名单              | P1     |
| `--mcp-config`           | MCP 配置文件                                                        | MCP 服务器管理面板      | P1     |
| `--strict-mcp-config`    | 只用指定 MCP                                                        | 开关                    | P2     |
| `--add-dir`              | 额外可访问目录                                                      | 目录列表                | P1     |
| `--agent`                | 指定 Agent                                                          | Agent 选择              | P2     |
| `--agents`               | 自定义 Agent 定义                                                   | Agent 编辑器            | P2     |
| `--verbose`              | 详细输出                                                            | 开关                    | P2     |
| `--no-chrome`            | 禁用 Chrome 集成                                                    | 开关                    | P2     |
| `--safe-mode`            | 安全模式                                                            | 开关                    | P2     |
| `--bare`                 | 最小模式                                                            | 开关                    | P2     |

### 2.2 交互功能

| CLI 交互           | 说明                  | ClaudePilot 展示              | 优先级 |
| ------------------ | --------------------- | ----------------------------- | ------ |
| 用户消息           | 输入提示词            | 聊天输入框                    | P0 ✅  |
| Assistant 回复     | 流式文本 + 工具调用   | 消息气泡 + 流式渲染           | P0 ✅  |
| Tool Use           | Claude 调用工具       | 工具调用卡片（可展开参数）    | P0 ✅  |
| Tool Result        | 工具执行结果          | 结果卡片                      | P0 ✅  |
| AskUserQuestion    | 需要用户确认          | 弹窗选择器                    | P0     |
| Permission Request | 权限请求              | 权限确认弹窗（允许/拒绝）     | P0     |
| EnterPlanMode      | 进入计划模式          | Plan Mode 横幅 + 计划内容展示 | P1     |
| ExitPlanMode       | 退出计划模式          | Plan 反馈确认                 | P1     |
| Status 事件        | thinking/writing/idle | 状态指示器                    | P1     |
| Prompt Suggestion  | 下一个提示建议        | 建议按钮                      | P2     |

### 2.3 输出事件（stream-json）

| 事件类型             | 说明          | ClaudePilot 展示  | 优先级 |
| -------------------- | ------------- | ----------------- | ------ |
| `system`             | 系统信息      | 状态栏            | P1     |
| `init`               | 会话初始化    | 静默处理          | P0 ✅  |
| `status`             | 思考/等待状态 | 状态指示器 + 动画 | P1     |
| `assistant`          | Claude 回复   | 消息气泡          | P0 ✅  |
| `user`               | 工具结果回传  | 结果卡片          | P0 ✅  |
| `result`             | 最终结果      | 结果展示          | P0 ✅  |
| `permission_request` | 权限请求      | 权限弹窗          | P0     |
| `error`              | 错误          | 错误提示          | P0 ✅  |
| `compact`            | 上下文压缩    | 用量提示          | P2     |

### 2.4 CLI 子命令

| 子命令           | 说明            | ClaudePilot 映射 | 优先级 |
| ---------------- | --------------- | ---------------- | ------ |
| `claude agents`  | 管理后台 Agent  | Agent 状态面板   | P2     |
| `claude mcp`     | 管理 MCP 服务器 | MCP 管理面板     | P1     |
| `claude doctor`  | 健康检查        | 诊断页面         | P2     |
| `claude project` | 项目状态        | 项目设置         | P2     |

## 3. 页面架构

```
┌──────────────────────────────────────────────────────────────┐
│  ClaudePilot                              [语言] [设置]      │
├────────────┬─────────────────────────────────────────────────┤
│            │  [Chat]  [Files]  [Terminal]  [Settings]        │
│  项目列表   │─────────────────────────────────────────────────│
│  ────────  │                                                 │
│  ▸ proj-1  │   主内容区                                       │
│  ▸ proj-2  │   （根据标签切换）                                 │
│            │                                                 │
│  会话列表   │                                                 │
│  ────────  │                                                 │
│  ▸ sess-1  │                                                 │
│  ▸ sess-2  │                                                 │
│  + 新会话   │                                                 │
│            │                                                 │
│  打开本地   │                                                 │
│  [Browse]  │                                                 │
│  [Open]    │                                                 │
└────────────┴─────────────────────────────────────────────────┘
```

### 3.1 Chat 标签

核心对话界面：

- **消息列表**：用户消息、Assistant 回复、工具调用/结果卡片
- **输入框**：Enter 发送，Shift+Enter 换行
- **流式渲染**：Assistant 回复实时追加
- **工具调用卡片**：显示工具名、输入参数（可折叠）、执行结果
- **AskUserQuestion 弹窗**：当 Claude 需要用户选择时弹出
- **权限请求弹窗**：当 Claude 需要执行敏感操作时弹出确认
- **状态栏**：当前模型、effort 级别、权限模式、会话计时器

### 3.2 Files 标签

文件浏览器 + 编辑器：

- **左侧 FileTree**：项目目录树，可展开折叠
- **右侧 Monaco Editor**：语法高亮、编辑、保存
- 只读 + 保存，不做文件 CRUD（删除/重命名/新建）

### 3.3 Terminal 标签

嵌入式终端：

- 基于 xterm.js + PTY
- 工作目录为项目根目录
- 单个终端，Phase 2 支持多 tab

### 3.4 Settings 标签

Session 级配置：

| 配置项        | 控件        | 对应 CLI 参数                          |
| ------------- | ----------- | -------------------------------------- |
| 模型          | 下拉选择    | `--model`                              |
| 权限模式      | 单选        | `--permission-mode`                    |
| Effort        | 选择器      | `--effort`                             |
| 最大轮次      | 数字输入    | `--max-turns`                          |
| 备用模型      | 下拉选择    | `--fallback-model`                     |
| 系统提示追加  | 文本框      | `--append-system-prompt`               |
| 工具白/黑名单 | 开关列表    | `--allowedTools` / `--disallowedTools` |
| MCP 服务器    | 列表 + 配置 | `--mcp-config`                         |
| 额外目录      | 路径列表    | `--add-dir`                            |

## 4. 核心用户流程

### 4.1 打开本地项目

1. 左侧点击 **Browse** → 弹出目录选择器
2. 导航到目标目录 → 点击 **Select This Folder**
3. 点击 **Open** → 自动创建项目并选中

### 4.2 开始对话

1. 选择项目 → 自动创建/复用空会话
2. 在输入框发消息 → 后端启动 Claude CLI（带配置参数）
3. 实时看到 Assistant 回复流式输出
4. 工具调用以卡片展示

### 4.3 恢复历史会话

1. 左侧点击历史会话 → 自动 resume
2. 加载历史消息 + 恢复 Claude 上下文
3. 继续对话

### 4.4 权限确认（待实现）

1. Claude 请求权限 → 前端弹出确认框
2. 显示工具名、命令内容
3. 用户选择 允许/拒绝 → 通过 stdin 发回 CLI

### 4.5 Plan 模式（待实现）

1. Claude 进入 Plan Mode → 顶部显示 Plan 横幅
2. 显示 Claude 的计划内容
3. 用户确认/修改 → 发送反馈

## 5. 中英文切换规则

三层切换，独立控制：

| 层级          | 影响                      | 实现                               |
| ------------- | ------------------------- | ---------------------------------- |
| UI 语言       | 界面文字                  | react-i18next，localStorage 持久化 |
| 系统提示语言  | Claude 回复的语言风格     | `--append-system-prompt`           |
| 代码/文档语言 | Claude 生成代码的注释风格 | 系统提示中的代码偏好指令           |

## 6. MVP 已完成

| 功能                               | 状态 |
| ---------------------------------- | ---- |
| 项目创建与管理                     | ✅   |
| 打开本地路径（目录选择器）         | ✅   |
| 会话创建与复用（空会话不重复创建） | ✅   |
| 聊天界面（发送/接收/流式渲染）     | ✅   |
| 消息持久化（SQLite）               | ✅   |
| 工具调用展示                       | ✅   |
| 中英文切换（UI + 系统提示）        | ✅   |
| WebSocket 实时推送                 | ✅   |
| 文件浏览器 + Monaco 编辑器         | ✅   |
| 历史会话 resume                    | ✅   |
| 路径越界保护                       | ✅   |

## 7. MVP 待完成

| 功能                                                   | 优先级 | 复杂度 |
| ------------------------------------------------------ | ------ | ------ |
| AskUserQuestion 弹窗                                   | P0     | 中     |
| Permission Request 弹窗                                | P0     | 中     |
| 终端（xterm.js + PTY）                                 | P0     | 中     |
| Session Settings 面板（model/effort/permission/tools） | P0     | 中     |
| 会话计时器                                             | P1     | 低     |
| Plan Mode 展示                                         | P1     | 中     |
| 状态指示器（thinking/idle/error）                      | P1     | 低     |
| 设置持久化                                             | P1     | 低     |

## 8. Phase 2

| 功能               | 说明                             |
| ------------------ | -------------------------------- |
| MCP 服务器管理面板 | 可视化配置、启停 MCP             |
| 工具白/黑名单      | 按工具名开关                     |
| Agent 管理         | 自定义 Agent、后台 Agent 状态    |
| 用量统计看板       | Token 用量、缓存命中率、费用估算 |
| 桌面宠物           | 会话状态监控，权限确认提醒       |
| Prompt Suggestion  | Claude 推荐的下一步操作          |
| 多终端 Tab         | 多个 xterm.js 实例               |
| 诊断页面           | 等同 `claude doctor`             |
| 远程控制           | `--remote-control` 的 Web 展示   |

## 9. 技术架构

```
┌─────────────────────────────────────────────────┐
│  ClaudePilot Web UI                              │
│  React + TypeScript + Tailwind + shadcn/ui       │
│  Chat | Files | Terminal | Settings              │
└───────────────────┬─────────────────────────────┘
                    │ HTTP REST + WebSocket
┌───────────────────▼─────────────────────────────┐
│  ClaudePilot Server                              │
│  FastAPI + uvicorn + SQLite                      │
│  - Session 配置 → CLI 启动参数映射                │
│  - Claude CLI subprocess 驱动                    │
│  - stdin/stdout JSON 流双向通信                   │
│  - Permission/Question 代理转发                   │
│  - 文件系统 API                                   │
│  - 消息持久化                                     │
└───────────────────┬─────────────────────────────┘
                    │ asyncio subprocess
                    │ --input-format stream-json
                    │ --output-format stream-json
                    │ --print
┌───────────────────▼─────────────────────────────┐
│  Claude Code CLI Process                         │
└─────────────────────────────────────────────────┘
```

## 10. 关键设计决策

1. **一个 Session = 一个 Claude CLI 子进程**，通过 `--session-id` 绑定
2. **本地 SQLite** 管理所有数据，不依赖 CLI 的记忆机制
3. **所有 CLI 参数都可前端配置**，Session 创建时传入
4. **Permission/Question 代理**：CLI 请求 → 后端转发 → 前端弹窗 → 用户选择 → 后端回传 stdin
5. **测试与开发数据库隔离**：测试使用内存 SQLite

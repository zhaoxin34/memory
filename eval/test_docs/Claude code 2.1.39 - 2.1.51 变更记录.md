本文档整理了 Claude Code 从版本 2.1.39 到 2.1.51 的主要新功能和变更，按功能类别进行组织。

---

## 新增功能

### CLI 命令与子命令

- **remote-control 子命令**: 新增 `claude remote-control` 子命令，支持外部构建，允许本地环境为所有用户服务
- **claude agents 命令**: 新增 `claude agents` CLI 命令列出所有配置的代理
- **认证子命令**: 新增 `claude auth login/status/logout` 子命令
- **Worktree 支持**: 新增 `--worktree` (`-w`) 标志启动隔离的 git worktree
- **VSCode 支持**: 添加 `/extra-usage` 命令支持

### Agent 与 Subagent

- **Agent 工作树隔离**: Agent 定义支持 `isolation: worktree`，允许在隔离的 git worktree 中运行
- **后台代理**: Agent 定义支持 `background: true` 始终作为后台任务运行

### Hook 事件

- **Worktree Hook 事件**: 新增 `WorktreeCreate` 和 `WorktreeRemove` hook 事件，支持在代理 worktree 隔离创建/删除时进行自定义 VCS 设置
- **ConfigChange Hook**: 新增配置变更时触发的 hook 事件

### 模型支持

- **Claude Sonnet 4.6**: 支持新的 Sonnet 4.6 模型
- **Opus 4.6 快速模式**: 现在包含完整的 1M 上下文窗口
- **1M 上下文控制**: 新增 `CLAUDE_CODE_DISABLE_1M_CONTEXT` 环境变量禁用 1M 上下文窗口支持

### 插件系统

- **自定义 npm 注册表**: 支持安装插件时使用自定义 npm 注册表和指定版本固定
- **插件默认配置**: 插件可以包含 `settings.json` 提供默认配置
- **MCP 连接器支持**: 支持在 Claude Code 中使用 claude.ai MCP 连接器

### SDK 增强

- **环境变量**: 新增 `CLAUDE_CODE_ACCOUNT_UUID`、`CLAUDE_CODE_USER_EMAIL`、`CLAUDE_CODE_ORGANIZATION_UUID` 环境变量供 SDK 调用者同步提供账户信息
- **速率限制事件**: 新增 `SDKRateLimitInfo` 和 `SDKRateLimitEvent` 类型
- **LSP 服务器超时配置**: 支持 `startupTimeout` 配置
- **SDK 模型信息**: SDK 模型信息新增 `supportsEffort`、`supportedEffortLevels`、`supportsAdaptiveThinking` 字段

### 配置与设置

- **目录配置读取**: 支持从 `--add-dir` 目录读取 `enabledPlugins` 和 `extraKnownMarketplaces`
- **自定义提示**: 新增 `spinnerTipsOverride` 设置自定义旋转提示
- **/model 选择器改进**: 显示人类可读的模型标签（如 "Sonnet 4.5"），而非原始模型 ID
- **自动命名会话**: `/rename` 无参数时自动从对话上下文生成会话名

### 平台支持

- **Windows ARM64**: 新增 Windows ARM64 (win32-arm64) 原生二进制支持

### 其他

- **Simple 模式增强**: Simple 模式现在包含文件编辑工具
- **插件 Git 超时配置**: 插件市场默认 Git 超时从 30s 增加到 120s，新增 `CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS` 环境变量配置
- **MCP OAuth 改进**: 改进 OAuth 认证，支持 step-up auth 和发现缓存

---

## 性能优化

### 启动性能

- 改进无头模式（`-p` 标志）启动性能
- 改进非交互模式启动性能
- 改进启动性能（延迟 Zod schema 构建）
- 改进启动性能（SessionStart hook 延迟执行，减少约 500ms）
- 改进启动性能（缓存 MCP 认证失败、减少分析 token 计算、批量 MCP tool token 计数）
- 改进启动性能（减少 eager loading of session history）
- 改进无头模式启动性能（延迟 Yoga WASM 和 UI 组件导入）

### 内存优化

- 改进长时间会话的内存使用
- 修复多个内存泄漏问题：
  - Agent Teams 中已完成任务未被垃圾回收
  - AppState 中的已完成任务状态对象
  - LSP 诊断数据
  - 已完成任务输出
  - TaskOutput 保留的最近行
  - CircularBuffer 中未释放的项目
  - Shell 命令执行中的 ChildProcess 和 AbortController 引用
  - 代理任务消息历史
  - API 流缓冲区、代理上下文、技能状态
  - 文件历史快照限制
  - Yoga WASM 线性内存增长
- 改进长时间会话内存使用（处理后清除大型工具结果）
- 改进长时间会话内存使用（压缩后清除内部缓存）

### 缓存与命中率

- 改进提示建议缓存命中率
- 改进提示缓存命中率（将日期移出系统提示）
- 修复提示建议缓存回归问题
- 改进 HTTP 和 SSE MCP 服务器的认证失败缓存

### 命令执行

- **BashTool 优化**: 当 shell 快照可用时，默认跳过登录 shell（`-l` 标志），提升命令执行性能
- 改进 shell 命令大输出的内存使用（RSS 不再随输出大小无限增长）

### 终端渲染

- 终端渲染性能改进

### 其他

- 改进文件提及 `@` 的性能（文件建议预热索引、使用会话缓存）
- 改进文件读取性能（非阻塞 FIFOs、`/dev/stdin`、大文件）

---

## Bug 修复

### 终端与显示

- Windows 终端渲染修复（包括 `\r\n` 问题）
- 修复终端屏幕边界字符丢失
- 修复详细转录视图中的空行
- CJK 宽字符导致时间戳和布局元素错位
- OSC 8 超链接仅在第一行可点击

### 会话管理

- 修复致命错误被吞没的问题
- 修复会话关闭后进程挂起
- 修复会话名称在 compaction 后丢失
- 修复 `/resume` 会话列表显示中断消息为标题
- 修复 `/resume` 预览显示原始 XML 标签
- 修复大型第一提示（>16KB）的会话在列表中消失
- 修复自定义会话标题在恢复后丢失
- 修复 SSH 断开时会话数据丢失

### 文件操作

- 文件写入工具保留尾随空行
- 修复 ENAMETOOLONG 错误（深层嵌套目录路径）
- 文件未找到错误现在建议纠正路径

### Agent 与 Subagent

- 修复 Agent Teams 在 Bedrock/Vertex/Foundry 上的失败问题
- 修复 Agent Teams 使用错误的模型标识符
- 修复后台任务工具崩溃（Task tool ReferenceError）
- 修复后台任务结果返回原始转录数据而非最终答案

### Hook

- 修复 hook 阻塞错误不向用户显示 stderr
- 修复 hook 阻塞错误显示 stderr 内容在 UI 中
- 修复 hooks（PreToolUse、PostToolUse）在 Windows 上静默失败

### Shell

- 修复 shell 命令永久失败（命令删除其工作目录后）
- 修复 shell 函数双下划线前缀（如 `__git_ps1`）在 shell 会话间不保留
- 修复 bash 权限分类器验证问题

### 插件与 MCP

- 修复 MCP 服务器在延迟加载后不出现在 MCP 管理对话框
- 修复斜杠命令自动完成在插件描述为非字符串类型时崩溃
- 修复技能名称/描述为裸数字时崩溃
- 修复参数提示使用 YAML 序列语法时崩溃
- 修复插件代理技能使用裸名称加载失败

### Windows 特定

- 修复 Windows CWD 跟踪临时文件未清理
- 修复同一 CLAUDE.md 文件被加载两次
- 修复 worktree 会话匹配（驱动器字母大小写不同）
- 修复 zsh heredoc 在沙箱命令中失败
- 修复图像粘贴在 WSL2 上不工作（BMP 格式）

### 其他

- 修复 `/resume` 在第一消息超过 16KB 或使用数组格式内容时静默丢弃会话
- 修复 `/mcp reconnect` 在给定不存在的服务器名时冻结 CLI
- 修复 `/rename` 后状态栏中的会话名称持续存在
- 修复用户定义的代理仅在 NFS/FUSE 文件系统上加载一个文件
- 修复自定义代理的 `model` 字段在生成团队队友时被忽略
- 修复计划模式在上下文压缩后丢失
- 修复 `alwaysThinkingEnabled: true` 在 Bedrock 和 Vertex 提供商上未启用思考模式
- 修复后台任务通知在流式传输 Agent SDK 模式下未送达

---

## 安全修复

- **Hook 安全漏洞**: 修复 `statusLine` 和 `fileSuggestion` hook 命令可能在交互模式下绕过工作区信任执行的问题
- **防止嵌套启动**: 防止在 Claude Code 会话中启动 Claude Code
- **权限设置**: 修复 `disableAllHooks` 设置尊重托管设置层次结构

---

## 用户体验改进

### 后台代理

- 使用 `ctrl+f` 杀死所有后台代理而非按两次 ESC
- 后台代理现在在您按 ESC 取消主线程时继续运行

### VSCode 集成

- **计划预览**: 改进计划预览，自动更新、仅在计划准备好时启用评论、拒绝时保持预览打开以便修改

### 权限提示

- 权限提示现在显示限制原因而非空提示
- 改进了路径安全和工作目录阻止的权限提示

### 权限管理

- 修复 "始终允许" 多行 bash 命令创建无效权限模式
- 修复设置更改时清除陈旧权限规则

### 消息反馈

- 修复自动压缩失败错误通知显示给用户
- 修复压缩失败时显示错误通知

### 其他

- 改进了窄终端布局（提示页脚）
- 改进了折叠的读取/搜索组以显示当前正在处理的文件或搜索模式
- 修复旋转器显示 "0 tokens" 计数器（实际未收到 token 前）
- 修复旋转器不尊重自定义 spinnerVerbs

---

## 版本遗漏说明

- **2.1.48**: 该版本在 CHANGELOG 中未列出，可能是一个内部版本或跳过了
- **2.1.40**: 该版本在 CHANGELOG 中未列出

---

_文档生成时间: 2026-02-24_

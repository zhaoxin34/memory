> 官方文档：[Remote Control](https://code.claude.com/docs/en/remote-control)

## 什么是 Remote Control？

Remote Control（远程控制）让你可以在手机、平板或任何浏览器上继续使用本地 Claude Code 会话。支持 [claude.ai/code](https://claude.ai/code) 和 Claude 手机应用（iOS/Android）。

### 核心特性

- **完整的本地环境**：你的文件系统、MCP 服务器、工具和项目配置都保持可用
- **多设备同步**：对话在所有连接的设备间保持同步，可以从终端、浏览器和手机交替发送消息
- **抗中断能力**：如果笔记本睡眠或网络断开，会话会自动重新连接

> [!NOTE]
> Remote Control 目前是 Pro 和 Max 计划的研究预览版，不适用于 Team 或 Enterprise 计划。

## 前置要求

使用 Remote Control 前，请确认满足以下条件：

1. **订阅**：需要 Pro 或 Max 计划，不支持 API 密钥
2. **认证**：运行 `claude` 并使用 `/login` 通过 claude.ai 登录
3. **工作区信任**：至少在项目目录中运行一次 `claude` 来接受工作区信任对话框

## 启动 Remote Control 会话

有两种方式启动远程控制会话：

### 方式一：直接启动新会话

```bash
claude remote-control
```

进程会在终端中保持运行，等待远程连接。它会显示一个会话 URL，用于从其他设备连接。按空格键可以显示 QR 码以便手机快速扫描。

支持的参数：

- `--verbose`：显示详细的连接和会话日志
- `--sandbox` / `--no-sandbox`：启用或禁用沙箱（文件系统和网络隔离）。默认关闭

### 方式二：从现有会话连接

如果你已经在 Claude Code 会话中，想远程继续，使用 `/remote-control`（或 `/rc`）命令：

```bash
/remote-control
# 或简写
/rc
```

## 从其他设备连接

一旦 Remote Control 会话启动，可以通过以下方式连接：

1. **打开会话 URL**：在浏览器中直接访问 [claude.ai/code](https://claude.ai/code)
2. **扫描 QR 码**：使用 Claude 手机应用扫描显示的 QR 码
3. **在应用中查找**：打开 claude.ai/code 或 Claude 应用，在会话列表中找到会话（显示带绿色状态点的电脑图标）

会话名称来自你最后的消息、`/rename` 的值，如果没有对话历史则显示 "Remote Control session"。

## 启用所有会话自动开启 Remote Control

默认情况下，Remote Control 只有在显式运行 `claude remote-control` 或 `/remote-control` 时才激活。

要自动为每个会话启用，运行 `/config` 并将 **Enable Remote Control for all sessions** 设置为 `true`。

> 每个 Claude Code 实例一次只支持一个远程会话。

## 连接与安全

- 你的本地 Claude Code 会话仅发起出站 HTTPS 请求，不会打开入站端口
- 所有流量通过 Anthropic API 的 TLS 传输
- 连接使用多个短生命周期凭证，每个凭证仅限于单一用途并独立过期

## Remote Control vs Claude Code 网页版

| 特性         | Remote Control | Claude Code 网页版   |
| ------------ | -------------- | -------------------- |
| 会话运行位置 | 本地机器       | Anthropic 云基础设施 |
| MCP 服务器   | 保持可用       | 不可用               |
| 本地文件访问 | ✅             | ❌                   |

**使用场景**：

- 使用 Remote Control：当你在进行本地工作，想从另一设备继续
- 使用 Claude Code 网页版：当你不想本地设置就想开始任务、克隆你没有的仓库，或并行运行多个任务

## 限制

1. **一次一个远程会话**：每个 Claude Code 会话只支持一个远程连接
2. **终端必须保持打开**：Remote Control 作为本地进程运行，关闭终端或停止进程会导致会话结束
3. **网络中断**：如果机器开机但无法访问网络超过约 10 分钟，会话会超时并退出

---

_本文档基于 [官方 Remote Control 文档](https://code.claude.com/docs/en/remote-control) 编写_

## Context

当前系统已有基于 structlog 的日志模块（`src/memory/observability/logging.py`），但仅支持控制台输出。系统日志无法持久化到文件，CLI 命令调用也没有记录机制。在生产环境中，无法通过日志排查历史问题，也无法追溯用户的操作记录。

## Goals / Non-Goals

**Goals:**
- 实现系统日志文件输出，支持按日期轮转
- 实现 CLI 调用记录功能，记录命令名称、参数、执行时间、执行结果
- 系统日志和 CLI 日志使用独立的日志器和日志文件
- 配置简单，与现有 structlog 模块良好集成

**Non-Goals:**
- 不实现日志上传到远程服务器（如 Loki、ELK）
- 不实现复杂的日志级别动态调整
- 不修改现有代码中已有的日志调用方式（保持兼容性）

## Decisions

### 1. 日志框架选择

**决策**: 继续使用现有的 structlog，扩展文件输出能力。

**理由**:
- 现有代码已深度集成 structlog，换框架成本高
- structlog 支持多种 renderer，便于扩展

**替代方案考虑**:
- Python logging + handlers: 需要重写现有日志调用，工作量大
- loguru: 语法更简洁，但与现有代码风格不一致

### 2. 日志轮转方案

**决策**: 使用 `logging.handlers.TimedRotatingFileHandler` 配合 structlog。

**理由**:
- Python 标准库，无需额外依赖
- 按天轮转，满足大多数场景需求
- 自动清理过期日志（通过 `when='midnight'` + `interval=1`）

**替代方案考虑**:
- 手动实现轮转: 工作量大，容易出错
-第三方库如 `python-rotating-handlers`: 增加依赖

### 3. 日志目录结构

**决策**: 日志目录为 `~/.memory/logs/`，包含：
- `system.log` - 系统日志（当日文件）
- `system-YYYY-MM-DD.log` - 轮转后的系统日志
- `cli-audit.log` - CLI 调用记录（当日文件）
- `cli-audit-YYYY-MM-DD.log` - 轮转后的 CLI 日志

**理由**:
- 放在用户数据目录下（`~/.memory/`），便于管理
- 与项目的数据存储路径保持一致
- 文件名清晰，便于识别和查找

### 4. CLI 审计日志格式

**决策**: 使用 JSON Lines 格式（每行一个 JSON 对象）。

**理由**:
- 便于后续程序解析和分析
- 与系统日志的 JSON 模式保持一致
- 支持流式写入，性能好

**日志字段**:
```json
{
  "timestamp": "2026-02-28T10:00:00Z",
  "command": "memory ingest",
  "args": ["--repo", "notes", "file.md"],
  "exit_code": 0,
  "duration_ms": 1234,
  "user": "zhaoxin"
}
```

### 5. 配置方式

**决策**: 在现有配置系统（TOML）中添加日志相关配置。

**配置项**:
```toml
[logging]
level = "INFO"           # 日志级别
log_dir = "~/.memory/logs"  # 日志目录
max_days = 30            # 日志保留天数
enable_file = true       # 是否启用文件日志

[logging.audit]
enable = true            # 是否启用 CLI 审计日志
```

## Risks / Trade-offs

| 风险 | 描述 | 缓解措施 |
|------|------|----------|
| 日志目录不存在 | `~/.memory/logs/` 目录可能不存在 | 首次写入时自动创建目录 |
| 磁盘空间不足 | 长时间运行可能积累大量日志 | 通过 `max_days` 配置自动清理 |
| 日志写入阻塞 I/O | 同步写入可能影响性能 | 使用缓冲写入，或考虑异步 |
| 权限问题 | 无法创建日志目录或写入文件 | 捕获异常，提供友好的错误提示 |

## Migration Plan

1. 修改 `src/memory/observability/logging.py`，添加文件输出支持
2. 添加新的 `get_audit_logger()` 函数用于 CLI 审计
3. 在 `src/memory/config/schema.py` 添加日志配置模型
4. 更新 CLI 入口点，在命令执行前后记录审计日志
5. 测试日志轮转功能

## Open Questions

- [ ] 是否需要支持日志压缩（.gz）？
- [ ] CLI 审计日志是否需要记录命令输出内容（可能包含敏感信息）？
- [ ] 是否需要支持日志级别动态调整（如通过信号）？

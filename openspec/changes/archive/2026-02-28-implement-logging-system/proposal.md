## Why

当前系统缺少结构化的日志输出能力，所有日志都输出到控制台，无法满足生产环境的问题排查需求。同时，CLI 命令的调用记录也没有被持久化，无法追溯用户的操作历史。这两个日志功能是独立的需求，应该分别实现。

## What Changes

- 实现系统日志功能，支持将 debug/info/warn/error 日志输出到文件
- 实现 CLI 调用记录功能，记录用户每次执行的命令（名称、参数、执行时间、执行结果）
- 系统日志和 CLI 日志使用独立的日志器和文件输出
- 支持按日期轮转日志文件，避免单文件过大

## Capabilities

### New Capabilities

- `system-logging`: 系统日志功能，提供结构化的 debug/info/warn/error 日志，支持文件输出和日志轮转
- `cli-audit-log`: CLI 调用记录功能，记录用户每次执行的命令操作，用于审计和追溯

### Modified Capabilities

无

## Impact

- 可能需要更新现有代码的日志调用方式
- 添加配置文件中的日志相关配置项

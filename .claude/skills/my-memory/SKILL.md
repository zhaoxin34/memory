---
name: my-memory
description: 个人知识库管理技能，当用户想要查询、导入、管理知识库时，调用本技能。个人知识库也称作“我的知识库”
license: MIT
metadata:
  author: zhaoxin
  version: "1.1"
---

## 使用指南

使用 my-memory.sh 脚本管理知识库

---

## 命令参考

### 搜索知识库

```bash
my-memory.sh search "关键词"
```

### 导入文档

```bash
my-memory.sh ingest /path/to/file
```

### 列出所有仓库

```bash
my-memory.sh list
```

### 查看仓库信息

```bash
my-memory.sh info [仓库名]
```

### 清空仓库

```bash
my-memory.sh clear [仓库名]
```

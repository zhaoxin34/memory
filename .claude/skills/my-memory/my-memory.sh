#!/bin/bash
# my-memory wrapper script

# 默认仓库
DEFAULT_REPO="my-obsidian"

# 帮助信息
show_help() {
  echo "Usage: my-memory <command> [options]"
  echo ""
  echo "Commands:"
  echo "  search <query>       搜索知识库"
  echo "  sync                同步文档（从仓库根目录）"
  echo "  create <root> [pat] 创建仓库（指定根目录和可选的文件模式）"
  echo "  list                列出所有仓库"
  echo "  info [repo]         查看仓库信息"
  echo "  clear <repo>        清空仓库文档"
  echo ""
  echo "Examples:"
  echo "  my-memory search \"Python 技巧\""
  echo "  my-memory sync"
  echo "  my-memory create /path/to/docs \"*.md\""
  echo "  my-memory list"
}

# 搜索
cmd_search() {
  local query="$1"
  if [ -z "$query" ]; then
    echo "Error: 请输入搜索关键词"
    exit 1
  fi
  memory search "$query" --repository "$DEFAULT_REPO" --top-k 1 --output json
}

# 同步文档
cmd_sync() {
  memory sync --repository "$DEFAULT_REPO"
}

# 创建仓库
cmd_create() {
  local root_path="$1"
  local pattern="$2"
  if [ -z "$root_path" ]; then
    echo "Error: 请输入根目录路径"
    exit 1
  fi
  if [ -n "$pattern" ]; then
    memory repo create "$DEFAULT_REPO" --root-path "$root_path" --pattern "$pattern"
  else
    memory repo create "$DEFAULT_REPO" --root-path "$root_path"
  fi
}

# 列出仓库
cmd_list() {
  memory repo list
}

# 仓库信息
cmd_info() {
  local repo="${1:-$DEFAULT_REPO}"
  memory repo info "$repo"
}

# 清空仓库
cmd_clear() {
  local repo="${1:-$DEFAULT_REPO}"
  read -p "确定要清空仓库 $repo 吗？(y/n) " confirm
  if [ "$confirm" = "y" ]; then
    memory repo clear "$repo"
  fi
}

# 主逻辑
case "$1" in
search)
  cmd_search "$2"
  ;;
sync)
  cmd_sync
  ;;
create)
  cmd_create "$2" "$3"
  ;;
list)
  cmd_list
  ;;
info)
  cmd_info "$2"
  ;;
clear)
  cmd_clear "$2"
  ;;
-h | --help | help)
  show_help
  ;;
*)
  echo "未知命令: $1"
  show_help
  exit 1
  ;;
esac

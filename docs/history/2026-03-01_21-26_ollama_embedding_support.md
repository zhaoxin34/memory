# 修改记录

## 2026-03-01

### feat: 添加 Ollama embedding provider 支持

**变更描述**

添加了使用本地 Ollama 服务提供 embedding 的能力。通过 OpenAI 兼容 API 接口，用户可以在本地运行 Ollama 服务来生成向量嵌入，无需依赖外部云服务。

**变更详情**

- **config/schema.py**: 在 `EmbeddingProviderType` 枚举中添加 `OLLAMA = "ollama"` 类型
- **providers/openai.py**:
  - 添加 Ollama 模型元数据：`nomic-embed-text` (768维), `mxbai-embed-large` (1024维), `bge-m3` (1024维)
  - 修改 API key 验证逻辑：当使用自定义 base_url 时跳过 api_key 验证（Ollama 本地服务不需要 API key）
- **providers/__init__.py**: 在 `create_embedding_provider()` 中支持 ollama 类型，自动转换为 openai provider
- **config.toml**: 配置使用 ollama + bge-m3 模型，base_url 设置为 `http://localhost:11434/v1`

**相关文件**

- `/Volumes/data/working/life/memory/config.toml`
- `/Volumes/data/working/life/memory/src/memory/config/schema.py`
- `/Volumes/data/working/life/memory/src/memory/providers/openai.py`
- `/Volumes/data/working/life/memory/src/memory/providers/__init__.py`

**使用方法**

1. 确保 Ollama 服务运行在 localhost:11434
2. 拉取 embedding 模型：`ollama pull bge-m3`
3. 配置文件中设置：
   ```toml
   provider = "ollama"
   model_name = "bge-m3"

   [embedding.extra_params]
   base_url = "http://localhost:11434/v1"
   ```

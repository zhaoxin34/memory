# Memory 项目与 Docling 集成可行性调研报告

## 执行摘要

本报告调研了 Memory 个人知识库系统与 Docling 文档理解库集成的技术可行性。调研结果表明，Docling 能有效填补 Memory 在 PDF/HTML 文档处理方面的能力短板。推荐采用**预处理层集成方案**，通过最小改动实现 Docling 与现有 ingestion pipeline 的无缝对接。

---

## 1. Memory 项目文档处理现状分析

### 1.1 当前支持的文件格式

| 文件类型 | 扩展名 | 支持状态 | 实现方式 |
|---------|--------|---------|---------|
| Markdown | .md, .markdown | **完整支持** | 智能语义分块 |
| PDF | .pdf | ⚠️ 仅标记类型 | `read_text()` 原始文本提取 |
| HTML | .html, .htm | ⚠️ 仅标记类型 | `read_text()` 原始文本提取 |
| 纯文本 | .txt | **完整支持** | 固定大小分块 |

### 1.2 当前 PDF/HTML 处理流程

**问题核心**：`ingestion.py` 中的文件读取仅使用简单的文本读取：

```python
# src/memory/pipelines/ingestion.py 行 333
content = file_path.read_text(encoding="utf-8")
```

**存在问题**：
- PDF 文件作为二进制格式，直接 `read_text()` 无法正确解析
- HTML 文件仅提取原始文本，丢失文档结构
- 表格、图像、标题层级等结构化信息完全丢失
- 无法利用 PDF 的视觉布局信息

### 1.3 DocumentType 枚举定义

```python
# src/memory/core/models.py
class DocumentType(str, Enum):
    MARKDOWN = "markdown"
    PDF = "pdf"
    HTML = "html"
    TEXT = "text"
    UNKNOWN = "unknown"
```

当前 PDF 和 HTML 仅为标记类型，无实际解析逻辑支撑。

### 1.4 文档导入流程

```
┌─────────────────────────────────────────────────────────────┐
│                    IngestionPipeline                        │
├─────────────────────────────────────────────────────────────┤
│  File → 读取内容 → 检测类型 → Document → 分块 → 嵌入 → 存储  │
└─────────────────────────────────────────────────────────────┘

当前问题：PDF/HTML 在"读取内容"步骤仅得到无结构的原始文本
```

---

## 2. Docling 核心能力介绍

> Docling 是专注于文档理解的开源库，提供专业级的 PDF 和 HTML 解析能力。

### 2.1 核心功能特性

| 功能 | 描述 |
|-----|------|
| **PDF 解析** | 保留文档结构（标题层级、段落、列表） |
| **表格识别** | 准确提取表格数据和结构，支持复杂表格 |
| **图像处理** | 支持 OCR 文字识别，提取图表描述 |
| **布局分析** | 理解文档的视觉结构和阅读顺序 |
| **表单识别** | 识别 PDF 表单字段和结构 |

### 2.2 输出格式支持

| 格式 | 描述 |
|-----|------|
| **Markdown** | 保留文档结构的纯文本格式 |
| **JSON** | 结构化数据表示，包含完整元数据 |
| **文本** | 纯文本提取 |
| **HTML** | 保留格式的 HTML 输出 |

### 2.3 使用方式

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("document.pdf")

# 导出为 Markdown
markdown = result.document.export_to_markdown()

# 导出为 JSON
json_data = result.document.export_to_dict()
```

---

## 3. 集成技术方案

### 3.1 推荐方案：预处理层集成

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Memory Ingestion Pipeline                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Input File                                                         │
│       │                                                               │
│       ├───► .md/.txt ──────────────────────► 现有流程                 │
│       │                                                               │
│       ├───► .pdf/.html ───────────────────► Docling 预处理           │
│       │         │                            │                        │
│       │         └──► Converter ─────────────► Markdown 输出            │
│       │                                       │                        │
│       └──────────────────────────────────────┴──────────► 统一流程   │
│                                                              │       │
│                                              智能分块 + 嵌入生成 + 存储 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**设计原则**：
1. **最小改动**：仅在 ingestion pipeline 入口处添加预处理层
2. **格式统一**：Docling 输出 Markdown，与现有智能分块兼容
3. **可配置**：可选择是否启用 Docling（作为可选依赖）
4. **可替换**：预处理层抽象为接口，便于后续替换

### 3.2 集成点设计

```python
# src/memory/preprocessors/base.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import NamedTuple

class PreprocessedDocument(NamedTuple):
    """预处理后的文档结果"""
    content: str
    metadata: dict[str, Any]

class DocumentPreprocessor(ABC):
    """文档预处理器抽象接口"""

    @abstractmethod
    async def convert(self, file_path: Path) -> PreprocessedDocument:
        """将文件转换为结构化文档"""
        pass

    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """检查是否支持该文件类型"""
        pass

# src/memory/preprocessors/docling.py
class DoclingPreprocessor(DocumentPreprocessor):
    """基于 Docling 的文档预处理器"""

    def __init__(self, output_format: str = "markdown"):
        self.converter = DocumentConverter()
        self.output_format = output_format

    async def convert(self, file_path: Path) -> PreprocessedDocument:
        result = self.converter.convert(str(file_path))

        if self.output_format == "markdown":
            content = result.document.export_to_markdown()
        elif self.output_format == "json":
            content = result.document.export_to_json()
        else:
            content = result.document.export_to_text()

        return PreprocessedDocument(
            content=content,
            metadata={
                "num_tables": len(result.document.tables),
                "num_images": len(result.document.images),
                "document_format": result.document.format.name
            }
        )

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in {".pdf", ".html", ".htm"}
```

### 3.3 ingestion.py 集成示例

```python
# src/memory/pipelines/ingestion.py 修改

class IngestionPipeline:
    def __init__(
        self,
        repository_id: UUID,
        preprocessor: DocumentPreprocessor | None = None
    ):
        # ... 现有初始化代码 ...
        self.preprocessor = preprocessor

    async def ingest_file(
        self,
        file_path: Path,
        repository_id: UUID | None = None,
    ) -> ProcessingResult:
        """导入文件到知识库"""

        # 检测是否需要预处理
        if self.preprocessor and self.preprocessor.supports(file_path):
            converted = await self.preprocessor.convert(file_path)
            content = converted.content
            doc_type = DocumentType.MARKDOWN  # Docling 输出视为 Markdown
            # 保留 Docling 特有的元数据
        else:
            content = file_path.read_text(encoding="utf-8")
            doc_type = self._detect_document_type(file_path)

        # ... 其余处理流程不变 ...
```

---

## 4. 深入集成选项

### 4.1 Docling 特有元数据利用

Docling 提取的结构化信息可以作为额外元数据存储：

| 元数据 | 用途 |
|-------|------|
| `num_tables` | 统计文档中的表格数量 |
| `num_images` | 统计图像数量 |
| `table_data` | 表格的完整结构化数据 |
| `image_ocr` | 图像中的文字内容 |
| `document_format` | 原始文档格式信息 |

```python
# 表格智能问答示例
async def answer_about_table(
    self,
    query: str,
    document_id: UUID
) -> str:
    """基于表格内容回答问题"""
    doc = await self.metadata_store.get_document(document_id)
    tables = doc.metadata.get("table_data", [])
    table_context = "\n".join([
        f"表格 {i+1}:\n{table.content}"
        for i, table in enumerate(tables)
    ])
    # 使用 LLM 基于表格内容生成回答
```

### 4.2 图像描述集成

```python
# 存储图像描述
image_metadata = {
    "images": [
        {
            "index": 0,
            "description": result.document.images[0].description,
            "page": result.document.images[0].page_no
        }
    ]
}
```

### 4.3 结构化搜索增强

```python
# 按标题层级搜索
async def search_by_heading_level(
    self,
    query: str,
    min_level: int = 1,
    max_level: int = 6
) -> list[SearchResult]:
    """搜索指定标题层级内的内容"""
    chunks = await self.metadata_store.get_chunks_by_document(doc_id)
    filtered = [
        c for c in chunks
        if min_level <= c.metadata.get("heading_level", 0) <= max_level
    ]
    # ... 执行搜索 ...
```

---

## 5. 实现路线图

### Phase 1：基础预处理层（1-2 周）

| 任务 | 描述 | 产出 |
|-----|------|-----|
| 创建预处理接口 | 定义 `DocumentPreprocessor` 抽象类 | `src/memory/preprocessors/base.py` |
| 实现 Docling 处理器 | 创建 `DoclingPreprocessor` 类 | `src/memory/preprocessors/docling.py` |
| 集成到 pipeline | 修改 `ingestion.py` 添加预处理钩子 | 修改 `src/memory/pipelines/ingestion.py` |

### Phase 2：元数据增强（1 周）

| 任务 | 描述 | 产出 |
|-----|------|-----|
| 表格元数据存储 | 在 Document metadata 中保存表格信息 | 修改 `src/memory/core/models.py` |
| 图像元数据存储 | 保存图像描述和 OCR 结果 | 修改 `models.py` |
| 查询增强 | 支持基于结构化数据的问答 | 新增查询方法 |

### Phase 3：配置化和可选依赖（1 周）

| 任务 | 描述 | 产出 |
|-----|------|-----|
| 配置项添加 | 在 schema.py 中添加 docling 配置 | 修改 `src/memory/config/schema.py` |
| 可选依赖声明 | 在 pyproject.toml 中添加 | 修改 `pyproject.toml` |
| 降级处理 | Docling 不可用时回退原始提取 | 完善错误处理 |

### Phase 4：高级特性（可选）

| 任务 | 描述 |
|-----|------|
| 表格智能问答 | 基于表格内容的问答功能 |
| 图像搜索 | 利用图像描述进行搜索 |
| 复杂布局处理 | 保留复杂 PDF 布局信息 |

---

## 6. 依赖管理

### 6.1 添加可选依赖

```toml
# pyproject.toml
[project.optional-dependencies]
docling = ["docling>=2.0"]
```

### 6.2 安装方式

```bash
# 基础安装
uv sync

# 包含 Docling 支持
uv sync --extra docling
```

### 6.3 条件导入

```python
# src/memory/preprocessors/docling.py

def _check_docling_available() -> bool:
    """检查 Docling 是否已安装"""
    try:
        import docling
        return True
    except ImportError:
        return False

class DoclingPreprocessor:
    """基于 Docling 的文档预处理器"""

    def __init__(self, output_format: str = "markdown"):
        if not _check_docling_available():
            raise ImportError(
                "Docling 未安装。请运行 'uv sync --extra docling' 安装。"
            )
        from docling.document_converter import DocumentConverter
        self.converter = DocumentConverter()
        self.output_format = output_format
```

---

## 7. 风险与注意事项

### 7.1 风险评估

| 风险项 | 影响程度 | 缓解措施 |
|-------|---------|---------|
| Docling 依赖较大 | 低 | 可选依赖，不强制安装 |
| PDF 解析性能 | 中 | 异步处理，考虑缓存 |
| API 兼容性变化 | 中 | 固定版本，锁定兼容性 |
| 内存占用 | 中 | 流式处理大批量文件 |

### 7.2 注意事项

1. **版本锁定**：在 `pyproject.toml` 中指定兼容的 Docling 版本
2. **内存管理**：大批量 PDF 处理时注意内存使用
3. **错误处理**：Docling 解析失败时应回退到原始文本提取
4. **增量处理**：复用现有 MD5 智能覆盖机制，避免重复处理

---

## 8. 结论与建议

### 8.1 主要结论

1. **高度可行**：预处理层集成方案改动小，风险低
2. **收益显著**：填补 PDF/HTML 处理短板，提升文档理解能力
3. **兼容性好**：Docling 输出 Markdown，与现有智能分块无缝对接
4. **灵活可控**：作为可选依赖，不影响现有用户

### 8.2 实施建议

1. **立即可行**：Phase 1 可在 1-2 周内完成
2. **按需扩展**：根据实际需求选择实现哪些 Phase
3. **渐进增强**：从基础预处理开始，逐步添加高级特性
4. **保持简洁**：避免过度设计，优先解决核心问题

### 8.3 不实施的理由

当前不考虑此方案的理由：
- 需要评估实际 PDF 处理需求的频率
- Docling 作为重型依赖，需权衡收益与成本
- 可先使用简单的 PDF 文本提取作为过渡

---

## 参考资料

- Memory 项目源码：`/Volumes/data/working/life/memory/src/memory/`
- Docling 项目：https://github.com/docling-project/docling
- Docling 文档：https://docling-project.github.io/docling/

---

**报告生成日期**：2026-02-13
**调研范围**：Memory 项目文档处理现状、Docling 核心能力、集成技术方案
**建议保存路径**：`/Volumes/data/working/life/memory/docs/docling_integration_report.md`

## 结论

2026-02-13 暂时记录调研结果，待后续评估是否需要实现。

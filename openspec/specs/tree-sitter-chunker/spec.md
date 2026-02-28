# tree-sitter-chunker Specification

## Purpose
TBD - created by archiving change rewrite-markdown-chunking-with-tree-sitter. Update Purpose after archive.
## Requirements
### Requirement: Markdown syntax tree parsing

The system SHALL use tree-sitter-markdown to parse Markdown documents into an accurate syntax tree for intelligent chunking.

#### Scenario: Parse basic headings
- **WHEN** a Markdown document with multiple heading levels is parsed
- **THEN** the syntax tree SHALL correctly identify heading nodes with their levels (H1-H6)

#### Scenario: Parse nested lists
- **WHEN** a Markdown document contains nested lists (indented sub-items)
- **THEN** the syntax tree SHALL represent list items with proper parent-child relationships

#### Scenario: Parse tables
- **WHEN** a Markdown document contains a table with `|` separators
- **THEN** the syntax tree SHALL identify table, table_row, and table_cell nodes

#### Scenario: Parse code blocks
- **WHEN** a Markdown document contains fenced code blocks with language tags
- **THEN** the syntax tree SHALL identify code_block nodes with language metadata

### Requirement: Semantic chunk creation from syntax tree

The system SHALL create chunks based on syntax tree nodes while respecting semantic boundaries.

#### Scenario: Preserve complete heading context
- **WHEN** a heading and its following paragraphs are within target_size
- **THEN** they SHALL be combined into a single chunk with the heading as context

#### Scenario: Split at paragraph boundaries
- **WHEN** paragraphs exceed target_size individually
- **THEN** chunks SHALL be split at paragraph boundaries, never in the middle of a paragraph

#### Scenario: Keep list items intact
- **WHEN** a list item is part of a chunk
- **THEN** the list item SHALL NOT be split across multiple chunks

#### Scenario: Preserve table integrity
- **WHEN** a table is small enough to fit in target_size
- **THEN** the entire table (header + all rows) SHALL be in a single chunk

#### Scenario: Handle large code blocks
- **WHEN** a fenced code block exceeds target_size
- **THEN** the code block SHALL be split at blank lines or function boundaries

### Requirement: Fallback to fixed-size chunking

The system SHALL gracefully fall back to fixed-size chunking when tree-sitter parsing fails.

#### Scenario: Missing tree-sitter parser
- **WHEN** tree-sitter-markdown parser is not available
- **THEN** the system SHALL fall back to fixed-size chunking with overlap

#### Scenario: Invalid Markdown syntax
- **WHEN** the Markdown document contains unparseable syntax
- **THEN** the system SHALL log a warning and fall back to fixed-size chunking

#### Scenario: Parser timeout
- **WHEN** parsing takes longer than 5 seconds
- **THEN** the system SHALL cancel parsing and fall back to fixed-size chunking


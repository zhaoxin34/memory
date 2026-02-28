# markdown-semantic-boundary Specification

## Purpose
TBD - created by archiving change rewrite-markdown-chunking-with-tree-sitter. Update Purpose after archive.
## Requirements
### Requirement: Semantic boundary detection

The system SHALL detect semantic boundaries in Markdown documents to prevent inappropriate chunk splitting.

#### Scenario: Never split mid-sentence
- **WHEN** a paragraph contains a sentence that spans multiple lines
- **THEN** the chunk boundary SHALL NOT be placed in the middle of that sentence

#### Scenario: Respect sentence-ending punctuation
- **WHEN** determining chunk boundaries in a paragraph
- **THEN** boundaries SHALL be placed only after sentence-ending punctuation (`.`, `!`, `?`)

#### Scenario: Preserve clause integrity
- **WHEN** a sentence contains commas or semicolons
- **THEN** chunk boundaries SHALL NOT split within the clause

### Requirement: Context preservation for headings

The system SHALL preserve heading context across chunks to maintain document structure.

#### Scenario: Heading context attachment
- **WHEN** creating a chunk from content under a heading
- **THEN** the chunk SHALL include the heading text as prefix (e.g., `# Title\n\nContent`)

#### Scenario: Nested heading context
- **WHEN** content is under multiple nested headings
- **THEN** the nearest ancestor heading SHALL be included as context

#### Scenario: Context for continuation
- **WHEN** a chunk is continued from a previous split
- **THEN** the heading context SHALL NOT be duplicated

### Requirement: Overlap strategy for semantic continuity

The system SHALL use overlap to maintain semantic continuity across chunk boundaries.

#### Scenario: Overlap at paragraph boundaries
- **WHEN** chunk_size forces a split within a paragraph
- **THEN** the overlap SHALL include the last complete sentence of the previous chunk

#### Scenario: Heading overlap
- **WHEN** a chunk boundary falls within a heading's subsection
- **THEN** the next chunk SHALL start with the subsection heading

#### Scenario: List item overlap
- **WHEN** a list spans multiple chunks
- **THEN** the incomplete list items from the previous chunk SHALL be included in the next

### Requirement: Chunk metadata for semantic type

The system SHALL store semantic type information in chunk metadata for retrieval quality.

#### Scenario: Mark heading chunks
- **WHEN** a chunk is primarily a heading
- **THEN** metadata SHALL include `chunk_type: "heading"`

#### Scenario: Mark code chunks
- **WHEN** a chunk contains a fenced code block
- **THEN** metadata SHALL include `chunk_type: "code"`

#### Scenario: Mark table chunks
- **WHEN** a chunk contains a Markdown table
- **THEN** metadata SHALL include `chunk_type: "table"`

#### Scenario: Mark list chunks
- **WHEN** a chunk contains primarily list items
- **THEN** metadata SHALL include `chunk_type: "list"`


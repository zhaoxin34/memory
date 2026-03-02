## ADDED Requirements

### Requirement: BM25 embedding generation
The system SHALL generate BM25 sparse vectors for text documents using ChromaDB's built-in BM25 embedding function.

#### Scenario: Generate BM25 embedding for single text
- **WHEN** BM25 embedding function is called with a single text string
- **THEN** system returns a sparse vector with term frequencies and IDF weights

#### Scenario: Generate BM25 embeddings for batch text
- **WHEN** BM25 embedding function is called with multiple text strings
- **THEN** system returns a list of sparse vectors, one for each input text

### Requirement: BM25 parameters configuration
The system SHALL support configurable BM25 parameters (k, b, avg_doc_length).

#### Scenario: Custom BM25 parameters
- **WHEN** user configures BM25 parameters in config file
- **THEN** system uses the configured values when generating embeddings

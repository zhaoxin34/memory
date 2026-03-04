## ADDED Requirements

### Requirement: Hybrid search with vector and BM25
The system SHALL support hybrid search combining vector similarity search and BM25 keyword search using Reciprocal Rank Fusion (RRF).

#### Scenario: Hybrid search returns combined results
- **WHEN** user performs a search query with hybrid mode enabled
- **THEN** system executes both vector search and BM25 search, then merges results using RRF formula

#### Scenario: Hybrid search respects weight configuration
- **WHEN** user configures vector/BM25 weights (e.g., 0.7/0.3)
- **THEN** system applies the configured weights when merging results

### Requirement: Configurable hybrid search
The system SHALL allow enabling/disabling hybrid search via configuration.

#### Scenario: Enable hybrid search
- **WHEN** `hybrid_search.enabled = true` in configuration
- **THEN** search operations use hybrid mode (vector + BM25)

#### Scenario: Disable hybrid search (use vector only)
- **WHEN** `hybrid_search.enabled = false` or not set in configuration
- **THEN** search operations use vector-only mode (backward compatible)

### Requirement: Hybrid search with repository filtering
The system SHALL support hybrid search within a specific repository.

#### Scenario: Hybrid search scoped to repository
- **WHEN** user performs hybrid search with repository_id specified
- **THEN** system restricts both vector and BM25 search to that repository's documents

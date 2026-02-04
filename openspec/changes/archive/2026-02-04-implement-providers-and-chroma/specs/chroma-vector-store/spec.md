## ADDED Requirements

### Requirement: Chroma client initialization
The system SHALL initialize a Chroma client with proper configuration for persistent vector storage.

#### Scenario: Successful initialization with persist directory
- **WHEN** ChromaVectorStore is initialized with a valid persist directory path
- **THEN** a Chroma client is created with persistent storage at that location

#### Scenario: Default persist directory
- **WHEN** no persist directory is specified
- **THEN** Chroma uses an in-memory database

#### Scenario: Invalid persist directory
- **WHEN** an invalid or inaccessible persist directory is specified
- **THEN** a StorageError is raised with directory access error details

### Requirement: Collection management with repository isolation
The system SHALL create and manage separate Chroma collections for each repository.

#### Scenario: Collection creation for new repository
- **WHEN** embeddings are added for a repository that doesn't have a collection
- **THEN** a new collection named "{collection_name}_{repository_name}" is created

#### Scenario: Collection reuse for existing repository
- **WHEN** embeddings are added for a repository with an existing collection
- **THEN** the existing collection is used

#### Scenario: Collection name validation
- **WHEN** a repository name contains invalid characters for Chroma
- **THEN** the name is sanitized while maintaining uniqueness

### Requirement: Single embedding storage
The system SHALL store individual embeddings with associated chunk metadata in Chroma.

#### Scenario: Successful embedding storage
- **WHEN** add_embedding() is called with an embedding and chunk
- **THEN** the embedding is stored in the appropriate repository collection with chunk metadata

#### Scenario: Duplicate embedding handling
- **WHEN** an embedding with the same chunk_id is added twice
- **THEN** the second addition updates the existing embedding

#### Scenario: Invalid embedding dimension
- **WHEN** an embedding with incorrect dimension is added
- **THEN** a StorageError is raised

### Requirement: Batch embedding storage
The system SHALL efficiently store multiple embeddings in batch mode.

#### Scenario: Successful batch storage
- **WHEN** add_embeddings_batch() is called with embeddings and chunks
- **THEN** all embeddings are stored in a single Chroma operation

#### Scenario: Empty batch handling
- **WHEN** add_embeddings_batch() is called with empty lists
- **THEN** no operation is performed and no error is raised

#### Scenario: Mismatched batch sizes
- **WHEN** embeddings and chunks lists have different lengths
- **THEN** a StorageError is raised

### Requirement: Similarity search with repository filtering
The system SHALL perform vector similarity search within specified repository collections.

#### Scenario: Repository-scoped search
- **WHEN** search() is called with a repository_id
- **THEN** only embeddings from that repository's collection are searched

#### Scenario: Global search across all repositories
- **WHEN** search() is called without a repository_id
- **THEN** all repository collections are searched

#### Scenario: Search with metadata filters
- **WHEN** search() is called with additional metadata filters
- **THEN** results are filtered by both vector similarity and metadata criteria

#### Scenario: Empty search results
- **WHEN** no embeddings match the search criteria
- **THEN** an empty list is returned

### Requirement: Embedding deletion by document
The system SHALL delete all embeddings associated with a specific document.

#### Scenario: Successful document deletion
- **WHEN** delete_by_document_id() is called with a valid document_id
- **THEN** all embeddings for that document are removed and the count is returned

#### Scenario: Non-existent document
- **WHEN** delete_by_document_id() is called with a non-existent document_id
- **THEN** zero is returned

### Requirement: Embedding deletion by chunk
The system SHALL delete embeddings for specific chunks.

#### Scenario: Successful chunk deletion
- **WHEN** delete_by_chunk_id() is called with a valid chunk_id
- **THEN** the embedding is removed and True is returned

#### Scenario: Non-existent chunk
- **WHEN** delete_by_chunk_id() is called with a non-existent chunk_id
- **THEN** False is returned

### Requirement: Embedding deletion by repository
The system SHALL delete all embeddings for a specific repository.

#### Scenario: Successful repository deletion
- **WHEN** delete_by_repository() is called with a valid repository_id
- **THEN** the entire repository collection is deleted and the count is returned

#### Scenario: Non-existent repository
- **WHEN** delete_by_repository() is called with a non-existent repository_id
- **THEN** zero is returned

### Requirement: Embedding count
The system SHALL provide the total count of stored embeddings.

#### Scenario: Count across all repositories
- **WHEN** count() is called
- **THEN** the total number of embeddings across all collections is returned

#### Scenario: Empty database
- **WHEN** count() is called on an empty database
- **THEN** zero is returned

### Requirement: Resource cleanup
The system SHALL properly close Chroma connections and persist data when closed.

#### Scenario: Explicit cleanup with persistence
- **WHEN** close() is called on the store
- **THEN** all data is persisted to disk and connections are closed

#### Scenario: Context manager support
- **WHEN** the store is used as a context manager
- **THEN** resources are automatically cleaned up on exit

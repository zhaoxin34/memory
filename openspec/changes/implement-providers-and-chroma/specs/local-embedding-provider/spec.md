## ADDED Requirements

### Requirement: Local embedding model initialization
The system SHALL initialize a sentence-transformers model locally for generating text embeddings without requiring external API calls.

#### Scenario: Successful model loading
- **WHEN** LocalEmbeddingProvider is initialized with a valid model name
- **THEN** the sentence-transformers model is loaded into memory

#### Scenario: Model caching
- **WHEN** the same model is requested multiple times
- **THEN** the model is loaded only once and reused for subsequent requests

#### Scenario: Invalid model name
- **WHEN** LocalEmbeddingProvider is initialized with an invalid model name
- **THEN** a ProviderError is raised with a descriptive error message

### Requirement: Single text embedding generation
The system SHALL generate embeddings for individual text strings using the local model.

#### Scenario: Successful single embedding
- **WHEN** embed_text() is called with a non-empty text string
- **THEN** a vector embedding of the correct dimension is returned

#### Scenario: Empty text handling
- **WHEN** embed_text() is called with an empty string
- **THEN** a ProviderError is raised

#### Scenario: Long text handling
- **WHEN** embed_text() is called with text exceeding max_tokens
- **THEN** the text is truncated and a warning is logged

### Requirement: Batch embedding generation
The system SHALL generate embeddings for multiple text strings efficiently in batch mode.

#### Scenario: Successful batch embedding
- **WHEN** embed_batch() is called with a list of text strings
- **THEN** a list of vector embeddings is returned with the same length as the input

#### Scenario: Empty batch handling
- **WHEN** embed_batch() is called with an empty list
- **THEN** an empty list is returned

#### Scenario: Batch with mixed content
- **WHEN** embed_batch() is called with a mix of valid and empty strings
- **THEN** a ProviderError is raised for the empty strings

### Requirement: Model metadata access
The system SHALL provide access to model metadata including dimension and max token length.

#### Scenario: Get embedding dimension
- **WHEN** get_dimension() is called
- **THEN** the correct embedding dimension for the loaded model is returned

#### Scenario: Get max tokens
- **WHEN** get_max_tokens() is called
- **THEN** the maximum token length supported by the model is returned

### Requirement: Resource cleanup
The system SHALL properly release model resources when the provider is closed.

#### Scenario: Explicit cleanup
- **WHEN** close() is called on the provider
- **THEN** the model is unloaded from memory

#### Scenario: Context manager support
- **WHEN** the provider is used as a context manager
- **THEN** resources are automatically cleaned up on exit

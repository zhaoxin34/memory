## ADDED Requirements

### Requirement: OpenAI API client initialization
The system SHALL initialize an OpenAI API client with proper authentication for generating text embeddings via the OpenAI API.

#### Scenario: Successful client initialization with API key
- **WHEN** OpenAIEmbeddingProvider is initialized with a valid API key
- **THEN** the OpenAI client is configured and ready to make API calls

#### Scenario: Missing API key
- **WHEN** OpenAIEmbeddingProvider is initialized without an API key
- **THEN** a ProviderError is raised indicating missing credentials

#### Scenario: Invalid API key
- **WHEN** embed_text() is called with an invalid API key
- **THEN** a ProviderError is raised with the authentication error details

### Requirement: Single text embedding generation via API
The system SHALL generate embeddings for individual text strings by calling the OpenAI embeddings API.

#### Scenario: Successful single embedding
- **WHEN** embed_text() is called with a non-empty text string
- **THEN** a vector embedding is returned from the OpenAI API

#### Scenario: Empty text handling
- **WHEN** embed_text() is called with an empty string
- **THEN** a ProviderError is raised

#### Scenario: API rate limit handling
- **WHEN** the OpenAI API returns a rate limit error
- **THEN** a ProviderError is raised with rate limit information

#### Scenario: Network error handling
- **WHEN** a network error occurs during API call
- **THEN** a ProviderError is raised with connection error details

### Requirement: Batch embedding generation via API
The system SHALL generate embeddings for multiple text strings efficiently using the OpenAI batch API.

#### Scenario: Successful batch embedding
- **WHEN** embed_batch() is called with a list of text strings
- **THEN** a list of vector embeddings is returned with the same length as the input

#### Scenario: Empty batch handling
- **WHEN** embed_batch() is called with an empty list
- **THEN** an empty list is returned

#### Scenario: Large batch handling
- **WHEN** embed_batch() is called with more texts than the API batch limit
- **THEN** the texts are split into multiple API calls and results are combined

### Requirement: Model configuration
The system SHALL support configurable OpenAI embedding models.

#### Scenario: Default model usage
- **WHEN** no model is specified in configuration
- **THEN** the default OpenAI embedding model is used

#### Scenario: Custom model specification
- **WHEN** a specific model name is provided in configuration
- **THEN** that model is used for all embedding requests

#### Scenario: Unsupported model
- **WHEN** an unsupported model name is specified
- **THEN** a ProviderError is raised when attempting to generate embeddings

### Requirement: Model metadata access
The system SHALL provide access to model metadata including dimension and max token length.

#### Scenario: Get embedding dimension
- **WHEN** get_dimension() is called
- **THEN** the correct embedding dimension for the configured model is returned

#### Scenario: Get max tokens
- **WHEN** get_max_tokens() is called
- **THEN** the maximum token length for the configured model is returned

### Requirement: API cost tracking
The system SHALL track token usage for cost estimation purposes.

#### Scenario: Token usage logging
- **WHEN** embeddings are generated
- **THEN** the number of tokens processed is logged

#### Scenario: Batch token counting
- **WHEN** embed_batch() is called
- **THEN** the total token count across all texts is logged

### Requirement: Resource cleanup
The system SHALL properly close API connections when the provider is closed.

#### Scenario: Explicit cleanup
- **WHEN** close() is called on the provider
- **THEN** the OpenAI client connection is closed

#### Scenario: Context manager support
- **WHEN** the provider is used as a context manager
- **THEN** resources are automatically cleaned up on exit

## Why

Users need the ability to completely clear a repository of all documents without having to delete and recreate the repository itself. This is essential for:
- Cleaning up test or temporary data
- Resetting a repository to a fresh state while preserving its configuration
- Managing storage by removing outdated or obsolete documents
- Avoiding the overhead of repository deletion/recreation which may lose associated metadata

Currently, users must delete the entire repository and create a new one to remove all documents, which is cumbersome and risks losing repository configuration.

## What Changes

Add a new `clear` subcommand to the `memory repo` command that:
- Accepts a repository name as argument
- Removes all documents, chunks, and embeddings from the specified repository
- Displays progress and confirmation of the operation
- Provides dry-run option to preview what would be deleted
- Requires explicit confirmation to prevent accidental data loss
- Returns count of documents deleted

Example usage:
```bash
# Clear all documents from a repository
memory repo clear my-repo

# Preview what would be deleted without actually deleting
memory repo clear my-repo --dry-run

# Skip confirmation prompt (use with caution)
memory repo clear my-repo --yes
```

## Capabilities

### New Capabilities
- `repository-clear-command`: A new CLI command that removes all documents, chunks, and embeddings from a specified repository while preserving the repository itself

### Modified Capabilities
- None. This is a net-new capability that doesn't change existing repository management requirements.

## Impact

**CLI Interface:**
- New `repo clear` subcommand added to the CLI
- New command-line options: `--dry-run`, `--yes` flags
- Integration with existing repository listing and info commands

**Core Storage:**
- MetadataStore: Requires `delete_by_repository()` method implementation
- VectorStore: Requires `delete_by_repository()` method implementation
- RepositoryManager: Add `clear_repository()` method that orchestrates the clear operation

**Data Safety:**
- Confirmation prompts to prevent accidental deletions
- Dry-run mode for safe preview of deletions
- Clear messaging about irreversible nature of operation

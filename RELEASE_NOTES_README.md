# Release Notes Generation System

This directory contains tools for automatically generating release notes based on git commit history for the Laboratory Inventory Management System.

## Files

- `release_notes_generator.py` - Core release notes generation library
- `generate_release_notes.py` - Easy-to-use command line script
- `RELEASE_NOTES.md` - Current release notes in Markdown format
- `RELEASE_NOTES.json` - Current release notes in JSON format
- `COMPREHENSIVE_RELEASE_NOTES.md` - Detailed system overview and release documentation

## Quick Start

### Generate Current Release Notes

```bash
python generate_release_notes.py current
```

This creates release notes for all commits in the repository.

### Preview Release Notes

```bash
python generate_release_notes.py preview
```

This shows a preview of the release notes in the console without saving files.

### Generate Notes Since a Tag

```bash
python generate_release_notes.py since v1.0.0
```

This generates release notes for all commits since the specified git tag.

## Advanced Usage

### Using the Core Library

```python
from release_notes_generator import ReleaseNotesGenerator

generator = ReleaseNotesGenerator()

# Generate markdown release notes
notes = generator.generate_markdown_release_notes(
    version="v2.0.0",
    since="v1.0.0"
)

# Save to file
generator.save_release_notes(
    "release_v2.0.0.md",
    format="markdown",
    version="v2.0.0",
    since="v1.0.0"
)
```

### Command Line Options

```bash
python release_notes_generator.py --help
```

Available options:
- `--version` - Specify version string
- `--since` - Start commit/tag for changes
- `--until` - End commit/tag for changes
- `--output` - Output file path
- `--format` - Output format (markdown or json)
- `--repo` - Repository path

## Features

### Automatic Categorization

Commits are automatically categorized based on keywords in the commit message:

- **Features**: add, implement, create, new, feature, introduce, support, enable, allow
- **Bug Fixes**: fix, bug, issue, resolve, correct, repair, patch, hotfix, error, crash
- **Improvements**: improve, enhance, optimize, refactor, update, upgrade, performance, speed, efficiency, better
- **Documentation**: doc, documentation, readme, comment, guide, help, manual, example
- **Other Changes**: Everything else

### Multiple Output Formats

- **Markdown**: Human-readable format suitable for GitHub releases
- **JSON**: Machine-readable format for integration with other tools

### Comprehensive Statistics

- Total commits in release
- Files changed
- Lines added/removed
- Author information
- Detailed file listings

## Release Notes Structure

### Markdown Format

```markdown
# Version

**Release Date:** Date

## Summary
- Commit count
- Files changed
- Line statistics

## Features
- Feature commits with descriptions

## Bug Fixes
- Bug fix commits with descriptions

## Improvements
- Improvement commits with descriptions

## Documentation
- Documentation commits with descriptions

## Other Changes
- Miscellaneous commits

## Detailed Changes
### Files Modified
- Complete list of changed files
```

### JSON Format

```json
{
  "version": "v1.0.0",
  "release_date": "2025-09-06T05:31:44.609568",
  "summary": {
    "total_commits": 2,
    "total_files": 66,
    "total_insertions": 16816,
    "total_deletions": 0
  },
  "categories": {
    "Features": [...],
    "Bug Fixes": [...],
    ...
  }
}
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Generate Release Notes
on:
  push:
    tags:
      - 'v*'

jobs:
  release-notes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'
      
      - name: Generate Release Notes
        run: |
          python generate_release_notes.py current
          
      - name: Create Release
        uses: actions/create-release@v1
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          body_path: RELEASE_NOTES.md
```

## Customization

### Adding Custom Categories

Edit the keywords in `release_notes_generator.py`:

```python
CUSTOM_KEYWORDS = [
    'security', 'vulnerability', 'auth', 'permission'
]
```

### Custom Formatting

Modify the `generate_markdown_release_notes` method to change the output format.

### Additional Metadata

The system can be extended to include:
- Jira ticket references
- Pull request links
- Breaking changes indicators
- Migration notes

## Best Practices

### Writing Commit Messages

For best categorization, use clear commit message prefixes:

```
feat: Add user authentication system
fix: Resolve inventory calculation bug
docs: Update installation guide
refactor: Improve database connection handling
```

### Release Workflow

1. **Development**: Make commits with clear, descriptive messages
2. **Pre-release**: Use `python generate_release_notes.py preview` to review
3. **Release**: Generate final notes with `python generate_release_notes.py current`
4. **Distribution**: Use generated files for GitHub releases, documentation, etc.

## Troubleshooting

### Common Issues

**No commits found**: Ensure you're in a git repository with commit history

**Permission errors**: Ensure write permissions for output directory

**Git not found**: Ensure git is installed and available in PATH

### Debug Mode

Set environment variable for verbose output:
```bash
export DEBUG=1
python generate_release_notes.py current
```

## Contributing

To improve the release notes generator:

1. Add new categorization keywords
2. Improve formatting templates
3. Add support for additional output formats
4. Enhance commit parsing logic

---

*This system automatically generates professional release notes from git commit history, making it easy to communicate changes to users and stakeholders.*
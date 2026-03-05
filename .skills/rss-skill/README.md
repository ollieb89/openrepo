# RSS/Atom Feed to Markdown Skill

Converts RSS and Atom feed URLs to readable Markdown format.

## Files

- `SKILL.md` - Skill definition and usage instructions
- `scripts/feed_to_md.py` - Secure feed-to-markdown converter

## Requirements

- Python 3.7+

## Usage

```bash
# Basic usage (prints to stdout)
python3 scripts/feed_to_md.py "https://example.com/feed.xml"

# Write to file
python3 scripts/feed_to_md.py "https://example.com/feed.xml" --output feed.md

# Limit items
python3 scripts/feed_to_md.py "https://example.com/feed.xml" --limit 10

# Full template with summaries
python3 scripts/feed_to_md.py "https://example.com/feed.xml" --template full
```

## Security

- Validates URLs to prevent SSRF attacks
- Blocks localhost and private IP addresses
- Validates redirect targets
- Validates output paths are workspace-relative

## License

MIT (from openclaw/skills)

# RSS/Atom Feed to Markdown Skill

**name:** feed-to-md  
**title:** Feed to Markdown  
**description:** Convert RSS or Atom feed URLs into Markdown using a bundled local converter script. Use this when a user asks to turn a feed URL into readable Markdown, optionally limiting items or writing to a file.  
**emoji:** 📰  
**requires:** python3

## When to Use This Skill

Use this skill when the task is to:
- Convert an RSS or Atom feed URL to Markdown
- Read and summarize feed content
- Export feed items to a Markdown file

## What This Skill Does

- Converts a feed URL to Markdown via a bundled local script
- Supports stdout output or writing to a Markdown file
- Supports limiting article count and summary controls
- Validates URLs to prevent SSRF (blocks localhost/private IPs)

## Inputs

- **Required:** RSS/Atom URL (http or https only)
- **Optional:**
  - Output path (must be relative, end in `.md`)
  - Max item count (`--limit`)
  - Template preset (`short` or `full`)
  - Exclude summaries (`--no-summary`)
  - Summary max length (`--summary-max-length`)

## Usage

### Basic usage (stdout)

```bash
python3 scripts/feed_to_md.py "https://example.com/feed.xml"
```

### Write to file

```bash
python3 scripts/feed_to_md.py "https://example.com/feed.xml" --output feed.md
```

### Limit to 10 items

```bash
python3 scripts/feed_to_md.py "https://example.com/feed.xml" --limit 10
```

### Use full template with summaries

```bash
python3 scripts/feed_to_md.py "https://example.com/feed.xml" --template full
```

## Security Rules (Required)

- Never interpolate raw user input into a shell string
- Always pass arguments directly to the script as separate argv tokens
- URL must be `http` or `https` and must not resolve to localhost/private addresses
- Every HTTP redirect target (and final URL) is re-validated and must also resolve to public IPs
- Output path must be workspace-relative and end in `.md`
- Do not use shell redirection for output; use `--output`

### Safe Command Pattern

```bash
cmd=(python3 scripts/feed_to_md.py "$feed_url")
[[ -n "${output_path:-}" ]] && cmd+=(--output "$output_path")
[[ -n "${limit:-}" ]] && cmd+=(--limit "$limit")
[[ "${template:-short}" = "full" ]] && cmd+=(--template full)
"${cmd[@]}"
```

## Script Options

| Option | Description |
|--------|-------------|
| `-o, --output <file>` | Write markdown to file |
| `--limit <number>` | Max number of articles |
| `--no-summary` | Exclude summaries |
| `--summary-max-length <number>` | Truncate summary length |
| `--template <preset>` | `short` (default) or `full` |

## Output Templates

### Short Template

A simple list with titles, links, and publish dates:

```markdown
# Feed Title

- [Article Title](https://example.com/article1) (Mon, 01 Jan 2024)
- [Article Title 2](https://example.com/article2) (Tue, 02 Jan 2024)
```

### Full Template

Detailed output with summaries:

```markdown
# Feed Title

## [Article Title](https://example.com/article1)
- Published: Mon, 01 Jan 2024

Summary of the article content...

## [Article Title 2](https://example.com/article2)
- Published: Tue, 02 Jan 2024

Summary of the article content...
```

## Files

- `SKILL.md` - This skill definition
- `scripts/feed_to_md.py` - Secure feed-to-markdown converter

## Requirements

- Python 3.7+

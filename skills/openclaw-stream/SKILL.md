---
name: openclaw-stream
description: Streaming and block chunking configuration in OpenClaw. Use when enabling block streaming, configuring chunk sizes, setting up preview streaming (Telegram/Discord/Slack), adjusting coalescing behavior, enabling human-like pacing, or troubleshooting streaming issues. Triggers for: "block streaming", "stream chunks", "chunking", "preview streaming", "partial streaming", "coalesce", "chunk size", "blockStreamingDefault", "streaming mode", "Telegram streaming", "Discord streaming".
---

# OpenClaw Streaming

OpenClaw has two separate streaming layers — block streaming (channel messages) and preview streaming (live editing a preview message).

**There is no true token-delta streaming to channel messages.** All streaming is message-based.

## Block Streaming (Channel Messages)

Emits completed chunks of the assistant's reply as it writes, rather than waiting for the full message.

```json5
{
  agents: {
    defaults: {
      blockStreamingDefault: "on",        // off (default) | on
      blockStreamingBreak: "text_end",    // text_end | message_end
      blockStreamingChunk: {
        minChars: 800,
        maxChars: 1200,
        breakPreference: "paragraph"      // paragraph | newline | sentence | whitespace
      }
    }
  }
}
```

**Break modes:**
- `text_end` — stream blocks as they fill the buffer (progressive output)
- `message_end` — wait for full message, then flush in chunks

**Non-Telegram channels** need explicit per-channel override too:
```json5
{
  channels: {
    discord: { blockStreaming: "on" },
    slack:   { blockStreaming: "on" }
  }
}
```

## Chunking Algorithm

- Buffer fills until `minChars` reached (low bound)
- Prefers to split at `maxChars` before, using `breakPreference`
- Code fences never split mid-fence — if forced at `maxChars`, closes and reopens fence
- `maxChars` clamped to channel `textChunkLimit`

## Coalescing (Merge Small Chunks)

Reduces "single-line spam" by merging consecutive blocks before send:

```json5
{
  agents: {
    defaults: {
      blockStreamingCoalesce: {
        minChars: 1500,   // don't flush until this accumulated (Signal/Slack/Discord default)
        maxChars: 3000,
        idleMs: 800       // flush after idle gap
      }
    }
  }
}
```

## Human-Like Pacing

Adds natural delays between block replies:

```json5
{
  agents: {
    defaults: {
      humanDelay: {
        mode: "natural"  // off (default) | natural | custom
        // custom: { minMs: 500, maxMs: 1500 }
      }
    }
  }
}
```

Natural mode: 800–2500ms delay between blocks. Applies only to block replies, not final replies or tool summaries.

## Preview Streaming (Per Channel)

Shows a live "typing" preview while generating. Configured per channel:

```json5
{
  channels: {
    telegram: { streaming: "partial" },  // off | partial | block
    discord:  { streaming: "block" },    // off | partial | block
    slack:    { streaming: "progress" }  // off | partial | block | progress (Slack only)
  }
}
```

**Slack native streaming** (real-time token stream via Slack API):
```json5
{
  channels: {
    slack: {
      streaming: "partial",
      nativeStreaming: true   // default true when streaming=partial
    }
  }
}
```

## Common Configurations

**"Stream chunks as they're written":**
```json5
blockStreamingDefault: "on", blockStreamingBreak: "text_end"
// + channel: { blockStreaming: "on" } for Discord/Slack
```

**"Send everything at end in chunks":**
```json5
blockStreamingDefault: "on", blockStreamingBreak: "message_end"
```

**"No block streaming":**
```json5
blockStreamingDefault: "off"
```

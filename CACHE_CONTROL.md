# Anthropic Cache Control Implementation

This document describes the cache control feature for Anthropic models when using OpenRouter.

## Overview

Cache control allows you to mark specific parts of your messages for caching, reducing costs and improving response times for repeated queries with similar context. This is particularly useful for:

- Large system prompts
- Character cards
- CSV data
- RAG (Retrieval Augmented Generation) data
- Book chapters or other large text content

## How It Works

When using an Anthropic model (e.g., `claude-3-5-sonnet`) through OpenRouter, the bot will automatically:

1. Detect if the model is an Anthropic model
2. Convert messages to multipart format (required for cache control)
3. Apply cache control breakpoints to appropriate messages
4. Track cache usage and discounts

## Configuration

Add the following to your `config.yaml`:

```yaml
# Minimum text length to consider for caching (default: 1000)
cache_min_length: 1000
```

## Cache Control Rules

- **Maximum 4 breakpoints** per request
- **Cache expires in 5 minutes**
- **Priority order**:
  1. System prompts (highest priority)
  2. Older messages in the conversation
  3. Larger messages within the same priority level
- Only text content with length >= `cache_min_length` is considered

## Message Format

Cache control is applied automatically. The bot converts messages to the required format:

```json
{
  "role": "user",
  "content": [
    {
      "type": "text",
      "text": "Your message here",
      "cache_control": {"type": "ephemeral"}
    }
  ]
}
```

## Cost Savings

- Cached tokens are charged at **0.25x** the original input token cost
- Cache writes are charged at the input token cost plus 5 minutes of cache storage
- The bot logs cache discounts when available

## Logging

The bot provides detailed logging for cache control:

- When cache control is applied to messages
- Which messages received cache control
- Cache discount information (when available)

Example log output:
```
Applied cache control to system message (index 0, length 2500)
Applied cache control to user message (index 2, length 1800)
Applied 2 cache control breakpoints for Anthropic model
Cache discount for Anthropic model: 0.75
```

## Best Practices

1. **Use large system prompts**: They're static and reused across conversations
2. **Keep message order consistent**: Cache hits are more likely when the initial portion of messages stays the same
3. **Set appropriate cache_min_length**: Too low wastes breakpoints on small messages, too high misses caching opportunities
4. **Monitor logs**: Check cache discount logs to verify cost savings

## Limitations

- Only works with Anthropic models through OpenRouter
- Maximum 4 cache breakpoints per request
- Cache expires after 5 minutes
- Only text content can be cached (not images or other content types)
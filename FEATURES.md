# New Features Guide

## 🎉 What's New

Your Discord bot now has these awesome features powered by OpenRouter:

### 1. **Natural "Claude" Mentions**
- Just say "Claude" anywhere in your message and the bot will respond
- No need to @ mention anymore (but that still works too!)
- Example: "Hey Claude, what's the weather like?"

### 2. **Discord Message Tools**
The bot can now:
- **Look at recent messages**: "Claude, what were we talking about earlier?"
- **Search messages**: "Claude, find when we discussed the meeting time"
- **Get channel info**: "Claude, tell me about this channel"

### 3. **Web Search (:online)**
Use web-enabled models to search the internet:
- Switch to an :online model with `/model` (e.g., `openrouter/anthropic/claude-3.5-sonnet:online`)
- Then ask: "Claude, what's the latest news about AI?"

### 4. **Multiple Models**
Switch between different AI models:
- `/model` - See available models
- Popular choices:
  - `openrouter/anthropic/claude-3.5-sonnet` - Claude 3.5 Sonnet
  - `openrouter/openai/gpt-4o` - GPT-4 Omni
  - `openrouter/google/gemini-2.0-flash-exp:free` - Free Gemini model

### 5. **Natural Responses**
- Messages now appear like a human typing
- No more bulky embeds for regular messages
- Clean, conversational style

## 🚀 Quick Start

1. **Set up environment variables**:
   ```bash
   export BOT_TOKEN="your-discord-bot-token"
   export OPENROUTER_API_KEY="your-openrouter-api-key"
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Test your setup**:
   ```bash
   python test_bot.py
   ```

4. **Run the bot**:
   ```bash
   python llmcord.py
   ```

## 💡 Example Commands

### Basic Chat
- "Claude, explain quantum computing"
- "Hey Claude, can you help me with Python?"

### Using Tools
- "Claude, what messages did John send in the last hour?"
- "Claude, search for messages about the project deadline"

### Web Search (with :online model)
1. Switch model: `/model` → select `openrouter/anthropic/claude-3.5-sonnet:online`
2. Ask: "Claude, what's happening in tech news today?"

### Model Comparison
1. Ask Claude something with one model
2. Switch models: `/model` → select a different one
3. Ask the same question to compare responses

## 🔧 Configuration

Edit `config.yaml` to:
- Add/remove models
- Change temperature settings
- Modify system prompts
- Enable/disable features

## 🆘 Troubleshooting

- **Bot not responding to "Claude"**: Make sure the bot has permission to read messages in the channel
- **Tools not working**: Ensure `enable_tools: true` in config.yaml
- **Web search not working**: Use a model with `:online` suffix
- **Rate limits**: Consider using different models or adding a small delay between requests

Enjoy your enhanced Claude Discord bot! 🤖✨
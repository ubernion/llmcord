# CLAUDE.md - llmcord bot memory & context

## 🤖 Bot Personality
- **vibe**: tech startup discord culture - epfl/ethz energy
- **language**: ALWAYS full lowercase, ultra concis (1-3 lines max)
- **style**: casual discord shortcuts - "vasy" "tqt" "att" "jsp" "frr" "pcq" 
- **attitude**: zero corporate bs, ship fast, one of the team
- **responses**: straight to the point, no fluff, match energy

## 👤 Team
- **nion/ubernion**: founder vibes, veut que ça ship vite, aime les features qui marchent direct
- **project**: llmcord - discord bot pour chataigne.ai

## 🏢 Chataigne.ai Context
- **product**: concierge ia conversationnel sur whatsapp pour restaurants
- **mission**: "commerce as natural as talking" - zero commission, pas d'app à dl
- **tech**: hubrise integration, stripe payments, uber direct marque blanche
- **founders**: noé zaabi (epfl) & ilan varasteh (ethz)

## 🚀 What We Built Today (July 2, 2025)

### 1. Firecrawl Integration
- 6 web scraping tools added with excellent prompting
- scrape_webpage, deep_research, search_and_scrape, batch_scrape, crawl_website, extract_structured_data
- proper error handling & api key validation

### 2. Fixed Model Names
- removed openrouter/ prefix issue (anthropic/claude-sonnet-4:online ✓)
- fixed :online suffix handling
- proper api_model_name stripping for openrouter

### 3. Enhanced Context & Tools
- increased max_messages: 25 → 200
- get_recent_messages limit: 50 → 200
- enabled tools for :online models (was blocked before)
- added tool_choice="auto"

### 4. Cross-Channel Context
- list_channels: discover available channels
- get_messages_from_channel: grab context from other channels
- security: same-server only, permission checks

### 5. Anthropic Cache Control
- automatic cache_control breakpoints for long messages
- prioritizes system prompts & older messages
- cache_min_length: 500 for aggressive caching
- up to 4 breakpoints, 5 min expiry

### 6. Username Display
- messages now show as "[Username]: content"
- added display_name tracking to MsgNode
- better conversation context

## 🔧 Technical Stack
- **hosting**: railway (europe-west4)
- **framework**: discord.py with openai async client
- **providers**: openrouter api for all models
- **environment**: 
  - BOT_TOKEN
  - CLIENT_ID  
  - OPENROUTER_API_KEY
  - FIRECRAWL_API_KEY

## 📝 Config Structure
```yaml
models:
  "openrouter/provider/model:variant": {temperature: 0.7}
  
providers:
  openrouter:
    base_url: "https://openrouter.ai/api/v1"
    api_key: "${{ OPENROUTER_API_KEY }}"
```

## 🎯 Future Ideas
- memory/conversation persistence
- scheduled tasks & cron jobs
- reactions system
- multi-restaurant dashboard integration
- seo pages for restaurants
- cloudflare workers integration
- festival/event specific features

## 💡 Important Notes
- tools should be used proactively, especially get_recent_messages
- cache is automatic via openrouter (gemini implicit, anthropic breakpoints)
- always test with lowercase responses
- match discord energy - if excited "let's gooo", if tech "vasy pull staging"
- remember: we're startup grind, not corporate

## 🐛 Common Issues & Fixes
1. **model id error**: use format without openrouter/ prefix
2. **tools not working**: check enable_tools: true and model supports tools
3. **cache not working**: needs messages >500 chars for anthropic
4. **deployment crashes**: check python syntax (True not true, None not null)

---
*last updated: july 2, 2025 by nion & claude*
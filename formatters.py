"""
Discord formatting utilities for clean message display.
"""

import discord
from typing import List, Dict, Any, Optional
import json
import re


def format_web_search_results(results: List[Dict[str, Any]]) -> discord.Embed:
    """Format web search results as a Discord embed."""
    embed = discord.Embed(
        title="🔍 Web Search Results",
        color=discord.Color.blue()
    )
    
    for i, result in enumerate(results[:5]):  # Limit to 5 results
        title = result.get("title", "No title")
        url = result.get("url", "")
        snippet = result.get("snippet", "No description")
        
        # Truncate snippet if too long
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."
        
        embed.add_field(
            name=f"{i+1}. {title}",
            value=f"{snippet}\n[Link]({url})" if url else snippet,
            inline=False
        )
    
    return embed


def format_tool_result(tool_name: str, result: Any) -> str:
    """Format a tool result for display."""
    if isinstance(result, dict) and "error" in result:
        return f"❌ **{tool_name}** error: {result['error']}"
    
    if tool_name == "get_recent_messages":
        messages = result.get("messages", [])
        output = f"📋 **Recent Messages** ({len(messages)} messages):\n"
        
        for msg in messages[-5:]:  # Show last 5
            author = msg["author"]["name"]
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            output += f"• **{author}**: {content}\n"
        
        return output
    
    elif tool_name == "search_messages":
        results = result.get("results", [])
        output = f"🔎 **Message Search** (found {len(results)} matches):\n"
        
        for res in results[:3]:  # Show first 3
            author = res["author"]["name"]
            preview = res["match_preview"]
            output += f"• **{author}**: {preview}\n"
        
        return output
    
    elif tool_name == "get_channel_info":
        channel = result.get("channel", {})
        server = result.get("server", {})
        
        output = f"ℹ️ **Channel Info**:\n"
        output += f"• Channel: {channel.get('name', 'Unknown')}\n"
        
        if server:
            output += f"• Server: {server.get('name', 'Unknown')}\n"
            output += f"• Members: {server.get('member_count', 'Unknown')}\n"
        
        return output
    
    # Default formatting
    return f"📊 **{tool_name}** result:\n```json\n{json.dumps(result, indent=2)[:500]}\n```"


def format_reasoning_content(reasoning: str) -> discord.Embed:
    """Format reasoning content as a collapsible embed."""
    embed = discord.Embed(
        title="💭 Reasoning Process",
        description=reasoning[:1024] + "..." if len(reasoning) > 1024 else reasoning,
        color=discord.Color.purple()
    )
    
    return embed


def extract_web_citations(content: str) -> List[Dict[str, str]]:
    """Extract web citations from OpenRouter response."""
    # Look for markdown links [text](url)
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(pattern, content)
    
    citations = []
    for text, url in matches:
        if url.startswith("http"):
            citations.append({"text": text, "url": url})
    
    return citations


def format_response_with_citations(content: str, citations: List[Dict[str, Any]]) -> discord.Embed:
    """Format response with web citations."""
    # Main response embed
    embed = discord.Embed(
        description=content[:4096],
        color=discord.Color.green()
    )
    
    # Add citations if any
    if citations:
        citation_text = ""
        for i, cite in enumerate(citations[:5]):  # Limit to 5 citations
            url = cite.get("url", "")
            title = cite.get("title", f"Source {i+1}")
            citation_text += f"[{i+1}. {title}]({url})\n"
        
        embed.add_field(
            name="📚 Sources",
            value=citation_text,
            inline=False
        )
    
    # Add timestamp
    embed.timestamp = discord.utils.utcnow()
    
    return embed


def create_error_embed(error_message: str) -> discord.Embed:
    """Create an error embed."""
    embed = discord.Embed(
        title="❌ Error",
        description=error_message,
        color=discord.Color.red()
    )
    
    return embed


def create_usage_embed(tokens_used: int, cost_estimate: float = None) -> discord.Embed:
    """Create a usage statistics embed."""
    embed = discord.Embed(
        title="📊 Usage Statistics",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="Tokens Used",
        value=f"{tokens_used:,}",
        inline=True
    )
    
    if cost_estimate:
        embed.add_field(
            name="Estimated Cost",
            value=f"${cost_estimate:.4f}",
            inline=True
        )
    
    return embed
"""
Tool definitions and handlers for the Discord bot.
Focused on Discord-specific tools that the AI can use.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import discord
from discord.ext import commands


class DiscordTools:
    """Handles Discord-specific tools for the AI."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tool_definitions = self._get_tool_definitions()
        
    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for OpenAI function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_recent_messages",
                    "description": "Get recent messages from the current Discord channel to understand context and what happened before.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of messages to retrieve (default: 10, max: 50)",
                                "default": 10
                            },
                            "before_message_id": {
                                "type": "string",
                                "description": "Get messages before this message ID (optional)",
                                "default": None
                            }
                        }
                    }
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "search_messages",
                    "description": "Search for messages in the channel containing specific keywords or from specific users.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Text to search for in messages"
                            },
                            "author_id": {
                                "type": "string",
                                "description": "Discord user ID to filter messages by author (optional)",
                                "default": None
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 10, max: 25)",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_channel_info",
                    "description": "Get information about the current Discord channel and server.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]
    
    async def get_recent_messages(
        self, 
        channel: discord.TextChannel,
        limit: int = 10,
        before_message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get recent messages from a Discord channel."""
        try:
            limit = min(max(limit, 1), 50)
            
            # Get the before message if ID provided
            before = None
            if before_message_id:
                try:
                    before = await channel.fetch_message(int(before_message_id))
                except:
                    return {"error": "Invalid message ID provided"}
            
            messages = []
            async for msg in channel.history(limit=limit, before=before):
                # Don't include bot's own messages unless they're relevant
                if msg.author == self.bot.user and not msg.reference:
                    continue
                    
                message_data = {
                    "id": str(msg.id),
                    "author": {
                        "name": msg.author.display_name,
                        "id": str(msg.author.id),
                        "bot": msg.author.bot
                    },
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat(),
                    "attachments": [
                        {"filename": att.filename, "url": att.url}
                        for att in msg.attachments
                    ]
                }
                
                # Include reply context
                if msg.reference and msg.reference.cached_message:
                    ref_msg = msg.reference.cached_message
                    message_data["replying_to"] = {
                        "author": ref_msg.author.display_name,
                        "content": ref_msg.content[:100] + "..." if len(ref_msg.content) > 100 else ref_msg.content
                    }
                
                messages.append(message_data)
            
            # Reverse to show chronological order
            messages.reverse()
            
            return {
                "channel": channel.name,
                "message_count": len(messages),
                "messages": messages
            }
            
        except Exception as e:
            logging.error(f"Error getting recent messages: {e}")
            return {"error": str(e)}
    
    async def search_messages(
        self,
        channel: discord.TextChannel,
        query: str,
        author_id: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search for messages in the channel."""
        try:
            limit = min(max(limit, 1), 25)
            query_lower = query.lower()
            
            matches = []
            count = 0
            
            async for msg in channel.history(limit=500):  # Search through last 500 messages
                # Check if we've found enough matches
                if count >= limit:
                    break
                
                # Filter by author if specified
                if author_id and str(msg.author.id) != author_id:
                    continue
                
                # Search in message content
                if query_lower in msg.content.lower():
                    matches.append({
                        "id": str(msg.id),
                        "author": {
                            "name": msg.author.display_name,
                            "id": str(msg.author.id)
                        },
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat(),
                        "match_preview": self._get_match_preview(msg.content, query)
                    })
                    count += 1
            
            return {
                "query": query,
                "author_filter": author_id,
                "results_count": len(matches),
                "results": matches
            }
            
        except Exception as e:
            logging.error(f"Error searching messages: {e}")
            return {"error": str(e)}
    
    async def get_channel_info(self, channel: discord.TextChannel) -> Dict[str, Any]:
        """Get information about the current channel and server."""
        try:
            info = {
                "channel": {
                    "name": channel.name,
                    "id": str(channel.id),
                    "type": str(channel.type),
                    "topic": channel.topic,
                    "created_at": channel.created_at.isoformat()
                }
            }
            
            # Add server info if not DM
            if hasattr(channel, 'guild') and channel.guild:
                info["server"] = {
                    "name": channel.guild.name,
                    "id": str(channel.guild.id),
                    "member_count": channel.guild.member_count,
                    "created_at": channel.guild.created_at.isoformat()
                }
                
                # Add category info if in one
                if channel.category:
                    info["category"] = {
                        "name": channel.category.name,
                        "id": str(channel.category.id)
                    }
            
            return info
            
        except Exception as e:
            logging.error(f"Error getting channel info: {e}")
            return {"error": str(e)}
    
    def _get_match_preview(self, content: str, query: str, context_chars: int = 40) -> str:
        """Get a preview of where the query matches in the content."""
        lower_content = content.lower()
        lower_query = query.lower()
        
        index = lower_content.find(lower_query)
        if index == -1:
            return content[:100] + "..." if len(content) > 100 else content
        
        start = max(0, index - context_chars)
        end = min(len(content), index + len(query) + context_chars)
        
        preview = content[start:end]
        if start > 0:
            preview = "..." + preview
        if end < len(content):
            preview = preview + "..."
            
        return preview
    
    async def handle_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        channel: discord.TextChannel
    ) -> Any:
        """Handle a tool call from the AI."""
        if tool_name == "get_recent_messages":
            return await self.get_recent_messages(
                channel,
                arguments.get("limit", 10),
                arguments.get("before_message_id")
            )
        elif tool_name == "search_messages":
            return await self.search_messages(
                channel,
                arguments["query"],
                arguments.get("author_id"),
                arguments.get("limit", 10)
            )
        elif tool_name == "get_channel_info":
            return await self.get_channel_info(channel)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
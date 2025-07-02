"""
Tool definitions and handlers for the Discord bot.
Focused on Discord-specific tools that the AI can use.
"""

import json
import logging
import os
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
            },
            {
                "type": "function",
                "function": {
                    "name": "scrape_webpage",
                    "description": "Extract clean, readable content from any webpage. Perfect for reading articles, documentation, blog posts, or any web content. Removes ads, navigation, and other clutter to get just the main content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The full URL of the webpage to scrape (e.g., https://example.com/article)"
                            },
                            "format": {
                                "type": "string",
                                "description": "Output format: 'markdown' for formatted text with headers/links, 'text' for plain text, 'html' for clean HTML",
                                "enum": ["markdown", "text", "html"],
                                "default": "markdown"
                            },
                            "only_main_content": {
                                "type": "boolean",
                                "description": "Extract only the main article content, removing sidebars and unrelated sections",
                                "default": True
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "deep_research",
                    "description": "Conduct comprehensive web research on any topic. Automatically searches, crawls relevant pages, and synthesizes information from multiple sources to provide a thorough analysis. Great for complex questions that need multiple perspectives.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The research question or topic to investigate (e.g., 'How does quantum computing work?')"
                            },
                            "max_time": {
                                "type": "integer",
                                "description": "Maximum time in seconds to spend researching (default: 60, max: 180)",
                                "default": 60
                            },
                            "max_sources": {
                                "type": "integer",
                                "description": "Maximum number of sources to analyze (default: 20, max: 50)",
                                "default": 20
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_and_scrape",
                    "description": "Search the web for a query and automatically scrape the top results. Combines web search with content extraction to quickly gather information from multiple sources.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "What to search for on the web"
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "Number of search results to scrape (default: 3, max: 10)",
                                "default": 3
                            },
                            "country": {
                                "type": "string",
                                "description": "Country code for search results (e.g., 'us', 'uk', 'de')",
                                "default": "us"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "batch_scrape_webpages",
                    "description": "Scrape multiple webpages at once efficiently. Perfect for comparing information across multiple sources or gathering data from a list of URLs.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "urls": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of URLs to scrape (max 10 URLs)"
                            },
                            "format": {
                                "type": "string",
                                "description": "Output format for all pages",
                                "enum": ["markdown", "text", "html"],
                                "default": "markdown"
                            }
                        },
                        "required": ["urls"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "crawl_website",
                    "description": "Crawl an entire website or section to discover and index all pages. Useful for understanding site structure, finding specific content, or comprehensive analysis.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The starting URL to crawl from"
                            },
                            "max_pages": {
                                "type": "integer",
                                "description": "Maximum number of pages to crawl (default: 50, max: 100)",
                                "default": 50
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "Maximum depth of links to follow (default: 2)",
                                "default": 2
                            },
                            "include_pattern": {
                                "type": "string",
                                "description": "Regex pattern for URLs to include (e.g., '.*blog.*' for blog posts)"
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_structured_data",
                    "description": "Extract specific structured information from webpages using AI. Define what data you want (prices, contacts, specs, etc.) and get it in a structured format.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "urls": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "URLs to extract data from (max 5)"
                            },
                            "extraction_prompt": {
                                "type": "string",
                                "description": "Describe what information to extract (e.g., 'Extract product name, price, and availability')"
                            },
                            "schema": {
                                "type": "object",
                                "description": "Optional JSON schema to structure the output",
                                "default": None
                            }
                        },
                        "required": ["urls", "extraction_prompt"]
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
    
    async def scrape_webpage(
        self,
        url: str,
        format: str = "markdown",
        only_main_content: bool = True
    ) -> Dict[str, Any]:
        """Scrape and extract content from a webpage using Firecrawl."""
        try:
            # Import here to avoid issues if not installed
            from firecrawl import FirecrawlApp
            
            # Initialize Firecrawl
            api_key = os.environ.get("FIRECRAWL_API_KEY")
            if not api_key:
                return {
                    "error": "Firecrawl API key not configured. Please set FIRECRAWL_API_KEY environment variable."
                }
            
            app = FirecrawlApp(api_key=api_key)
            
            # Scrape the page
            scrape_options = {
                "formats": [format],
                "onlyMainContent": only_main_content,
                "timeout": 30000,  # 30 second timeout
                "removeBase64Images": True  # Don't include base64 images in response
            }
            
            result = app.scrape_url(url, scrape_options)
            
            # Extract relevant data
            content = result.get(format, result.get("text", ""))
            metadata = result.get("metadata", {})
            
            # Format response based on content type
            response = {
                "url": url,
                "title": metadata.get("title", "No title"),
                "description": metadata.get("description", ""),
                "content_preview": content[:500] + "..." if len(content) > 500 else content,
                "full_content": content,
                "word_count": len(content.split()),
                "language": metadata.get("language", "unknown")
            }
            
            # Add source metadata if available
            if metadata.get("author"):
                response["author"] = metadata["author"]
            if metadata.get("publishedDate"):
                response["published_date"] = metadata["publishedDate"]
            
            return response
            
        except ImportError:
            return {
                "error": "Firecrawl library not installed. Please install with: pip install firecrawl-py"
            }
        except Exception as e:
            logging.error(f"Error scraping webpage {url}: {e}")
            return {
                "error": f"Failed to scrape {url}: {str(e)}"
            }
    
    async def deep_research(
        self,
        query: str,
        max_time: int = 60,
        max_sources: int = 20
    ) -> Dict[str, Any]:
        """Conduct deep research on a topic using Firecrawl."""
        try:
            from firecrawl import FirecrawlApp
            
            api_key = os.environ.get("FIRECRAWL_API_KEY")
            if not api_key:
                return {
                    "error": "Firecrawl API key not configured. Please set FIRECRAWL_API_KEY environment variable."
                }
            
            app = FirecrawlApp(api_key=api_key)
            
            # Limit time and sources to reasonable values
            max_time = min(max(max_time, 30), 180)  # Between 30-180 seconds
            max_sources = min(max(max_sources, 5), 50)  # Between 5-50 sources
            
            # Start deep research
            research_params = {
                "query": query,
                "maxDepth": 3,
                "timeLimit": max_time,
                "maxUrls": max_sources
            }
            
            # Note: This is an async operation that returns immediately
            result = app.deep_research(research_params)
            
            # Extract the analysis
            if "finalAnalysis" in result:
                return {
                    "query": query,
                    "analysis": result["finalAnalysis"],
                    "sources_analyzed": len(result.get("sources", [])),
                    "research_complete": True
                }
            else:
                return {
                    "query": query,
                    "status": "Research initiated",
                    "message": "Deep research is running. This may take up to {} seconds.".format(max_time),
                    "sources_to_analyze": max_sources
                }
                
        except ImportError:
            return {
                "error": "Firecrawl library not installed. Please install with: pip install firecrawl-py"
            }
        except Exception as e:
            logging.error(f"Error conducting research for '{query}': {e}")
            return {
                "error": f"Failed to research '{query}': {str(e)}"
            }
    
    async def search_and_scrape(
        self,
        query: str,
        num_results: int = 3,
        country: str = "us"
    ) -> Dict[str, Any]:
        """Search the web and scrape top results using Firecrawl."""
        try:
            from firecrawl import FirecrawlApp
            
            api_key = os.environ.get("FIRECRAWL_API_KEY")
            if not api_key:
                return {
                    "error": "Firecrawl API key not configured. Please set FIRECRAWL_API_KEY environment variable."
                }
            
            app = FirecrawlApp(api_key=api_key)
            
            # Limit results to reasonable amount
            num_results = min(max(num_results, 1), 10)
            
            # Search with scraping enabled
            search_params = {
                "query": query,
                "limit": num_results,
                "lang": "en",
                "country": country,
                "scrapeOptions": {
                    "formats": ["markdown"],
                    "onlyMainContent": True
                }
            }
            
            results = app.search(search_params)
            
            # Format the results
            formatted_results = []
            for idx, result in enumerate(results.get("data", [])):
                # Extract content from the result
                content = result.get("markdown", result.get("text", ""))
                metadata = result.get("metadata", {})
                
                formatted_results.append({
                    "position": idx + 1,
                    "title": metadata.get("title", result.get("title", "No title")),
                    "url": result.get("url", ""),
                    "description": metadata.get("description", result.get("description", "")),
                    "content_preview": content[:300] + "..." if len(content) > 300 else content,
                    "full_content": content
                })
            
            return {
                "query": query,
                "country": country,
                "results_count": len(formatted_results),
                "results": formatted_results
            }
            
        except ImportError:
            return {
                "error": "Firecrawl library not installed. Please install with: pip install firecrawl-py"
            }
        except Exception as e:
            logging.error(f"Error searching and scraping for '{query}': {e}")
            return {
                "error": f"Failed to search and scrape for '{query}': {str(e)}"
            }
    
    async def batch_scrape_webpages(
        self,
        urls: List[str],
        format: str = "markdown"
    ) -> Dict[str, Any]:
        """Batch scrape multiple webpages using Firecrawl."""
        try:
            from firecrawl import FirecrawlApp
            
            api_key = os.environ.get("FIRECRAWL_API_KEY")
            if not api_key:
                return {
                    "error": "Firecrawl API key not configured. Please set FIRECRAWL_API_KEY environment variable."
                }
            
            app = FirecrawlApp(api_key=api_key)
            
            # Limit URLs to prevent abuse
            urls = urls[:10]  # Max 10 URLs
            
            # Prepare batch scrape
            scrape_options = {
                "formats": [format],
                "onlyMainContent": True,
                "timeout": 30000
            }
            
            # Note: Using individual scrapes for better control
            # In production, you might want to use Firecrawl's batch API
            results = []
            for idx, url in enumerate(urls):
                try:
                    result = app.scrape_url(url, scrape_options)
                    content = result.get(format, result.get("text", ""))
                    metadata = result.get("metadata", {})
                    
                    results.append({
                        "index": idx + 1,
                        "url": url,
                        "title": metadata.get("title", "No title"),
                        "content_preview": content[:300] + "..." if len(content) > 300 else content,
                        "full_content": content,
                        "success": True
                    })
                except Exception as e:
                    results.append({
                        "index": idx + 1,
                        "url": url,
                        "success": False,
                        "error": str(e)
                    })
            
            successful = [r for r in results if r.get("success", False)]
            failed = [r for r in results if not r.get("success", False)]
            
            return {
                "total_urls": len(urls),
                "successful": len(successful),
                "failed": len(failed),
                "results": results
            }
            
        except ImportError:
            return {
                "error": "Firecrawl library not installed. Please install with: pip install firecrawl-py"
            }
        except Exception as e:
            logging.error(f"Error batch scraping webpages: {e}")
            return {
                "error": f"Failed to batch scrape: {str(e)}"
            }
    
    async def crawl_website(
        self,
        url: str,
        max_pages: int = 50,
        max_depth: int = 2,
        include_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crawl a website to discover pages using Firecrawl."""
        try:
            from firecrawl import FirecrawlApp
            
            api_key = os.environ.get("FIRECRAWL_API_KEY")
            if not api_key:
                return {
                    "error": "Firecrawl API key not configured. Please set FIRECRAWL_API_KEY environment variable."
                }
            
            app = FirecrawlApp(api_key=api_key)
            
            # Limit crawl parameters
            max_pages = min(max(max_pages, 10), 100)
            max_depth = min(max(max_depth, 1), 3)
            
            # Prepare crawl parameters
            crawl_params = {
                "url": url,
                "limit": max_pages,
                "maxDepth": max_depth,
                "allowBackwardLinks": False,
                "allowExternalLinks": False
            }
            
            if include_pattern:
                crawl_params["includePaths"] = [include_pattern]
            
            # Start crawl - this returns immediately with a crawl ID
            crawl_result = app.crawl_url(**crawl_params)
            
            # For async crawls, we'd normally poll for status
            # For now, return the initial response
            if isinstance(crawl_result, dict):
                if "id" in crawl_result:
                    return {
                        "status": "crawl_started",
                        "crawl_id": crawl_result["id"],
                        "message": f"Crawl initiated for {url}. This may take a few minutes.",
                        "parameters": {
                            "max_pages": max_pages,
                            "max_depth": max_depth,
                            "include_pattern": include_pattern
                        }
                    }
                elif "data" in crawl_result:
                    # Immediate results
                    pages = crawl_result.get("data", [])
                    return {
                        "status": "completed",
                        "url": url,
                        "pages_found": len(pages),
                        "pages": [
                            {
                                "url": page.get("url", ""),
                                "title": page.get("metadata", {}).get("title", "No title"),
                                "description": page.get("metadata", {}).get("description", "")[:200]
                            }
                            for page in pages[:20]  # Limit preview to 20 pages
                        ]
                    }
            
            return {
                "status": "unknown",
                "message": "Crawl initiated but status unclear",
                "raw_result": str(crawl_result)[:500]
            }
            
        except ImportError:
            return {
                "error": "Firecrawl library not installed. Please install with: pip install firecrawl-py"
            }
        except Exception as e:
            logging.error(f"Error crawling website {url}: {e}")
            return {
                "error": f"Failed to crawl {url}: {str(e)}"
            }
    
    async def extract_structured_data(
        self,
        urls: List[str],
        extraction_prompt: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract structured data from webpages using Firecrawl's LLM extraction."""
        try:
            from firecrawl import FirecrawlApp
            
            api_key = os.environ.get("FIRECRAWL_API_KEY")
            if not api_key:
                return {
                    "error": "Firecrawl API key not configured. Please set FIRECRAWL_API_KEY environment variable."
                }
            
            app = FirecrawlApp(api_key=api_key)
            
            # Limit URLs
            urls = urls[:5]  # Max 5 URLs for extraction
            
            # Prepare extraction parameters
            extract_params = {
                "urls": urls,
                "prompt": extraction_prompt,
                "allowExternalLinks": False
            }
            
            if schema:
                extract_params["schema"] = schema
            
            # Perform extraction
            result = app.extract(extract_params)
            
            # Format the response
            if "data" in result:
                extracted_data = result["data"]
                return {
                    "extraction_prompt": extraction_prompt,
                    "urls_processed": len(urls),
                    "extracted_data": extracted_data,
                    "success": True
                }
            else:
                return {
                    "extraction_prompt": extraction_prompt,
                    "urls_processed": len(urls),
                    "raw_result": result,
                    "success": False,
                    "message": "Extraction completed but data format unexpected"
                }
                
        except ImportError:
            return {
                "error": "Firecrawl library not installed. Please install with: pip install firecrawl-py"
            }
        except Exception as e:
            logging.error(f"Error extracting structured data: {e}")
            return {
                "error": f"Failed to extract data: {str(e)}"
            }
    
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
        elif tool_name == "scrape_webpage":
            return await self.scrape_webpage(
                arguments["url"],
                arguments.get("format", "markdown"),
                arguments.get("only_main_content", True)
            )
        elif tool_name == "deep_research":
            return await self.deep_research(
                arguments["query"],
                arguments.get("max_time", 60),
                arguments.get("max_sources", 20)
            )
        elif tool_name == "search_and_scrape":
            return await self.search_and_scrape(
                arguments["query"],
                arguments.get("num_results", 3),
                arguments.get("country", "us")
            )
        elif tool_name == "batch_scrape_webpages":
            return await self.batch_scrape_webpages(
                arguments["urls"],
                arguments.get("format", "markdown")
            )
        elif tool_name == "crawl_website":
            return await self.crawl_website(
                arguments["url"],
                arguments.get("max_pages", 50),
                arguments.get("max_depth", 2),
                arguments.get("include_pattern")
            )
        elif tool_name == "extract_structured_data":
            return await self.extract_structured_data(
                arguments["urls"],
                arguments["extraction_prompt"],
                arguments.get("schema")
            )
        else:
            return {"error": f"Unknown tool: {tool_name}"}
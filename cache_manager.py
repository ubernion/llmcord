"""
Cache manager for OpenRouter prompt caching.
Handles intelligent caching for Anthropic Claude and other supported models.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib


@dataclass
class CacheEntry:
    """Represents a cached prompt entry."""
    content: str
    hash: str
    model: str
    timestamp: float
    hits: int = 0
    last_accessed: float = field(default_factory=time.time)
    token_count: int = 0
    cache_type: str = "ephemeral"  # or "persistent"
    
    def access(self):
        """Update access statistics."""
        self.hits += 1
        self.last_accessed = time.time()


class CacheManager:
    """Manages prompt caching for OpenRouter."""
    
    def __init__(self, max_cache_size: int = 100, ttl_seconds: int = 300):
        self.max_cache_size = max_cache_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_stats = defaultdict(int)
        self.supported_models = {
            "anthropic/claude-3-opus",
            "anthropic/claude-3-sonnet", 
            "anthropic/claude-3-5-sonnet",
            "anthropic/claude-3-7-sonnet",
            "openai/gpt-4",
            "openai/gpt-4-turbo",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "deepseek/deepseek-r1",
            "google/gemini-2-5-pro",
            "google/gemini-2-5-flash"
        }
        
    def _generate_hash(self, content: str) -> str:
        """Generate a hash for content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _should_cache(self, content: str, model: str) -> bool:
        """Determine if content should be cached."""
        # Check if model supports caching
        if not any(supported in model.lower() for supported in self.supported_models):
            return False
        
        # Don't cache very short content
        if len(content) < 100:
            return False
        
        # Cache longer content
        return True
    
    def _evict_old_entries(self):
        """Remove old or least recently used cache entries."""
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry.timestamp > self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self.cache[key]
            self.cache_stats["evictions_ttl"] += 1
        
        # If still over limit, remove LRU entries
        if len(self.cache) > self.max_cache_size:
            sorted_entries = sorted(
                self.cache.items(),
                key=lambda x: x[1].last_accessed
            )
            
            num_to_remove = len(self.cache) - self.max_cache_size
            for key, _ in sorted_entries[:num_to_remove]:
                del self.cache[key]
                self.cache_stats["evictions_lru"] += 1
    
    def prepare_messages_for_caching(
        self, 
        messages: List[Dict[str, Any]], 
        model: str
    ) -> List[Dict[str, Any]]:
        """Prepare messages with cache control for supported models."""
        if not any(supported in model.lower() for supported in self.supported_models):
            return messages
        
        cached_messages = []
        
        for i, msg in enumerate(messages):
            msg_copy = msg.copy()
            
            # Handle system prompts and large user messages
            if msg["role"] == "system" or (
                msg["role"] == "user" and 
                isinstance(msg.get("content"), str) and 
                len(msg["content"]) > 500
            ):
                # For Anthropic models, add cache_control
                if "anthropic" in model.lower():
                    content = msg.get("content", "")
                    
                    if isinstance(content, str) and self._should_cache(content, model):
                        # Convert to multipart format for cache control
                        msg_copy["content"] = [
                            {
                                "type": "text",
                                "text": content,
                                "cache_control": {"type": "ephemeral"}
                            }
                        ]
                        
                        # Track cache usage
                        content_hash = self._generate_hash(content)
                        if content_hash not in self.cache:
                            self.cache[content_hash] = CacheEntry(
                                content=content,
                                hash=content_hash,
                                model=model,
                                timestamp=time.time(),
                                token_count=len(content.split())  # Rough estimate
                            )
                            self.cache_stats["cache_writes"] += 1
                        else:
                            self.cache[content_hash].access()
                            self.cache_stats["cache_hits"] += 1
                
                # For OpenAI models, they handle caching automatically
                elif "openai" in model.lower() or "gpt" in model.lower():
                    # No special formatting needed, OpenAI handles it
                    pass
                
                # For Google models with implicit caching
                elif "gemini" in model.lower():
                    # Gemini 2.5 models support implicit caching automatically
                    pass
            
            cached_messages.append(msg_copy)
        
        # Clean up old cache entries
        self._evict_old_entries()
        
        return cached_messages
    
    def add_reasoning_cache(
        self,
        messages: List[Dict[str, Any]],
        reasoning_content: str,
        model: str
    ) -> List[Dict[str, Any]]:
        """Add reasoning content with caching for supported models."""
        if "anthropic" in model.lower() and reasoning_content:
            # For Anthropic, add reasoning as a cached message
            reasoning_msg = {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": reasoning_content,
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            }
            return messages + [reasoning_msg]
        
        return messages
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        total_hits = sum(entry.hits for entry in self.cache.values())
        
        return {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "cache_writes": self.cache_stats["cache_writes"],
            "cache_hits": self.cache_stats["cache_hits"],
            "evictions_ttl": self.cache_stats["evictions_ttl"],
            "evictions_lru": self.cache_stats["evictions_lru"],
            "hit_rate": (
                self.cache_stats["cache_hits"] / 
                (self.cache_stats["cache_hits"] + self.cache_stats["cache_writes"])
                if self.cache_stats["cache_hits"] + self.cache_stats["cache_writes"] > 0
                else 0
            ),
            "cache_size_mb": sum(
                len(entry.content.encode()) for entry in self.cache.values()
            ) / (1024 * 1024)
        }
    
    def estimate_cache_savings(self, model: str) -> Dict[str, float]:
        """Estimate cost savings from caching."""
        # Rough estimates based on OpenRouter documentation
        cache_discounts = {
            "anthropic": {"write": 1.25, "read": 0.1},  # 25% more for writes, 90% discount for reads
            "openai": {"write": 0, "read": 0.5},  # No write cost, 50% discount for reads
            "google": {"write": 0, "read": 0.25},  # No write cost, 75% discount for reads
            "deepseek": {"write": 1.0, "read": 0.1}  # Same cost for writes, 90% discount for reads
        }
        
        provider = model.split("/")[0].lower()
        discount = cache_discounts.get(provider, {"write": 0, "read": 0})
        
        total_tokens_cached = sum(entry.token_count for entry in self.cache.values())
        total_cache_reads = sum(entry.hits for entry in self.cache.values())
        
        # Estimate savings (very rough approximation)
        write_cost = total_tokens_cached * discount["write"]
        read_savings = total_cache_reads * total_tokens_cached * (1 - discount["read"])
        
        return {
            "estimated_tokens_cached": total_tokens_cached,
            "estimated_cache_reads": total_cache_reads,
            "estimated_write_cost": write_cost,
            "estimated_read_savings": read_savings,
            "net_savings": read_savings - write_cost
        }
    
    def clear_cache(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.cache_stats.clear()
        logging.info("Cache cleared")
    
    def get_model_cache_info(self, model: str) -> Dict[str, Any]:
        """Get cache information for a specific model."""
        is_supported = any(supported in model.lower() for supported in self.supported_models)
        
        cache_info = {
            "model": model,
            "caching_supported": is_supported,
            "cache_type": None,
            "notes": []
        }
        
        if "anthropic" in model.lower():
            cache_info["cache_type"] = "explicit"
            cache_info["notes"].append("Uses cache_control headers")
            cache_info["notes"].append("Supports ephemeral caching (5 min TTL)")
            
        elif "openai" in model.lower() or "gpt" in model.lower():
            cache_info["cache_type"] = "automatic"
            cache_info["notes"].append("Automatic caching, no configuration needed")
            cache_info["notes"].append("Minimum 1024 tokens for caching")
            
        elif "gemini" in model.lower() and "2-5" in model:
            cache_info["cache_type"] = "implicit"
            cache_info["notes"].append("Implicit caching for Gemini 2.5 models")
            cache_info["notes"].append("3-5 minute average TTL")
            
        elif "deepseek" in model.lower():
            cache_info["cache_type"] = "automatic"
            cache_info["notes"].append("Automatic caching enabled")
            
        return cache_info
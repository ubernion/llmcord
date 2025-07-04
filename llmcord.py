import asyncio
from base64 import b64encode
from dataclasses import dataclass, field
from datetime import datetime
import logging
import os
import re
from typing import Any, Literal, Optional
import json
import copy

import discord
from discord.app_commands import Choice
from discord.ext import commands
import httpx
from openai import AsyncOpenAI
import yaml

from tools import DiscordTools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

VISION_MODEL_TAGS = ("gpt-4", "o3", "o4", "claude", "gemini", "gemma", "llama", "pixtral", "mistral", "vision", "vl")
PROVIDERS_SUPPORTING_USERNAMES = ("openai", "x-ai")
TOOLS_SUPPORTING_MODELS = ("gpt-4", "claude", "gemini", "mistral")

EMBED_COLOR_COMPLETE = discord.Color.dark_green()
EMBED_COLOR_INCOMPLETE = discord.Color.orange()

STREAMING_INDICATOR = "..."
EDIT_DELAY_SECONDS = 1

MAX_MESSAGE_NODES = 2000  # Increased for better memory


def replace_env_vars(obj: Any) -> Any:
    """Recursively replace environment variable placeholders in config."""
    if isinstance(obj, str):
        # Match ${VAR} or ${{ VAR }} patterns
        def replacer(match):
            var_name = match.group(1).strip()
            value = os.environ.get(var_name)
            if value is None:
                logging.warning(f"Environment variable {var_name} not found, keeping placeholder")
                return match.group(0)
            return value
        
        # Replace both ${VAR} and ${{ VAR }} patterns
        obj = re.sub(r'\$\{\{\s*(\w+)\s*\}\}', replacer, obj)
        obj = re.sub(r'\$\{(\w+)\}', replacer, obj)
        return obj
    elif isinstance(obj, dict):
        return {k: replace_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_env_vars(item) for item in obj]
    else:
        return obj


def get_config(filename: str = "config.yaml") -> dict[str, Any]:
    with open(filename, encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return replace_env_vars(config)


config = get_config()
# Set default model to Claude Sonnet 4 with online
curr_model = "openrouter/anthropic/claude-sonnet-4:online"
if curr_model not in config["models"]:
    curr_model = next(iter(config["models"]))

msg_nodes = {}
last_task_time = 0

intents = discord.Intents.default()
intents.message_content = True
activity = discord.CustomActivity(name=(config["status_message"] or "github.com/jakobdylanc/llmcord")[:128])
discord_bot = commands.Bot(intents=intents, activity=activity, command_prefix=None)

# Initialize Discord tools
discord_tools = DiscordTools(discord_bot)

httpx_client = httpx.AsyncClient()


@dataclass
class MsgNode:
    text: Optional[str] = None
    images: list[dict[str, Any]] = field(default_factory=list)

    role: Literal["user", "assistant"] = "assistant"
    user_id: Optional[int] = None
    display_name: Optional[str] = None

    has_bad_attachments: bool = False
    fetch_parent_failed: bool = False

    parent_msg: Optional[discord.Message] = None

    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def apply_anthropic_cache_control(messages: list[dict], config: dict) -> list[dict]:
    """
    Apply cache control breakpoints to messages for Anthropic models via OpenRouter.
    
    Rules:
    - Maximum 4 breakpoints allowed
    - Cache expires in 5 minutes
    - Prioritize system prompt and older/larger messages
    - Only apply to text content in multipart messages
    """
    MIN_CACHE_LENGTH = config.get("cache_min_length", 1000)  # Minimum text length to consider caching
    MAX_BREAKPOINTS = 4
    
    # Create a deep copy to avoid modifying the original
    messages = copy.deepcopy(messages)
    
    # Convert all messages to multipart format if needed
    for msg in messages:
        if isinstance(msg.get("content"), str):
            msg["content"] = [{"type": "text", "text": msg["content"]}]
    
    # Collect candidates for caching (message index, content index, text length)
    cache_candidates = []
    
    for msg_idx, msg in enumerate(messages):
        if isinstance(msg.get("content"), list):
            for content_idx, content in enumerate(msg["content"]):
                if content.get("type") == "text" and len(content.get("text", "")) >= MIN_CACHE_LENGTH:
                    # Prioritize system messages, then older messages
                    priority = 0 if msg["role"] == "system" else msg_idx + 1
                    cache_candidates.append({
                        "msg_idx": msg_idx,
                        "content_idx": content_idx,
                        "length": len(content["text"]),
                        "priority": priority,
                        "role": msg["role"]
                    })
    
    # Sort by priority (system first, then older messages), then by length (larger first)
    cache_candidates.sort(key=lambda x: (x["priority"], -x["length"]))
    
    # Apply cache control to top candidates
    breakpoints_applied = 0
    for candidate in cache_candidates[:MAX_BREAKPOINTS]:
        msg_idx = candidate["msg_idx"]
        content_idx = candidate["content_idx"]
        
        # Add cache_control to the content
        messages[msg_idx]["content"][content_idx]["cache_control"] = {"type": "ephemeral"}
        breakpoints_applied += 1
        
        logging.info(f"Applied cache control to {candidate['role']} message (index {msg_idx}, length {candidate['length']})")
    
    if breakpoints_applied > 0:
        logging.info(f"Applied {breakpoints_applied} cache control breakpoints for Anthropic model")
    
    return messages


@discord_bot.tree.command(name="model", description="View or switch the current model")
async def model_command(interaction: discord.Interaction, model: str) -> None:
    global curr_model

    if model == curr_model:
        output = f"Current model: `{curr_model}`"
    else:
        if user_is_admin := interaction.user.id in config["permissions"]["users"]["admin_ids"]:
            curr_model = model
            output = f"Model switched to: `{model}`"
            logging.info(output)
        else:
            output = "You don't have permission to change the model."

    await interaction.response.send_message(output, ephemeral=(interaction.channel.type == discord.ChannelType.private))


@model_command.autocomplete("model")
async def model_autocomplete(interaction: discord.Interaction, curr_str: str) -> list[Choice[str]]:
    global config

    if curr_str == "":
        config = await asyncio.to_thread(get_config)

    choices = [Choice(name=f"○ {model}", value=model) for model in config["models"] if model != curr_model and curr_str.lower() in model.lower()][:24]
    choices += [Choice(name=f"◉ {curr_model} (current)", value=curr_model)] if curr_str.lower() in curr_model.lower() else []

    return choices


@discord_bot.event
async def on_ready() -> None:
    if client_id := config["client_id"]:
        logging.info(f"\n\nBOT INVITE URL:\nhttps://discord.com/oauth2/authorize?client_id={client_id}&permissions=412317273088&scope=bot\n")

    await discord_bot.tree.sync()


@discord_bot.event
async def on_message(new_msg: discord.Message) -> None:
    global last_task_time

    is_dm = new_msg.channel.type == discord.ChannelType.private

    # Check if the message mentions the bot or contains "Claude" (case insensitive)
    mentioned = discord_bot.user in new_msg.mentions
    contains_claude = "claude" in new_msg.content.lower()
    
    if (not is_dm and not mentioned and not contains_claude) or new_msg.author.bot:
        return

    role_ids = set(role.id for role in getattr(new_msg.author, "roles", ()))
    channel_ids = set(filter(None, (new_msg.channel.id, getattr(new_msg.channel, "parent_id", None), getattr(new_msg.channel, "category_id", None))))

    config = await asyncio.to_thread(get_config)

    allow_dms = config.get("allow_dms", True)

    permissions = config["permissions"]

    user_is_admin = new_msg.author.id in permissions["users"]["admin_ids"]

    (allowed_user_ids, blocked_user_ids), (allowed_role_ids, blocked_role_ids), (allowed_channel_ids, blocked_channel_ids) = (
        (perm["allowed_ids"], perm["blocked_ids"]) for perm in (permissions["users"], permissions["roles"], permissions["channels"])
    )

    allow_all_users = not allowed_user_ids if is_dm else not allowed_user_ids and not allowed_role_ids
    is_good_user = user_is_admin or allow_all_users or new_msg.author.id in allowed_user_ids or any(id in allowed_role_ids for id in role_ids)
    is_bad_user = not is_good_user or new_msg.author.id in blocked_user_ids or any(id in blocked_role_ids for id in role_ids)

    allow_all_channels = not allowed_channel_ids
    is_good_channel = user_is_admin or allow_dms if is_dm else allow_all_channels or any(id in allowed_channel_ids for id in channel_ids)
    is_bad_channel = not is_good_channel or any(id in blocked_channel_ids for id in channel_ids)

    if is_bad_user or is_bad_channel:
        return

    provider_slash_model = curr_model
    
    # Check for model variants like :online or :thinking
    base_model = provider_slash_model
    model_variant = None
    if ":" in provider_slash_model:
        base_model, model_variant = provider_slash_model.rsplit(":", 1)
    
    provider, model = base_model.split("/", 1)
    model_parameters = config["models"].get(base_model, {})

    base_url = config["providers"][provider]["base_url"]
    api_key = config["providers"][provider].get("api_key", "sk-no-key-required")
    openai_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    
    # Check if model supports tools
    supports_tools = any(tag in model.lower() for tag in TOOLS_SUPPORTING_MODELS)
    use_tools = supports_tools and config.get("enable_tools", True)

    accept_images = any(x in model.lower() for x in VISION_MODEL_TAGS)
    accept_usernames = any(x in provider_slash_model.lower() for x in PROVIDERS_SUPPORTING_USERNAMES)

    max_text = config.get("max_text", 100000)
    max_images = config.get("max_images", 5) if accept_images else 0
    max_messages = config.get("max_messages", 50)  # Increased for better context

    # Build message chain and set user warnings
    messages = []
    user_warnings = set()
    processed_msg_ids = set()  # Track which messages we've already added
    
    # First, try to get recent channel context if we have tools - DISABLED for now
    # This was causing duplicate messages
    if False and use_tools and len(messages) < max_messages:
        try:
            # Get last 30 messages from channel for context
            recent_msgs = [m async for m in new_msg.channel.history(limit=30)]
            recent_msgs.reverse()  # Make chronological
            
            # Add recent messages that mention the bot or are from the bot
            for msg in recent_msgs:
                if len(messages) >= max_messages:
                    break
                if msg.id == new_msg.id:
                    continue  # Skip the current message, we'll add it properly
                if msg.author == discord_bot.user or discord_bot.user in msg.mentions or "claude" in msg.content.lower():
                    # Process this message
                    node = msg_nodes.setdefault(msg.id, MsgNode())
                    async with node.lock:
                        if node.text is None:
                            node.text = msg.content
                            node.role = "assistant" if msg.author == discord_bot.user else "user"
                            node.user_id = msg.author.id if node.role == "user" else None
                            node.display_name = msg.author.display_name if node.role == "user" else None
                    
                    if node.text:
                        content = node.text[:max_text]
                        if node.role == "user" and node.display_name:
                            content = f"[{node.display_name}]: {content}"
                        
                        message = dict(content=content, role=node.role)
                        if accept_usernames and node.user_id != None:
                            message["name"] = str(node.user_id)
                        messages.append(message)
        except Exception as e:
            logging.warning(f"Failed to get recent context: {e}")
    
    # Now build the reply chain as before
    curr_msg = new_msg

    while curr_msg != None and len(messages) < max_messages:
        curr_node = msg_nodes.setdefault(curr_msg.id, MsgNode())

        async with curr_node.lock:
            if curr_node.text == None:
                cleaned_content = curr_msg.content.removeprefix(discord_bot.user.mention).lstrip()

                good_attachments = [att for att in curr_msg.attachments if att.content_type and any(att.content_type.startswith(x) for x in ("text", "image"))]

                attachment_responses = await asyncio.gather(*[httpx_client.get(att.url) for att in good_attachments])

                curr_node.text = "\n".join(
                    ([cleaned_content] if cleaned_content else [])
                    + ["\n".join(filter(None, (embed.title, embed.description, embed.footer.text))) for embed in curr_msg.embeds]
                    + [resp.text for att, resp in zip(good_attachments, attachment_responses) if att.content_type.startswith("text")]
                )

                curr_node.images = [
                    dict(type="image_url", image_url=dict(url=f"data:{att.content_type};base64,{b64encode(resp.content).decode('utf-8')}"))
                    for att, resp in zip(good_attachments, attachment_responses)
                    if att.content_type.startswith("image")
                ]

                curr_node.role = "assistant" if curr_msg.author == discord_bot.user else "user"

                curr_node.user_id = curr_msg.author.id if curr_node.role == "user" else None
                curr_node.display_name = curr_msg.author.display_name if curr_node.role == "user" else None

                curr_node.has_bad_attachments = len(curr_msg.attachments) > len(good_attachments)

                try:
                    if (
                        curr_msg.reference == None
                        and discord_bot.user.mention not in curr_msg.content
                        and "claude" not in curr_msg.content.lower()
                        and (prev_msg_in_channel := ([m async for m in curr_msg.channel.history(before=curr_msg, limit=1)] or [None])[0])
                        and prev_msg_in_channel.type in (discord.MessageType.default, discord.MessageType.reply)
                        and prev_msg_in_channel.author == (discord_bot.user if curr_msg.channel.type == discord.ChannelType.private else curr_msg.author)
                    ):
                        curr_node.parent_msg = prev_msg_in_channel
                    else:
                        is_public_thread = curr_msg.channel.type == discord.ChannelType.public_thread
                        parent_is_thread_start = is_public_thread and curr_msg.reference == None and curr_msg.channel.parent.type == discord.ChannelType.text

                        if parent_msg_id := curr_msg.channel.id if parent_is_thread_start else getattr(curr_msg.reference, "message_id", None):
                            if parent_is_thread_start:
                                curr_node.parent_msg = curr_msg.channel.starter_message or await curr_msg.channel.parent.fetch_message(parent_msg_id)
                            else:
                                curr_node.parent_msg = curr_msg.reference.cached_message or await curr_msg.channel.fetch_message(parent_msg_id)

                except (discord.NotFound, discord.HTTPException):
                    logging.exception("Error fetching next message in the chain")
                    curr_node.fetch_parent_failed = True

            if curr_node.images[:max_images]:
                content = ([dict(type="text", text=curr_node.text[:max_text])] if curr_node.text[:max_text] else []) + curr_node.images[:max_images]
            else:
                content = curr_node.text[:max_text]

            if content != "":
                # Add display name to the beginning of user messages for context
                if curr_node.role == "user" and curr_node.display_name:
                    if isinstance(content, str):
                        content = f"[{curr_node.display_name}]: {content}"
                    elif isinstance(content, list) and content and content[0].get("type") == "text":
                        content[0]["text"] = f"[{curr_node.display_name}]: {content[0]['text']}"
                
                message = dict(content=content, role=curr_node.role)
                if accept_usernames and curr_node.user_id != None:
                    message["name"] = str(curr_node.user_id)

                messages.append(message)

            if len(curr_node.text) > max_text:
                user_warnings.add(f"⚠️ Max {max_text:,} characters per message")
            if len(curr_node.images) > max_images:
                user_warnings.add(f"⚠️ Max {max_images} image{'' if max_images == 1 else 's'} per message" if max_images > 0 else "⚠️ Can't see images")
            if curr_node.has_bad_attachments:
                user_warnings.add("⚠️ Unsupported attachments")
            if curr_node.fetch_parent_failed or (curr_node.parent_msg != None and len(messages) == max_messages):
                user_warnings.add(f"⚠️ Only using last {len(messages)} message{'' if len(messages) == 1 else 's'}")

            curr_msg = curr_node.parent_msg

    logging.info(f"Message received (user ID: {new_msg.author.id}, attachments: {len(new_msg.attachments)}, conversation length: {len(messages)}):\n{new_msg.content}")

    if system_prompt := config["system_prompt"]:
        now = datetime.now().astimezone()

        system_prompt = system_prompt.replace("{date}", now.strftime("%B %d %Y")).replace("{time}", now.strftime("%H:%M:%S %Z%z")).strip()

        messages.append(dict(role="system", content=system_prompt))
    
    # Prepare tool definitions if supported
    tools = None
    if use_tools:
        tools = discord_tools.tool_definitions

    # Generate and send response message(s) (can be multiple if response is long)
    curr_content = finish_reason = edit_task = None
    response_msgs = []
    response_contents = []

    use_plain_responses = config.get("use_plain_responses", False)
    max_message_length = 2000 if use_plain_responses else (4096 - len(STREAMING_INDICATOR))
    
    # Handle warnings
    if user_warnings and use_plain_responses:
        warning_msg = "⚠️ " + " | ".join(sorted(user_warnings))
        await new_msg.reply(content=warning_msg, silent=True, delete_after=30)
    elif user_warnings and not use_plain_responses:
        embed = discord.Embed()
        for warning in sorted(user_warnings):
            embed.add_field(name=warning, value="", inline=False)

    # Apply cache control for Anthropic models via OpenRouter
    is_anthropic = provider == "openrouter" and ("anthropic" in model.lower() or "claude" in model.lower())
    if is_anthropic:
        messages = apply_anthropic_cache_control(messages, config)

    try:
        async with new_msg.channel.typing():
            # Create the completion request with optional tools
            # Remove the provider prefix for the API call
            api_model_name = model if not model_variant else f"{model}:{model_variant}"
            create_params = {
                "model": api_model_name,  # Use model name without provider prefix
                "messages": messages[::-1],
                "stream": True
            }
            
            # Add model parameters
            if model_parameters:
                create_params["extra_body"] = model_parameters
            
            # Add tools if supported
            if tools:
                create_params["tools"] = tools
                create_params["tool_choice"] = "auto"  # Let model decide when to use tools
            
            # Handle reasoning mode
            if model_variant == "thinking":
                if "extra_body" not in create_params:
                    create_params["extra_body"] = {}
                create_params["extra_body"]["reasoning"] = {
                    "enabled": True,
                    "effort": "medium"
                }
            
            # Enable usage tracking for Anthropic models to see cache savings
            if is_anthropic:
                if "extra_body" not in create_params:
                    create_params["extra_body"] = {}
                create_params["extra_body"]["usage"] = {"include": True}
            
            # Stream the response
            tool_calls = []
            cache_discount = None
            async for curr_chunk in await openai_client.chat.completions.create(**create_params):
                if finish_reason != None:
                    break

                if not (choice := curr_chunk.choices[0] if curr_chunk.choices else None):
                    continue

                finish_reason = choice.finish_reason
                
                # Check for cache usage information
                if is_anthropic and hasattr(curr_chunk, 'usage') and curr_chunk.usage:
                    if hasattr(curr_chunk.usage, 'cache_discount'):
                        cache_discount = curr_chunk.usage.cache_discount

                # Handle tool calls
                if hasattr(choice.delta, 'tool_calls') and choice.delta.tool_calls:
                    for tool_call in choice.delta.tool_calls:
                        if len(tool_calls) <= tool_call.index:
                            tool_calls.append({
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            })
                        
                        if tool_call.id:
                            tool_calls[tool_call.index]["id"] = tool_call.id
                        if tool_call.function.name:
                            tool_calls[tool_call.index]["function"]["name"] = tool_call.function.name
                        if tool_call.function.arguments:
                            tool_calls[tool_call.index]["function"]["arguments"] += tool_call.function.arguments

                prev_content = curr_content or ""
                curr_content = choice.delta.content or ""

                new_content = prev_content if finish_reason == None else (prev_content + curr_content)

                if response_contents == [] and new_content == "":
                    continue

                if start_next_msg := response_contents == [] or len(response_contents[-1] + new_content) > max_message_length:
                    response_contents.append("")

                response_contents[-1] += new_content

                if not use_plain_responses:
                    if 'embed' not in locals():
                        embed = discord.Embed()
                    ready_to_edit = (edit_task == None or edit_task.done()) and datetime.now().timestamp() - last_task_time >= EDIT_DELAY_SECONDS
                    msg_split_incoming = finish_reason == None and len(response_contents[-1] + curr_content) > max_message_length
                    is_final_edit = finish_reason != None or msg_split_incoming
                    is_good_finish = finish_reason != None and finish_reason.lower() in ("stop", "end_turn")

                    if start_next_msg or ready_to_edit or is_final_edit:
                        if edit_task != None:
                            await edit_task

                        embed.description = response_contents[-1] if is_final_edit else (response_contents[-1] + STREAMING_INDICATOR)
                        embed.color = EMBED_COLOR_COMPLETE if msg_split_incoming or is_good_finish else EMBED_COLOR_INCOMPLETE

                        if start_next_msg:
                            reply_to_msg = new_msg if response_msgs == [] else response_msgs[-1]
                            response_msg = await reply_to_msg.reply(embed=embed, silent=True)
                            response_msgs.append(response_msg)

                            msg_nodes[response_msg.id] = MsgNode(parent_msg=new_msg)
                            await msg_nodes[response_msg.id].lock.acquire()
                        else:
                            edit_task = asyncio.create_task(response_msgs[-1].edit(embed=embed))

                        last_task_time = datetime.now().timestamp()
            
            # Handle tool calls if any - loop until no more tools requested
            while tool_calls and finish_reason == "tool_calls":
                # Process tool calls and show indicator
                tool_results = []
                
                # Process tool calls silently - no indicator messages
                
                for tool_call in tool_calls:
                    try:
                        # Handle both dict and object formats
                        if isinstance(tool_call, dict):
                            func_name = tool_call["function"]["name"]
                            func_args = json.loads(tool_call["function"]["arguments"])
                            tool_id = tool_call["id"]
                        else:
                            func_name = tool_call.function.name
                            func_args = json.loads(tool_call.function.arguments)
                            tool_id = tool_call.id
                        
                        # Execute the tool
                        result = await discord_tools.handle_tool_call(
                            func_name,
                            func_args,
                            new_msg.channel
                        )
                        
                        tool_results.append(result)
                        
                        # Don't add tool result yet, we'll add it after the assistant message
                        
                    except Exception as e:
                        logging.error(f"Error executing tool {func_name}: {e}")
                        tool_results.append({"error": str(e)})
                
                # Add assistant message with tool calls first
                messages.insert(0, {
                    "role": "assistant",
                    "content": None,  # Important: content should be None when using tools
                    "tool_calls": tool_calls
                })
                
                # Now add tool results AFTER the assistant message (so they come after when reversed)
                for i, tool_call in enumerate(tool_calls):
                    # Handle both dict and object formats
                    if isinstance(tool_call, dict):
                        func_name = tool_call["function"]["name"]
                        tool_id = tool_call["id"]
                    else:
                        func_name = tool_call.function.name
                        tool_id = tool_call.id
                    
                    messages.insert(0, {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": func_name,
                        "content": json.dumps(tool_results[i])
                    })
                
                # Make another API call with tool results
                try:
                    # Debug: log the messages to understand the issue
                    logging.info(f"Messages being sent for tool response (first 3): {json.dumps(messages[:3], indent=2)[:500]}...")
                    
                    final_response = await openai_client.chat.completions.create(
                        model=api_model_name,  # Use the same model name format as initial request
                        messages=messages[::-1],
                        stream=False,
                        tools=tools,  # Keep tools available for continued use
                        tool_choice="auto"
                    )
                    
                    final_msg = final_response.choices[0].message
                    finish_reason = final_response.choices[0].finish_reason
                    
                    # Check if more tools are requested
                    if finish_reason == "tool_calls" and hasattr(final_msg, 'tool_calls') and final_msg.tool_calls:
                        # Add assistant message and prepare for next loop iteration
                        messages.insert(0, final_msg.model_dump())
                        tool_calls = final_msg.tool_calls
                        continue  # Loop back to process more tools
                    
                    elif final_msg.content:
                        # Send the final response naturally
                        final_content = final_msg.content
                        
                        # Split long messages if needed
                        if len(final_content) > 2000:
                            chunks = [final_content[i:i+2000] for i in range(0, len(final_content), 2000)]
                            for chunk in chunks[:3]:  # Limit to 3 messages
                                if response_msgs:
                                    response_msg = await response_msgs[-1].reply(content=chunk, suppress_embeds=True, silent=True)
                                else:
                                    response_msg = await new_msg.reply(content=chunk, suppress_embeds=True, silent=True)
                                response_msgs.append(response_msg)
                                msg_nodes[response_msg.id] = MsgNode(parent_msg=new_msg)
                                await msg_nodes[response_msg.id].lock.acquire()
                        else:
                            if response_msgs:
                                response_msg = await response_msgs[-1].reply(content=final_content, suppress_embeds=True, silent=True)
                            else:
                                response_msg = await new_msg.reply(content=final_content, suppress_embeds=True, silent=True)
                            response_msgs.append(response_msg)
                            msg_nodes[response_msg.id] = MsgNode(parent_msg=new_msg)
                            await msg_nodes[response_msg.id].lock.acquire()
                        
                        # Update response contents for final processing
                        response_contents.append(final_content)
                    
                    # Exit the tool loop
                    tool_calls = None
                    
                except Exception as e:
                    logging.error(f"Error getting final response after tools: {e}")
                    tool_calls = None  # Exit loop on error

            # Log cache discount if available
            if is_anthropic and cache_discount is not None:
                logging.info(f"Cache discount for Anthropic model: {cache_discount}")
            
            if use_plain_responses:
                for content in response_contents:
                    reply_to_msg = new_msg if response_msgs == [] else response_msgs[-1]
                    response_msg = await reply_to_msg.reply(content=content, suppress_embeds=True)
                    response_msgs.append(response_msg)

                    msg_nodes[response_msg.id] = MsgNode(parent_msg=new_msg)
                    await msg_nodes[response_msg.id].lock.acquire()

    except Exception:
        logging.exception("Error while generating response")

    for response_msg in response_msgs:
        msg_nodes[response_msg.id].text = "".join(response_contents)
        msg_nodes[response_msg.id].lock.release()

    # Delete oldest MsgNodes (lowest message IDs) from the cache
    if (num_nodes := len(msg_nodes)) > MAX_MESSAGE_NODES:
        for msg_id in sorted(msg_nodes.keys())[: num_nodes - MAX_MESSAGE_NODES]:
            async with msg_nodes.setdefault(msg_id, MsgNode()).lock:
                msg_nodes.pop(msg_id, None)


async def main() -> None:
    await discord_bot.start(config["bot_token"])


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass

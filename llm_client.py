"""
Production-grade LLM client with comprehensive error handling, observability,
resilience patterns, and proper resource management.
"""

import asyncio
import hashlib
import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Optional, Protocol

import structlog
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from cachetools import TTLCache
from pybreaker import CircuitBreaker

from client.response import (
    StreamEventType,
    StreamEvent,
    TextDelta,
    TokenUsage,
    ToolCall,
    ToolCallDelta,
    parse_tool_call_arguments,
)
from config.config import Config

# Configure structured logging
logger = structlog.get_logger(__name__)


# ============================================================================
# Configuration Classes
# ============================================================================


@dataclass
class TimeoutConfig:
    """HTTP timeout configuration for different operations."""
    
    connect: float = 10.0  # Connection establishment timeout
    read: float = 120.0    # Read timeout (higher for streaming)
    write: float = 10.0    # Write timeout
    pool: float = 5.0      # Connection pool timeout


@dataclass
class RetryConfig:
    """Retry configuration with exponential backoff."""
    
    max_attempts: int = 3
    min_wait: float = 1.0
    max_wait: float = 60.0
    multiplier: float = 2.0
    
    def __post_init__(self):
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.min_wait <= 0:
            raise ValueError("min_wait must be positive")


@dataclass
class CacheConfig:
    """Cache configuration for request/response caching."""
    
    enabled: bool = True
    max_size: int = 100
    ttl_seconds: int = 3600  # 1 hour
    
    def __post_init__(self):
        if self.max_size < 0:
            raise ValueError("max_size must be non-negative")
        if self.ttl_seconds < 0:
            raise ValueError("ttl_seconds must be non-negative")


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration for fault tolerance."""
    
    enabled: bool = True
    fail_max: int = 5           # Open circuit after N failures
    timeout_duration: int = 60   # Seconds before attempting reset
    
    def __post_init__(self):
        if self.fail_max < 1:
            raise ValueError("fail_max must be at least 1")


@dataclass
class LLMClientConfig:
    """Comprehensive LLM client configuration."""
    
    api_config: Config
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    enable_metrics: bool = True
    
    def __post_init__(self):
        """Validate API configuration."""
        if not self.api_config.api_key or not self.api_config.api_key.strip():
            raise ValueError("API key cannot be empty")
        if not self.api_config.base_url or not self.api_config.base_url.startswith("http"):
            raise ValueError("Invalid base URL - must start with http:// or https://")
        if not self.api_config.model_name or not self.api_config.model_name.strip():
            raise ValueError("Model name cannot be empty")


# ============================================================================
# Metrics & Observability
# ============================================================================


class MetricsCollector(Protocol):
    """Protocol for metrics collection (can be implemented with Prometheus, StatsD, etc.)."""
    
    def record_request(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_seconds: float,
    ) -> None:
        """Record a successful LLM request."""
        ...
    
    def record_error(self, model: str, error_type: str) -> None:
        """Record an error."""
        ...
    
    def record_cache_hit(self, model: str) -> None:
        """Record a cache hit."""
        ...
    
    def record_cache_miss(self, model: str) -> None:
        """Record a cache miss."""
        ...


class SimpleMetricsCollector:
    """Simple in-memory metrics collector for development/testing."""
    
    def __init__(self):
        self.requests = 0
        self.errors = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_tokens = 0
    
    def record_request(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_seconds: float,
    ) -> None:
        self.requests += 1
        self.total_tokens += prompt_tokens + completion_tokens
        logger.debug(
            "request_recorded",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration=duration_seconds,
        )
    
    def record_error(self, model: str, error_type: str) -> None:
        self.errors += 1
        logger.warning("error_recorded", model=model, error_type=error_type)
    
    def record_cache_hit(self, model: str) -> None:
        self.cache_hits += 1
        logger.debug("cache_hit", model=model)
    
    def record_cache_miss(self, model: str) -> None:
        self.cache_misses += 1
        logger.debug("cache_miss", model=model)
    
    def get_stats(self) -> dict[str, int]:
        """Get current metrics snapshot."""
        return {
            "requests": self.requests,
            "errors": self.errors,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_tokens": self.total_tokens,
        }


# ============================================================================
# Custom Exceptions
# ============================================================================


class LLMClientError(Exception):
    """Base exception for LLM client errors."""
    pass


class LLMConfigurationError(LLMClientError):
    """Configuration validation error."""
    pass


class LLMToolValidationError(LLMClientError):
    """Tool schema validation error."""
    pass


class LLMCircuitBreakerOpenError(LLMClientError):
    """Circuit breaker is open, requests are blocked."""
    pass


# ============================================================================
# Tool Validation
# ============================================================================


class ToolValidator:
    """Validates tool definitions against OpenAI function calling schema."""
    
    TOOL_SCHEMA = {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {
                "type": "string",
                "minLength": 1,
                "maxLength": 64,
                "pattern": "^[a-zA-Z0-9_-]+$"
            },
            "description": {"type": "string"},
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "properties": {"type": "object"},
                    "required": {"type": "array"}
                }
            }
        }
    }
    
    @staticmethod
    def validate_tool(tool: dict[str, Any]) -> None:
        """
        Validate a single tool definition.
        
        Args:
            tool: Tool definition dictionary
            
        Raises:
            LLMToolValidationError: If tool is invalid
        """
        if not isinstance(tool, dict):
            raise LLMToolValidationError("Tool must be a dictionary")
        
        if "name" not in tool:
            raise LLMToolValidationError("Tool must have a 'name' field")
        
        name = tool["name"]
        if not isinstance(name, str) or not name.strip():
            raise LLMToolValidationError("Tool name must be a non-empty string")
        
        if not name.replace("_", "").replace("-", "").isalnum():
            raise LLMToolValidationError(
                f"Tool name '{name}' must contain only alphanumeric characters, "
                "hyphens, and underscores"
            )
        
        if len(name) > 64:
            raise LLMToolValidationError(f"Tool name '{name}' exceeds 64 characters")
        
        # Validate parameters if present
        if "parameters" in tool:
            params = tool["parameters"]
            if not isinstance(params, dict):
                raise LLMToolValidationError("Tool parameters must be a dictionary")
            
            if "type" in params and params["type"] != "object":
                raise LLMToolValidationError("Tool parameters type must be 'object'")
    
    @staticmethod
    def validate_tools(tools: list[dict[str, Any]]) -> None:
        """Validate a list of tool definitions."""
        if not isinstance(tools, list):
            raise LLMToolValidationError("Tools must be a list")
        
        seen_names = set()
        for idx, tool in enumerate(tools):
            try:
                ToolValidator.validate_tool(tool)
            except LLMToolValidationError as e:
                raise LLMToolValidationError(f"Tool at index {idx} is invalid: {e}")
            
            name = tool["name"]
            if name in seen_names:
                raise LLMToolValidationError(f"Duplicate tool name: {name}")
            seen_names.add(name)


# ============================================================================
# Main LLM Client
# ============================================================================


class LLMClient:
    """
    Production-grade async LLM client with comprehensive features:
    - Automatic retries with exponential backoff
    - Circuit breaker pattern for fault tolerance
    - Request/response caching
    - Structured logging and metrics
    - Tool schema validation
    - Proper resource management
    - Context manager support
    """
    
    def __init__(
        self,
        config: LLMClientConfig,
        metrics_collector: Optional[MetricsCollector] = None,
    ):
        """
        Initialize LLM client.
        
        Args:
            config: Client configuration
            metrics_collector: Optional metrics collector
        """
        self.config = config
        self.metrics = metrics_collector or SimpleMetricsCollector()
        
        self._client: Optional[AsyncOpenAI] = None
        self._circuit_breaker: Optional[CircuitBreaker] = None
        self._cache: Optional[TTLCache] = None
        self._is_closed = False
        
        # Initialize circuit breaker if enabled
        if config.circuit_breaker.enabled:
            self._circuit_breaker = CircuitBreaker(
                fail_max=config.circuit_breaker.fail_max,
                timeout_duration=config.circuit_breaker.timeout_duration,
            )
        
        # Initialize cache if enabled
        if config.cache.enabled:
            self._cache = TTLCache(
                maxsize=config.cache.max_size,
                ttl=config.cache.ttl_seconds,
            )
        
        logger.info(
            "llm_client_initialized",
            model=config.api_config.model_name,
            base_url=config.api_config.base_url,
            cache_enabled=config.cache.enabled,
            circuit_breaker_enabled=config.circuit_breaker.enabled,
        )
    
    def _get_client(self) -> AsyncOpenAI:
        """Get or create AsyncOpenAI client instance."""
        if self._is_closed:
            raise LLMClientError("Client is closed")
        
        if self._client is None:
            import httpx
            
            self._client = AsyncOpenAI(
                api_key=self.config.api_config.api_key,
                base_url=self.config.api_config.base_url,
                timeout=httpx.Timeout(
                    connect=self.config.timeout.connect,
                    read=self.config.timeout.read,
                    write=self.config.timeout.write,
                    pool=self.config.timeout.pool,
                ),
                max_retries=0,  # We handle retries ourselves
            )
            logger.debug("openai_client_created")
        
        return self._client
    
    async def close(self) -> None:
        """Close the client and cleanup resources."""
        if self._client and not self._is_closed:
            await self._client.close()
            self._client = None
            self._is_closed = True
            logger.info("llm_client_closed")
    
    async def __aenter__(self):
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        await self.close()
    
    def _build_cache_key(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]],
    ) -> str:
        """Generate cache key from request parameters."""
        cache_data = {
            "model": self.config.api_config.model_name,
            "messages": messages,
            "tools": tools,
        }
        content = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _build_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Build OpenAI function calling format from tool definitions.
        
        Args:
            tools: List of tool definitions
            
        Returns:
            List of formatted tools for OpenAI API
            
        Raises:
            LLMToolValidationError: If tools are invalid
        """
        ToolValidator.validate_tools(tools)
        
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get(
                        "parameters",
                        {
                            "type": "object",
                            "properties": {},
                        },
                    ),
                },
            }
            for tool in tools
        ]
    
    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        stream: bool = True,
        use_cache: bool = True,
        on_event: Optional[Callable[[StreamEvent], None]] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Execute chat completion with streaming or non-streaming response.
        
        Args:
            messages: Conversation messages
            tools: Optional tool definitions
            stream: Whether to stream the response
            use_cache: Whether to use cache (only for non-streaming)
            on_event: Optional callback for each event
            
        Yields:
            StreamEvent objects as they occur
            
        Raises:
            LLMClientError: On unrecoverable errors
            LLMCircuitBreakerOpenError: If circuit breaker is open
        """
        request_id = str(uuid.uuid4())
        start_time = asyncio.get_event_loop().time()
        
        logger.info(
            "chat_completion_start",
            request_id=request_id,
            model=self.config.api_config.model_name,
            message_count=len(messages),
            has_tools=tools is not None,
            stream=stream,
        )
        
        # Check circuit breaker
        if self._circuit_breaker and self._circuit_breaker.current_state == "open":
            error_msg = "Circuit breaker is open, requests are temporarily blocked"
            logger.error("circuit_breaker_open", request_id=request_id)
            self.metrics.record_error(
                self.config.api_config.model_name,
                "circuit_breaker_open"
            )
            yield StreamEvent(
                type=StreamEventType.ERROR,
                error=error_msg,
            )
            raise LLMCircuitBreakerOpenError(error_msg)
        
        # Check cache for non-streaming requests
        if not stream and use_cache and self._cache is not None:
            cache_key = self._build_cache_key(messages, tools)
            if cache_key in self._cache:
                logger.info("cache_hit", request_id=request_id, cache_key=cache_key)
                self.metrics.record_cache_hit(self.config.api_config.model_name)
                cached_event = self._cache[cache_key]
                if on_event:
                    on_event(cached_event)
                yield cached_event
                return
            else:
                self.metrics.record_cache_miss(self.config.api_config.model_name)
        
        # Build request kwargs
        kwargs = {
            "model": self.config.api_config.model_name,
            "messages": messages,
            "stream": stream,
        }
        
        if tools:
            kwargs["tools"] = self._build_tools(tools)
            kwargs["tool_choice"] = "auto"
        
        # Execute with retry logic
        try:
            if stream:
                async for event in self._execute_with_retry(
                    self._stream_response,
                    kwargs,
                    request_id,
                ):
                    if on_event:
                        on_event(event)
                    yield event
            else:
                async for event in self._execute_with_retry(
                    self._non_stream_response,
                    kwargs,
                    request_id,
                ):
                    # Cache successful non-streaming responses
                    if (
                        use_cache
                        and self._cache is not None
                        and event.type == StreamEventType.MESSAGE_COMPLETE
                    ):
                        cache_key = self._build_cache_key(messages, tools)
                        self._cache[cache_key] = event
                        logger.debug("response_cached", cache_key=cache_key)
                    
                    if on_event:
                        on_event(event)
                    yield event
            
            # Record metrics
            duration = asyncio.get_event_loop().time() - start_time
            logger.info(
                "chat_completion_success",
                request_id=request_id,
                duration=duration,
            )
            
        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            logger.error(
                "chat_completion_failed",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__,
                duration=duration,
            )
            self.metrics.record_error(
                self.config.api_config.model_name,
                type(e).__name__
            )
            raise
    
    async def _execute_with_retry(
        self,
        func: Callable,
        kwargs: dict[str, Any],
        request_id: str,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Execute function with retry logic and circuit breaker."""
        
        @retry(
            stop=stop_after_attempt(self.config.retry.max_attempts),
            wait=wait_exponential(
                multiplier=self.config.retry.multiplier,
                min=self.config.retry.min_wait,
                max=self.config.retry.max_wait,
            ),
            retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
            before_sleep=before_sleep_log(logger, logging_level="WARNING"),
        )
        async def _inner():
            client = self._get_client()
            
            if self._circuit_breaker:
                try:
                    async for event in func(client, kwargs):
                        yield event
                    # Reset circuit breaker on success
                    if self._circuit_breaker.current_state == "half-open":
                        self._circuit_breaker.call(lambda: None)
                except Exception as e:
                    # Record failure in circuit breaker
                    try:
                        self._circuit_breaker.call(lambda: self._raise(e))
                    except Exception:
                        pass
                    raise
            else:
                async for event in func(client, kwargs):
                    yield event
        
        try:
            async for event in _inner():
                yield event
        except (RateLimitError, APIConnectionError) as e:
            logger.error(
                "request_failed_after_retries",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            yield StreamEvent(
                type=StreamEventType.ERROR,
                error=f"{type(e).__name__}: {str(e)}",
            )
        except APIError as e:
            logger.error(
                "api_error",
                request_id=request_id,
                error=str(e),
            )
            yield StreamEvent(
                type=StreamEventType.ERROR,
                error=f"API error: {str(e)}",
            )
    
    @staticmethod
    def _raise(exception):
        """Helper to raise exception in circuit breaker."""
        raise exception
    
    async def _stream_response(
        self,
        client: AsyncOpenAI,
        kwargs: dict[str, Any],
    ) -> AsyncGenerator[StreamEvent, None]:
        """Handle streaming response from API."""
        response = await client.chat.completions.create(**kwargs)
        
        finish_reason: Optional[str] = None
        usage: Optional[TokenUsage] = None
        tool_calls: dict[int, dict[str, Any]] = {}
        
        async for chunk in response:
            # Extract usage information
            if hasattr(chunk, "usage") and chunk.usage:
                usage = TokenUsage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                    cached_tokens=getattr(
                        chunk.usage.prompt_tokens_details,
                        "cached_tokens",
                        0
                    ),
                )
            
            if not chunk.choices:
                continue
            
            choice = chunk.choices[0]
            delta = choice.delta
            
            if choice.finish_reason:
                finish_reason = choice.finish_reason
            
            # Handle text content
            if delta.content:
                yield StreamEvent(
                    type=StreamEventType.TEXT_DELTA,
                    text_delta=TextDelta(delta.content),
                )
            
            # Handle tool calls
            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    idx = tool_call_delta.index
                    
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": tool_call_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }
                    
                    if tool_call_delta.function:
                        if tool_call_delta.function.name:
                            tool_calls[idx]["name"] = tool_call_delta.function.name
                            yield StreamEvent(
                                type=StreamEventType.TOOL_CALL_START,
                                tool_call_delta=ToolCallDelta(
                                    call_id=tool_calls[idx]["id"],
                                    name=tool_call_delta.function.name,
                                ),
                            )
                        
                        if tool_call_delta.function.arguments:
                            tool_calls[idx]["arguments"] += tool_call_delta.function.arguments
                            
                            yield StreamEvent(
                                type=StreamEventType.TOOL_CALL_DELTA,
                                tool_call_delta=ToolCallDelta(
                                    call_id=tool_calls[idx]["id"],
                                    name=tool_calls[idx]["name"],
                                    arguments_delta=tool_call_delta.function.arguments,
                                ),
                            )
        
        # Emit complete tool calls
        for idx, tc in tool_calls.items():
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL_COMPLETE,
                tool_call=ToolCall(
                    call_id=tc["id"],
                    name=tc["name"],
                    arguments=parse_tool_call_arguments(tc["arguments"]),
                ),
            )
        
        # Record metrics if usage available
        if usage and self.config.enable_metrics:
            self.metrics.record_request(
                model=self.config.api_config.model_name,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                duration_seconds=0.0,  # Duration tracked at higher level
            )
        
        # Emit completion event
        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            finish_reason=finish_reason,
            usage=usage,
        )
    
    async def _non_stream_response(
        self,
        client: AsyncOpenAI,
        kwargs: dict[str, Any],
    ) -> AsyncGenerator[StreamEvent, None]:
        """Handle non-streaming response from API."""
        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message
        
        text_delta = None
        if message.content:
            text_delta = TextDelta(content=message.content)
        
        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        call_id=tc.id,
                        name=tc.function.name,
                        arguments=parse_tool_call_arguments(tc.function.arguments),
                    )
                )
        
        usage = None
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cached_tokens=getattr(
                    response.usage.prompt_tokens_details,
                    "cached_tokens",
                    0
                ),
            )
            
            if self.config.enable_metrics:
                self.metrics.record_request(
                    model=self.config.api_config.model_name,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    duration_seconds=0.0,
                )
        
        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            text_delta=text_delta,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=choice.finish_reason,
            usage=usage,
        )


# ============================================================================
# Convenience Factory Functions
# ============================================================================


def create_llm_client(
    api_key: str,
    base_url: str,
    model_name: str,
    **kwargs,
) -> LLMClient:
    """
    Convenience factory to create LLM client with defaults.
    
    Args:
        api_key: API key
        base_url: Base URL for API
        model_name: Model identifier
        **kwargs: Additional configuration overrides
        
    Returns:
        Configured LLMClient instance
    """
    from config.config import Config
    
    api_config = Config(
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
    )
    
    client_config = LLMClientConfig(
        api_config=api_config,
        **kwargs
    )
    
    return LLMClient(config=client_config)


@asynccontextmanager
async def llm_client_session(
    api_key: str,
    base_url: str,
    model_name: str,
    **kwargs,
) -> AsyncGenerator[LLMClient, None]:
    """
    Context manager for LLM client with automatic cleanup.
    
    Usage:
        async with llm_client_session(api_key, base_url, model) as client:
            async for event in client.chat_completion(messages):
                print(event)
    """
    client = create_llm_client(api_key, base_url, model_name, **kwargs)
    try:
        yield client
    finally:
        await client.close()
import functools
import hashlib
import json
import redis
from typing import Any, Callable, Optional
import io


class RedisCache:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        ttl: int = 3600,
        serializer: Callable = json.dumps,
    ):
        # Create two Redis clients - one for text and one for binary data
        self.redis_client_text = redis.Redis(
            host=host, port=port, decode_responses=True
        )
        self.redis_client_binary = redis.Redis(
            host=host, port=port, decode_responses=False
        )
        self.ttl = ttl
        self.serializer = serializer

    def _generate_cache_key(self, func: Callable, *args: Any, **kwargs: Any) -> str:
        """Generate a unique cache key based on function name and arguments."""
        # Sort kwargs to ensure consistent key generation
        sorted_kwargs = dict(sorted(kwargs.items()))

        # Create a dictionary with function name and all arguments
        key_data = {"func": func.__name__, "args": args, "kwargs": sorted_kwargs}

        # Generate MD5 hash of the JSON-encoded data
        return f"{func.__name__}:{hashlib.md5(self.serializer(key_data).encode()).hexdigest()}"

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                # Generate cache key
                cache_key = self._generate_cache_key(func, *args, **kwargs)

                # Try to get from cache - first try binary client
                cached_result = self.redis_client_binary.get(cache_key)

                if cached_result:
                    # If we got binary data, return it as BytesIO
                    return io.BytesIO(cached_result)

                # If not found in binary cache, try text cache
                cached_result = self.redis_client_text.get(cache_key)
                if cached_result:
                    try:
                        return self.serializer(cached_result)
                    except json.JSONDecodeError:
                        return cached_result

                # Execute function if not in cache
                result = await func(*args, **kwargs)

                # Cache the result
                if isinstance(result, io.BytesIO):
                    # For binary data (like images)
                    self.redis_client_binary.setex(
                        cache_key, self.ttl, result.getvalue()
                    )
                else:
                    # For JSON-serializable data
                    self.redis_client_text.setex(
                        cache_key, self.ttl, self.serializer(result)
                    )

                return result

            except redis.RedisError as e:
                # If Redis fails, just execute the function
                print(f"Redis error: {e}")
                return await func(*args, **kwargs)

        return wrapper


def redis_cache(
    host: str = "localhost",
    port: int = 6379,
    ttl: int = 3600,
    serializer: Callable = json.dumps,
) -> Callable:
    """
    Decorator for caching function results in Redis.

    Args:
        host: Redis host
        port: Redis port
        ttl: Time to live in seconds (default: 1 hour)

    Example:
        @redis_cache(host="redis", ttl=1800)
        async def my_function(arg1, arg2):
            return result
    """
    cache = RedisCache(host=host, port=port, ttl=ttl, serializer=serializer)
    return cache

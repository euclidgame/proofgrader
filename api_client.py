import asyncio
import logging
import time
import os
from typing import List, Dict, Any, Optional, Union, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
from openai import OpenAI, AsyncOpenAI
from google import genai
import litellm

# Configure logging
logger = logging.getLogger(__name__)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('openai._base_client').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Initialize API clients
async_client = AsyncOpenAI()
gemini_client = genai.Client(vertexai=True)

# Rate limiting configuration
RATE_LIMITS = {
    "gemini": 300,   # requests per minute
    "openai": 500,
    "default": 120,
}

# Request timeout in seconds
DEFAULT_TIMEOUT = 1200  # 40 minutes


class RateLimiter:
    """Rate limiter for API calls with non-blocking async implementation."""
    
    def __init__(self, requests_per_minute: int = 120):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum number of requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self.lock = asyncio.Lock()
        self.min_interval = 60.0 / requests_per_minute
    
    async def acquire(self):
        """Acquire permission to make a request."""
        while True:
            async with self.lock:
                now = time.time()
                
                # Remove requests older than 1 minute
                self.requests = [t for t in self.requests if now - t < 60]
                
                # Check if we can proceed
                if len(self.requests) < self.requests_per_minute:
                    if not self.requests or (now - max(self.requests)) >= self.min_interval:
                        self.requests.append(now)
                        return
                    sleep_time = self.min_interval - (now - max(self.requests))
                else:
                    sleep_time = min(self.requests) + 60 - now
                    if sleep_time <= 0:
                        self.requests.append(now)
                        return
            
            logger.debug(f"Rate limit hit, sleeping for {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)


# Rate limiters for different services
_rate_limiters = {
    "gemini": RateLimiter(RATE_LIMITS["gemini"]),
    "openai": RateLimiter(RATE_LIMITS["openai"]),
    "default": RateLimiter(RATE_LIMITS["default"])
}


def _get_rate_limiter(model_name: str) -> RateLimiter:
    """Get appropriate rate limiter for the model."""
    if model_name.startswith("gemini"):
        return _rate_limiters["gemini"]
    elif model_name.startswith(("gpt", "o1", "o3")):
        return _rate_limiters["openai"]
    return _rate_limiters["default"]


def _extract_usage(response, is_gemini: bool = False) -> Dict[str, Optional[int]]:
    """
    Extract token usage from API response (unified for all models).
    
    Args:
        response: API response object
        is_gemini: Whether this is a Gemini response
        
    Returns:
        Dictionary with token counts (may contain None values)
    """
    def _get(obj, attr, default=None):
        """Safely get attribute from object or dict."""
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)
    
    if is_gemini:
        metadata = _get(response, 'usage_metadata')
        if not metadata:
            return {'prompt_tokens': None, 'completion_tokens': None, 
                    'total_tokens': None, 'reasoning_tokens': None}
        return {
            'prompt_tokens': _get(metadata, 'prompt_token_count'),
            'completion_tokens': _get(metadata, 'candidates_token_count'),
            'total_tokens': _get(metadata, 'total_token_count'),
            'reasoning_tokens': _get(metadata, 'thoughts_token_count'),
        }
    
    # OpenAI / LiteLLM format
    usage = _get(response, 'usage')
    if not usage:
        return {'prompt_tokens': None, 'completion_tokens': None,
                'total_tokens': None, 'reasoning_tokens': None}
    
    # Handle output_tokens_details for reasoning tokens
    details = _get(usage, 'output_tokens_details')
    reasoning = _get(details, 'reasoning_tokens') if details else None
    
    return {
        'prompt_tokens': _get(usage, 'prompt_tokens') or _get(usage, 'input_tokens'),
        'completion_tokens': _get(usage, 'completion_tokens') or _get(usage, 'output_tokens'),
        'total_tokens': _get(usage, 'total_tokens'),
        'reasoning_tokens': reasoning or _get(usage, 'reasoning_tokens'),
    }


async def _retry_with_backoff(func: Callable, max_retries: int = 3, initial_delay: float = 1.0):
    """Retry async function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = initial_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)


async def _get_model_response_async(prompt: str, model_name: str, max_tokens: int = 65536) -> tuple:
    """
    Asynchronous API call with rate limiting and retries.
    
    Args:
        prompt: Input prompt text
        model_name: Name of the model to use
        max_tokens: Maximum tokens to generate
        
    Returns:
        Tuple of (response_text, token_usage_dict)
    """
    rate_limiter = _get_rate_limiter(model_name)
    await rate_limiter.acquire()
    
    async def _make_request():
        messages = [{"role": "user", "content": prompt}]
        
        # Use native clients for specific models
        if model_name.startswith("gemini"):
            # Gemini doesn't have async client, use executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: gemini_client.models.generate_content(model=model_name, contents=prompt)
            )
            usage = _extract_usage(response, is_gemini=True)
            return response.text, usage
        
        elif model_name in ["o1-pro", "o3", "gpt-5"] or model_name.startswith("gpt"):
            response = await async_client.responses.create(
                model=model_name,
                input=messages,
                reasoning={"effort": "high"} if model_name in ["o3", "gpt-5"] else None,
                timeout=DEFAULT_TIMEOUT
            )
            usage = _extract_usage(response)
            text = response.output_text if hasattr(response, 'output_text') else response.choices[0].message.content
            return text, usage
        
        # Use LiteLLM for other models
        else:
            kwargs = {"model": model_name, "messages": messages, "max_tokens": max_tokens, "timeout": DEFAULT_TIMEOUT}
            
            response = await litellm.acompletion(**kwargs)
            usage = _extract_usage(response)
            return response.choices[0].message.content, usage
    
    try:
        return await asyncio.wait_for(_retry_with_backoff(_make_request), timeout=DEFAULT_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error(f"Request timed out after {DEFAULT_TIMEOUT}s for {model_name}")
        raise Exception(f"Request timed out after {DEFAULT_TIMEOUT}s")


async def _get_model_responses_batch_async(
    prompts: List[str], 
    model_name: str, 
    max_concurrent: int = 10,
    progress_callback: Optional[Callable] = None,
    return_usage: bool = False
) -> Union[List[str], tuple]:
    """
    Process multiple prompts asynchronously with concurrency control.
    
    Args:
        prompts: List of input prompts
        model_name: Name of the model to use
        max_concurrent: Maximum number of concurrent requests
        progress_callback: Optional callback function(completed, total)
        return_usage: Whether to return token usage information
        
    Returns:
        List of responses, or tuple of (responses, usages) if return_usage=True
    """
    logger.info(f"Batch processing {len(prompts)} prompts with {model_name} (max_concurrent={max_concurrent})")
    
    semaphore = asyncio.Semaphore(max_concurrent)
    completed_count = 0
    lock = asyncio.Lock()
    start_time = time.time()
    
    async def process_prompt(prompt: str, index: int) -> tuple:
        nonlocal completed_count
        async with semaphore:
            try:
                response, token_usage = await _get_model_response_async(prompt, model_name)
                async with lock:
                    completed_count += 1
                    if progress_callback and (completed_count % max(1, len(prompts) // 50) == 0 or completed_count == len(prompts)):
                        progress_callback(completed_count, len(prompts))
                return index, response, None, token_usage
            except Exception as e:
                logger.error(f"Error processing prompt {index}: {e}")
                async with lock:
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, len(prompts))
                return index, None, str(e), None
    
    tasks = [process_prompt(prompt, i) for i, prompt in enumerate(prompts)]
    results_raw = await asyncio.gather(*tasks, return_exceptions=True)
    
    total_time = time.time() - start_time
    logger.info(f"Batch completed in {total_time:.2f}s ({total_time/len(prompts):.2f}s per request)")
    
    # Sort and extract results
    results = [None] * len(prompts)
    usages = [None] * len(prompts) if return_usage else None
    
    for result in results_raw:
        if isinstance(result, Exception):
            logger.error(f"Task exception: {result}")
            continue
        index, response, error, usage = result
        results[index] = f"ERROR: {error}" if error else response
        if return_usage:
            usages[index] = usage
    
    return (results, usages) if return_usage else results


class APIClient:
    """
    Unified API client for calling remote language models.
    
    Supports OpenAI, Gemini, Claude, and other models via LiteLLM.
    Includes rate limiting, retries, batch processing, and usage tracking.
    
    Example:
        client = APIClient(default_model="gemini-2.5-pro")
        response = client.get_response("What is 2+2?")
        
        # Batch async
        responses = await client.get_responses_batch(prompts, max_concurrent=10)
    """
    
    def __init__(self, default_model: str = "gemini-2.5-pro"):
        """
        Initialize API client.
        
        Args:
            default_model: Default model to use if not specified in requests
        """
        self.default_model = default_model
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0
        }
    
    async def get_responses_batch(
        self, 
        prompts: List[str], 
        model_name: Optional[str] = None,
        max_concurrent: int = 10,
        progress_callback: Optional[Callable] = None,
        return_usage: bool = False
    ) -> Union[List[str], tuple]:
        """Get multiple responses asynchronously."""
        model_name = model_name or self.default_model
        return await _get_model_responses_batch_async(
            prompts, model_name, max_concurrent, progress_callback, return_usage
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return self.stats.copy()

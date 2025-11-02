"""vLLM client for interacting with the inference server."""

import requests
import json
import logging
from typing import List, Dict, Any, Optional
import time
import asyncio
import aiohttp
from tqdm import tqdm

logger = logging.getLogger(__name__)

class VLLMClient:
    """Client for interacting with vLLM server."""
    
    def __init__(self, base_url: str = "http://localhost:8000", model: str = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.session = requests.Session()
        
    def is_server_ready(self, timeout: int = 30) -> bool:
        """Check if the vLLM server is ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(1)
        return False
    
    def generate(self, 
                 prompt: str, 
                 max_tokens: int = 512,
                 temperature: float = 0.7,
                 top_p: float = 0.9,
                 stream: bool = False) -> Dict[str, Any]:
        """Generate text from a single prompt using chat completions API."""
        # Convert prompt to chat format
        messages = [{"role": "user", "content": prompt}]
        
        data = {
            "model": self.model,  # Required by vLLM
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=data,
                timeout=120
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error generating text: {e}")
            # Log the response content for debugging
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            return {"error": str(e)}
    
    def generate_batch(self, 
                      prompts: List[str], 
                      max_tokens: int = 512,
                      temperature: float = 0.7,
                      top_p: float = 0.9,
                      max_concurrent: int = 10) -> List[Dict[str, Any]]:
        """Generate text from multiple prompts efficiently using async requests."""
        try:
            # Use async method for best performance
            return asyncio.run(self._generate_batch_async(
                prompts, max_tokens, temperature, top_p, max_concurrent
            ))
        except Exception as e:
            logger.error(f"Async batch generation failed: {e}")
            # Fallback to sequential processing
            logger.info("Falling back to sequential processing...")
            return self._generate_batch_sequential(prompts, max_tokens, temperature, top_p)
    
    async def _generate_batch_async(self, 
                                   prompts: List[str], 
                                   max_tokens: int = 512,
                                   temperature: float = 0.7,
                                   top_p: float = 0.9,
                                   max_concurrent: int = 10) -> List[Dict[str, Any]]:
        """Internal async batch generation method."""
        
        model = self.model  # Capture model for nested function
        
        async def generate_single(session, prompt, semaphore, pbar):
            async with semaphore:
                # Convert prompt to chat format
                messages = [{"role": "user", "content": prompt}]
                
                data = {
                    "model": model,  # Required by vLLM
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "stream": False
                }
                
                try:
                    async with session.post(
                        f"{self.base_url}/v1/chat/completions",
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=10000000)
                    ) as response:
                        response.raise_for_status()
                        result = await response.json()
                        pbar.update(1)
                        return result
                except Exception as e:
                    logger.error(f"Error generating text: {e}")
                    # Log more details for debugging
                    logger.error(f"Error type: {type(e)}")
                    pbar.update(1)
                    return {"error": str(e)}
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Create progress bar
        pbar = tqdm(total=len(prompts), desc="Generating responses (async)")
        
        async with aiohttp.ClientSession() as session:
            tasks = [
                generate_single(session, prompt, semaphore, pbar) 
                for prompt in prompts
            ]
            results = await asyncio.gather(*tasks)
        
        pbar.close()
        return results
    
    def _generate_batch_sequential(self, 
                                  prompts: List[str], 
                                  max_tokens: int = 512,
                                  temperature: float = 0.7,
                                  top_p: float = 0.9) -> List[Dict[str, Any]]:
        """Fallback sequential batch generation."""
        results = []
        for prompt in tqdm(prompts, desc="Generating responses (sequential)"):
            result = self.generate(prompt, max_tokens, temperature, top_p)
            results.append(result)
        return results
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       max_tokens: int = 512,
                       temperature: float = 0.7,
                       top_p: float = 0.9) -> Dict[str, Any]:
        """Chat completion API with conversation history (OpenAI-compatible)."""
        data = {
            "model": self.model,  # Required by vLLM
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=data,
                timeout=120
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error in chat completion: {e}")
            # Log the response content for debugging
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            return {"error": str(e)}
    
    def generate_with_conversation(self, 
                                 conversation: List[Dict[str, str]], 
                                 max_tokens: int = 512,
                                 temperature: float = 0.7,
                                 top_p: float = 0.9) -> Dict[str, Any]:
        """Generate text from a conversation history."""
        return self.chat_completion(conversation, max_tokens, temperature, top_p)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        try:
            response = self.session.get(f"{self.base_url}/v1/models", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error getting model info: {e}")
            return {"error": str(e)} 
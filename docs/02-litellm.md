# LiteLLM Guide

LiteLLM provides a unified interface to interact with various Large Language Models (LLMs) using a consistent API similar to OpenAI's interface.

## Installation

```bash
pip install litellm
```

## Basic Usage

### 1. Simple Completion

```python
from litellm import completion

# Basic completion
response = completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What is the capital of France?"}]
)
print(response.choices[0].message.content)
```

### 2. Using Environment Variables

Create a `.env` file:
```env
OPENAI_API_KEY=your_api_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

Load and use environment variables:
```python
from dotenv import load_dotenv
import os
from litellm import completion

load_dotenv()

response = completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello, how are you?"}],
    api_key=os.getenv("OPENAI_API_KEY")
)
```

### 3. Model Fallbacks

```python
from litellm import completion

# Set up model fallbacks
fallback_models = ["gpt-4o-mini", "claude-2", "palm-2"]

for model in fallback_models:
    try:
        response = completion(
            model=model,
            messages=[{"role": "user", "content": "Write a short poem about Python"}]
        )
        print(f"Success with model: {model}")
        print(response.choices[0].message.content)
        break
    except Exception as e:
        print(f"Error with {model}: {str(e)}")
        continue
```

### 4. Async Operations

```python
import asyncio
from litellm import acompletion

async def get_completion(message):
    response = await acompletion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": message}]
    )
    return response.choices[0].message.content

async def main():
    messages = [
        "What is Python?",
        "What is JavaScript?",
        "What is Rust?"
    ]
    
    tasks = [get_completion(msg) for msg in messages]
    responses = await asyncio.gather(*tasks)
    
    for msg, response in zip(messages, responses):
        print(f"Q: {msg}")
        print(f"A: {response}\n")

# Run async code
asyncio.run(main())
```

### 5. Streaming Responses

```python
from litellm import completion

response = completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Write a story about a robot"}],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")
```

## Advanced Features

### 1. Token Counting

```python
from litellm import completion

response = completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello, how are you?"}],
    get_token_count=True
)

print(f"Input tokens: {response.usage.prompt_tokens}")
print(f"Output tokens: {response.usage.completion_tokens}")
print(f"Total tokens: {response.usage.total_tokens}")
```

### 2. Cost Tracking

```python
from litellm import completion, get_cost_per_token

# Get cost for a specific model
cost_per_token = get_cost_per_token("gpt-4o-mini")
print(f"Cost per token: ${cost_per_token}")

# Track cost of completion
response = completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Write a haiku"}],
    get_token_count=True
)

total_cost = (
    response.usage.total_tokens * cost_per_token
)
print(f"Total cost: ${total_cost:.4f}")
```

## Best Practices

1. **API Key Management**
   - Always use environment variables for API keys
   - Never hardcode API keys in your code
   - Use a `.env` file for local development

2. **Error Handling**
   - Implement proper try-except blocks
   - Use model fallbacks for reliability
   - Log errors for debugging

3. **Performance Optimization**
   - Use async operations for multiple requests
   - Implement caching when appropriate
   - Monitor token usage and costs

4. **Security**
   - Keep API keys secure
   - Validate user inputs
   - Implement rate limiting
   - Monitor usage patterns

## Common Issues and Solutions

1. **Rate Limiting**
```python
from litellm import completion
import time

def rate_limited_completion(message, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            return completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": message}]
            )
        except Exception as e:
            if "rate_limit" in str(e).lower():
                if attempt < max_retries - 1:
                    time.sleep(delay * (attempt + 1))
                    continue
            raise
```

2. **Handling Timeouts**
```python
from litellm import completion

try:
    response = completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Long prompt here..."}],
        timeout=30  # 30 seconds timeout
    )
except Exception as e:
    print(f"Request timed out: {str(e)}")
```

## Model Support and Compatibility

### Supported Models

LiteLLM supports a wide range of models across different providers:

| Provider | Models | Aliases |
|----------|---------|---------|
| OpenAI | gpt-4, gpt-3.5-turbo | openai/gpt-4, openai/gpt-3.5-turbo |
| Anthropic | claude-2, claude-instant-1 | anthropic/claude-2 |
| Google | palm-2 | google/palm-2 |
| Azure OpenAI | Same as OpenAI | azure/gpt-4, azure/gpt-3.5-turbo |

### Model-Specific Parameters

```python
from litellm import completion

# OpenAI-specific parameters
response = completion(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.7,
    top_p=1.0,
    presence_penalty=0,
    frequency_penalty=0
)

# Anthropic-specific parameters
response = completion(
    model="claude-2",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens_to_sample=100,
    temperature=0.7
)
```

## Configuration Options

### Basic Configuration

```python
from litellm import completion, set_verbose, set_timeout

# Enable debug logging
set_verbose(True)

# Set global timeout
set_timeout(30)

# Custom retry configuration
response = completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}],
    num_retries=3,
    retry_delay=1
)
```

### Enterprise Setup

```python
from litellm import completion

# Proxy configuration
response = completion(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    proxy="http://proxy.example.com:8080",
    custom_headers={
        "Authorization": "Bearer your-token",
        "X-Custom-Header": "value"
    }
)
```

## Testing and Quality Assurance

### Unit Testing

```python
import unittest
from unittest.mock import patch
from litellm import completion

class TestLiteLLM(unittest.TestCase):
    def test_completion(self):
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}]
        )
        self.assertIsNotNone(response)
        self.assertTrue(hasattr(response, 'choices'))

    @patch('litellm.completion')
    def test_completion_mock(self, mock_completion):
        # Mock response
        mock_completion.return_value.choices = [{
            "message": {"content": "Hello there!"},
            "finish_reason": "stop"
        }]
        
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}]
        )
        self.assertEqual(
            response.choices[0].message.content,
            "Hello there!"
        )
```

## Monitoring and Observability

### Logging Setup

```python
import logging
from litellm import completion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('litellm')

def log_completion(response, error=None):
    if error:
        logger.error(f"Completion error: {error}")
    else:
        logger.info(
            f"Completion success: {len(response.choices[0].message.content)} chars"
        )

# Usage with logging
try:
    response = completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}]
    )
    log_completion(response)
except Exception as e:
    log_completion(None, error=e)
```

### Cost and Usage Tracking

```python
from litellm import completion
from datetime import datetime

class UsageTracker:
    def __init__(self):
        self.total_tokens = 0
        self.total_cost = 0
        self.requests = 0

    def track(self, response):
        self.total_tokens += response.usage.total_tokens
        self.total_cost += (
            response.usage.total_tokens * 
            get_cost_per_token(response.model)
        )
        self.requests += 1

# Usage
tracker = UsageTracker()
response = completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}],
    get_token_count=True
)
tracker.track(response)
```

## Performance Optimization

### Caching

```python
import hashlib
import json
from functools import lru_cache
from litellm import completion

@lru_cache(maxsize=1000)
def cached_completion(message_hash):
    return completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": message_hash}]
    )

def get_completion(message):
    # Create a hash of the message for caching
    message_hash = hashlib.md5(
        json.dumps(message, sort_keys=True).encode()
    ).hexdigest()
    return cached_completion(message_hash)
```

### Batch Processing

```python
import asyncio
from litellm import acompletion

async def process_batch(messages, batch_size=5):
    """Process messages in batches to avoid rate limits"""
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i + batch_size]
        tasks = [
            acompletion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": msg}]
            )
            for msg in batch
        ]
        yield await asyncio.gather(*tasks)
        # Add delay between batches to respect rate limits
        await asyncio.sleep(1)

# Usage
async def main():
    messages = ["Hello", "Hi", "Hey", "Greetings", "Good day"]
    async for batch_responses in process_batch(messages):
        for response in batch_responses:
            print(response.choices[0].message.content)

asyncio.run(main())
```

## Resources

- [LiteLLM GitHub Repository](https://github.com/BerriAI/litellm)
- [Official Documentation](https://docs.litellm.ai/)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)

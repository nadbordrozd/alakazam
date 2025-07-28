"""
LLM Client for embedding and completion operations using OpenAI API.
"""

from typing import List, Dict, Optional, Any
import os
import yaml
import time
import uuid
from datetime import datetime
from pathlib import Path
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI clients (both sync and async)
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

async_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Configure YAML to use literal block scalars for multiline strings (once at module import)
class SuperAggressiveDumper(yaml.SafeDumper):
    """Custom YAML dumper that forces literal block scalars for multiline content, even with problematic characters."""
    
    def represent_str(self, data):
        if '\n' in data or len(data) > 80:
            # Force literal style regardless of content (JSON, quotes, asterisks, etc.)
            tag = 'tag:yaml.org,2002:str'
            return self.represent_scalar(tag, data, style='|')
        return self.represent_scalar('tag:yaml.org,2002:str', data)
    
    def choose_scalar_style(self):
        # Override the style choice mechanism to force literal blocks
        if self.event.tag == 'tag:yaml.org,2002:str':
            if self.event.value and ('\n' in self.event.value or len(self.event.value) > 80):
                return '|'
        return super().choose_scalar_style()

# Register the custom string representer
SuperAggressiveDumper.add_representer(str, SuperAggressiveDumper.represent_str)

# Generate a unique session ID when the module is imported
SESSION_ID = str(uuid.uuid4())[:8]  # Use first 8 chars for readability
SESSION_START = datetime.now()
LOG_FILE = LOG_DIR / f"llm_session_{SESSION_START.strftime('%Y%m%d_%H%M%S')}_{SESSION_ID}.yaml"

# Initialize call counter for unique call IDs
_call_counter = 0

# Initialize session log file with header structure
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    session_header = {
        'session_info': {
            'session_id': SESSION_ID,
            'started_at': SESSION_START.isoformat(),
            'log_file': LOG_FILE.name
        },
        'calls': {}
    }
    
    yaml.dump(session_header, f, Dumper=SuperAggressiveDumper, default_flow_style=False, allow_unicode=True, width=120, indent=2)


def log_llm_call(call_type: str, input_data: dict, response_data: dict, duration: float, error: str = None):
    """
    Log LLM call as a nested YAML object under a unique call key.
    Each call becomes a collapsible section in the YAML hierarchy.
    """
    global _call_counter
    _call_counter += 1
    
    timestamp = datetime.now().isoformat()
    
    # Create unique call ID
    call_id = f"call_{_call_counter:03d}_{timestamp.replace(':', '').replace('-', '').replace('.', '')[:15]}"
    
    log_entry = {
        'timestamp': timestamp,
        'session_id': SESSION_ID,
        'call_type': call_type,
        'duration_seconds': round(duration, 3),
        'input': input_data,
        'response': response_data
    }
    
    if error:
        log_entry['error'] = error
    
    # Read existing log file
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        log_data = yaml.safe_load(f) or {'session_info': {}, 'calls': {}}
    
    # Add new call to the calls section
    log_data['calls'][call_id] = log_entry
    
    # Write updated log file
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(log_data, f, Dumper=SuperAggressiveDumper, default_flow_style=False, allow_unicode=True, width=120, indent=2)


def get_embedding(
    input: str | List[str], 
    model: str = "text-embedding-3-small"
) -> List[float]:
    """
    Get embedding for the given text using OpenAI embedding API.
    
    Args:
        input: Text string or list of text strings to embed
        model: Embedding model to use
        
    Returns:
        Embedding vector for single input, or list of embedding vectors for multiple inputs
    """
    start_time = time.time()
    error = None
    response_data = None
    
    try:
        response = client.embeddings.create(
            input=input,
            model=model
        )
        
        # Prepare response data for logging (truncate embeddings for readability)
        if isinstance(input, str):
            embedding = response.data[0].embedding
            response_data = {
                'embedding_length': len(embedding),
                'embedding_preview': embedding[:5],  # First 5 values for preview
                'usage': response.usage.model_dump() if hasattr(response, 'usage') else None
            }
            result = embedding
        else:
            embeddings = [item.embedding for item in response.data]
            response_data = {
                'embeddings_count': len(embeddings),
                'embedding_length': len(embeddings[0]) if embeddings else 0,
                'first_embedding_preview': embeddings[0][:5] if embeddings else [],
                'usage': response.usage.model_dump() if hasattr(response, 'usage') else None
            }
            result = embeddings
            
    except Exception as e:
        error = str(e)
        result = None
        response_data = {'error': error}
    
    finally:
        duration = time.time() - start_time
        
        # Log the call
        input_data = {
            'input_type': 'string' if isinstance(input, str) else f'list[{len(input)}]',
            'input': input,
            'model': model
        }
        
        log_llm_call('embedding', input_data, response_data, duration, error)
    
    if error:
        raise Exception(error)
    
    return result


async def get_completion_async(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o",
    temperature: float = 0.7,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[str] = None
) -> str:
    """
    Get completion from OpenAI chat completions API (asynchronous).
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        model: Model to use for completion
        temperature: Sampling temperature (0-2)
        tools: Optional list of tool definitions for function calling
        tool_choice: Optional tool choice strategy ("auto", "none", or specific tool)
        
    Returns:
        Generated completion text (tool calls are not executed, just returned as text)
    """
    start_time = time.time()
    error = None
    response_data = None
    
    try:
        # Build API parameters
        api_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        # Add tools if provided
        if tools:
            api_params["tools"] = tools
            if tool_choice:
                api_params["tool_choice"] = tool_choice
        
        response = await async_client.chat.completions.create(**api_params)
        
        message = response.choices[0].message
        result = message.content
        
        response_data = {
            'content': result,
            'finish_reason': response.choices[0].finish_reason,
            'usage': response.usage.model_dump() if response.usage else None,
            'model': response.model,
            'tool_calls': [call.model_dump() for call in message.tool_calls] if message.tool_calls else None
        }
        
    except Exception as e:
        error = str(e)
        result = None
        response_data = {'error': error}
    
    finally:
        duration = time.time() - start_time
        
        # Log the call
        input_data = {
            'messages': messages,
            'model': model,
            'temperature': temperature,
            'message_count': len(messages),
            'total_input_chars': sum(len(str(msg.get('content', ''))) for msg in messages),
            'tools_provided': len(tools) if tools else 0,
            'tool_choice': tool_choice
        }
        
        log_llm_call('completion_async', input_data, response_data, duration, error)
    
    if error:
        raise Exception(error)
    
    return result

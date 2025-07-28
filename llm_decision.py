#!/usr/bin/env python3

import json
from typing import List, Dict, Optional, Any, Union
from llm_client import get_completion_async


def _convert_messages_to_openai_format(messages: List[Any]) -> List[Dict[str, str]]:
    """
    Convert Message objects to OpenAI chat format.
    
    Args:
        messages: List of Message objects
        
    Returns:
        List of dictionaries with 'role' and 'content' keys for OpenAI API
    """
    openai_messages = []
    for message in messages:
        openai_messages.append({
            "role": "assistant" if message.role == "bot" else message.role,
            "content": message.text
        })
    return openai_messages

async def is_relevant(
    messages: List[Any],  # List of Message objects
    snippet: str,
    model: str = "gpt-4o"
) -> Dict[str, Union[bool, float, str]]:
    """
    Use LLM to judge if a knowledge base snippet is relevant to the conversation.
    
    Args:
        messages: List of conversation messages (Message objects)
        snippet: Knowledge base snippet to evaluate
        model: LLM model to use for relevance judgment
        
    Returns:
        Dict with keys:
        - "is_relevant": Boolean indicating if snippet is relevant
        - "confidence": Float score 0-1 indicating confidence in judgment
        - "reasoning": String explaining the relevance judgment
    """
    
    # Convert messages to OpenAI format
    conversation_messages = _convert_messages_to_openai_format(messages)
    
    # Create the system prompt for relevance judgment
    system_prompt = """You are an expert at evaluating the relevance of knowledge snippets to conversations. Your task is to determine whether a given knowledge base snippet could be useful for answering the user's questions or continuing the conversation meaningfully.

Consider the following factors when evaluating relevance:
1. Does the snippet contain information that directly answers any user question?
2. Does the snippet provide context that would help understand the conversation topic?
3. Could the snippet help provide better, more informed responses?
4. Is the snippet related to the main themes or topics being discussed?

A snippet is RELEVANT if it:
- Directly answers a user's question
- Provides useful background information on the conversation topic
- Contains facts, procedures, or details that enhance the response quality
- Relates to the user's interests or needs expressed in the conversation

A snippet is NOT RELEVANT if it:
- Discusses completely unrelated topics
- Contains information that doesn't add value to the conversation
- Is about subjects that haven't been mentioned and aren't contextually related

You must respond with a valid JSON object containing exactly these fields:
{
    "is_relevant": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why the snippet is or isn't relevant"
}

Be precise in your judgment and provide clear reasoning."""

    # Create the evaluation prompt for the snippet
    evaluation_prompt = f"""Based on the conversation above, please evaluate whether this knowledge snippet is relevant:

KNOWLEDGE SNIPPET TO EVALUATE:
{snippet}

Please evaluate whether this knowledge snippet is relevant to the conversation and could be useful for answering the user's questions or providing better responses."""

    # Build the full message list for OpenAI
    # Start with system prompt, then conversation history, then evaluation request
    api_messages = [{"role": "system", "content": system_prompt}]
    api_messages.extend(conversation_messages)
    api_messages.append({"role": "user", "content": evaluation_prompt})

    try:
        # Call OpenAI API via async client
        llm_response = await get_completion_async(
            messages=api_messages,
            model=model,
            temperature=0.1  # Low temperature for consistent relevance judgments
        )
        
        # Extract and clean the response content
        llm_response = llm_response.strip()
        
        # Handle markdown-wrapped JSON (```json ... ```)
        if llm_response.startswith("```json") and llm_response.endswith("```"):
            llm_response = llm_response[7:-3].strip()  # Remove ```json and ```
        elif llm_response.startswith("```") and llm_response.endswith("```"):
            llm_response = llm_response[3:-3].strip()  # Remove ``` and ```
        
        # Parse as JSON
        result = json.loads(llm_response)
        
        # Validate the response structure
        if not isinstance(result, dict):
            raise ValueError("Response is not a dictionary")
        
        # Ensure all required keys exist with proper defaults
        return {
            "is_relevant": bool(result.get("is_relevant", False)),
            "confidence": float(result.get("confidence", 0.0)),
            "reasoning": str(result.get("reasoning", "No reasoning provided"))
        }
        
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        # If JSON parsing fails, try to extract boolean from text
        lower_response = llm_response.lower()
        is_relevant = any(word in lower_response for word in ["true", "relevant", "yes", "useful"])
        
        return {
            "is_relevant": is_relevant,
            "confidence": 0.5,  # Medium confidence for fallback
            "reasoning": f"Failed to parse structured response: {llm_response[:100]}..."
        }
    except Exception as e:
        # Handle any API errors gracefully
        return {
            "is_relevant": False,
            "confidence": 0.0,
            "reasoning": f"Error during relevance evaluation: {str(e)}"
        }

async def respond(
    messages: List[Any],  # List of Message objects
    available_workflows: List[str],
    active_node: Optional[Any],  # WorkflowNode object or None
    context: str,
    model: str = "gpt-4o"
) -> Dict[str, Optional[str]]:
    """
    Generate LLM response to determine next action.
    
    Args:
        messages: List of Message objects from the conversation
        available_workflows: Available workflow names
        active_node: Current workflow node object (WorkflowNode or None)
        context: Relevant knowledge base snippets for context
        model: LLM model to use for response generation
    
    Returns:
        Dict with keys:
        - "text": Response text (only if no option/workflow chosen)
        - "decision_option": Which workflow option to select (optional)
        - "workflow": Which workflow to start/switch to (optional)
    """
    
    # Convert messages to OpenAI format and build the message list
    conversation_messages = _convert_messages_to_openai_format(messages)
    
    # Extract available options from active node
    available_options = list(active_node.options.keys()) if active_node else []
    
    # Create the system prompt
    context_section = context if context.strip() else "No specific context available for this conversation."
    
    system_prompt = f"""You are an intelligent assistant helping users navigate through decision workflows. Your job is to:

1. Understand what the user wants to do based on their input and conversation history
2. Decide the appropriate next action from the available options
3. Provide helpful, conversational responses

You have three types of actions you can take:

1. **Select a workflow option**: If the user's input matches one of the available workflow options, select it
2. **Start a workflow**: If the user wants to begin a new workflow that's available
3. **Provide a response**: If neither of the above apply, give a helpful conversational response

AVAILABLE WORKFLOWS:
- edibility_determination: Help determine if a Pokemon is safe to eat
- good_pet_determination: Help determine if a Pokemon would make a good pet

RELEVANT KNOWLEDGE BASE CONTEXT:
{context_section}

RESPONSE FORMAT:
You must respond with a valid JSON object containing exactly these fields:
{{
    "text": "Your conversational response to the user (OPTIONAL - see rules below)",
    "decision_option": "exact_option_name_if_selecting_one" or null,
    "workflow": "exact_workflow_name_if_starting_one" or null
}}

IMPORTANT RULES:
- If you select a decision_option, it must be exactly one of the available options
- If you start a workflow, it must be exactly one of the available workflows  
- The "text" field is OPTIONAL:
  * When selecting a decision_option, text is usually UNNECESSARY (the action is the response)
  * When starting a workflow, text can be helpful but brief
  * Only include text when you need to provide clarification, ask for more info, or give a conversational response
- Only use "decision_option" OR "workflow", never both
- When you do include text, be conversational and helpful
- Handle variations of yes/no responses appropriately (e.g. "sure", "nope", "definitely", etc.)"""

    # Create context message about current state
    context_parts = []
    if active_node and active_node.name:
        context_parts.append(f"Current workflow node: {active_node.name}")
    if available_options:
        context_parts.append(f"Available options: {available_options}")
    context_parts.append(f"Available workflows: {available_workflows}")
    
    context_message = "Context: " + " = ".join(context_parts)

    # Build the full message list for OpenAI
    api_messages = [{"role": "system", "content": system_prompt}]
    api_messages.extend(conversation_messages)
    api_messages.append({"role": "user", "content": context_message})

    try:
        # Call OpenAI API via async client
        llm_response = await get_completion_async(
            messages=api_messages,
            model=model,
            temperature=0.3  # Lower temperature for more consistent responses
        )
        
        # Extract and clean the response content
        llm_response = llm_response.strip()
        
        # Handle markdown-wrapped JSON (```json ... ```)
        if llm_response.startswith("```json") and llm_response.endswith("```"):
            llm_response = llm_response[7:-3].strip()  # Remove ```json and ```
        elif llm_response.startswith("```") and llm_response.endswith("```"):
            llm_response = llm_response[3:-3].strip()  # Remove ``` and ```
        
        # Parse as JSON
        decision = json.loads(llm_response)
        
        # Validate the response structure
        if not isinstance(decision, dict):
            raise ValueError("Response is not a dictionary")
        
        # Ensure all required keys exist with proper defaults
        result = {
            "text": decision.get("text"),  # Can be None/null
            "decision_option": decision.get("decision_option"),
            "workflow": decision.get("workflow")
        }
        
        # Validate that decision_option is in available_options if provided
        if result["decision_option"] and result["decision_option"] not in available_options:
            result["decision_option"] = None
            result["text"] = "I'm not sure which option you mean. Could you be more specific?"
        
        # Validate that workflow is in available_workflows if provided
        if result["workflow"] and result["workflow"] not in available_workflows:
            result["workflow"] = None
            result["text"] = "I'm not sure which workflow you want to start. Could you be more specific?"
        
        # If no action was taken and no text provided, give a default response
        if not result["decision_option"] and not result["workflow"] and not result["text"]:
            result["text"] = "I'm not sure how to help with that. Could you be more specific?"
        
        return result
        
    except json.JSONDecodeError:
        # If JSON parsing fails, treat the entire response as text
        return {
            "text": llm_response if llm_response else "I'm having trouble understanding. Could you rephrase that?",
            "decision_option": None,
            "workflow": None
        }
    except Exception as e:
        # Handle any API errors gracefully
        return {
            "text": f"I'm having some technical difficulties right now. Could you try again? (Error: {str(e)})",
            "decision_option": None,
            "workflow": None
        }

#!/usr/bin/env python3

import os
import json
from typing import List, Dict, Optional, Any
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def process_user_input_with_llm(
    messages: List[Any],  # List of Message objects
    available_options: List[str], 
    available_workflows: List[str],
    current_node_context: Dict[str, Any]
) -> Dict[str, Optional[str]]:
    """
    Process user input using OpenAI GPT-4 to determine next action.
    
    Args:
        messages: List of Message objects from the conversation
        available_options: Current workflow options (empty if no active workflow)
        available_workflows: Available workflow names
        current_node_context: Context about the current workflow node
    
    Returns:
        Dict with keys:
        - "text": Response text (only if no option/workflow chosen)
        - "decision_option": Which workflow option to select (optional)
        - "workflow": Which workflow to start/switch to (optional)
    """
    
    # Convert messages to OpenAI format and build the message list
    conversation_messages = _convert_messages_to_openai_format(messages)
    
    # Create the system prompt
    system_prompt = """You are an intelligent assistant helping users navigate through decision workflows. Your job is to:

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

RESPONSE FORMAT:
You must respond with a valid JSON object containing exactly these fields:
{
    "text": "Your conversational response to the user (OPTIONAL - see rules below)",
    "decision_option": "exact_option_name_if_selecting_one" or null,
    "workflow": "exact_workflow_name_if_starting_one" or null
}

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
    if current_node_context.get('node_name'):
        context_parts.append(f"Current workflow node: {current_node_context['node_name']}")
    if available_options:
        context_parts.append(f"Available options: {available_options}")
    context_parts.append(f"Available workflows: {available_workflows}")
    
    context_message = "Context: " + " | ".join(context_parts)

    # Build the full message list for OpenAI
    api_messages = [{"role": "system", "content": system_prompt}]
    api_messages.extend(conversation_messages)
    api_messages.append({"role": "user", "content": context_message})

    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=api_messages,
            temperature=0.3,  # Lower temperature for more consistent responses
            max_tokens=500,   # Reasonable limit for responses
        )
        
        # Extract the response content
        llm_response = response.choices[0].message.content.strip()
        
        # Try to parse as JSON
        try:
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


# Legacy helper functions (kept for backwards compatibility if needed elsewhere)
def _matches_option(user_input: str, option: str) -> bool:
    """Check if user input matches a workflow option"""
    # Exact match
    if option in user_input:
        return True
    
    # Handle yes/no variations
    if option == "yes":
        yes_patterns = ["sure", "yeah", "yep", "of course", "definitely", "absolutely"]
        return any(pattern in user_input for pattern in yes_patterns)
    
    if option == "no":
        no_patterns = ["nah", "nope", "not really", "don't think so"]
        return any(pattern in user_input for pattern in no_patterns)
    
    return False


def _matches_workflow(user_input: str, workflow_name: str) -> bool:
    """Check if user input indicates desire for a specific workflow"""
    # Direct name match (handle underscores)
    workflow_words = workflow_name.lower().replace('_', ' ')
    if workflow_words in user_input:
        return True
    
    # Check individual words
    if any(word in user_input for word in workflow_words.split()):
        return True
    
    # Specific intent keywords
    if workflow_name == "edibility_determination":
        keywords = ["safe to eat", "edible", "eat", "food", "poisonous", "toxic"]
        return any(keyword in user_input for keyword in keywords)
    
    if workflow_name == "good_pet_determination":
        keywords = ["pet", "companion", "animal friend"]
        return any(keyword in user_input for keyword in keywords)
    
    return False


def _convert_messages_to_openai_format(messages: List[Any]) -> List[Dict[str, str]]:
    """
    Convert Message objects to OpenAI API format.
    
    Args:
        messages: List of Message objects
    
    Returns:
        List of message dicts in OpenAI format
    """
    openai_messages = []
    
    for message in messages:
        # Convert role: "user" stays "user", "bot" becomes "assistant"
        role = "user" if message.role == "user" else "assistant"
        
        openai_messages.append({
            "role": role,
            "content": message.text
        })
    
    return openai_messages 
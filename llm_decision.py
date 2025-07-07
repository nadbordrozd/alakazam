#!/usr/bin/env python3

from typing import List, Dict, Optional

def process_user_input_with_llm(
    conversation_history: str,
    available_options: List[str], 
    available_workflows: List[str]
) -> Dict[str, Optional[str]]:
    """
    Process user input to determine next action.
    
    Args:
        conversation_history: Full conversation as string
        available_options: Current workflow options (empty if no active workflow)
        available_workflows: Available workflow names
    
    Returns:
        Dict with keys:
        - "text": Response text (only if no option/workflow chosen)
        - "decision_option": Which workflow option to select (optional)
        - "workflow": Which workflow to start/switch to (optional)
    """
    
    # Extract last user message from conversation history
    lines = conversation_history.strip().split('\n')
    last_user_message = ""
    
    for line in reversed(lines):
        if line.startswith('Human: ') or line.startswith('H: '):
            last_user_message = line.split(': ', 1)[1] if ': ' in line else ""
            break
    
    if not last_user_message:
        return {"text": "Sorry I don't understand", "decision_option": None, "workflow": None}
    
    user_input = last_user_message.lower().strip()
    
    # First, try to match available options
    if available_options:
        for option in available_options:
            if _matches_option(user_input, option.lower()):
                # Provide acknowledgment text along with option selection
                acknowledgment_text = f"Got it, I understand you mean '{option}'."
                return {"text": acknowledgment_text, "decision_option": option, "workflow": None}
    
    # Second, try to match workflow names
    for workflow in available_workflows:
        if _matches_workflow(user_input, workflow):
            # Provide acknowledgment text along with workflow switch
            workflow_name = workflow.replace('_', ' ').title()
            acknowledgment_text = f"I'll help you with {workflow_name}."
            return {"text": acknowledgment_text, "decision_option": None, "workflow": workflow}
    
    # If nothing matches, return don't understand
    return {"text": "Sorry I don't understand", "decision_option": None, "workflow": None}


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
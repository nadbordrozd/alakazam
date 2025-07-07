from typing import Dict, Optional, Any, List
from datetime import datetime
from dataclasses import dataclass
from workflow import Workflow, WorkflowNode
from llm_decision import process_user_input_with_llm

# Unified message class for both user and bot messages
@dataclass
class Message:
    id: int
    timestamp: datetime
    text: str
    role: str  # "user" or "bot"
    node: Optional[WorkflowNode] = None  # Only used for user messages
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        return {
            "id": self.id,
            "text": self.text,
            "role": self.role,
            "timestamp": self.timestamp.isoformat(),
            "node": self.node.name if self.node else None
        }


class Bot:
    def __init__(self):
        # Former ConversationState fields
        self.messages: List[Message] = []
        self.next_message_id = 1
        self.workflow_positions: Dict[Workflow, WorkflowNode] = {}
        self.active_node: Optional[WorkflowNode] = None
        
        # Bot functionality
        self.workflows: Dict[str, Workflow] = {}
    
    # Former ConversationState methods
    def add_user_message(self, text: str) -> Message:
        """Add a user message with current workflow state"""
        message = Message(
            id=self.next_message_id,
            timestamp=datetime.now(),
            text=text,
            role="user",
            node=self.active_node
        )
        self.messages.append(message)
        self.next_message_id += 1
        return message
    
    def add_bot_message(self, text: str) -> Message:
        """Add a bot message"""
        message = Message(
            id=self.next_message_id,
            timestamp=datetime.now(),
            text=text,
            role="bot"
        )
        self.messages.append(message)
        self.next_message_id += 1
        return message
    
    def set_active_node(self, node: WorkflowNode):
        """Set the active node (and update workflow position tracking)"""
        if node and node.workflow:
            self.workflow_positions[node.workflow] = node
        self.active_node = node
    
    def switch_workflow(self, workflow: Workflow):
        """Switch to a different workflow"""
        self.active_node = self.workflow_positions.get(workflow)
        # If no node is saved for this workflow, set to first node
        if not self.active_node and workflow:
            self.active_node = workflow.get_first_node()
    
    def can_go_back(self) -> bool:
        """Check if we can go back"""
        if len(self.messages) < 2:
            return False
        
        # Look for the most recent user message that has bot messages after it
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i].role == "user":
                # Found a user message, check if there are bot messages after it
                return i < len(self.messages) - 1
        
        return False
    
    # Bot public interface methods
    def get_greeting_message(self) -> Message:
        """Get the opening greeting message for the conversation"""
        return self.add_bot_message(
            "Hello! I'm a chatbot designed to help you navigate through decision workflows. "
            "I can guide you through various topics using interactive questions and provide "
            "relevant information along the way. To get started, please select or start a workflow."
        )
    
    def load_workflow(self, name: str, file_path: str):
        """Load a workflow for use"""
        self.workflows[name] = Workflow(name, file_path)
    
    def start_workflow(self, workflow_name: str) -> Message:
        """Start a new workflow"""
        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        workflow = self.workflows[workflow_name]
        first_node = workflow.get_first_node()
        if not first_node:
            raise ValueError("Empty workflow")
        
        # Set active node
        self.set_active_node(first_node)
        
        # Add and return bot message
        return self.add_bot_message(self._get_bot_text(first_node))
    
    def process_user_input(self, text: str):
        """Process user input - yields user message immediately, then bot response"""
        # Add user message first
        user_msg = self.add_user_message(text)
        
        # Yield user message immediately (fast operation)
        yield user_msg
        
        # Get context for LLM decision
        conversation_history = self.get_conversation_history_for_llm()
        available_options = list(self.active_node.options.keys()) if self.active_node else []
        available_workflows = list(self.workflows.keys())
        
        # Let LLM decide what to do
        decision = process_user_input_with_llm(conversation_history, available_options, available_workflows)
        
        # Process LLM decision
        
        # First, if LLM provided text, always send it
        if decision["text"]:
            yield self.add_bot_message(decision["text"])
        
        # Then, if there's a decision option, process it
        if decision["decision_option"]:
            if self.active_node and decision["decision_option"] in self.active_node.options:
                next_node = self.active_node.next(decision["decision_option"])
                self.set_active_node(next_node)
                bot_text = self._get_bot_text(next_node)
                yield self.add_bot_message(bot_text)
        
        # Then, if there's a workflow to start, process it
        elif decision["workflow"]:
            if decision["workflow"] in self.workflows:
                yield self.start_workflow(decision["workflow"])
    
    def go_back(self) -> List[int]:
        """Go back one step in the conversation"""
        if not self.can_go_back():
            return []
        
        # Find the most recent user message
        user_msg_index = -1
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i].role == "user":
                user_msg_index = i
                break
        
        if user_msg_index == -1:
            return []  # No user message found (shouldn't happen if can_go_back is correct)
        
        # Get the user message for state restoration
        user_msg = self.messages[user_msg_index]
        
        # Collect all messages to remove (user message and everything after it)
        removed_message_ids = []
        for i in range(user_msg_index, len(self.messages)):
            removed_message_ids.append(self.messages[i].id)
        
        # Remove all messages from user_msg_index onwards
        self.messages = self.messages[:user_msg_index]
        
        # Restore workflow state from the user message
        self.active_node = user_msg.node
        
        # Update workflow_positions based on the restored state
        if user_msg.node and user_msg.node.workflow:
            self.workflow_positions[user_msg.node.workflow] = user_msg.node
        
        return removed_message_ids
    
    def get_conversation_history_for_llm(self) -> str:
        """Format conversation history as a string for LLM consumption"""
        if not self.messages:
            return "No conversation history yet."
        
        # Format each message with role prefix
        formatted_messages = []
        for message in self.messages:
            role_prefix = "Human" if message.role == "user" else "Assistant"
            formatted_messages.append(f"{role_prefix}: {message.text}")
        
        # Join with double newlines for clear separation
        conversation = "\n\n".join(formatted_messages)
        
        # Add context about current workflow state if available
        context_info = []
        if self.active_node:
            context_info.append(f"Current workflow node: {self.active_node.name}")
            if self.active_node.options:
                available_options = list(self.active_node.options.keys())
                context_info.append(f"Available options: {available_options}")
        
        if context_info:
            context = "\n\n[Context: " + " | ".join(context_info) + "]"
            conversation += context
        
        return conversation
    
    # Helper methods
    def _get_bot_text(self, node: WorkflowNode) -> str:
        """Helper to get appropriate bot text from a node"""
        if node.is_question():
            return node.question
        elif node.is_verdict():
            return node.verdict
        else:
            return "Something went wrong"


# Example usage
if __name__ == "__main__":
    bot = Bot()
    
    # Load workflows
    bot.load_workflow("pet_advisor", "workflows/good_pet_determination.yaml")
    bot.load_workflow("edibility_check", "workflows/edibility_determination.yaml")
    
    # Show greeting message
    print("=== Bot Greeting ===")
    greeting = bot.get_greeting_message()
    print(f"Bot: {greeting.text}")
    
    # Start workflow
    print("\n=== Starting pet advisor workflow ===")
    response = bot.start_workflow("pet_advisor")
    print(f"Bot: {response.text}")
    print(f"Options: {list(bot.active_node.options.keys())}")
    
    # Test valid input (generator approach)
    print("\n=== Testing 'no' (generator approach) ===")
    responses = bot.process_user_input("no")
    user_response = next(responses)
    print(f"User (immediate): {user_response.text}")
    
    bot_response = next(responses)
    print(f"Bot: {bot_response.text}")
    print(f"Options: {list(bot.active_node.options.keys())}")
    
    # Test invalid input (generator approach)
    print("\n=== Testing 'maybe' (generator approach) ===")
    responses = bot.process_user_input("maybe")
    user_response = next(responses)
    print(f"User (immediate): {user_response.text}")
    
    bot_response = next(responses)
    print(f"Bot: {bot_response.text}")
    print(f"Current node: {bot.active_node.name}")
    
    # Test go back
    print("\n=== Testing go back ===")
    deleted_ids = bot.go_back()
    print(f"Deleted message IDs: {deleted_ids}")
    
    # Test conversation history for LLM
    print("\n=== Conversation History for LLM ===")
    llm_history = bot.get_conversation_history_for_llm()
    print(llm_history) 
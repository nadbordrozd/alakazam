from typing import Dict, Optional, Any, List
from datetime import datetime
from dataclasses import dataclass
from workflow import Workflow, WorkflowNode

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
        return (len(self.messages) >= 2 and 
                self.messages[-1].role == "bot" and 
                self.messages[-2].role == "user")
    
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
        
        # Now process bot response (potentially slow operation)
        if not self.active_node:
            bot_msg = self.add_bot_message("No active workflow. Please start a workflow first.")
            yield bot_msg
            return
        
        current_node = self.active_node
        
        # Try to match user input to available options
        user_choice = text.strip().lower()
        matched_option = None
        
        # Find case-insensitive match
        for option_key in current_node.options.keys():
            if option_key.lower() == user_choice:
                matched_option = option_key
                break
        
        if not matched_option:
            # No match found
            bot_msg = self.add_bot_message("Sorry I don't understand")
            yield bot_msg
            return
        
        # Found a match, move to next node
        next_node = current_node.next(matched_option)
        
        # Update active node
        self.set_active_node(next_node)
        
        # Generate bot response (potentially slow operation here)
        bot_text = self._get_bot_text(next_node)
        bot_msg = self.add_bot_message(bot_text)
        
        # Yield bot response
        yield bot_msg
    
    def go_back(self) -> List[int]:
        """Go back one step in the conversation"""
        if not self.can_go_back():
            return []
        
        # Pop the messages
        bot_msg = self.messages.pop()
        user_msg = self.messages.pop()
        
        # Restore workflow state from the user message
        self.active_node = user_msg.node
        
        # Update workflow_positions based on the restored state
        if user_msg.node and user_msg.node.workflow:
            self.workflow_positions[user_msg.node.workflow] = user_msg.node
        
        return [user_msg.id, bot_msg.id]
    
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
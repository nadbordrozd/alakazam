from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from workflow import Workflow, WorkflowNode


@dataclass
class UserMessage:
    id: int
    timestamp: datetime
    text: str
    workflow: Optional['Workflow']  # Active workflow before this message
    node: Optional['WorkflowNode']      # Active node before this message


@dataclass
class BotMessage:
    id: int
    timestamp: datetime
    text: str


class ConversationState:
    def __init__(self):
        self.messages: List[Union[UserMessage, BotMessage]] = []
        self.next_message_id = 1
        self.workflow_positions: Dict['Workflow', 'WorkflowNode'] = {}  # workflow -> current_node
        self.active_workflow: Optional['Workflow'] = None
    
    def add_user_message(self, text: str) -> UserMessage:
        """Add a user message with current workflow state"""
        message = UserMessage(
            id=self.next_message_id,
            timestamp=datetime.now(),
            text=text,
            workflow=self.active_workflow,
            node=self.workflow_positions.get(self.active_workflow) if self.active_workflow else None
        )
        self.messages.append(message)
        self.next_message_id += 1
        return message
    
    def add_bot_message(self, text: str) -> BotMessage:
        """Add a bot message"""
        message = BotMessage(
            id=self.next_message_id,
            timestamp=datetime.now(),
            text=text
        )
        self.messages.append(message)
        self.next_message_id += 1
        return message
    
    def set_workflow_position(self, workflow: 'Workflow', node: 'WorkflowNode'):
        """Set current position in a workflow"""
        self.workflow_positions[workflow] = node
        self.active_workflow = workflow
    
    def get_current_position(self, workflow: 'Workflow') -> Optional['WorkflowNode']:
        """Get current position in a workflow"""
        return self.workflow_positions.get(workflow)
    
    def switch_workflow(self, workflow: 'Workflow'):
        """Switch to a different workflow"""
        self.active_workflow = workflow
    
    def go_back(self) -> Optional[Tuple[int, int]]:
        """
        Go back one step by removing last bot and user messages.
        Returns tuple of (user_message_id, bot_message_id) that were removed, or None if can't go back.
        """
        if not self.can_go_back():
            return None
        
        # Pop the messages
        bot_msg = self.messages.pop()
        user_msg = self.messages.pop()
        
        # Restore workflow state from the user message
        self.active_workflow = user_msg.workflow
        
        # Update workflow_positions based on the restored state
        if user_msg.workflow:
            if user_msg.node:
                self.workflow_positions[user_msg.workflow] = user_msg.node

        
        return (user_msg.id, bot_msg.id)
    
    def can_go_back(self) -> bool:
        """Check if we can go back"""
        return (len(self.messages) >= 2 and 
                isinstance(self.messages[-1], BotMessage) and 
                isinstance(self.messages[-2], UserMessage))


# Example usage would require importing actual Workflow and WorkflowNode objects
# if __name__ == "__main__":
#     from workflow import Workflow
#     conv = ConversationState()
#     workflow = Workflow("workflows/good_pet_determination.yaml")
#     node = workflow.nodes["legendary_check"]
#     conv.set_workflow_position(workflow, node)
#     # ... etc 
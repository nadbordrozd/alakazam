from typing import Dict, Optional, Any, List
from datetime import datetime
from dataclasses import dataclass
import asyncio
from workflow import Workflow, WorkflowNode
from llm_decision import respond, is_relevant, rewrite_query_for_search
from knowledge_base_store import KnowledgeBaseStore

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
    def __init__(self, 
        embedding_model: str = "text-embedding-3-small", 
        knowledge_base_dir: str = "knowledge_base", 
        cache_dir: str = ".cache", 
        context_messages_count: int = 5, 
        relevance_model: str = "gpt-4.1-mini", 
        relevance_messages_count: int = 5, 
        generator_model: str = "gpt-4.1",
        rewriter_model: str = "gpt-4o-mini"
    ):
        # Former ConversationState fields
        self.messages: List[Message] = []
        self.next_message_id = 1
        self.workflow_positions: Dict[str, WorkflowNode] = {}
        self.active_node: Optional[WorkflowNode] = None
        
        # Bot functionality
        self.workflows: Dict[str, Workflow] = {}
        self.context_messages_count = context_messages_count
        
        # Relevance filtering parameters
        self.relevance_model = relevance_model
        self.relevance_messages_count = relevance_messages_count
        
        # Response generation parameters
        self.generator_model = generator_model
        
        # Query rewriting parameters
        self.rewriter_model = rewriter_model
        
        # Knowledge base
        self.knowledge_base = KnowledgeBaseStore(
            knowledge_base_dir=knowledge_base_dir,
            cache_dir=cache_dir,
            model_name=embedding_model
        )
        self.last_knowledge_snippets: List[Dict[str, Any]] = []
    
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
            self.workflow_positions[node.workflow.name] = node
        self.active_node = node
    

    
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
    
    async def process_user_input(self, text: str):
        """Process user input - yields user message immediately, then bot response"""
        # Add user message first
        user_msg = self.add_user_message(text)
        
        # Yield user message immediately (fast operation)
        yield user_msg
        
        # Process bot response (may take time with LLM)
        bot_messages = await self.process_bot_response()
        
        # Yield each bot message
        for bot_msg in bot_messages:
            yield bot_msg
    
    async def process_bot_response(self) -> List[Message]:
        """Process bot response based on the last user message"""
        # Get context for LLM decision
        available_workflows = list(self.workflows.keys())
        
        # Generate knowledge base context from recent messages
        context = await self._generate_knowledge_context()
        
        # Let LLM decide what to do
        decision = await respond(self.messages, available_workflows, self.active_node, context, self.generator_model)
        
        bot_messages = []
        
        # Process LLM decision
        # First, if LLM provided text, always send it
        if decision.get("text"):
            bot_msg = self.add_bot_message(decision["text"])
            bot_messages.append(bot_msg)
        
        # Then, if there's a decision option, process it
        if decision.get("decision_option"):
            if self.active_node and decision["decision_option"] in self.active_node.options:
                next_node = self.active_node.next(decision["decision_option"])
                self.set_active_node(next_node)
                bot_text = self._get_bot_text(next_node)
                bot_msg = self.add_bot_message(bot_text)
                bot_messages.append(bot_msg)
        
        # Then, if there's a workflow to start, process it
        elif decision.get("workflow"):
            if decision["workflow"] in self.workflows:
                bot_msg = self.start_workflow(decision["workflow"])
                bot_messages.append(bot_msg)
        
        return bot_messages
    
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
            self.workflow_positions[user_msg.node.workflow.name] = user_msg.node
        
        return removed_message_ids
    
    async def _generate_knowledge_context(self) -> str:
        """Generate knowledge base context from recent conversation messages with relevance filtering"""
        # Clear previous snippets
        self.last_knowledge_snippets = []
        
        if not self.messages:
            return ""
        
        # Use query rewriter to generate an effective search query from the entire conversation
        try:
            query_string = await rewrite_query_for_search(self.messages, self.rewriter_model)
        except Exception as e:
            print(f"Error rewriting query: {e}")
            # Fallback: use the last user message
            last_user_msg = None
            for message in reversed(self.messages):
                if message.role == "user":
                    last_user_msg = message.text
                    break
            query_string = last_user_msg or ""
        
        # Don't query if there's no meaningful content
        if not query_string.strip():
            return ""
        
        try:
            # Retrieve potential snippets from knowledge base
            snippets = self.knowledge_base.retrieve_snippets(query_string, top_k=3)
            
            if not snippets:
                return ""
            
            # Get messages for relevance evaluation (last n messages)
            relevance_messages = self.messages[-self.relevance_messages_count:]
            
            # Run all relevance checks in parallel
            relevance_tasks = [
                is_relevant(
                    messages=relevance_messages,
                    snippet=snippet['content'],
                    model=self.relevance_model
                )
                for snippet in snippets
            ]
            
            try:
                relevance_results = await asyncio.gather(*relevance_tasks)
            except Exception as e:
                print(f"Error during parallel relevance checking: {e}")
                # Fallback: assume all snippets are relevant
                relevance_results = [
                    {
                        'is_relevant': True,
                        'confidence': 0.5,
                        'reasoning': f"Relevance check failed: {str(e)}"
                    }
                    for _ in snippets
                ]
            
            # Combine snippets with their relevance results and filter
            relevant_snippets = []
            for snippet, relevance_result in zip(snippets, relevance_results):
                snippet_with_relevance = snippet.copy()
                snippet_with_relevance['relevance'] = relevance_result
                
                # Only keep relevant snippets
                if relevance_result['is_relevant']:
                    relevant_snippets.append(snippet_with_relevance)
            
            # Store filtered snippets for frontend display
            self.last_knowledge_snippets = relevant_snippets
            
            # Concatenate relevant snippets into context
            context_parts = []
            for snippet in relevant_snippets:
                # Add snippet content with source info
                source_info = f"[From: {snippet['file_name']}]"
                context_parts.append(f"{source_info}\n{snippet['content']}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            # If knowledge base retrieval fails, return empty context
            print(f"Error retrieving knowledge base context: {e}")
            return ""
   
    def get_active_sidebars(self) -> List[str]:
        """Get the sidebar files for the currently active workflow node"""
        if self.active_node:
            return self.active_node.sidebars
        return []
    
    def get_current_workflow_name(self) -> Optional[str]:
        """Get the name of the currently active workflow"""
        if self.active_node and self.active_node.workflow:
            return self.active_node.workflow.name
        return None
    
    # Helper methods
    def _get_bot_text(self, node: WorkflowNode) -> str:
        """Helper to get appropriate bot text from a node"""
        if node.is_question():
            return node.question
        elif node.is_verdict():
            return node.verdict
        else:
            return "Something went wrong"


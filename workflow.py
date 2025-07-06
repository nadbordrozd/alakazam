from typing import Dict, List, Optional, Any
import yaml


class WorkflowNode:
    def __init__(self, name: str, data: Dict[str, Any], workflow: 'Workflow' = None):
        self.name = name
        self.data = data
        self.workflow = workflow
    
    @property
    def question(self) -> Optional[str]:
        """Get the question text if this is a question node"""
        return self.data.get('question')
    
    @property
    def verdict(self) -> Optional[str]:
        """Get the verdict text if this is a verdict node"""
        return self.data.get('verdict')
    
    @property
    def options(self) -> Dict[str, str]:
        """Get the available options (choice -> next_node)"""
        return self.data.get('options', {})
    
    @property
    def sidebars(self) -> List[str]:
        """Get the sidebar files for this node"""
        return self.data.get('sidebars', [])
    
    def is_question(self) -> bool:
        """Check if this is a question node"""
        return 'question' in self.data
    
    def is_verdict(self) -> bool:
        """Check if this is a verdict node"""
        return 'verdict' in self.data
    
    def has_option(self, choice: str) -> bool:
        """Check if this node has a specific option"""
        return choice in self.options
    
    def get_next_node(self, choice: str) -> Optional[str]:
        """Get the next node name for a given choice"""
        return self.options.get(choice)
    
    def next(self, option_name: str) -> Optional['WorkflowNode']:
        """Get the next WorkflowNode for a given option"""
        next_node_name = self.options.get(option_name)
        if next_node_name and self.workflow:
            return self.workflow.get_node(next_node_name)
        return None


class Workflow:
    def __init__(self, name: str, file_path: str):
        self.name = name
        self.file_path = file_path
        self.nodes: Dict[str, WorkflowNode] = {}
        self.first_node: Optional[str] = None
        self.load()
    
    def load(self):
        """Load workflow from YAML file"""
        with open(self.file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        
        # Create nodes
        for node_name, node_data in data.items():
            self.nodes[node_name] = WorkflowNode(node_name, node_data, self)
        
        # Set first node
        if self.nodes:
            self.first_node = list(self.nodes.keys())[0]
    
    def get_node(self, name: str) -> Optional[WorkflowNode]:
        """Get a node by name"""
        return self.nodes.get(name)
    
    def get_first_node(self) -> Optional[WorkflowNode]:
        """Get the first node in the workflow"""
        return self.nodes.get(self.first_node) if self.first_node else None
    
    def has_node(self, name: str) -> bool:
        """Check if workflow has a node with given name"""
        return name in self.nodes
    
    def get_all_node_names(self) -> List[str]:
        """Get all node names in the workflow"""
        return list(self.nodes.keys())


# Example usage
if __name__ == "__main__":
    # Load a workflow
    workflow = Workflow("pet_advisor", "workflows/good_pet_determination.yaml")
    
    print(f"Workflow: {workflow.name}")
    print(f"Total nodes: {len(workflow.nodes)}")
    print(f"First node: {workflow.first_node}")
    
    # Get first node
    first_node = workflow.get_first_node()
    if first_node:
        print(f"\nFirst node details:")
        print(f"  Name: {first_node.name}")
        print(f"  Question: {first_node.question}")
        print(f"  Is question: {first_node.is_question()}")
        print(f"  Options: {list(first_node.options.keys())}")
        print(f"  Sidebars: {first_node.sidebars}")
        
        # Test next method
        next_node = first_node.next('no')
        if next_node:
            print(f"\nNext node for 'no': {next_node.name}")
            print(f"  Question: {next_node.question}")
        else:
            print(f"\nNo next node found for 'no'") 
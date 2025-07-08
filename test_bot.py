#!/usr/bin/env python3

import unittest
from unittest.mock import patch, AsyncMock
import asyncio
from bot import Bot, Message

class TestBotGoBack(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.bot = Bot()
        self.bot.load_workflow("test", "test_workflow.yaml")
    
    def test_go_back_no_messages(self):
        """Test go_back when no messages exist"""
        result = self.bot.go_back()
        
        self.assertEqual(result, [])
        self.assertIsInstance(result, list)
        self.assertFalse(self.bot.can_go_back())
    
    def test_go_back_only_bot_message(self):
        """Test go_back when only bot message exists (can't go back)"""
        self.bot.start_workflow("test")  # creates only bot message
        
        self.assertFalse(self.bot.can_go_back())
        result = self.bot.go_back()
        
        self.assertEqual(result, [])
    
    @patch('llm_decision.respond')
    def test_go_back_successful(self, mock_respond):
        """Test successful go_back operation with mocked LLM"""
        # Mock LLM to select the "red" option
        mock_respond.return_value = {
            "text": None,
            "decision_option": "red", 
            "workflow": None
        }
        
        # Start workflow
        self.bot.start_workflow("test")
        initial_node = self.bot.active_node
        initial_message_count = len(self.bot.messages)
        
        # Process user input (should create user message + bot response)
        async def async_test():
            responses = []
            async for response in self.bot.process_user_input("red"):
                responses.append(response)
            return responses
        
        responses = asyncio.run(async_test())
        
        # Verify workflow progressed
        self.assertEqual(self.bot.active_node.name, "red_response")
        self.assertGreater(len(self.bot.messages), initial_message_count)
        
        # Store state before go_back
        messages_before_goback = len(self.bot.messages)
        
        # Test can_go_back
        self.assertTrue(self.bot.can_go_back())
        
        # Perform go_back
        result = self.bot.go_back()
        
        # Verify go_back results
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)  # Should have removed some messages
        self.assertTrue(all(isinstance(msg_id, int) for msg_id in result))
        
        # Verify state restoration
        self.assertEqual(self.bot.active_node.name, "start")  # Should be back to initial node
        self.assertLess(len(self.bot.messages), messages_before_goback)  # Fewer messages
        
        # Verify workflow positions were updated
        if self.bot.active_node and self.bot.active_node.workflow:
            self.assertEqual(
                self.bot.workflow_positions[self.bot.active_node.workflow.name], 
                self.bot.active_node
            )
    
    @patch('llm_decision.respond')
    def test_go_back_multiple_times(self, mock_respond):
        """Test multiple go_back operations with mocked LLM"""
        # Mock LLM to select the "red" option
        mock_respond.return_value = {
            "text": None,
            "decision_option": "red",
            "workflow": None
        }
        
        self.bot.start_workflow("test")
        
        # Process user input
        async def async_test():
            responses = []
            async for response in self.bot.process_user_input("red"):
                responses.append(response)
            return responses
        
        asyncio.run(async_test())
        
        # First go_back should succeed
        self.assertTrue(self.bot.can_go_back())
        result1 = self.bot.go_back()
        self.assertGreater(len(result1), 0)
        
        # Second go_back should return empty (only initial bot message left)
        self.assertFalse(self.bot.can_go_back())
        result2 = self.bot.go_back()
        self.assertEqual(result2, [])
    
    @patch('llm_decision.respond')
    def test_go_back_message_id_tracking(self, mock_respond):
        """Test that go_back correctly tracks and returns message IDs"""
        # Mock LLM response
        mock_respond.return_value = {
            "text": "I'll help you with that",
            "decision_option": "red",
            "workflow": None
        }
        
        self.bot.start_workflow("test")
        initial_messages = len(self.bot.messages)
        
        # Process user input
        async def async_test():
            responses = []
            async for response in self.bot.process_user_input("red"):
                responses.append(response)
            return responses
        
        responses = asyncio.run(async_test())
        
        # Collect message IDs that should be removed
        messages_after = self.bot.messages[initial_messages:]
        expected_removed_ids = [msg.id for msg in messages_after]
        
        # Perform go_back
        actual_removed_ids = self.bot.go_back()
        
        # Verify correct message IDs were returned
        self.assertEqual(set(actual_removed_ids), set(expected_removed_ids))
        
        # Verify messages were actually removed
        current_message_ids = [msg.id for msg in self.bot.messages]
        for removed_id in actual_removed_ids:
            self.assertNotIn(removed_id, current_message_ids)
    
    def test_can_go_back_logic(self):
        """Test the can_go_back method logic"""
        # Initially no messages
        self.assertFalse(self.bot.can_go_back())
        
        # Add only bot message
        bot_msg = self.bot.add_bot_message("Hello")
        self.assertFalse(self.bot.can_go_back())
        
        # Add user message (but no bot response after it)
        user_msg = self.bot.add_user_message("Hi")
        self.assertFalse(self.bot.can_go_back())
        
        # Add bot response after user message
        bot_response = self.bot.add_bot_message("How can I help?")
        self.assertTrue(self.bot.can_go_back())
        
        # Add another user message (no bot response after)
        user_msg2 = self.bot.add_user_message("Help me")
        self.assertFalse(self.bot.can_go_back())
        
        # Add bot response
        bot_response2 = self.bot.add_bot_message("Sure!")
        self.assertTrue(self.bot.can_go_back())


if __name__ == "__main__":
    unittest.main() 
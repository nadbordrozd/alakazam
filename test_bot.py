#!/usr/bin/env python3

import unittest
import os
from bot import Bot, Message

class TestBot(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.bot = Bot()
        self.bot.load_workflow("test", "test_workflow.yaml")
    
    def test_process_user_input_no_active_workflow(self):
        """Test process_user_input when no workflow is active"""
        responses = self.bot.process_user_input("hello")
        user_response = next(responses)
        bot_response = next(responses)
        
        self.assertIsInstance(user_response, Message)
        self.assertIsInstance(bot_response, Message)
        self.assertEqual(user_response.role, "user")
        self.assertEqual(bot_response.role, "bot")
        self.assertEqual(user_response.text, "hello")
        self.assertEqual(bot_response.text, "No active workflow. Please start a workflow first.")
    
    def test_process_user_input_valid_option(self):
        """Test process_user_input with valid option"""
        # Start workflow first
        self.bot.start_workflow("test")
        
        # Test valid input
        responses = self.bot.process_user_input("red")
        user_response = next(responses)
        bot_response = next(responses)
        
        self.assertIsInstance(user_response, Message)
        self.assertIsInstance(bot_response, Message)
        self.assertEqual(user_response.role, "user")
        self.assertEqual(bot_response.role, "bot")
        
        self.assertEqual(user_response.text, "red")
        self.assertEqual(bot_response.text, "Red is a warm color!")
        
        # Check workflow state
        self.assertEqual(self.bot.active_node.name, "red_response")
        self.assertEqual(list(self.bot.active_node.options.keys()), [])  # verdict node has no options
    
    def test_process_user_input_case_insensitive(self):
        """Test that process_user_input is case insensitive"""
        self.bot.start_workflow("test")
        
        responses = self.bot.process_user_input("RED")  # uppercase
        user_response = next(responses)
        bot_response = next(responses)
        
        self.assertEqual(bot_response.text, "Red is a warm color!")
        self.assertEqual(self.bot.active_node.name, "red_response")
    
    def test_process_user_input_invalid_option(self):
        """Test process_user_input with invalid option"""
        self.bot.start_workflow("test")
        
        responses = self.bot.process_user_input("green")  # not a valid option
        user_response = next(responses)
        bot_response = next(responses)
        
        self.assertIsInstance(user_response, Message)
        self.assertIsInstance(bot_response, Message)
        self.assertEqual(user_response.role, "user")
        self.assertEqual(bot_response.role, "bot")
        
        self.assertEqual(user_response.text, "green")
        self.assertEqual(bot_response.text, "Sorry I don't understand")
        
        # Should stay on same node
        self.assertEqual(self.bot.active_node.name, "start")
        self.assertEqual(list(self.bot.active_node.options.keys()), ["red", "blue"])
    
    def test_go_back_no_messages(self):
        """Test go_back when no messages exist"""
        result = self.bot.go_back()
        
        self.assertEqual(result, [])
        self.assertIsInstance(result, list)
    
    def test_go_back_only_bot_message(self):
        """Test go_back when only bot message exists (can't go back)"""
        self.bot.start_workflow("test")  # creates only bot message
        
        result = self.bot.go_back()
        
        self.assertEqual(result, [])
    
    def test_go_back_successful(self):
        """Test successful go_back operation"""
        self.bot.start_workflow("test")
        
        # Process user input (creates user + bot messages)
        responses = self.bot.process_user_input("red")
        user_response = next(responses)
        bot_response = next(responses)
        
        # Check state before go_back
        self.assertEqual(self.bot.active_node.name, "red_response")
        
        result = self.bot.go_back()
        
        # Should return list of 2 message IDs
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result, list)
        self.assertTrue(all(isinstance(msg_id, int) for msg_id in result))
        
        # Should restore to previous state
        self.assertEqual(self.bot.active_node.name, "start")
    
    def test_go_back_multiple_times(self):
        """Test multiple go_back operations"""
        self.bot.start_workflow("test")
        
        # Process user input
        responses = self.bot.process_user_input("red")
        user_response = next(responses)
        bot_response = next(responses)
        
        # First go_back should succeed
        result1 = self.bot.go_back()
        self.assertEqual(len(result1), 2)
        
        # Second go_back should return empty (only bot message left)
        result2 = self.bot.go_back()
        self.assertEqual(result2, [])
    
    def test_greeting_message(self):
        """Test the greeting message functionality"""
        greeting = self.bot.get_greeting_message()
        
        # Check that it returns a Message object
        self.assertIsInstance(greeting, Message)
        self.assertEqual(greeting.role, "bot")
        
        # Check that the message contains expected content
        self.assertIn("Hello", greeting.text)
        self.assertIn("chatbot", greeting.text)
        self.assertIn("workflow", greeting.text)
        
        # Check that it's added to message history
        self.assertEqual(len(self.bot.messages), 1)
        self.assertEqual(self.bot.messages[0], greeting)
        
        # Check that it has proper ID and timestamp
        self.assertEqual(greeting.id, 1)
        self.assertIsNotNone(greeting.timestamp)
    
    def test_workflow_progression(self):
        """Test complete workflow progression"""
        # Start workflow
        start_response = self.bot.start_workflow("test")
        self.assertIsInstance(start_response, Message)
        self.assertEqual(start_response.role, "bot")
        self.assertEqual(self.bot.active_node.name, "start")
        self.assertEqual(list(self.bot.active_node.options.keys()), ["red", "blue"])
        
        # Choose blue
        responses = self.bot.process_user_input("blue")
        user_response = next(responses)
        blue_response = next(responses)
        self.assertEqual(self.bot.active_node.name, "blue_response")
        self.assertEqual(blue_response.text, "Blue is a cool color!")
        self.assertEqual(list(self.bot.active_node.options.keys()), [])
        
        # Go back
        deleted_ids = self.bot.go_back()
        self.assertEqual(len(deleted_ids), 2)
        self.assertEqual(self.bot.active_node.name, "start")
        
        # Choose red this time
        responses = self.bot.process_user_input("red")
        user_response = next(responses)
        red_response = next(responses)
        self.assertEqual(self.bot.active_node.name, "red_response")
        self.assertEqual(red_response.text, "Red is a warm color!")


if __name__ == "__main__":
    unittest.main() 
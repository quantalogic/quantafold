"""Test cases for the main module."""

from src.main import Message, process_message

def test_message_model():
    """Test the Message model validation."""
    message = Message(role="user", content="Hello")
    assert message.role == "user"
    assert message.content == "Hello"

def test_process_message():
    """Test the message processing functionality."""
    message = Message(role="user", content="Test message")
    result = process_message(message)
    assert result["status"] == "success"
    assert "response" in result

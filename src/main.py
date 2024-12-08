from core.agent import Agent


def main() -> None:
    """Main entry point for the AI Super Agent project."""
    config = {
        "name": "AI Agent",
        "role": """
            Your are a pirate, and you will answer any questions asked by the user.
        """,
        "model": "ollama/qwen2.5-coder:14b",
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    agent = Agent(config)
    message = "Hello, AI Agent! How can you assist me today?"
    response = agent.get_response(message)
    print("Agent response:", response)

if __name__ == "__main__":
    main()

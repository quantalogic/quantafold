from core.agent import Agent
from core.reagent import ReactAgent


def main() -> None:
    """Main entry point for the AI Super Agent project."""
    config = {
        "name": "Super Agent",
        "role": "AI Assistant",
        "model": "ollama/qwen2.5-coder:14b",
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    agent = ReactAgent.from_config(config)
    message = "Write a haiku"
    response = agent.reason_and_decompose(message)
    print("Agent response:", response)

if __name__ == "__main__":
    main()

import logging

from core.agent import Agent
from core.generative_model import GenerativeModel
from tools.wikipedia import use_wikipedia

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s:%(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> None:
    model = GenerativeModel(model="ollama/qwen2.5-coder:14b")
    agent = Agent(model=model)
    agent.register("SEARCH_WIKIPEDIA", use_wikipedia)

    print("Welcome to the AI Assistant!")
    print(
        "You can ask questions about any topic, and I'll search Wikipedia for information."
    )
    print("Type 'quit' or 'exit' to end the session.\n")

    while True:
        print("\nAsk a question:")
        query = input().strip()

        if query.lower() in ["quit", "exit"]:
            print("Goodbye!")
            break

        if not query:
            print("Please enter a question.")
            continue

        try:
            response = agent.execute(query)
            print("\nResponse:", response)
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Please try again with a different question.")


if __name__ == "__main__":
    main()

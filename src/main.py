import logging

from core.agent import Agent
from core.generative_model import GenerativeModel
from models.shell_command import shell_command_tool
from models.tool import Tool as ToolModel
from models.tool import ToolArgument
from tools.shell_command import execute_shell_command
from tools.wikipedia import use_wikipedia

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s:%(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

MODEL_NAME = "gpt-4o-mini"


def main() -> None:
    model = GenerativeModel(model=MODEL_NAME)
    agent = Agent(model=model)

    wikipedia_tool = ToolModel(
        name="SEARCH_WIKIPEDIA",
        description="Searches Wikipedia for information based on a query.",
        arguments=[
            ToolArgument(
                name="query",
                type="string",
                description="The search term to query on Wikipedia.",
            )
        ],
    )

    agent.register(wikipedia_tool, use_wikipedia)

    agent.register(shell_command_tool, execute_shell_command)

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

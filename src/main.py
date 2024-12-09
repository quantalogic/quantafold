from core.agent import Agent
from core.generative_model import GenerativeModel
from tools.wikipedia import use_wikipedia


def main() -> None:
    model = GenerativeModel(model="ollama/qwen2.5-coder:14b")
    agent = Agent(model=model)
    agent.register("search_wikipedia",use_wikipedia)
    print("Ask a question:")
    response = agent.execute(input())
    print(response)


if __name__ == "__main__":
    main()

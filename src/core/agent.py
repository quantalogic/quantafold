# src/react/agent.py
import json
import logging
from typing import Callable

from .enums import Name
from .generative_model import GenerativeModel
from .models import Choice, Message
from .tool import Tool

logger = logging.getLogger(__name__)

class Agent:
    def __init__(self, model: GenerativeModel) -> None:
        self.model = model
        self.tools: dict[Name, Tool] = {}
        self.messages: list[Message] = []
        self.query = ""
        self.max_iterations = 5
        self.current_iteration = 0
        self.prompt_template = self.load_template()

    def load_template(self) -> str:
        return """
        You are a ReAct (Reasoning and Acting) agent tasked with answering the following query:

        Query: {query}

        Your goal is to reason about the query and decide on the best course of action to answer it accurately.

        Previous reasoning steps and observations: {history}

        Available tools: {tools}

        Instructions:
        1. Analyze the query, previous reasoning steps, and observations.
        2. Decide on the next action: use a tool or provide a final answer.
        3. Respond in the following JSON format:

        If you need to use a tool:
        {{
            "thought": "Your detailed reasoning about what to do next",
            "action": {{
                "name": "Tool name (wikipedia, google, serpapi, or none)",
                "reason": "Explanation of why you chose this tool",
                "input": "Specific input for the tool, if different from the original query"
            }}
        }}

        If you have enough information to answer the query:
        {{
            "thought": "Your final reasoning process",
            "answer": "Your comprehensive answer to the query"
        }}

        Remember:
        - Be thorough in your reasoning.
        - Use tools when you need more information.
        - Always base your reasoning on the actual observations from tool use.
        - If a tool returns no results or fails, acknowledge this and consider using a different tool or approach.
        - Provide a final answer only when you're confident you have sufficient information.
        - If you cannot find the necessary information after using available tools, admit that you don't have enough information to answer the query confidently.
        """

    def register(self, name: Name, func: Callable[[str], str]) -> None:
        self.tools[name] = Tool(name, func)

    def trace(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))

    def get_history(self) -> str:
        return "\n".join([f"{msg.role}: {msg.content}" for msg in self.messages])

    def think(self) -> None:
        self.current_iteration += 1
        if self.current_iteration > self.max_iterations:
            logger.warning("Reached maximum iterations. Stopping.")
            return
        prompt = self.prompt_template.format(
            query=self.query,
            history=self.get_history(),
            tools=", ".join([str(tool.name) for tool in self.tools.values()]),
        )
        response = self.ask_llm(prompt)
        self.trace("assistant", f"Thought: {response}")
        self.decide(response)

    def decide(self, response: str) -> None:
        try:
            parsed_response = json.loads(response.strip().strip("`").strip())
            if "action" in parsed_response:
                action = parsed_response["action"]
                tool_name_str = action["name"].upper()
                if tool_name_str not in Name.__members__:
                    raise ValueError(f"Unsupported tool: {tool_name_str}")
                tool_name = Name[tool_name_str]
                self.act(tool_name, action.get("input", self.query))
            elif "answer" in parsed_response:
                self.trace("assistant", f"Final Answer: {parsed_response['answer']}")
            else:
                raise ValueError("Invalid response format")
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            self.think()

    def act(self, tool_name: Name, query: str) -> None:
        tool = self.tools.get(tool_name)
        if tool:
            result = tool.use(query)
            observation = f"Observation from {tool_name}: {result}"
            self.trace("system", observation)
            self.think()
        else:
            logger.error(f"No tool registered for choice: {tool_name}")
            self.think()

    def execute(self, query: str) -> str:
        self.query = query
        self.think()
        final_answers = [
            msg.content
            for msg in self.messages
            if msg.role == "assistant" and "Final Answer" in msg.content
        ]
        return (
            final_answers[-1].split("Final Answer: ")[-1]
            if final_answers
            else "Unable to provide an answer."
        )

    def ask_llm(self, prompt: str) -> str:
        response = self.model.generate(prompt)
        return response.content

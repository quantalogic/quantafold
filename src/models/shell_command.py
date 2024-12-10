from models.tool import Tool, ToolArgument

shell_command_tool = Tool(
    name="shell_command",
    description="Execute a shell command and return its output",
    arguments=[
        ToolArgument(
            name="command",
            type="string",
            description="The shell command to execute"
        )
    ]
)

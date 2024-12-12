
def  output_format() -> str:
    return """
### Format 1 - If you need to use a tool, or you are planning to use a tool:
```xml
<response>
    <thought>
        <reasoning> ... bases on the query, history and observations explain your reasoning ...</reasoning>
        <plan>
            - [X] Task 1, done with success
            - [ ] Task 2 to be done
            - [ ] Task 3 to be done
        </plan>
    </thought>
    <!-- action is mandatory with this format-->
    <action>
        <tool_name>EXACT_TOOL_NAME</tool_name>
        <!-- use CDATA to handle special characters in reason and arguments -->
        <!-- reason is mandatory -->
        <reason><![CDATA[Brief explanation of why you chose this tool]]></reason>
        <!-- arguments is mandatory -->
        <arguments>
            <!-- arg is mandatory an must have name and value, multiple args are allowed -->
            <arg>
                <name>argument_name</name>
                <value><![CDATA[argument_value]]></value>
            </arg>
            <!-- Additional arguments as needed -->
        </arguments>
    </action>
</response>
```

### Format 2 - If you have enough information to answer and all the steps are completed,
VERY IMPORTANT: ONLY USE THIS IF THE GOAL IS FULLY COMPLETED:
```xml
<response>
    <!-- thought is mandatory -->
    <!-- use CDATA to handle special characters in thought and answer -->
    <thought><![CDATA[Your reasoning about why you can now answer the query]]></thought>
    <!-- answer is mandatory -->
    <!- answer is mandatory with this format-->
    <answer><![CDATA[Your final answer to the query, prefer Markdown format if the format is not defined in the query]]></answer>
</response>
```

DO NOT include any text before or after the XML object. The response must be well-formed XML.

"""

def query_template() -> str:
    return """

# Goal to achieve:

You are a ReAct (Reasoning and Acting) agent tasked to achieve the following goal:

## Query to solve:

<query><![CDATA[
{query}
]]></query>

## Session History:

<history><![CDATA[
{history}
]]></history>

- Current iteration: {current_iteration}
- Max iterations: {max_iterations}
- You have {remaining_iterations} iterations left.

## Available tools:

Here are examples of how to use the available tools:

<available_tools>
<![CDATA[
{tools}
]]>
</available_tools>

## Instructions:

1. Analyze the query, previous reasoning steps, and observations in history and decide on the best course of action to answer it accurately.
2. Decide on the next action: use a tool or provide a final answer.
3. You must answer in less than {max_iterations} iterations.
4. You MUST respond with ONLY a valid XML object in one of these two formats:

{output_format}
"""

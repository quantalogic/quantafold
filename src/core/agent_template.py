import datetime
import os


def output_format() -> str:
    return """
#### Format 1 - If you need to use a tool, or you are planning to use a tool:
```xml
<response>
    <thought>
        <reasoning> ... bases on the query, history and observations explain your reasoning ...</reasoning>
        <to_do>
            <!- list of the envisioned steps to do to answer the query -->
            <step>
                <!-- name is mandatory, snake_case -->
                <name>step_name</name>
                <!-- description is mandatory -->
                <description><![CDATA[description of the step]]></description>
                <reason><![CDATA[explanation of why you chose this step]]></reason>
                <depends_on_steps>
                    <!-- list of the previous steps where result can be useful for this step -->
                    <step_name>step_name</step_name>
                    <!-- Additional step names as needed -->
                </depends_on_steps>
            </step>
            <!-- Additional steps as needed -->
        </to_do>
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

#### Format 2 - If you have enough information to answer, and all the steps are done:
BEFORE USING THIS FORMAT, MAKE SURE YOU HAVE DONE ALL THE STEPS IN THE PLAN AND YOU HAVE ENOUGH INFORMATION TO ANSWER THE QUERY.
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


def query_template(
    query: str,
    history: str,
    current_iteration: int,
    max_iterations: int,
    remaining_iterations: int,
    tools: str,
    output_format: str,
    done_steps: str = "",
) -> str:
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    operating_system = os.uname().sysname
    current_shell = os.environ.get("SHELL", "N/A")
    return f"""
# Goal to achieve:

You are a ReAct (Reasoning and Acting) agent tasked to achieve the following goal:

## Query to solve:

<query><![CDATA[
{query}
]]></query>

### Environment:

Current date: {current_date}
Operating System: {operating_system}
Shell: {current_shell}

### Session History:

<history><![CDATA[
{history}
]]></history>

<steps_done>
<![CDATA[{done_steps}]]>
</steps_done>

### Context:

- Current iteration: {current_iteration}/{max_iterations}
- Remaining iterations: {remaining_iterations}

### Available Tools:

<available_tools>
<![CDATA[
{tools}
]]>
</available_tools>

### Instructions:

1. Analyze the query, history and completed steps to determine the best course of action
2. Create a structured plan if needed
3. Either:
   - Use a tool to gather more information
   - Provide a final answer if you have sufficient information
4. Response must be within {max_iterations} iterations
5. Format response as valid XML using one of the formats below:

### Output Format:

{output_format}
"""

import datetime
import os


def output_format() -> str:
    return """
#### Format 1 - If you need to use a tool, or you are planning to use a tool:
```xml
<response>
    <thought>
        <reasoning>
            - Reformulate the goal
            - Review the past Toughts in <history>, to see what has been done to achieve the goal
            - Identify the next steps to take
            - Rewrite the plan if necessary, including the steps from the previous iteration taken from <history>
            - Provide reasoning for each step
            - Ensure that the steps are in a logical order
            - Clearly state the dependencies between steps
            - Clearly state the final goal
            - Ensure that the final goal is achievable with the steps provided
            - Ensure that the final goal is a valid answer to the query
            - Ensure that the final goal is clearly stated
        </reasoning>
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
        <done>
            <!-- list of the completed steps with results -->
            <step>
                <!-- name is mandatory, snake_case -->
                <name>step_name</name>
                <!-- description is mandatory -->
                <description><![CDATA[description of the step]]></description>
                <reason><![CDATA[explanation of why you chose this step]]></reason>
                <!-- result is optional -->
                <result><![CDATA[summary of the result]]></result>
                <!-- depends_on_steps is optional -->
                <depends_on_steps>
                    <!-- list of the previous steps where result can be useful for this step -->
                    <step_name>step_name</step_name>
                    <!-- Additional step names as needed -->
                </depends_on_steps>
            </step>
            <!-- Additional steps as needed -->
        </done>
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
                <!-- use CDATA to handle special characters in value -->
                <value>![CDATA[ ... the value of the argument ... ]]</value>
            </arg>
            <!-- Additional arguments as needed -->
        </arguments>
    </action>
</response>

Example:

<response>
    <thought>
        <reasoning>
            - Reformulate the goal
            - Review the past Toughts in <history>, to see what has been done to achieve the goal
        </reasoning>
        <to_do>
            <step>
                <name>step_1</name>
                <description><![CDATA[Do something]]></description>
                <reason><![CDATA[Because I need to]]></reason>
            </step>
        </to_do>
        <done>
            <step>
                <name>step_2</name>
                <description><![CDATA[Did something]]></description>
                <reason><![CDATA[Because I needed to]]></reason>
                <result><![CDATA[Something was done]]></result>
            </step>
        </done>
    </thought>
    <action>
        <tool_name>shell_command</tool_name>
        <reason><![CDATA[To execute a command]]></reason>
        <arguments>
            <arg>
                <name>command</name>
                <value><![CDATA[ls -l /tmp]]></value>
            </arg>
        </arguments>
    </action>
</response>

```

#### Format 2 - Only use format this if the goal is completed, be sure to provide a final answer:
```xml
<response>
    <!-- thought is mandatory -->
    <!-- use CDATA to handle special characters in thought and answer -->
    <thought><![CDATA[Your reasoning about why you can now answer the query]]></thought>
    <!-- final_answer is mandatory -->
    <!- final_answer is mandatory with this format-->
    <final_answer><![CDATA[Your final answer to the query, prefer Markdown format if the format is not defined in the query]]></final_answer>
</response>
```
VERY IMPORTANT:

- <action> or <final_answer> must be included in the response, but not both.
- The response must be well-formed XML.

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
   - Use a tool to gather more information, perform an action, or achieve the goal
   - Provide a final answer if you have sufficient information
4. Response must be within {max_iterations} iterations
5. Format response as valid XML using one of the formats below:
6. If you need a tool and you get the information you need, vary the tool_name and arguments as needed

### Output Format:

{output_format}

### Session History:

<history>
{history}
</history>

### Context:

- Current iteration: {current_iteration}/{max_iterations}
- Remaining iterations: {remaining_iterations}

"""

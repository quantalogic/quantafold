import datetime
import os

EXAMPLE_FORMAT = """
<response>
    <thought>
        <reasoning>
            - The goal is to utilize a tool to gather weather information based on user preferences.
            - Reviewing past thoughts in <history>, I noticed that the user wants the weather forecast for their location.
            - The next step involves fetching the current weather data using an appropriate tool.
            - I need to ensure that the chosen tool can access live weather data and is compatible with our current system.
            - Each step in the plan will be clearly stated along with dependencies.
            - The final goal is to present the user with the most accurate weather information.
        </reasoning>
        <to_do>
            <step>
                <name>get_weather_data</name>
                <description><![CDATA[Fetch the current weather data for the user's location]]></description>
                <reason><![CDATA[Using a weather API to get real-time data is essential for accuracy]]></reason>
                <depends_on_steps>
                    <step_name>resolve_user_location</step_name>
                </depends_on_steps>
            </step>
        </to_do>
        <done>
            <step>
                <name>resolve_user_location</name>
                <description><![CDATA[Determine the user's current location based on their profile]]></description>
                <reason><![CDATA[Knowing the user's location is crucial for fetching relevant weather information]]></reason>
            </step>
        </done>
    </thought>
    <action>
        <step_name>get_weather_data</step_name>
        <tool_name>WeatherAPI</tool_name>
        <reason><![CDATA[Chosen for its reliability and accuracy in providing weather data]]></reason>
        <arguments>
            <location><![CDATA[$resolve_user_location$]]></location>
            <units><![CDATA[metric]]></units>
        </arguments>
    </action>
</response>
"""


def output_format() -> str:
    return """
#### Format 1 - If you need to use a tool, or you are planning to use a tool:
```xml
<response>
    <thought>
        <reasoning>
            - Reformulate the goal, ensure that the final goal is clearly stated
            - Review the past Toughts in <history>, to see what has been done to achieve the goal
            - Identify the next steps to take
            - Rewrite the plan if necessary, including the steps from the previous iteration taken from <history>
            - Provide reasoning for each step
            - Ensure that the steps are in a logical order
            - Clearly state the dependencies between steps
            - Clearly state the final goal
            - Ensure that the final goal is achievable with the steps provided
            - Ensure that the final goal is a valid answer to the query
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
            <step_name>step_name</step_name>
            <tool_name>EXACT_TOOL_NAME</tool_name>
            <reason><![CDATA[Brief explanation of why you chose this tool]]></reason>
            <arguments>
                <!-- Variable interpolation allows referencing results from previous steps -->
                <!-- Format: $step_name$ will be replaced with the output of that step -->
                <!-- Examples:
                     - $read_file_step$ : Gets content from a previous file read step
                     - $api_response.data$ : Accesses the 'data' field from an API response
                     - $extract_value.result$ : Gets the 'result' from an extraction step
                -->
                <argument1><![CDATA[Hello $previous_step$]]></argument1>
                <argument2><![CDATA[Path: $file_read.path$]]></argument2>
            </arguments>
        </action>
</response>

Example for arguments:

```xml
<arguments>
    <name><![CDATA[value]]></name>
    <temperature><![CDATA[0.7]]></temperature>
</arguments>
```

#### Format 2 - Only use format this if the goal is completed, be sure to provide a final answer:
```xml
<response>
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

""" + """
Example format:
""" + EXAMPLE_FORMAT


def query_template(
    query: str,
    history: str,
    current_iteration: int,
    max_iterations: int,
    remaining_iterations: int,
    tools: str,
    output_format: str,
    done_steps: str = "",
    step_result_variables: str = "",
) -> str:
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    operating_system = os.uname().sysname
    current_shell = os.environ.get("SHELL", "N/A")
    return (
        f"""
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

### Variables from previous steps:

<step_result_variables>
{step_result_variables}
</step_results_variables>

### Using variables from previous steps:

Variables from previous steps can be used in your tool arguments using $step_name$ syntax.

For example:

1. If a step named "get_weather" returned the value "sunny":

    Example:
    <step_result_variables>
        <get_weather><![CDATA[sunny]]></get_weather>
    </step_result_variables>
 
    - You can use $get_weather$ in your next tool arguments
   - It will be replaced with "sunny"

2. Complete example with multiple variables:
   ```xml
   <action>
       <tool_name>create_report</tool_name>
       <reason><![CDATA[Generate weather report for user]]></reason>
       <arguments>
           <user><![CDATA[$get_user_name$]]></user>
           <weather><![CDATA[$get_weather$]]></weather>
           <temperature><![CDATA[$get_temperature$]]></temperature>
       </arguments>
   </action>
   ```

### Instructions:

1. Analyze the query, history and completed steps to determine the best course of action
2. Create a structured plan if needed
3. Take one of these actions:
   a. Use a tool to gather information or perform an action
   b. Provide final answer if goal is achieved
   c. Use variables from previous steps in tool arguments

4. Response must be within {max_iterations} iterations
5. Format response as valid XML following the output format below
6. Adapt tool usage based on results and needs

### Session History:

<history>
{history}
</history>

### Context:

- Current iteration: {current_iteration}/{max_iterations}
- Remaining iterations: {remaining_iterations}

### Output Format:
{output_format}

"""
    )

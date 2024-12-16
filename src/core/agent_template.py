import datetime
import os

EXAMPLE_FORMAT = """

Example of Format with Action Using a Tool:

```xml
<response>
    <thought>
        <reasoning>
            - The goal is to utilize a tool to gather weather information based on user preferences.
            - Reviewing past thoughts in <history>, I noticed that the user wants the weather forecast for their location.
            - The next step involves fetching the current weather data using an appropriate tool.
            - I need to ensure that the chosen tool can access live weather data and is compatible with our current system.
            - Each step in the plan will be clearly stated along with dependencies.
            - The final goal is to present the user with the most accurate weather information.
            - The final goal is achievable with the steps provided but not yet completed.
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
```

Example of Format with Final Answer:

```xml
<response>
    <thought><![CDATA[The user's query has been successfully resolved by providing the current weather forecast for their location.]]></thought>
    <final_answer><![CDATA[The current weather in New York is 25°C with clear skies.]]></final_answer>
</response>
```

"""


def output_format() -> str:
    return (
        """
#### Format 1 - If you need to use a tool, or you are planning to use a tool (action is mandatory)
```xml
<response>
    <thought>
        <reasoning>
            - Clearly define the final goal.
            - Review the past Toughts in <history>, to see what has already be been done to achieve the goal.
            - Assess whether the goal has been achieved. If not, outline the next steps.
            - Revise the action plan as necessary, incorporating learnings from <history>.
            - Justify each step's inclusion logically.
            - Ensure steps follow a logical sequence.
            - Clearly state the dependencies between steps.
            - Confirm the final goal is realistic and answerable.
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
            <step_name>step_name</step_name>A
            <!-- the tool_name is mandatory, and must be present in <available_tools> -->
            <tool_name>EXACT_TOOL_NAME</tool_name>
            <reason><![CDATA[
                - Brief explanation of why you chose this tool
                - Identify candidate interpolation variables names from previous steps
            ]]>
            </reason>
            <arguments>
                <!-- Variable interpolation allows referencing results from previous steps -->
                <!-- Variable interpolation MUST be used if the tool requires input from previous steps -->
                <!-- Format: $step_name$ will be replaced with the output of that step -->
                <!-- don't be lazy, you must provide the full content of the argument or you must use interpolated variables -->
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
```

#### Format 2 - Use this format if the goal is fully completed, be sure to provide a final answer (final_answer is mandatory):
```xml
<response>
    <thought><![CDATA[Your reasoning about why you can now answer the query]]></thought>
    <!-- final_answer is mandatory -->
    <!- final_answer is mandatory with this format-->
    <final_answer><![CDATA[Your final answer to the query, prefer Markdown format if the format is not defined in the query]]></final_answer>
</response>
```
### Key Points to Remember:

- Include either <action> or <final_answer>, but not both.
- Ensure that the XML is well-formed and adheres to the specified structure.
- Do not add any text before or after the XML; responses must be a valid XML format.

"""
        + """

Example of formats:

"""
        + EXAMPLE_FORMAT
    )


def query_template(
    query: str,
    history: str,
    current_iteration: int,
    max_iterations: int,
    remaining_iterations: int,
    tools: str,
    output_format: str,
    step_result_variables: str = "",
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

### Variables from previous steps:

<step_result_variables>
{step_result_variables}
</step_results_variables>

### Using variables from previous steps:

You can use results from previous steps in your tool arguments using the $step_name$ syntax.
The value will be automatically replaced with the actual result when the tool is executed.

Examples of variable interpolation:

1. Simple variable usage:
   ```xml
   <step_result_variables>
       <read_file>Hello World!</read_file>
   </step_result_variables>

   <action>
       <tool_name>PROCESS_TEXT</tool_name>
       <arguments>
           <text><![CDATA[$read_file$]]></text>
       </arguments>
   </action>
   ```

2. Multiple variables in one argument:
   ```xml
   <step_result_variables>
       <get_name>John</get_name>
       <get_age>30</get_age>
   </step_result_variables>

   <action>
       <tool_name>CREATE_PROFILE</tool_name>
       <arguments>
           <content><![CDATA[Name: $get_name$, Age: $get_age$]]></content>
       </arguments>
   </action>
   ```

3. Variables with additional text:
   ```xml
   <step_result_variables>
       <fetch_path>/home/user/</fetch_path>
       <get_filename>data.txt</get_filename>
   </step_result_variables>

   <action>
       <tool_name>READ_FILE</tool_name>
       <arguments>
           <filepath><![CDATA[$fetch_path$$get_filename$]]></filepath>
       </arguments>
   </action>
   ```

Important:
- Always use <![CDATA[...]]> around argument values
- Variables must exist in step_result_variables
- Variable names are case-sensitive

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

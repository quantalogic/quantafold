from bs4 import BeautifulSoup

from .response import Action, Response, Step, Thought


class ResponseBs4XmlParser:
    """Utility class to parse XML and create a Response object."""

    @staticmethod
    def parse(xml_data: str) -> Response:
        """Parse XML string to create a Response object.

        Args:
            xml_data (str): XML string representation of the Response.

        Returns:
            Response: A Pydantic Response object.

        Raises:
            ValueError: If the XML data is malformed or cannot be converted into a Response.
        """
        try:
            # Use BeautifulSoup to parse the XML data
            soup = BeautifulSoup(xml_data, "xml")

            # Extract thought details
            thought_elem = soup.find("thought")
            reasoning = thought_elem.find("reasoning").get_text()

            # Extract to_do steps
            to_do_steps = []
            to_do_elem = thought_elem.find("to_do_steps") or thought_elem.find("to_do")
            for step in to_do_elem.find_all("step"):
                to_do_steps.append(
                    Step(
                        name=step.find("name").get_text()
                        if step.find("name")
                        else step.find("n").get_text(),
                        description=step.find("description").get_text(),
                        reason=step.find("reason").get_text(),
                        result=step.find("result").get_text()
                        if step.find("result")
                        else step.find("r").get_text()
                        if step.find("r")
                        else None,
                        depends_on_steps=[
                            dep.get_text()
                            for dep in (
                                step.find("depends_on_steps") or step.find("depends_on")
                            ).find_all("step_name")
                        ]
                        if step.find("depends_on_steps") or step.find("depends_on")
                        else [],
                    )
                )

            # Extract done steps
            done_steps = []
            done_elem = thought_elem.find("done_steps") or thought_elem.find("done")
            for step in done_elem.find_all("step"):
                done_steps.append(
                    Step(
                        name=step.find("name").get_text()
                        if step.find("name")
                        else step.find("n").get_text(),
                        description=step.find("description").get_text(),
                        reason=step.find("reason").get_text(),
                        result=step.find("result").get_text()
                        if step.find("result")
                        else step.find("r").get_text()
                        if step.find("r")
                        else None,
                        depends_on_steps=[
                            dep.get_text()
                            for dep in (
                                step.find("depends_on_steps") or step.find("depends_on")
                            ).find_all("step_name")
                        ]
                        if step.find("depends_on_steps") or step.find("depends_on")
                        else [],
                    )
                )

            # Extract action details
            action_elem = soup.find("action")
            tool_name = action_elem.find("tool_name").get_text()
            reason = action_elem.find("reason").get_text()
            arguments = {}
            for arg in action_elem.find("arguments").find_all("arg"):
                arguments[arg.find("name").get_text()] = arg.find("value").get_text()

            # Create Response object
            response_data = Response(
                thought=Thought(
                    reasoning=reasoning,
                    to_do=to_do_steps,
                    done=done_steps,
                ),
                action=Action(
                    tool_name=tool_name,
                    reason=reason,
                    arguments=arguments,
                ),
            )

            # Return the validated Response object
            return response_data

        except Exception as e:
            raise ValueError("Error parsing XML data.") from e


# Example usage
if __name__ == "__main__":
    xml_example = """
    <x>
    XXX
    <response>
    <thought>
        <reasoning>Based on the analysis, the steps required are clear.</reasoning>
        <to_do>
            <step>
                <n>gather_data</n>
                <description>Collect relevant data from the database.</description>
                <reason>Data is necessary for the analysis.</reason>
                <r>Data gathered successfully.</r>
                <depends_on>
                    <step_name>initialize</step_name>
                </depends_on>
        </to_do>
        <done>
            <step>
                <n>initialize</n>
                <description>Initialize the database connection.</description>
                <reason>Connection required to gather data.</reason>
                <r>Database connection established.</r>
                <depends_on/>
            </step>
        </done>
    </thought>
    <action>
        <tool_name>data_collector</tool_name>
        <reason>Selected for its efficiency in gathering large data sets.</reason>
        <arguments>
            <arg>
                <name>database</name>
                <value>main_db</value>
            </arg>
            <arg>
                <name>limit</name>
                <value>100</value>
            </arg>
        </arguments>
    </action>
</response>"""

    try:
        response_obj = ResponseBs4XmlParser.parse(xml_example)
        print(response_obj.model_dump_json(indent=2))
    except ValueError as e:
        print(f"Error: {e}")

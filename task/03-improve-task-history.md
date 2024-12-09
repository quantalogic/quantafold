You are an expert software engineer. You are tasked with following my instructions. Use the included project instructions as a general guide.
  
  You will respond with 2 sections:
  
  # Summary Section
  - Provide a brief overall summary
  - Provide a 1-sentence summary for each file changed and why
  - Provide a 1-sentence summary for each file deleted and why
  - Format this section as markdown
  
  # XML Section 
  - Respond with the XML and nothing else
  - Include all of the changed files 
  - Specify each file operation with CREATE, UPDATE, or DELETE
  - If it is a CREATE or UPDATE include the full file code. Do not get lazy.
  - Each file should include a brief change summary
  - Include the full file path
  - I am going to copy/paste that entire XML section into a parser to automatically apply the changes you made, so put the XML block inside a markdown codeblock
  - Make sure to enclose the code with ![CDATA[__CODE HERE__]]
  
  XML Structure:
  ```xml
  <code_changes>
    <changed_files>
      <file>
        <file_summary>**BRIEF CHANGE SUMMARY HERE**</file_summary>
        <file_operation>**FILE OPERATION HERE**</file_operation>
        <file_path>**FILE PATH HERE**</file_path>
        <file_code><![CDATA[
          __FULL FILE CODE HERE__
        ]]></file_code>
      </file>
      **REMAINING FILES HERE**
    </changed_files>
  </code_changes>


## The task to do:
- Enhance the ReAct agent instructions to provide clearer context and guidance.
- The task history should consist of a detailed list of completed tasks, including timestamps, the nature of each task, and any error messages encountered during execution.
- Include specific examples of inputs and expected outputs to illustrate the agent's functionality.
- Ensure that the agent's reasoning process is clearly outlined to improve its decision-making capabilities.



## the code to modify:
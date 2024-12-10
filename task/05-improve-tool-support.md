You are an expert software engineer. You are tasked with following my instructions. Use the included project instructions as a general guide.
  
  You will respond with 3 sections:

  # Thinking Section
   
   In <thinking> section:
   - Rephrase the task in a way that is more clear to you
   - Propose 3 to 4 different ways to approach the task with pro and cons of each approach
   - Display in a table the approach and its pro and cons
   - Choose the approach that you think is the best for the task
   - Explain why you think this approach is the best
  
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

- Improve the way tools are described in the code. Today the description is seperated from function that implements it.
- We want to integrate the implementation of the function directly with the tool description in the pydantic class
- The xml block is an example of how each tool is described in the generation prompt is not provided.

Propose a better implementation.




## the code to modify:
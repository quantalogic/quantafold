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

  Replace the JSON generation by the agent and json extraction by the agent with XML generation and XML extraction.
  Make the XML generation and XML extraction as close as possible to the JSON generation and JSON extraction.
  Make the extraction very safe en resilient to errors.
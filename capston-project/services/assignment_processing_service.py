import streamlit as st
import re
from typing import Dict

# This prompt is for LLM to generate assignment content
def generate_assignment_creation_prompt(topic: str, difficulty: str, time_limit: int) -> str:
    """Generate the prompt for LLM coding assignment creation."""
    return f"""Create a high-quality coding assignment about {topic} for a {difficulty.lower()} level student that can be completed in approximately {time_limit} minutes.

Please format your response EXACTLY as follows, including the ```python and ``` markers for code blocks:

<title>
[Provide a concise, descriptive title for the assignment]
</title>

<background>
[Provide a brief background about the topic and its importance. Explain the problem clearly.]
</background>

<requirements>
[Provide a detailed, numbered list of functional and non-functional requirements for the solution.]
1. Requirement one.
2. Requirement two.
</requirements>

<hints>
[Provide 1-3 helpful hints that guide the student without giving away the solution directly.]
1. Hint one.
</hints>

<code_template>
```python
# Start with this Python code template
[Provide a basic Python code structure, function definition, or class to get the student started. Include comments where appropriate.]

# Example:
def solve_problem(input_data):
    # Your code here
    pass

if __name__ == '__main__':
    # Example usage or test case
    # result = solve_problem(some_input)
    # print(result)
    pass
```
</code_template>

<expected_output>
```
[Provide a clear example of the expected output or behavior of the correct solution. For console applications, show sample output. For functions, show example return values for given inputs.]

Example Output:
Input: [1, 2, 3]
Output: 6
```
</expected_output>

<evaluation_criteria>
[Explain how the submitted solution will be evaluated. Mention aspects like correctness, efficiency, code style (if applicable), and adherence to requirements.]
1. Correctness: Does the code produce the expected output for various test cases?
2. Adherence to requirements: Does the solution meet all specified requirements?
</evaluation_criteria>
"""

def parse_assignment_details(response: str) -> Dict[str, str]:
    """Parse the LLM response for assignment details into sections."""
    if not response:
        return {}
    
    sections = {
        "title": r'<title>(.*?)</title>',
        "background": r'<background>(.*?)</background>',
        "requirements": r'<requirements>(.*?)</requirements>',
        "hints": r'<hints>(.*?)</hints>',
        "code_template": r'<code_template>(.*?)</code_template>',
        "expected_output": r'<expected_output>(.*?)</expected_output>',
        "evaluation_criteria": r'<evaluation_criteria>(.*?)</evaluation_criteria>'
    }
    
    parsed_content = {}
    for key, pattern in sections.items():
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        parsed_content[key] = match.group(1).strip() if match else f"<{key}> section not found or format error."
    
    # Extract actual code from the code_template and expected_output sections
    if parsed_content.get("code_template") and "```python" in parsed_content["code_template"]:
        code_match = re.search(r'```python\s*(.*?)\s*```', parsed_content["code_template"], re.DOTALL)
        parsed_content["code_template_content"] = code_match.group(1).strip() if code_match else "# Error parsing code template."
    elif parsed_content.get("code_template"):
        # If markers are missing but it's the code_template section, assume all of it is code (less ideal)
        parsed_content["code_template_content"] = parsed_content["code_template"]
    else:
        parsed_content["code_template_content"] = "# No code template provided."

    if parsed_content.get("expected_output") and "```" in parsed_content["expected_output"]:
        output_match = re.search(r'```\s*(.*?)\s*```', parsed_content["expected_output"], re.DOTALL)
        parsed_content["expected_output_content"] = output_match.group(1).strip() if output_match else "# Error parsing expected output."
    elif parsed_content.get("expected_output"):
        parsed_content["expected_output_content"] = parsed_content["expected_output"]
    else:
        parsed_content["expected_output_content"] = "# No expected output provided."
        
    return parsed_content

# This prompt is for LLM to evaluate submitted code
def generate_code_evaluation_prompt(code: str, requirements: str, expected_output: str) -> str:
    """Generate the prompt for LLM code evaluation."""
    return f"""Please evaluate the following Python code solution for a coding assignment. 

ASSIGNMENT REQUIREMENTS:
{requirements}

EXPECTED OUTPUT / BEHAVIOR:
{expected_output}

PYTHON CODE TO EVALUATE:
```python
{code}
```

Provide a comprehensive review. Address the following points clearly:
1.  **Functionality**: Does the code work as expected based on the requirements? Does it produce the correct output?
2.  **Bugs/Errors**: Identify any syntax errors, runtime errors, or logical bugs.
3.  **Correctness**: How well does the solution address the problem stated in the requirements?
4.  **Suggestions for Improvement**: Offer specific advice on how the code could be improved (e.g., efficiency, readability, alternative logic, better use of Python features).
5.  **Alternative Approaches**: Briefly mention any alternative approaches or algorithms that could also solve the problem, perhaps more efficiently or elegantly.

Format your response using the following tags. Provide detailed information within each tag:
<verdict>Choose one: Yes / No / Partially (Does it broadly work?)</verdict>
<analysis>
[Your detailed analysis covering functionality, bugs, errors, and correctness.]
</analysis>
<improvements>
[Your specific suggestions for improvement and alternative approaches.]
</improvements>
"""

def parse_code_evaluation(evaluation: str) -> Dict[str, str]:
    """Parse the LLM response for code evaluation into sections."""
    if not evaluation:
        return {}
    
    verdict_match = re.search(r'<verdict>(.*?)</verdict>', evaluation, re.DOTALL | re.IGNORECASE)
    analysis_match = re.search(r'<analysis>(.*?)</analysis>', evaluation, re.DOTALL | re.IGNORECASE)
    improvements_match = re.search(r'<improvements>(.*?)</improvements>', evaluation, re.DOTALL | re.IGNORECASE)
    
    return {
        "verdict": verdict_match.group(1).strip() if verdict_match else "Unknown",
        "analysis": analysis_match.group(1).strip() if analysis_match else "Analysis not found or format error.",
        "improvements": improvements_match.group(1).strip() if improvements_match else "No specific improvements suggested or format error."
    } 
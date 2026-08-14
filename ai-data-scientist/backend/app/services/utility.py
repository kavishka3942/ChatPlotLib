def clean_python_code(code: str):

    code = code.strip()

    # remove markdown fences
    if code.startswith("```"):
        
        lines = code.splitlines()

        # remove first line ```python
        if lines[0].startswith("```"):
            lines = lines[1:]

        # remove last ```
        if lines[-1].strip() == "```":
            lines = lines[:-1]

        code = "\n".join(lines)

    return code.strip()
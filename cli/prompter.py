def build_prompt(code: str, language: str, mode: str) -> str:
    if not code or not code.strip():
        raise ValueError("The 'code' parameter cannot be empty.")
    if not language or not language.strip():
        raise ValueError("The 'language' parameter cannot be empty.")
    
    valid_modes = {"bugs", "security", "full"}
    if mode not in valid_modes:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of {valid_modes}.")

    if mode == "bugs":
        instructions = (
            "Focus ONLY on finding functional bugs. Fill the BUGS section. "
            "For the SECURITY and SUMMARY sections, write EXACTLY 'None found'."
        )
    elif mode == "security":
        instructions = (
            "Focus ONLY on finding security vulnerabilities. Fill the SECURITY section. "
            "For the BUGS section, write EXACTLY 'None found'. Write a brief SUMMARY of your security findings."
        )
    else:
        instructions = (
            "Perform a comprehensive review. Fill out the BUGS, SECURITY, "
            "and SUMMARY sections based on your findings."
        )

    prompt = f"""You are an expert offline code reviewer analyzing {language} code.
{instructions}

You MUST respond EXACTLY in this format:

BUGS:
- Line N: <description>
(or "None found")

SECURITY:
- <VULN_TYPE>: <description>
(or "None found")

SUMMARY:
<one paragraph>

--- CODE ---
{code}
"""
    return prompt
"""
YAML Validation & Sanitization Utilities for the BYOA Onboarding Wizard.

Handles:
- Stripping markdown code fences from raw LLM output
- Validating CV YAML against expected RenderCV schema
- Validating filtering YAML against expected config schema
- Merging user-provided config with safe defaults
- Extracting CV filename from parsed data
"""
import re
import os
import yaml


def clean_yaml_input(raw_text: str) -> str:
    """
    Strips markdown code fences from raw LLM output before YAML parsing.
    
    [AGENT_NOTE]: LLMs habitually wrap output in ```yaml ... ``` even when instructed
    not to. This function intercepts that pattern to prevent fatal parse errors.
    """
    if not raw_text:
        return ""
    
    text = raw_text.strip()
    
    # Pattern: ```yaml\n...\n``` or ```yml\n...\n``` or just ```\n...\n```
    fence_pattern = r"^```(?:ya?ml)?\s*\n(.*?)```\s*$"
    match = re.match(fence_pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Edge case: multiple code blocks — take the first one
    multi_match = re.search(r"```(?:ya?ml)?\s*\n(.*?)```", text, re.DOTALL)
    if multi_match:
        return multi_match.group(1).strip()
    
    return text


def validate_cv_yaml(raw_text: str) -> tuple:
    """
    Validates pasted CV YAML against the expected RenderCV schema.
    
    Returns:
        (is_valid: bool, parsed_data: dict | None, error_message: str)
    """
    cleaned = clean_yaml_input(raw_text)
    
    if not cleaned:
        return False, None, "Input is empty. Please paste your generated YAML."
    
    # 1. Parse
    try:
        data = yaml.safe_load(cleaned)
    except yaml.YAMLError as e:
        # Extract line number from YAML error for user-friendly feedback
        line_info = ""
        if hasattr(e, 'problem_mark') and e.problem_mark:
            line_info = f" (line {e.problem_mark.line + 1}, column {e.problem_mark.column + 1})"
        return False, None, f"YAML Syntax Error{line_info}: {e.problem if hasattr(e, 'problem') else str(e)}"
    
    if not isinstance(data, dict):
        return False, None, "Invalid structure: Expected a YAML dictionary at the root level."
    
    # 2. Check required top-level key
    if "cv" not in data:
        return False, None, "Missing required key: `cv`. Your YAML must start with a `cv:` block."
    
    cv_block = data["cv"]
    if not isinstance(cv_block, dict):
        return False, None, "Invalid structure: `cv` must be a dictionary."
    
    # 3. Check for name
    if not cv_block.get("name"):
        return False, None, "Missing required field: `cv.name`. The AI should have extracted your full name."
    
    # 4. Check for sections
    sections = cv_block.get("sections")
    if not sections or not isinstance(sections, dict):
        return False, None, "Missing required field: `cv.sections`. Your CV must have at least one section (experience, education, etc.)."
    
    # 5. Check at least one meaningful section exists
    meaningful_sections = [k for k, v in sections.items() if v and (isinstance(v, list) and len(v) > 0)]
    if not meaningful_sections:
        return False, None, "All sections are empty. The AI should have populated at least experience or education."
    
    return True, data, ""


def validate_filtering_yaml(raw_text: str) -> tuple:
    """
    Validates pasted filtering YAML against the expected config schema.
    
    Returns:
        (is_valid: bool, parsed_data: dict | None, error_message: str)
    """
    cleaned = clean_yaml_input(raw_text)
    
    if not cleaned:
        return False, None, "Input is empty. Please paste your generated filtering config."
    
    # 1. Parse
    try:
        data = yaml.safe_load(cleaned)
    except yaml.YAMLError as e:
        line_info = ""
        if hasattr(e, 'problem_mark') and e.problem_mark:
            line_info = f" (line {e.problem_mark.line + 1}, column {e.problem_mark.column + 1})"
        return False, None, f"YAML Syntax Error{line_info}: {e.problem if hasattr(e, 'problem') else str(e)}"
    
    if not isinstance(data, dict):
        return False, None, "Invalid structure: Expected a YAML dictionary at the root level."
    
    # 2. Check for tiered_skills (the most critical block)
    tiered = data.get("tiered_skills")
    if not tiered or not isinstance(tiered, dict):
        return False, None, "Missing required key: `tiered_skills`. The AI should have categorized your skills into tier1, tier2, tier3."
    
    for tier_key in ["tier1", "tier2", "tier3"]:
        if tier_key not in tiered:
            return False, None, f"Missing `tiered_skills.{tier_key}`. All three tiers are required."
        if not isinstance(tiered[tier_key], list):
            return False, None, f"`tiered_skills.{tier_key}` must be a list of skill strings."
    
    # 3. Check for titles
    titles = data.get("titles")
    if not titles or not isinstance(titles, dict):
        return False, None, "Missing required key: `titles`. The AI should have generated title filters."
    
    if "high_priority" not in titles or not isinstance(titles.get("high_priority"), list):
        return False, None, "Missing `titles.high_priority` list."
    
    return True, data, ""


def merge_filtering_with_defaults(user_config: dict, defaults_path: str) -> dict:
    """
    Deep-merges user-provided filtering config with the .example defaults.
    
    User values override defaults for keys they provide.
    Missing top-level blocks (system, restrictions, filtering) are filled from defaults.
    """
    defaults = {}
    if os.path.exists(defaults_path):
        try:
            with open(defaults_path, "r", encoding="utf-8") as f:
                defaults = yaml.safe_load(f) or {}
        except Exception:
            defaults = {}
    
    # Start with defaults, then overlay user config
    merged = dict(defaults)
    
    for key, value in user_config.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            # Shallow merge for nested dicts (user overrides default sub-keys)
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    
    return merged


def extract_cv_filename(cv_data: dict) -> str:
    """
    Parses cv.name and returns a safe filename.
    
    Example: {"cv": {"name": "Jane Doe"}} → "Jane_Doe_CV.yaml"
    Fallback: "Master_CV.yaml"
    """
    try:
        name = cv_data.get("cv", {}).get("name", "")
        if not name or not isinstance(name, str):
            return "Master_CV.yaml"
        
        # Sanitize: keep only alphanumeric, spaces, hyphens
        safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "-")).strip()
        if not safe_name:
            return "Master_CV.yaml"
        
        # Replace spaces with underscores
        safe_name = safe_name.replace(" ", "_")
        return f"{safe_name}_CV.yaml"
    except Exception:
        return "Master_CV.yaml"

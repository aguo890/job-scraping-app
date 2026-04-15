"""
Onboarding Prompt Constants for the BYOA (Bring Your Own Agent) Wizard.

These are the exact prompts displayed to users in the onboarding dialog.
Users copy them into ChatGPT / Claude / DeepSeek along with their resume.
The AI generates YAML that the user pastes back into the app.

[AGENT_NOTE]: These prompts use "skeleton-first" prompting — providing the
complete schema as a fill-in-the-blanks template rather than describing it
in prose. This eliminates hallucinated extra keys and ensures the output
matches our exact parser expectations.
"""

CV_GENERATION_PROMPT = '''You are a resume-to-YAML converter. The user will attach their resume (PDF, DOCX, or image).
Extract ALL information and output it as a single YAML code block conforming EXACTLY to this schema.

STRICT RULES:
1. Output ONLY a single ```yaml code block. No explanations before or after.
2. ZERO hallucination — extract only what exists in the resume. Do not invent companies, titles, dates, or skills.
3. Bold all technical keywords in highlights using **keyword** markdown syntax.
4. Use action verbs to start every highlight bullet (Architected, Engineered, Developed, Deployed, etc.)
5. Quantify results wherever the resume provides numbers (e.g., "reducing latency by **40%**").
6. For dates, use the format: YYYY-MM (e.g., 2024-06) or "Present" for current roles.
   Date ranges use: "2024-06 – Present" or "2023-01 – 2024-06"

EXACT SCHEMA (fill in from the resume):

cv:
  name: "Full Name"
  location: "City, State"
  email: "email@example.com"
  phone: "+1 555-555-5555"
  website: https://yoursite.com
  social_networks:
  - network: LinkedIn
    username: your-linkedin-handle
  - network: GitHub
    username: your-github-handle
  sections:
    summary:
    - "A 1-2 sentence professional summary. Write one if the resume doesn't have one."
    experience:
    - company: "Company Name"
      position: "Job Title"
      location: "City, State"
      date: "YYYY-MM – YYYY-MM"
      highlights:
      - "Action verb + **bold keywords** + quantified result."
    education:
    - institution: "University Name"
      area: "Major / Field of Study"
      degree: "Bachelor of Science"
      date: "Expected YYYY-MM"
      location: "City, State"
    projects:
    - name: "Project Name"
      date: "YYYY-MM – Present"
      summary: "One-line summary with **bold tech stack**."
      highlights:
      - "Action verb + what you built + impact."
    skills:
    - label: "Languages"
      details: "Python, JavaScript, SQL, etc."
    - label: "Frameworks"
      details: "React, FastAPI, etc."
    - label: "Tools & Cloud"
      details: "Docker, AWS, Git, etc."
design:
  theme: sb2nov

If a section doesn't exist in the resume (e.g., no projects), omit that section entirely.
If a field doesn't exist (e.g., no website), omit that field.'''


FILTERING_GENERATION_PROMPT = '''You are a job search configuration generator. Based on the resume the user just converted (or will attach), generate a YAML configuration for an automated job scraping engine.

STRICT RULES:
1. Output ONLY a single ```yaml code block. No explanations before or after.
2. Infer the user's experience level from their resume to set appropriate title filters.
3. For tiered_skills, categorize the user's skills by proficiency:
   - tier1 (Foundation, +10 pts): Skills they use daily / list prominently
   - tier2 (Strong Signal, +20 pts): Skills they know well but aren't primary
   - tier3 (Ultra-Niche, +50 pts): Domain-specific or rare skills that make them uniquely qualified
4. For penalty_skills: List technologies that are completely outside their background
   (e.g., if they're a web dev, penalize FPGA, VHDL, Mechanical Engineering, etc.)
5. For locations: Infer from their resume's location where they'd want to work.
   Include their state/city plus major US tech hubs. Exclude all international locations.
6. DO NOT output the "system", "filtering", or "restrictions" blocks. Only output the blocks shown below.

EXACT SCHEMA (fill in based on the resume):

titles:
  high_priority:
  - Intern
  - New Grad
  - Entry Level
  - Junior
  exclude:
  - Senior
  - Staff
  - Principal
  - Lead
  - Director
  - Manager
  - VP
  - PhD
  - Doctorate
tiered_skills:
  tier1:
  - Python
  tier2:
  - React
  tier3:
  - "Niche Skill"
penalty_skills:
- Swift
- MATLAB
locations:
  include:
  - united states
  - usa
  - remote
  exclude:
  - asia
  - europe
  - canada

Adjust the experience-level title keywords based on their years of experience:
- If 0-2 YOE: high_priority should include [Intern, New Grad, Entry Level, Junior, Associate, Early Career, Rotation]
- If 3-5 YOE: high_priority should include [Mid-Level, Software Engineer, SDE, Developer]
- If 6+ YOE: high_priority should include [Senior, Staff, Lead, Principal]'''


# --- User-facing instructions displayed above the prompts ---

CV_PROMPT_INSTRUCTIONS = """### Step 1: Generate Your Master CV

1. **Copy** the prompt below
2. **Open** your AI assistant (ChatGPT, Claude, DeepSeek, etc.)
3. **Paste** the prompt and **attach your resume** (PDF, DOCX, or screenshot)
4. **Copy** the YAML output the AI generates
5. **Paste** it into the text box in Step 2
"""

FILTERING_PROMPT_INSTRUCTIONS = """### Generate Your Job Search Config

1. **Copy** the prompt below
2. **Paste** it into the same AI chat (it already has your resume context)
3. **Copy** the YAML output
4. **Paste** it into the text box below
"""

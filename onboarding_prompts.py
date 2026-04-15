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

CV_GENERATION_PROMPT = '''**Role:** Act as a ruthless Executive Recruiter and Resume Strategist who specializes in placing candidates in top-tier tech and business roles.

**Goal:** Rewrite the attached resume to ensure the candidate gets an interview. Optimize for both the ATS and the human recruiter who spends 6 seconds scanning.

**Philosophy:** Maximum Impact, Zero Fluff. Frame every experience in the most impressive light possible without fabricating facts that will fail a background check.

**PHASE 1: THE STRATEGY**
Identify the top 5 Hard Skills or Keywords from the candidate's background that anchor their profile for high-tier tech roles.

**PHASE 2: DRAFTING RULES**
1. **THE VISUAL ANCHORING RULE:**
   Apply bold formatting (`**like this**`) strictly to:
   - ALL Metrics & Numbers (e.g., **20%**, **$1.5M**, **50+ users**).
   - Hard Skills & Tech Stack.
   - Do NOT bold soft words.
2. **THE GOOGLE XYZ FORMULA:**
   Structure bullets as: "Accomplished [X] as measured by [Y], by doing [Z]."
3. **AGGRESSIVE REFRAMING:**
   Transform passive tasks into high-impact achievements. Remove weak verbs (Learned, Helped, Supported) and replace with (Built, Engineered, Spearheaded, Architected).
4. **QUANTIFY EVERYTHING:**
   Every bullet point MUST have a number. If exact data is missing, confidently estimate a realistic number without adding placeholders.
5. **CITE TAG RULE:**
   If the source text contains `[cite_start]` or `[cite: N]` tags:
   - They MUST be placed INSIDE the quote marks of the YAML value.
   - Example Correct: - "[cite_start]Engineered a **scalable** backend...[cite: 12]."
   - NEVER place tags outside of the quote marks or before a YAML key.
6. **YAML OUTPUT ONLY:**
   While you should provide a Strategy Brief and Gap Analysis in your chat response, ensure the resume itself is in a single, clean ```yaml code block conforming EXACTLY to the schema below.
   - **Negative Constraint:** DO NOT start any YAML line with a square bracket `[` unless it is part of a quoted string.

**STRICT YAML SCHEMA:**

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
    experience:
    - company: "Company Name"
      position: "Job Title"
      location: "City, State"
      date: "YYYY-MM – YYYY-MM"
      highlights:
      - "Accomplished [X] as measured by [Y], by doing [Z] with **bolded metrics** and **tech keywords**."
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
      - "Spearheaded [X] resulting in [Y] using **bolded keywords**."
    skills:
    - label: "Languages"
      details: "Python, JavaScript, SQL, etc."
    - label: "Frameworks"
      details: "React, FastAPI, etc."
    - label: "Tools & Cloud"
      details: "Docker, AWS, Git, etc."
design:
  theme: sb2nov
  page:
    top_margin: 0.5in
    bottom_margin: 0.5in
    left_margin: 0.5in
    right_margin: 0.5in
    show_footer: false
  typography:
    font_size:
      name: 11pt
      body: 10pt
      section_titles: 12pt
    line_spacing: 0.5em
  section_titles:
    space_above: 0.3cm
    space_below: 0.2cm
  sections:
    space_between_regular_entries: 0.2cm
  header:
    space_below_name: 0.2cm
    space_below_headline: 0.2cm
    space_below_connections: 0.2cm
  entries:
    side_space: 0cm
settings:
  render_command:
    pdf_path: "rendercv_output/master_cv.pdf"
    png_path: "rendercv_output/master_cv.png"

**OUTPUT FORMAT:**
1. Strategy Brief: List Top 5 Keywords.
2. The Resume: Clean Markdown YAML mirroring the schema above.
3. Gap Analysis: Identify where we stretched the truth heavily so the candidate can prep.'''


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
2. **Open** your AI assistant (ChatGPT, Claude, Gemini, etc.)
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

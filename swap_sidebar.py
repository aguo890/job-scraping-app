import sys

with open("job-scraping-app/pages/CV_Editor.py", "r") as f:
    lines = f.readlines()

# 1. Fix the newline issue from the previous step
for i, line in enumerate(lines):
    if line.strip() == "st.switch_page(\"dashboard.py\")# --- 4. Modular UI Components ---":
        lines[i] = '        st.switch_page("dashboard.py")\n\n# --- 4. Modular UI Components ---\n'
        break

# We need to extract Draft Management, Download Button, Reset Button up to Application Workflow
# and we need to extract Back to Dashboard

dashboard_btn_start = -1
dashboard_btn_end = -1
for i, line in enumerate(lines):
    if "if st.button(\"⬅️ Back to Dashboard\", width=\"stretch\"):" in line:
        dashboard_btn_start = i - 2 # including the st.divider()
        dashboard_btn_end = i + 6
        break

dashboard_lines = lines[dashboard_btn_start:dashboard_btn_end+1]

draft_start = -1
draft_end = -1
for i, line in enumerate(lines):
    if "# --- 📄 Draft Management ---" in line:
        draft_start = i
        break

for i, line in enumerate(lines):
    if "def mark_as_applied(target_id):" in line: # Application Workflow starts few lines before
        draft_end = i - 3
        break

draft_lines = lines[draft_start:draft_end+1]

# Where to insert draft_lines? Right after Job Info Header, which is before the original dashboard button.
# Where to insert dashboard_lines? At the very end of the sidebar, right before Modular UI Components.

# Reconstruct
new_lines = []
i = 0
while i < len(lines):
    if i == dashboard_btn_start:
        # Instead of dashboard button, insert draft lines
        new_lines.extend(draft_lines)
        i = dashboard_btn_end + 1
        continue
    
    if i == draft_start:
        # Skip the original draft lines
        i = draft_end + 1
        continue
    
    if "# --- 4. Modular UI Components ---" in lines[i]:
        # Insert dashboard button right before this
        new_lines.extend(dashboard_lines)
        new_lines.append(lines[i])
        i += 1
        continue
        
    new_lines.append(lines[i])

with open("job-scraping-app/pages/CV_Editor.py", "w") as f:
    f.writelines(new_lines)

print("Done")


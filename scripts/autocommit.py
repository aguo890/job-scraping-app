import os
import subprocess
import sys
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent


try:
    from dotenv import load_dotenv
    from openai import OpenAI
except ImportError:
    print("⚠️  Missing dependencies (openai, python-dotenv).")
    subprocess.run(["git", "add", "."], cwd=ROOT_DIR)
    subprocess.run(["git", "commit", "-m", "wip: quick push (missing deps)"], cwd=ROOT_DIR)
    subprocess.run(["git", "push"], cwd=ROOT_DIR)
    sys.exit(0)

load_dotenv(ROOT_DIR / ".env")

def get_staged_diff():
    result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=ROOT_DIR)
    return result.stdout or ""

def get_staged_files():
    result = subprocess.run(["git", "diff", "--name-only", "--cached"], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=ROOT_DIR)
    return result.stdout or ""

def main():
    api_key = os.getenv("DEEPSEEK_API_KEY") # Or OPENAI_API_KEY
    commit_msg = ""
    
    print("📦 Staging all changes...")
    subprocess.run(["git", "add", "."], cwd=ROOT_DIR)
    
    diff = get_staged_diff()
    files = get_staged_files()
    
    if not diff.strip():
        print("No changes to commit.")
        sys.exit(0)

    if not api_key:
        print("⚠️  API Key not found. Using default message.")
        commit_msg = "wip: quick push (missing api key)"
    else:
        MAX_DIFF_LEN = 25000 
        is_lock_file = any(f.endswith(('.lock', '-lock.json', '.lock.yaml')) for f in files.splitlines())
        
        if is_lock_file:
            diff_context = "⚠️ Large lock file changes detected (excluded)." + "\n" + diff[:10000]
        elif len(diff) > MAX_DIFF_LEN:
            diff_context = f"⚠️ DIFF TRUNCATED. Showing first {MAX_DIFF_LEN} chars:\n" + diff[:MAX_DIFF_LEN]
        else:
            diff_context = diff
            
        prompt_content = f"Staged Files:\n{files}\n\nDiff Content:\n{diff_context}"
        
        # Adjust base_url/model if using standard OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        print("🤖 Generating commit message...")
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Generate a Conventional Commit message. First line under 72 chars. Use bullet points for details. No markdown formatting in output."},
                    {"role": "user", "content": prompt_content}
                ],
                temperature=0.4,
                max_tokens=250
            )
            commit_msg = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️  Generation failed: {e}")
            commit_msg = "wip: large update"

    print(f"🚀 Committing: {commit_msg}")
    try:
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=ROOT_DIR, check=True)
        subprocess.run(["git", "push"], cwd=ROOT_DIR, check=True)
        print("✅ Pushed!")
    except subprocess.CalledProcessError:
        print("❌ Failed to commit/push.")
        sys.exit(1)

if __name__ == "__main__":
    main()

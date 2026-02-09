import os
import sys
from ai_assistant import AIAssistant

def verify():
    print("="*40)
    print("Verifying environment...")
    print("="*40)
    
    # Check .env loading
    db_key = os.getenv('DEEPSEEK_API_KEY')
    print(f"DEEPSEEK_API_KEY present: {bool(db_key)}")
    if db_key:
        print(f"DEEPSEEK_API_KEY prefix: {db_key[:4]}...")
        
    print(f"AI_BASE_URL: {os.getenv('AI_BASE_URL')}")
    
    # Check AIAssistant init
    ai = AIAssistant()
    print(f"AIAssistant.api_key present: {bool(ai.api_key)}")
    print(f"AIAssistant.api_url: {ai.api_url}")
    print(f"AIAssistant.model: {ai.model}")
    
    # Check CV loading
    cv = ai.load_user_profile()
    print(f"CV loaded: {bool(cv)}")
    if cv:
        print(f"CV length: {len(cv)}")
        print(f"CV start: {cv[:50]}...")
    else:
        print("CV NOT loaded")
        sys.exit(1)

if __name__ == "__main__":
    verify()

import pandas as pd
import re

def test_season_extraction():
    test_titles = [
        "Software Engineer Intern (Summer 2026)",
        "Data Science Co-op 2025",
        "Grad Intern 2026 - AI",
        "Spring 2025 Engineering Rotational",
        "Winter 2027 Quantitative Analyst",
        "Q3 2026 Developer Advocate",
        "Generic Software Engineer Role",
        "Senior Developer (No Season Specified)"
    ]
    
    df = pd.DataFrame(test_titles, columns=['title'])
    
    season_regex = r'(Summer|Fall|Spring|Winter|Q[1-4]|Co-op|Grad Intern)\s+(\d{4})'
    extracted = df['title'].str.extract(season_regex, flags=re.IGNORECASE)
    
    df['Season'] = extracted[0].fillna('Other')
    df['Year'] = extracted[1].fillna('N/A')
    df['Season_Display'] = df.apply(lambda x: f"{x['Season']} {x['Year']}" if x['Year'] != 'N/A' else x['Season'], axis=1)

    print("--- Test Results ---")
    print(df[['title', 'Season_Display']])
    
    # Assertions
    assert df.loc[0, 'Season'].lower() == 'summer'
    assert df.loc[0, 'Year'] == '2026'
    assert df.loc[1, 'Season'].lower() == 'co-op'
    assert df.loc[2, 'Season'].lower() == 'grad intern'
    assert df.loc[2, 'Year'] == '2026'
    assert df.loc[5, 'Season'].upper() == 'Q3'
    assert df.loc[6, 'Season'] == 'Other'
    
    print("\n✅ Regex Extraction Tests Passed!")

if __name__ == "__main__":
    test_season_extraction()

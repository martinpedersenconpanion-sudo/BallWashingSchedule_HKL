import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
import re

# -----------------------------
# SETTINGS
# -----------------------------
TROOP_URL = "https://www.laget.se/HKLidkoping-Herrar/Troop"
OUTPUT_FILE = os.path.join("C:\\Users\\martinp\\Downloads\\", "HK_Lidkoping_BallWashingSchedule.csv")

SEASON_START = datetime(2025, 8, 25)
SEASON_END = datetime(2026, 4, 30)

# -----------------------------
# STEP 1: Scrape player info and profile links
# -----------------------------
r = requests.get(TROOP_URL, timeout=15)
soup = BeautifulSoup(r.text, "html.parser")

players = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    if "/HKLidkoping-Herrar/Troop/" in href and re.search(r"/\d+/", href):
        full_url = "https://www.laget.se" + href
        text_lines = [line.strip() for line in a.text.strip().splitlines() if line.strip()]
        if len(text_lines) == 3:
            number_text, name, position = text_lines
        elif len(text_lines) == 2:
            number_text, name = text_lines
            position = ""
        else:
            name = text_lines[0]
            number_text = None
            position = ""
        try:
            number = int(number_text)
        except:
            number = None
        players.append({
            "Number": number,
            "Name": name,
            "Position": position,
            "ProfileURL": full_url
        })

df = pd.DataFrame(players)

# -----------------------------
# STEP 2: Scrape age from each profile
# -----------------------------
def get_age_from_profile(url: str):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", class_="player__info")
        if table:
            for row in table.find_all("tr"):
                th = row.find("th")
                td = row.find("td")
                if th and td and th.text.strip() == "Ålder":
                    return int(td.text.strip())
    except Exception:
        return None
    return None

df["Age"] = df["ProfileURL"].apply(get_age_from_profile)

# -----------------------------
# STEP 3: Sort youngest → oldest
# -----------------------------
df = df.sort_values(by="Age", ascending=True, na_position="last").reset_index(drop=True)

# -----------------------------
# STEP 4: Generate training sessions
# -----------------------------
sessions = []
current_date = SEASON_START
while current_date <= SEASON_END:
    if current_date.weekday() == 0:  # Monday
        sessions.append(current_date.replace(hour=20, minute=15))
    if current_date.weekday() == 2:  # Wednesday
        sessions.append(current_date.replace(hour=19, minute=0))
    current_date += timedelta(days=1)

# -----------------------------
# STEP 5: Assign players to sessions (round-robin)
# -----------------------------
schedule = []
players_list = df.to_dict("records")
num_players = len(players_list)

for i, session in enumerate(sessions):
    player = players_list[i % num_players]
    schedule.append({
        "Number": player["Number"],
        "Name": player["Name"],
        "Position": player["Position"],
        "Age": player["Age"],
        "CleaningDate": session.strftime("%Y-%m-%d %H:%M")
    })

# -----------------------------
# STEP 6: Save CSV
# -----------------------------
out_df = pd.DataFrame(schedule)
out_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print(f"✅ Ball washing schedule saved to {OUTPUT_FILE}")

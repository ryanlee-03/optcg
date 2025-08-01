import requests
from bs4 import BeautifulSoup
import json

# --- CONFIG ---
url = "https://en.onepiece-cardgame.com/rules/blockicon-card/"
output_path = "data/block_rules.json"

# --- SCRAPE ---
response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(response.text, 'html.parser')

# Find the two main content sections
content_divs = soup.find_all('div', class_="detailCol isPdS mtS")

# Prepare containers
block_x = []
block_4 = []

# Loop through both blocks
for i, div in enumerate(content_divs):
    ul = div.find('ul')
    target = block_x if i == 0 else block_4
    if ul:
        for li in ul.find_all('li'):
            text = li.get_text(strip=True)
            if text:
                parts = text.split(" ", 1)
                code = parts[0]
                name = parts[1] if len(parts) > 1 else ""
                target.append({"code": code, "name": name})

# --- SAVE TO FILE ---
result = {
    "block_x": block_x,
    "block_4": block_4
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"✅ Scraped and saved {len(block_x)} Block X cards and {len(block_4)} Block 4 cards to '{output_path}'")
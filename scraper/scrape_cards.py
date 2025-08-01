import requests
from bs4 import BeautifulSoup, Tag
import json
import re
import os
import time



# --- SETS SCRAPING ---
# ---Clean and split the text of the <option> tag to get each SET NAME AND ID
def clean_and_split(option_tag: Tag) -> dict:
    # Get the 'value' attribute safely; this contains the SET ID (e.g. 569111)
    value = option_tag.get('value', '').strip()
    if not value:
      return None # Skip if the option tag doesn't have a value

    # Get the text content inside the option tag
    # this contains the SET TYPE, SET NAME, and SET NUMBER (e.g. "EXTRA BOOSTER -Anime 25th Collection- [EB-02]")
    text = option_tag.get_text().strip()

    # Remove any HTML entities (e.g. &lt;br&gt;)
    text = re.sub(r'<.*?>', '', text)

    # Now split the raw_text into parts
    # e.g. "EXTRA BOOSTER",  "ONE PIECE CARD THE BEST",  "[PRB-01]"
    # Split on hyphens not inside brackets (e.g. [PRB-01] should stay intact)
    parts = re.split(r'-(?![^[]*\])', text) 
    parts = [part.strip() for part in parts if part.strip()]

    raw_html = str(option_tag) # Save original HTML for debugging and reference

    return {
        'value': value,
        'raw_text': text,
        'parts': parts,
        'raw_html': raw_html
    }




# --- FETCH AND PARSE THE SETS FROM WEBPAGE ---
def fetch_onepiece_sets(url: str) -> list:
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve the page. Status code: {response.status_code}")

    soup = BeautifulSoup(response.text, 'html.parser')
    # Look for the <select> element with id='series' which contains all the sets
    set_list = soup.find('select', id='series') 

    if not set_list:
        raise Exception("Could not find the <select> element with id='series'.")

    op_set = []
    for option in set_list.find_all('option'):
      parsed = clean_and_split(option)
      if parsed:
        op_set.append(parsed)

    return op_set

# --- CACHE ---
opsets_cache_path = "data/onepiece_sets.json"
opcards_cache_path = "data/onepiece_cards.json"

# Save set information to a JSON file
def save_sets_to_json(data, path=opsets_cache_path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# Save card information to a JSON file
def save_cards_to_json(cards, path=opcards_cache_path):
    with open(path, "w") as f:
        json.dump(cards, f, indent=2)


# --- CARDS SCRAPING ---
# --- FETCH AND PARSE THE CARDS FROM WEBPAGE ---
def fetch_card_details(url):
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; Google Colab script)'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve page. Status: {response.status_code}")

    soup = BeautifulSoup(response.text, 'html.parser')
    result_col = soup.find('div', class_='resultCol') # All cards are under this container
    dl_tags = result_col.find_all('dl') if result_col else []

    # --- TARGET FIELDS ---
    # These are the fields that we want to extract from the <dd> tag
    target_fields = ['cost', 'attribute', 'power', 'counter', 'color', 'block', 'feature', 'text', 'getInfo']

    cards = []

    for dl in dl_tags:
        # --- From <dt>: card name and spans (top info section) ---
        dt = dl.find('dt')
        info_spans = []
        card_name = None
        if dt:
            info_col = dt.find('div', class_='infoCol')
            if info_col:
                info_spans = [span.get_text(strip=True) for span in info_col.find_all('span')]
            name_div = dt.find('div', class_='cardName')
            if name_div:
                card_name = name_div.get_text(strip=True)


        # --- From <dd>: "back side" of the card with stats and effects ---
        dd = dl.find('dd')
        back_data = {}
        if dd:
            back_col = dd.find('div', class_='backCol')
            if back_col:
                for field in target_fields:
                    container = back_col.find('div', class_=field)
                    if container:
                      if field == 'text':
                        # For text/effects, a card can have multiple text blocks ; we join all the text blocks
                        texts = [text.strip() for text in container.stripped_strings if text.strip()]
                        back_data[field] = ' '.join(texts)
                      else:
                        # The other fields will have their values in the last meaningful text
                        children = [child for child in container.children
                                               if not (getattr(child, 'name', None) in ['h3', 'img', 'a'])]

                        meaningful_texts = []
                        for child in children:
                            if isinstance(child, str):
                                text = child.strip()
                                if text:
                                    meaningful_texts.append(text)
                            else:
                                text = child.get_text(strip=True)
                                if text:
                                    meaningful_texts.append(text)

                        # Use last non-empty text found, fallback to cleaned container text
                        if meaningful_texts:
                            back_data[field] = meaningful_texts[-1]
                        else:
                            for tagname in ['h3', 'img', 'a']:
                                for tag in container.find_all(tagname):
                                    tag.extract()
                            back_data[field] = container.get_text(strip=True)

         # Extract card's ID attribute from the <dl> tag
        card_id = dl.get('id', 'UNKNOWN')                           

        # Append the card to the list
        cards.append({
            'card_name': card_name,
            'card_id': card_id,
            'info_spans': info_spans,
            'back_data': back_data
        })

    return cards



# --- Main execution: loop through all sets and save cards as one file ---
def main():
    print(">>> main started")
    initial_url = "https://en.onepiece-cardgame.com/cardlist/?series=569111" # the default set loaded into the webpage
    sets = fetch_onepiece_sets(initial_url)

    # --- FETCH AND SAVE THE CARDS ---
    all_cards = []
    set_ids = [s['value'] for s in sets]
    base_url = "https://en.onepiece-cardgame.com/cardlist/?series={}"

    for set_id in set_ids:
        print(f"Fetching cards for set: {set_id}")
        cards = fetch_card_details(base_url.format(set_id))
        all_cards.extend(cards)  # combine into one list

        time.sleep(2) # be polite

    # Save once at the end
    save_sets_to_json(sets)
    print(">>> sets saved")

    save_cards_to_json(all_cards)
    print(f"\nSaved all {len(all_cards)} cards to 'onepiece_cards.json'.")


# --- ENTRY POINT ---
if __name__ == "__main__":
    main()

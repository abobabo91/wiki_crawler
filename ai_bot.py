import requests
from bs4 import BeautifulSoup
import time
from openai import OpenAI

# OpenAI API setup
openai_api_key = "your_api_key"  # Replace with your actual key
client = OpenAI(api_key=openai_api_key)

# Wikipedia URLs
WIKI_MAIN_PAGE = "https://en.wikipedia.org/wiki/Main_Page"
WIKI_BASE_URL = "https://en.wikipedia.org"





def get_wikipedia_content_and_links(url):
    """Scrapes a Wikipedia page and extracts article links."""
    response = requests.get(url)
    if response.status_code != 200:
        return "", []

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text()

    links = [
        WIKI_BASE_URL + link.get("href")
        for link in soup.find_all("a", href=True)
        if link.get("href").startswith("/wiki/") and ":" not in link.get("href")
    ]

    return page_text, list(set(links))


def ask_gpt_to_choose_link(page, links, current_page, page_history, reason_history):
    """Asks GPT to choose the next Wikipedia link and explain why."""    
    gpt_prompt = ("You are on this website: " + current_page + 
                  "\n\nThe content of this website is this: " + page[:2000] + #optional
                  "\n\nThe links of this website are these: " + ';'.join(links) + 
                  "\n\nThe previous websites you visited: " + ';'.join(page_history) + 
                  "\n\nThe reasons you gave so far why you choose certain websites are: " + ';'.join(reason_history) +
                  "\n\nYour job now is to chose the link you want to follow, and give a reason why you choose that link. " + 
                  "Choose the link that you are most interested in and explain in one sentence why are you interested in that particular link." + 
                  "Output you answer in this format: \"THE_LINK_YOU_CHOSE;THE_REASON_YOU_CHOSE\". Output nothing else, but this two things, seperated by \";\"."
                  )
    
    client = OpenAI(api_key=openai.api_key)
    
    response = client.chat.completions.create(
        model='gpt-4o', 
        messages=[
        {"role": "system", "content": ""},
        {"role": "user", "content": gpt_prompt}],
        max_tokens = 200,
        temperature=0,
        timeout=30)
    
    extracted_text = response.choices[0].message.content.strip()
    chosen_link, reason = extracted_text.replace('\"','').split(';')
    
    return chosen_link, reason



def search_for_target_page(page, links, current_page, page_history, reason_history, target_page):
    """Asks GPT to find the shortest path to a target Wikipedia page."""
    gpt_prompt = ("You are on this website: " + current_page + 
                  "\n\nThe links of this website are these: " + ';'.join(links) + 
                  "\n\nThe previous websites you visited: " + ';'.join(page_history) + 
                  "\n\nThe reasons you gave so far why you choose certain websites are: " + ';'.join(reason_history) +                  
                  "\n\nYour job now is to chose the link you want to follow, and give a reason why you choose that link. " + 
                  "Your job is to reach the page of  \"" + target_page + "\", by going link from link, in the fewest amount of steps!" + 
                  "Output you answer in this format: \"THE_LINK_YOU_CHOSE;THE_REASON_YOU_CHOSE\". Output nothing else, but these two things, seperated by \";\". " + 
                  "If you found the page we look for, output \"0;THE_REASON_YOU_THINK_IT_IS_THE_TARGET_PAGE."
                  )
    
    client = OpenAI(api_key=openai.api_key)
    
    response = client.chat.completions.create(
        model='gpt-4o', 
        messages=[
        {"role": "system", "content": ""},
        {"role": "user", "content": gpt_prompt}],
        max_tokens = 200,
        temperature=0,
        timeout=30)
    
    extracted_text = response.choices[0].message.content.strip()
    
    chosen_link, reason = extracted_text.replace('\"','').split(';')
    
    return chosen_link, reason

def main():
    """Runs the Wikipedia crawling AI."""
    current_page = WIKI_MAIN_PAGE
    page_history = [current_page]
    reason_history = []
    target_page = "Alexandre Pato"

    for _ in range(10):  # Limit to 10 iterations
        page, links = get_wikipedia_content_and_links(current_page)
        if not links:
            print("No further links found. Stopping.")
            break

        chosen_link, reason = ask_gpt_to_choose_link(page, links, current_page, page_history, reason_history)
        # chosen_link, reason = search_for_target_page(page, links, current_page, page_history, reason_history, target_page)

        if chosen_link == "0":
            print(f"Target page '{target_page}' found! Reason: {reason}")
            break

        print(f"Navigating to: {chosen_link}\nReason: {reason}\n")

        page_history.append(chosen_link)
        reason_history.append(reason)
        current_page = chosen_link

        time.sleep(2)  # Pause to avoid excessive requests


if __name__ == "__main__":
    main()


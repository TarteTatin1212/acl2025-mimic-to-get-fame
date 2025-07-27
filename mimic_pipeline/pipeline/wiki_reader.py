import requests
import wikipediaapi
from bs4 import BeautifulSoup
import certifi

def scrape_wikipedia_article(url):
    # Send a request to the given URL
    response = requests.get(url, verify=False)
    
    # Check if the request was successful
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve the page. Status code: {response.status_code}")
    
    # Parse the HTML content of the page
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the main content of the article
    content_div = soup.find('div', {'class': 'mw-parser-output'})
    
    if not content_div:
        raise Exception("Failed to find the main content of the article.")
    
    # Extract all paragraphs within the main content
    paragraphs = content_div.find_all('p')
    
    # Join the paragraphs into a single string
    article_text = '\n'.join([para.get_text() for para in paragraphs])
    
    return article_text


def fetch_wikipedia_article(title):
    user_agent = 'MyUserAgent/1.0 (muneebkhan7rc@gmail.com)'  # Replace with your email and a user agent string
    wiki_wiki = wikipediaapi.Wikipedia('en', headers={'User-Agent': user_agent})
    page = wiki_wiki.page(title)
    if not page.exists():
        raise ValueError(f"The page '{title}' does not exist.")
    return page.summary
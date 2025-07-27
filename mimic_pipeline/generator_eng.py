from pipeline.wiki_reader import scrape_wikipedia_article
from pipeline.wiki_reader import fetch_wikipedia_article
from pipeline.summary_generator import transform_to_meeting_summary
from pipeline.meeting_plan_generator import MeetingPlanner
from pipeline.save_content import Saver
from pipeline.meeting_generator import MeetingGenerator
from pipeline.meeting_evaluator import MeetingEvaluator

from pipeline.wikiscrape import get_article_text   # better wikipedia scraper

import json
import logging
import pandas as pd

import random
import os

from openai import AzureOpenAI

# Configure the root logger 
logging.basicConfig( level=logging.INFO,
format='%(asctime)s - %(levelname)s - %(message)s'
)

MODEL_CONFIG_PATH = "./config_gpt.json"


# Example usage
with open(MODEL_CONFIG_PATH) as config_file:
    config = json.load(config_file)

API_KEY = config["api_key"]
API_VERSION = config["api_version"]
ENDPOINT = config["endpoint"]
MODEL_NAME = config["model"]

print(f"Using model: {MODEL_NAME} with endpoint {ENDPOINT}")

CLIENT = AzureOpenAI(
    api_key=API_KEY,
    api_version= API_VERSION,
    azure_endpoint=ENDPOINT,
)

print("client set up")


from urllib.parse import unquote, urlparse

def slug_from_url(url: str) -> str:
    """'/wiki/Jazz' -> 'Jazz'   '/wiki/Linguistic_diversity' -> 'Linguistic diversity'"""
    slug = urlparse(url).path.split("/wiki/")[-1]
    return unquote(slug).replace("_", " ")


meeting_formats_subset = ["Brainstorming Session", "Casual Catch-Up", "Cross-Functional Meeting", "Decision-Making Meeting", "Remote or Virtual Meeting", "Innovation Forum", "Stakeholder Meeting"]


from datetime import datetime

def log_missing_article(filename, article_info, url, domain=None):
    """
    Log missing article information to a file with timestamp and domain information.
    Creates the log file and directory if they don't exist.
    
    Args:
        filename (str): Path to the log file
        article_info (str): Title of the Wikipedia article
        url (str): URL of the Wikipedia article
        domain (str, optional): Domain category of the article
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Check if file exists and create header if it's new
        is_new_file = not os.path.exists(filename)
        
        # Open file in append mode, creating it if it doesn't exist
        with open(filename, 'a', encoding='utf-8') as f:
            # Write header if it's a new file
            if is_new_file:
                f.write("Timestamp | Domain | Article Title | URL\n")
                f.write("-" * 100 + "\n")
            
            # Write the log entry
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # If domain is provided in article_info (format: "domain|title")
            if "|" in article_info:
                domain, title = article_info.split("|", 1)
                log_entry = f"{timestamp} | {domain} | {title} | {url}\n"
            # If domain is provided as separate parameter
            elif domain:
                log_entry = f"{timestamp} | {domain} | {article_info} | {url}\n"
            # If no domain information is available
            else:
                log_entry = f"{timestamp} | N/A | {article_info} | {url}\n"
            
            f.write(log_entry)
            
    except Exception as e:
        print(f"Error logging missing article: {str(e)}")
        print(f"Article: {article_info}")
        print(f"URL: {url}")


class CompletedArticlesTracker:
    def __init__(self, tracker_file='./output/final_corpora/English/completed_articles.json'):
        """
        Initialize the tracker with a file path to store completed articles.
        
        Args:
            tracker_file (str): Path to the JSON file storing completed articles
        """
        self.tracker_file = tracker_file
        self.completed_articles = self._load_completed_articles()
        
    def _load_completed_articles(self):
        """Load the existing completed articles from file."""
        try:
            os.makedirs(os.path.dirname(self.tracker_file), exist_ok=True)
            if os.path.exists(self.tracker_file):
                with open(self.tracker_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading completed articles: {str(e)}")
            return {}
    
    def is_article_completed(self, domain, article_title):
        """Check if an article has been completed."""
        return (domain in self.completed_articles and 
                article_title in self.completed_articles[domain])
    
    def mark_article_completed(self, domain, article_title, output_path):
        """Mark an article as completed with timestamp and output path."""
        if domain not in self.completed_articles:
            self.completed_articles[domain] = {}
            
        self.completed_articles[domain][article_title] = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'output_path': output_path
        }
        
        self._save_tracker()
        
    def _save_tracker(self):
        """Save the completed articles to file."""
        try:
            with open(self.tracker_file, 'w', encoding='utf-8') as f:
                json.dump(self.completed_articles, f, indent=2)
        except Exception as e:
            print(f"Error saving completed articles: {str(e)}")
        

with open('pipeline/wiki_articles_eng.json', 'r', encoding='utf-8') as file:
    eng_articles = json.load(file)



tracker = CompletedArticlesTracker()

for domain, articles in eng_articles.items():
    for article_title, url in articles.items():
        # Check if article was already completed
        if tracker.is_article_completed(domain, article_title):
            print(f"\nSkipping completed article: {article_title}")
            continue

        print(f"\nProcessing ###{article_title}###...\n")
        print(f"Artcle Domain: {domain}\n")

        _title = slug_from_url(url)
        article_text = get_article_text(_title, 'en')

        if article_text == '':
            # Log the missing article
            log_missing_article(
                    './output/final_corpora/English/missing_articles_eng.log',
                    f"{domain}|{article_title}",
                    url
                )
            continue

        LANGUAGE = 'English'
        selected_meeting_type = random.choice(meeting_formats_subset)
        print(f"\n-->{selected_meeting_type}<--\n")

        # Create sanitized versions of strings for filename
        safe_domain = domain.replace(' ', '_').replace('/', '_')
        safe_article_title = article_title.replace(' ', '_').replace('/', '_')
        safe_meeting_type = selected_meeting_type.replace(' ', '_').replace('/', '_')
        
        OUTPUT_PATH = os.path.join(
                './output/final_corpora/English',
                f"{safe_meeting_type}_{safe_domain}_{LANGUAGE}_{safe_article_title}.csv"
            )
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)


        summary = transform_to_meeting_summary(article_title=safe_article_title, article=article_text, client=CLIENT, model_id=MODEL_NAME, meeting_type=selected_meeting_type, language=LANGUAGE)
        # print("-" * 20)
        print(summary)
        print()
        meeting_planner = MeetingPlanner(client=CLIENT, model_id=MODEL_NAME, article=article_text, article_title=safe_article_title, summary=summary, meeting_type=selected_meeting_type)
        meeting_plan, tags, personas = meeting_planner.plan_meeting(language=LANGUAGE)
        # print("-" * 20)
        print(meeting_plan)

        meeting_generator = MeetingGenerator(CLIENT, MODEL_NAME, personas, meeting_plan, article_text, safe_article_title, selected_meeting_type, safe_domain, language=LANGUAGE)
        meeting = meeting_generator.generate_meeting(meeting_type=selected_meeting_type, language=LANGUAGE)

        # evaluator = MeetingEvaluator(CLIENT, MODEL_NAME)
        # basic_evaluation = evaluator.basic_llm_evaluation(meeting)
        # psychology_evaluation = evaluator.psychology_based_llm_evaluation(meeting)
        print(f"Proceeding to save the final meeting...")
        Saver.save_csv(
            safe_article_title, 
            article_text, 
            tags, 
            personas, 
            summary, 
            meeting_plan, 
            meeting, 
            OUTPUT_PATH,
            # basic_evaluation,
            # psychology_evaluation,
            
        )

        # Mark article as completed after successful save
        tracker.mark_article_completed(domain, article_title, OUTPUT_PATH)
        print(f"✓ Successfully completed and tracked: {article_title}")
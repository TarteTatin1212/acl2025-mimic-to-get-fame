import os
import glob
import pandas as pd
import nltk
from collections import Counter, defaultdict
from typing import List, Dict, Any
import ast  # For parsing string representations of lists
import re

# Ensure NLTK resources are downloaded
# nltk.download('punkt')
# nltk.download('punkt_tab')

class SyntheticMeetingAnalyzer:
    def __init__(self, input_dir: str):
        self.input_dir = input_dir
        self.meetings_data = self.load_meetings()

    

    def load_meetings(self) -> List[Dict[str, Any]]:

        def extract_speaker_and_dialog(line):
            # Regular expression pattern
            pattern = r'^(.*?)(?:\s*\([^)]*\))?\s*:\s*(.*)'

            # Search for the pattern in the line
            match = re.search(pattern, line)

            if match:
                # Extract speaker name and dialog
                speaker = match.group(1).strip()
                dialog = match.group(2).strip()
                return speaker, dialog
            else:
                # Return None for both if no match is found
                return None, None


        meetings = []
        csv_files = glob.glob(os.path.join(self.input_dir, '*.csv'))
        for file_path in csv_files:
            try:
                df = pd.read_csv(file_path)
                if df.empty:
                    continue  # Skip empty files
                row = df.iloc[0]
                # Check if required columns exist
                required_columns = ['Personas', 'Title', 'Meeting_Plan', 'Meeting', 'Article', 'Summary']
                if not all(col in df.columns for col in required_columns):
                    print(f"Warning: Missing columns in file {file_path}. Skipping this file.")
                    continue
                # Skip if "Article" is empty or NaN
                if pd.isna(row['Article']) or row['Article'] == '':
                    continue
                # Extract meeting type from filename
                filename = os.path.basename(file_path)
                base_name = os.path.splitext(filename)[0]
                meeting_type = base_name.split('_')[0]
                # Extract other data
                personas = ast.literal_eval(row['Personas']) if 'Personas' in row and pd.notna(row['Personas']) else []
                participants = [p['role'] for p in personas if 'role' in p]
                title = row['Title'] if 'Title' in row else ''
                meeting_plan = ast.literal_eval(row['Meeting_Plan']) if 'Meeting_Plan' in row and pd.notna(row['Meeting_Plan']) else []
                meeting_text = row['Meeting'] if 'Meeting' in row else ''
                summary = row['Summary'] if 'Summary' in row else ''
                # Split meeting text into turns
                turns = meeting_text.split('>>')
                turns = [turn.strip() for turn in turns if turn.strip()]
                turns_dict = []
                for turn in turns:
                    if turn != '':
                        if ':' in turn:
                            speaker, text = extract_speaker_and_dialog(turn)
                            turns_dict.append({'speaker': speaker.strip(), 'text': text.strip()})
                        else:
                            turns_dict.append({'speaker': 'Unknown', 'text': turn})
                # Append meeting data
                meetings.append({
                    'meeting_type': meeting_type,
                    'participants': participants,
                    'title': title,
                    'meeting_plan': meeting_plan,
                    'turns': turns_dict,
                    'article': row['Article'],
                    'summary': summary
                })
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
        return meetings

    def evaluate_all(self) -> Dict[str, Dict[str, Any]]:
        return {
            "general": self.compute_general_stats(),
            "turn_level": self.compute_turn_level_stats(),
            "linguistic_diversity": self.compute_linguistic_diversity(),
            "summary_stats": self.compute_summary_stats()
        }

    def compute_general_stats(self) -> Dict[str, Any]:
        num_meetings = len(self.meetings_data)
        type_counts = Counter([m['meeting_type'] for m in self.meetings_data])
        avg_participants = (
            sum(len(m['participants']) for m in self.meetings_data) / num_meetings
            if num_meetings else 0
        )
        return {
            "number_of_meetings": num_meetings,
            "meetings_per_type": dict(type_counts),
            "average_number_of_participants": round(avg_participants, 2)
        }

    def compute_turn_level_stats(self) -> Dict[str, Any]:
        total_meetings = len(self.meetings_data)
        total_turns = sum(len(m['turns']) for m in self.meetings_data)
        total_words = sum(len(self.tokenize(turn['text'])) for m in self.meetings_data for turn in m['turns'])
        total_topics = sum(len(m['meeting_plan']) for m in self.meetings_data)
        avg_turns_per_meeting = total_turns / total_meetings if total_meetings else 0
        avg_words_per_meeting = total_words / total_meetings if total_meetings else 0
        avg_words_per_turn = total_words / total_turns if total_turns else 0
        avg_topics_per_meeting = total_topics / total_meetings if total_meetings else 0
        return {
            "avg_turns_per_meeting": round(avg_turns_per_meeting, 2),
            "avg_words_per_meeting": round(avg_words_per_meeting, 2),
            "avg_words_per_turn": round(avg_words_per_turn, 2),
            "avg_sub_topics_per_meeting": round(avg_topics_per_meeting, 2)
        }

    def compute_linguistic_diversity(self) -> Dict[str, Any]:
        all_tokens = []
        for meeting in self.meetings_data:
            for turn in meeting['turns']:
                all_tokens.extend(self.tokenize(turn['text']))
        vocab = set(all_tokens)
        total_tokens = len(all_tokens)
        type_token_ratio = len(vocab) / total_tokens if total_tokens else 0
        return {
            "vocabulary_size": len(vocab),
            "type_token_ratio": round(type_token_ratio, 4)
        }

    def compute_summary_stats(self) -> Dict[str, Any]:
        total_meetings = len(self.meetings_data)
        total_summary_words = sum(len(self.tokenize(m['summary'])) for m in self.meetings_data)
        avg_summary_length = total_summary_words / total_meetings if total_meetings else 0
        return {
            "avg_summary_length_in_words": round(avg_summary_length, 2)
        }

    def write_stats_to_file(self, filename: str):
        results = self.evaluate_all()
        with open(filename, 'w') as f:
            for category, stats in results.items():
                f.write(f"\n=== {category.upper()} ===\n")
                for metric, value in stats.items():
                    f.write(f"{metric}: {value}\n")

    def tokenize(self, text: str) -> List[str]:
        tokens = nltk.word_tokenize(text.lower())
        return [t for t in tokens if t.isalnum()] 

    def compute_ngram_overlap(self, text_a: str, text_b: str, n: int = 2) -> float:
        tokens_a = self.tokenize(text_a)
        tokens_b = self.tokenize(text_b)
        if len(tokens_a) < n or len(tokens_b) < n:
            return 0.0
        ngrams_a = set(self.get_ngrams(tokens_a, n))
        ngrams_b = set(self.get_ngrams(tokens_b, n))
        intersection = ngrams_a.intersection(ngrams_b)
        return len(intersection) / len(ngrams_a) if ngrams_a else 0.0

    def get_ngrams(self, tokens: List[str], n: int) -> List[tuple]:
        return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

# Example usage
if __name__ == "__main__":
    input_dir = './output/final_fn/longer_meetings/English'  # Replace with actual directory path
    analyzer = SyntheticMeetingAnalyzer(input_dir)
    analyzer.write_stats_to_file('./output/final_fn/longer_meetings/English/longer_english_meetings_stats.txt')
import re
import sys
import os
from typing import Dict
import json
import glob
import csv
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from basics.scripts.model_handler import ModelHandler

from openai import AzureOpenAI

MODEL_CONFIG_PATH = "./../config_gpt.json"

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

class MeetingChallengesEvaluator:
	"""
	Evaluates a given meeting transcript for various 'challenge dimensions'
	that might complicate summarization. Each dimension is rated (0–5) along
	with a step-by-step reasoning and confidence score.
    
	The seven dimensions are:
  	1) Spoken language
  	2) Speaker dynamics
  	3) Coreference
  	4) Discourse structure
  	5) Contextual turn-taking
  	6) Implicit context
  	7) Low information density
	"""

	def __init__(self, client, model_id):
		self.client = client
		self.model_id = model_id

    	# Challenge dimensions with definitions & instructions
		self.challenges = {
            "Spoken language": {
            	"definition": (
                	"The extent to which the transcript exhibits spoken-language features—"
                	"such as colloquialisms, jargon, false starts, or filler words—that make it "
                	"harder to parse or summarize."
            	),
            	"instructions": (
                	"1. Are there noticeable filler words, false starts, or informal expressions?\n"
                	"2. Does domain-specific jargon disrupt straightforward summarization?\n"
                	"3. How challenging are these elements for generating a coherent summary?\n"
            	),
        	},
        	"Speaker dynamics": {
            	"definition": (
                	"The challenge of correctly identifying and distinguishing between multiple speakers, "
                	"tracking who said what, and maintaining awareness of speaker roles if relevant."
            	),
            	"instructions": (
                	"1. Is it difficult to keep track of speaker identities or roles?\n"
                	"2. How significantly do these dynamics affect clarity for summarization?\n"
            	),
        	},
        	"Coreference": {
            	"definition": (
                	"The difficulty in resolving references (e.g., who or what a pronoun refers to) or clarifying "
                	"references to previous actions or decisions, so the summary remains coherent."
            	),
            	"instructions": (
                	"1. Are references (e.g., pronouns like “he” or “that”) ambiguous?\n"
                	"2. Do unclear references to earlier points or events appear?\n"
                	"3. How difficult is it to track these references for summary generation?\n"
            	),
        	},
        	"Discourse structure": {
            	"definition": (
                	"The complexity of following the meeting’s high-level flow—especially if it changes topics "
                	"or has multiple phases (planning, debate, decision)."
            	),
            	"instructions": (
                	"1. Does the transcript jump between topics or phases without clear transitions?\n"
                	"2. Are meeting phases or topical shifts difficult to delineate?\n"
                	"3. How challenging is it to maintain an overview for the summary?\n"
            	),
        	},
        	"Contextual turn-taking": {
            	"definition": (
                	"The challenge of interpreting local context as speakers take turns, including interruptions, "
                	"redundancies, and how each turn depends on previous utterances."
            	),
            	"instructions": (
                	"1. Do abrupt speaker turns or interjections complicate continuity?\n"
                	"2. Are important points lost or repeated inconsistently?\n"
                	"3. How difficult is it to integrate these nuances into a coherent summary?\n"
            	),
        	},
        	"Implicit context": {
            	"definition": (
                	"The reliance on unspoken or assumed knowledge, such as organizational history, known issues, "
                	"or prior decisions, only vaguely referenced in the meeting."
            	),
            	"instructions": (
                	"1. Do participants refer to hidden topics or internal knowledge without explaining?\n"
                	"2. Is there essential background or context missing?\n"
                	"3. How much does summarization rely on understanding this hidden context?\n"
            	),
        	},
        	"Low information density": {
            	"definition": (
                	"Segments where salient info is sparse, repeated, or only occasionally surfaced—making it "
                	"hard to find and isolate key points in a sea of less relevant content."
            	),
            	"instructions": (
                	"1. Are there long stretches with minimal new information?\n"
                	"2. Is meaningful content buried under trivial or repetitive remarks?\n"
                	"3. How challenging is it to isolate crucial points for the summary?\n"
            	),
        	}
    	}

	def extract_tag_content(self, text: str, tag: str) -> str:
		"""
        Extract content between <tag></tag> from text.
        """
		pattern = fr"<{tag}>(.*?)</{tag}>"
		match = re.search(pattern, text, re.DOTALL)
		return match.group(1).strip() if match else ""

	def evaluate_meeting_challenges(self, meeting_transcript: str) -> dict:
		"""
    	Evaluate each challenge dimension, returning a dictionary with:
        	{
          	dimension_name: {
            	"reasoning": <string>,
            	"confidence": <string>,
            	"score": <string>
          	},
          	...
        	}
    	"""
		results = {}
		
		for dimension, info in self.challenges.items():
			definition = info["definition"]
			instructions = info["instructions"]

			# Prompt the LLM to evaluate the transcript for this dimension
			system_prompt = (
				f"You are a meeting challenge evaluator focusing on the dimension: {dimension}.\n\n"
				f"Definition: {definition}\n"
				f"Instructions:\n{instructions}\n"
				"You must:\n"
            	"- Provide a step-by-step reasoning about how the challenge is present (or not) in the transcript.\n"
            	"- Give a confidence score (0-100%).\n"
            	"- Provide a final numeric rating (0 to 5), following the scoring guide:\n"
            	"  0: Not observed.\n"
            	"  1-2: Mild presence.\n"
            	"  3-4: Noticeable presence complicating summarization.\n"
            	"  5: Severe presence making it very difficult to summarize.\n\n"
            	"Format your final response in the following tags:\n"
            	"<reasoning>...</reasoning>\n"
            	"<confidence_score>...</confidence_score>\n"
            	"<score>...</score>\n\n"
            	"Do NOT include any text outside these tags."
        	)

			user_prompt = (
				f"Meeting Transcript:\n\n{meeting_transcript}\n\n"
				"Please identify how challenging this dimension is for summarization."
			)

			message = [
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_prompt}
			]

			# Call the model
			response = ModelHandler.call_model_with_retry(self.client, message, self.model_id)
			raw_output = response.choices[0].message.content.strip()

			# Parse the tags
			reasoning = self.extract_tag_content(raw_output, "reasoning")
			confidence = self.extract_tag_content(raw_output, "confidence_score")
			score = self.extract_tag_content(raw_output, "score")

			results[dimension] = {
				"reasoning": reasoning,
				"confidence": confidence,
				"score": score
			}

		return results


def process_meetings(input_folder: str, output_csv: str, client, model_id):
    """
    1. Locate all CSV files in 'input_folder'.
    2. For each CSV file, read 'Title' and 'Meeting' columns.
    3. Evaluate the meeting transcript across the challenge dimensions using MeetingChallengesEvaluator.
    4. Store the consolidated results in 'output_csv'.

    Assumes each CSV has columns at least: ['Title', 'Meeting'].
    """

    evaluator = MeetingChallengesEvaluator(client, model_id)
    all_results = []

    # Find all CSV files
    csv_files = glob.glob(os.path.join(input_folder, "*.csv"))
    if not csv_files:
        print(f"No CSV files found in {input_folder}")
        return

    for csv_file in csv_files:
        print(f"Processing: {csv_file}")
        try:
            df = pd.read_csv(csv_file)
        except Exception as e:
            print(f"Failed to read CSV: {csv_file} -> {e}")
            continue

        # Check if required columns exist
        if 'Title' not in df.columns or 'Meeting' not in df.columns:
            print(f"Skipping {csv_file}, missing 'Title' or 'Meeting' column.")
            continue

        for _, row in df.iterrows():
            title = str(row['Title'])
            meeting_transcript = str(row['Meeting'])

            # Evaluate
            challenge_scores = evaluator.evaluate_meeting_challenges(meeting_transcript)

            # Flatten results
            row_result = {
                "Title": title,
                "Meeting": meeting_transcript
            }

            # We have 7 dimensions. For each dimension, store dimension_name + Score, Confidence, Reasoning
            # E.g., "Spoken language Score", "Spoken language Confidence", "Spoken language Reasoning"
            for dimension, outcome in challenge_scores.items():
                dim_key = dimension.replace(" ", "_")  # To avoid spaces in column names if desired
                row_result[f"{dimension} Score"] = outcome["score"]
                row_result[f"{dimension} Confidence"] = outcome["confidence"]
                row_result[f"{dimension} Reasoning"] = outcome["reasoning"]

            all_results.append(row_result)

    # Convert to DataFrame
    if not all_results:
        print("No data to write. Exiting.")
        return

    final_df = pd.DataFrame(all_results)

    # Write to output CSV
    # Overwrite any existing file
    final_df.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"Consolidated results saved to: {output_csv}")


if __name__ == "__main__":
	# Example usage:
	# Suppose you have an LLM client and model_id set up, e.g.:
	# client = <some LLM client instance>
	# model_id = "gpt-4"

	# For demonstration, placeholders:
	client = CLIENT
	model_id = MODEL_NAME

	input_folder = "./output/final_fn/German"
	output_csv = "./output/final_fn/metrics/fff_german_meetings_challenges.csv"

	# example_transcript = """
	# >>Alice: Alright, let's get started. We need to figure out how to design the interface.
	# >>Bob: Yes, so about that. I'm thinking we use a tabbed layout—um, wait, wasn't that already tried?
	# >>Alice: Actually, we tried something else. The user feedback wasn't so great.
	# >>Bob: Right, so maybe a sidebar approach. But let me check the older specs...
	# >>Charlie: [interrupting] Actually guys, we might be missing the point. The user wants an entire new color scheme too.
	# >>Alice: True, that was in the last user test. They asked for more contrast. But let's not forget the timeline, we only have a week.
	# """

	# results = evaluator.evaluate_meeting_challenges(example_transcript)
	# for dimension, outcome in results.items():
	# 	print(f"=== {dimension.upper()} ===")
	# 	print(f"Reasoning:\n{outcome['reasoning']}\n")
	# 	print(f"Confidence Score: {outcome['confidence']}")
	# 	print(f"Score (0-5): {outcome['score']}\n")
      
	process_meetings(input_folder, output_csv, client, model_id)


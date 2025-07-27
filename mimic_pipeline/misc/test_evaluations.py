import sys
import os
import pandas as pd
from meeting_evaluator import MeetingEvaluator
import json
from pathlib import Path
import argparse

# Configure path for importing from parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from basics.scripts.model_handler import ModelHandler

# Load model configuration
MODEL_CONFIG_PATH = "./../config_gpt.json"
with open(MODEL_CONFIG_PATH) as config_file:
    config = json.load(config_file)

API_KEY = config["api_key"]
API_VERSION = config["api_version"]
ENDPOINT = config["endpoint"]
MODEL_NAME = config["model"]

from openai import AzureOpenAI
CLIENT = AzureOpenAI(
    api_key=API_KEY,
    api_version=API_VERSION,
    azure_endpoint=ENDPOINT,
)

def evaluate_meeting(meeting_text, output_path, language="English"):
    """
    Evaluate a meeting using both basic and psychological evaluation methods.
    
    Args:
        meeting_text (str): The meeting transcript to evaluate
        output_path (str): Path to save evaluation results
        language (str): Language of the meeting
    """
    evaluator = MeetingEvaluator(CLIENT, MODEL_NAME)
    
    print(f"\nEvaluating meeting in {language}...")
    print("-" * 50)
    
    # Perform evaluations
    basic_evaluation = evaluator.basic_llm_evaluation(meeting_text)
    psychology_evaluation = evaluator.psychology_based_llm_evaluation(meeting_text)
    
    # Create a dictionary for the evaluation results
    evaluation_results = {
        'Meeting': meeting_text,
        **{f"Basic_{criterion}_{key}": value 
           for criterion, results in basic_evaluation.items()
           for key, value in results.items()},
        **{f"Psych_{criterion}_{key}": value
           for criterion, results in psychology_evaluation.items()
           for key, value in results.items()}
    }
    
    # Convert to DataFrame and save
    df = pd.DataFrame([evaluation_results])
    df.to_csv(output_path, index=False)
    print(f"Evaluation results saved to: {output_path}")
    
    # Print summary of evaluations
    print("\nBasic Evaluation Scores:")
    for criterion, results in basic_evaluation.items():
        print(f"{criterion}: {results['score']} (Confidence: {results['confidence']})")
    
    print("\nPsychological Evaluation Scores:")
    for criterion, results in psychology_evaluation.items():
        print(f"{criterion}: {results['score']} (Confidence: {results['confidence']})")

def process_csv_file(input_file, output_dir, language="English"):
    """
    Process a CSV file containing meetings and evaluate each meeting.
    
    Args:
        input_file (str): Path to input CSV file
        output_dir (str): Directory to save evaluation results
        language (str): Language of the meetings
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Read the CSV file
    df = pd.read_csv(input_file)
    
    # Process each meeting in the file
    for idx, row in df.iloc[11:].iterrows():
        meeting = row['Meeting']  # Assuming 'Meeting' is the column name containing the transcript

        # Create output filename based on input filename and meeting index
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}_evaluation_{idx}.csv")
        
        print(f"\nProcessing meeting {idx+1}/{len(df)}")
        evaluate_meeting(meeting, output_file, language)
# "../../../../QMSUM/processed_qmsum_test.csv"
# "./output/final_fn/metrics/"
def main():
    parser = argparse.ArgumentParser(description='Evaluate meetings from CSV files')
    parser.add_argument('--input_file', help='Path to input CSV file containing meetings')
    parser.add_argument('--output_dir', default='evaluation_results', 
                      help='Directory to save evaluation results')
    parser.add_argument('--language', default='English',
                      help='Language of the meetings (default: English)')
    
    args = parser.parse_args()
    
    print(f"Processing file: {args.input_file}")
    print(f"Output directory: {args.output_dir}")
    print(f"Language: {args.language}")
    
    process_csv_file(args.input_file, args.output_dir, args.language)

if __name__ == "__main__":
    main() 
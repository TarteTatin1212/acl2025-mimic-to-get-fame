import os
import glob
import csv
from typing import Dict
import pandas as pd
from rouge_score import rouge_scorer

def measure_rouge_groundedness(article_text: str, meeting_text: str) -> Dict[str, Dict[str, float]]:
    """
    Computes ROUGE scores between the original article (article_text)
    and the generated meeting transcript (meeting_text) to assess how
    grounded the meeting is in the source content.

    :param article_text: The text of the Wikipedia article used as reference.
    :param meeting_text: The transcript of the generated meeting.
    :return: A dictionary containing precision, recall, and f1 scores 
             for ROUGE-1, ROUGE-2, and ROUGE-L.
    """
    # Initialize a ROUGE scorer with stemming enabled
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    
    # Compute the scores
    # - 'article_text' is treated as reference
    # - 'meeting_text' is treated as hypothesis
    scores = scorer.score(article_text, meeting_text)
    
    # Convert the results into a more readable format
    results = {}
    for rouge_type, score_obj in scores.items():
        results[rouge_type] = {
            "precision": score_obj.precision,
            "recall": score_obj.recall,
            "f1": score_obj.fmeasure
        }
    
    return results

def process_csv_files(
    input_folder: str, 
    output_csv: str
) -> None:
    """
    Reads all CSV files in 'input_folder', each containing columns:
    ['Article', 'Meeting']. For each row (meeting-article pair), computes
    ROUGE-based groundedness metrics and appends them to 'output_csv'.

    :param input_folder: The folder path containing CSV files to process.
    :param output_csv: The path to the final CSV file storing results.
    """
    # Prepare a list to store all results
    all_results = []
    
    # Find all CSV files in the input folder
    csv_files = glob.glob(os.path.join(input_folder, "*.csv"))
    
    if not csv_files:
        print(f"No CSV files found in {input_folder}")
        return
    
    for file_path in csv_files:
        print(f"Processing: {file_path}")
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue

        # Check if required columns exist
        if 'Article' not in df.columns or 'Meeting' not in df.columns:
            print(f"Missing 'Article' or 'Meeting' column in {file_path}. Skipping.")
            continue
        
        for _, row in df.iterrows():
            article_text = str(row['Article'])
            meeting_text = str(row['Meeting'])
            
            # Compute ROUGE-based groundedness
            scores = measure_rouge_groundedness(article_text, meeting_text)
            
            # Prepare a dictionary entry with relevant fields for final CSV
            result_entry = {
                "Article": article_text,
                "Meeting": meeting_text,
                # ROUGE-1
                "rouge1_precision": scores["rouge1"]["precision"],
                "rouge1_recall": scores["rouge1"]["recall"],
                "rouge1_f1": scores["rouge1"]["f1"],
                # ROUGE-2
                "rouge2_precision": scores["rouge2"]["precision"],
                "rouge2_recall": scores["rouge2"]["recall"],
                "rouge2_f1": scores["rouge2"]["f1"],
                # ROUGE-L
                "rougel_precision": scores["rougeL"]["precision"],
                "rougel_recall": scores["rougeL"]["recall"],
                "rougel_f1": scores["rougeL"]["f1"]
            }
            
            all_results.append(result_entry)
    
    if not all_results:
        print("No valid rows processed; no output produced.")
        return
    
    # Convert results to DataFrame, then write to a single output CSV
    final_df = pd.DataFrame(all_results)
    # If the output CSV already exists, we can append or overwrite as desired.
    # For simplicity, we'll overwrite here.
    final_df.to_csv(output_csv, index=False)
    print(f"All results stored in: {output_csv}")

if __name__ == "__main__":
    # Example usage:
    # Folder containing your input CSVs
    input_folder = "./output/final_fn/German_new"

    # Final output CSV
    output_csv = "./output/final_fn/metrics/german_meetings_groundedness.csv"

    # Process all CSV files in the input folder and gather results
    process_csv_files(input_folder, output_csv)
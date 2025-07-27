import pandas as pd
import logging
import time
import random
import json
from pathlib import Path

# For GPT
from openai import AzureOpenAI

# For ROUGE
from rouge_score import rouge_scorer

# For BERTScore
import torch
from bert_score import score as bert_score

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from basics.scripts.model_handler import ModelHandler

from openai import AzureOpenAI

import re

def extract_content_between_tags(text, tag):
    """
    Extracts content enclosed within specified tags.

    :param text: The full text containing the tags.
    :param tag: The tag name without angle brackets.
    :return: Extracted content as a string. Returns the original text if tags are not found.
    """
    pattern = f'<{tag}>(.*?)</{tag}>'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    else:
        print(f"Warning: No <{tag}></{tag}> tags found in the model response.")
        return text  # Return original text if tags not found
    

##############################################################################
# Evaluation function: compute ROUGE and BERTScore
##############################################################################
def evaluate_summaries(candidate_summaries, reference_text, language='English'):
    """
    :param candidate_summaries: dict of {model_name: summary_text}, e.g.:
        {
          "gpt-4": "Summary from GPT-4 ...",
          ...
        }
    :param reference_text: ground-truth summary string
    :return: dict of metrics, one for each model, e.g.:
        {
          "gpt-4_rouge1_f1": 0.72,
          "gpt-4_rouge2_f1": 0.65,
          "gpt-4_rougeL_f1": 0.70,
          "gpt-4_bert_p": 0.83,
          "gpt-4_bert_r": 0.81,
          "gpt-4_bert_f1": 0.82,
          ...
        }
    """
    # Create a single ROUGE scorer for ROUGE-1, ROUGE-2, and ROUGE-Lsum (LS)
    rouge_scorer_obj = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeLsum'], use_stemmer=True)

    if language == 'German':
        from nltk.stem.snowball import SnowballStemmer
        rouge_scorer_obj._stemmer = SnowballStemmer('german')


    # Prepare a results dictionary
    results = {}

    # First, compute ROUGE model-by-model
    for model_name, candidate_text in candidate_summaries.items():
        # For ROUGE, reference is the first argument, candidate is the second
        rouge_scores = rouge_scorer_obj.score(reference_text, candidate_text)

        # We’ll store F-measure (fmeasure) for each of the metrics
        results[f"{model_name}_rouge1_f1"] = rouge_scores["rouge1"].fmeasure
        results[f"{model_name}_rouge2_f1"] = rouge_scores["rouge2"].fmeasure
        results[f"{model_name}_rougeL_f1"] = rouge_scores["rougeLsum"].fmeasure

    # Then, compute BERTScore for all candidate texts in a single pass
    # BERTScore requires lists of candidate strings and reference strings
    candidate_texts = list(candidate_summaries.values())
    reference_texts = [reference_text] * len(candidate_texts)

    # This example uses a DeBERTa model for BERTScore
    if language == 'English':
        P, R, F1 = bert_score(
            cands=candidate_texts,
            refs=reference_texts,
            model_type="microsoft/deberta-xlarge-mnli",
            lang='en',
            verbose=False,
            idf=False,
            batch_size=4,
            device="cuda" if torch.cuda.is_available() else "cpu"
        )
    elif language == 'German':
        P, R, F1 = bert_score(
        cands=candidate_texts,
        refs=reference_texts,
        model_type="deepset/gbert-large",
        lang='de',  
        num_layers=24,
        verbose=False,
        idf=False,
        batch_size=4,
        device="cuda" if torch.cuda.is_available() else "cpu"
    )

    # BERTScore returns a list of precision, recall, F1 for each candidate
    # Match them to the correct model
    for idx, model_name in enumerate(candidate_summaries.keys()):
        results[f"{model_name}_bert_p"]  = P[idx].item()
        results[f"{model_name}_bert_r"]  = R[idx].item()
        results[f"{model_name}_bert_f1"] = F1[idx].item()

    return results

##############################################################################
# Main pipeline
##############################################################################
def main():
    # --------------------------------------------------------------------------
    # 1. LOAD DATASET (assume we have reference_summary in the CSV as well)
    # --------------------------------------------------------------------------
    input_csv_path = Path("./output/final_fn/metrics/final_english_meetings_aggregated.csv")
    df = pd.read_csv(input_csv_path)

    # Lists to store all results
    all_summaries = []
    all_evals = []
    all_meetings = []
    all_ref_summaries = []

    # LLM clients
    
    GPT_MODEL_CONFIG_PATH = "./../config_gpt.json"

    with open(GPT_MODEL_CONFIG_PATH) as config_file:
        config = json.load(config_file)
    
    API_KEY = config["api_key"]
    API_VERSION = config["api_version"]
    ENDPOINT = config["endpoint"]
    
    client_gpt = AzureOpenAI(
        api_key=API_KEY,
        api_version= API_VERSION,
        azure_endpoint=ENDPOINT,
    )

    # client_gemini = ...

    # Map model names to the corresponding client object
    model_client_map = {
        "gpt-4o": client_gpt,
         # "gemini": client_gemini,
    }

    # -----------------------------------------------------------
    # 2. FOR EACH SAMPLE, CALL MODELS & THEN EVALUATE SUMMARIES
    # -----------------------------------------------------------
    meeting_language = "English"
    for idx, row in df.iterrows():
        text_to_summarize = row["Meeting"]
        reference_summary = row["Summary"]

        # Example prompt
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Summarize the following meeting transcript (in {meeting_language}){text_to_summarize}.\n Output just the summary text (complete; without bullet points) (use {meeting_language} ) within <summary> </summary> tags and no additional text. The summary must be **strictly under 250 words**."}
        ]

        # Suppose you want to run multiple models for each sample
        model_list = ["gpt-4o"]  # Example placeholders -  "gemini"
        summaries_for_this_sample = {}

        for model_name in model_list:
            
            # Grab the right client from the dictionary
        # If a client is not found, you might raise an error or skip
            client_for_this_model = model_client_map.get(model_name, None)
            if client_for_this_model is None:
                raise ValueError(f"No client found for model '{model_name}'")

            print(f"{model_name} summarizing the meeting...")
            response = ModelHandler.call_model_with_retry(
                client=client_for_this_model,
                messages=messages,
                model=model_name,
                max_tokens=310,
                max_attempts=3,
                base_delay=1.0
            )

            # Extract text from the LLM response
            full_model_response = response.choices[0].message.content.strip()
            candidate_summary = extract_content_between_tags(full_model_response, 'summary')
            
            print("---"*20)
            print(candidate_summary)
            print("---"*20)
            summaries_for_this_sample[model_name] = candidate_summary

        # Evaluate the summaries from all models against the reference
        eval_results = evaluate_summaries(summaries_for_this_sample, reference_summary, meeting_language)

        # Collect data for each sample
        all_summaries.append(summaries_for_this_sample)
        all_evals.append(eval_results)
        all_meetings.append(text_to_summarize)
        all_ref_summaries.append(reference_summary)

    # --------------------------------------------------------------------
    # 3. BUILD A DATAFRAME OF RESULTS (SUMMARIES + METRICS) & SAVE TO CSV
    # --------------------------------------------------------------------
    output_data = []
    for meeting, ref_summary, summaries_dict, eval_dict in zip(all_meetings, all_ref_summaries, all_summaries, all_evals):
        # One row of output combining the raw summaries and the evaluation metrics
        row_dict = {}

        # Add each model's generated summary
        for model_name, summary_text in summaries_dict.items():
            row_dict[f"{model_name}_summary"] = summary_text

        # Add each model's metrics from eval_dict
        # These keys are e.g. "gpt-4_rouge1_f1", "gpt-4_bert_f1", ...
        for metric_key, metric_value in eval_dict.items():
            row_dict[metric_key] = metric_value
        row_dict["Meeting"] = meeting
        row_dict["ref_summary"] = ref_summary

        output_data.append(row_dict)

    # Convert to DataFrame
    output_df = pd.DataFrame(output_data)
    output_csv_path = Path("./output/final_fn/metrics/summary_eval/english_summary_assessment_gpt-4o.csv")
    output_df.to_csv(output_csv_path, index=False)

    print(f"Processing complete. Results saved to: {output_csv_path}")

if __name__ == "__main__":
    main()

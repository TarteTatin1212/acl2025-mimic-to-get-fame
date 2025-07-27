import os
import glob
import re
import pandas as pd
from typing import List

def convert_confidence(value):
    """
    Convert a confidence value to float. Removes '%' if present.
    """
    if isinstance(value, str):
        # Remove percentage symbol if present and strip whitespace
        value = value.replace('%', '').strip()
    try:
        return float(value)
    except ValueError:
        return None

def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process the DataFrame to convert confidence columns from percentages to float.
    """
    for col in df.columns:
        if "confidence" in col.lower():
            # Apply conversion to each value in the confidence column
            df[col] = df[col].apply(convert_confidence)
    return df

def aggregate_metrics(dataframes: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Compute mean and std for each metric across all provided dataframes.
    """
    # Concatenate all dataframes into one
    combined_df = pd.concat(dataframes, ignore_index=True)

    # Exclude non-metric columns if necessary, e.g., 'Title' and 'Meeting'

    substrings = ['confidence', 'score']

    metric_cols = combined_df.columns[combined_df.columns.str.contains('|'.join(substrings), case=False)]

    # Prepare a dictionary for aggregated metrics
    aggregated_data = {}
    for col in metric_cols:
        # Ensure the column is numeric; non-numeric entries are skipped
        numeric_values = pd.to_numeric(combined_df[col], errors='coerce')
        aggregated_data[f"{col} mean"] = numeric_values.mean()
        aggregated_data[f"{col} std"] = numeric_values.std()

    # Create a DataFrame with a single row containing mean and std values
    agg_df = pd.DataFrame(aggregated_data, index=[0])
    return combined_df, agg_df

def consolidate_meetings(dataframes: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Consolidate each meeting into a single DataFrame.
    Each row corresponds to one CSV file's data.
    """
    # Concatenate all meeting dataframes; assuming each CSV is one meeting row
    consolidated_df = pd.concat(dataframes, ignore_index=True)
    return consolidated_df

def process_directory(input_folder: str, output_eval_csv: str, output_agg_csv: str):
    """
    Processes all CSV files in the input_folder, computes aggregated metrics,
    and consolidates meetings into a single CSV file.
    """
    csv_files = glob.glob(os.path.join(input_folder, "*.csv"))
    if not csv_files:
        print(f"No CSV files found in {input_folder}")
        return

    meeting_dfs = []
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            # Preprocess the DataFrame, especially confidence columns
            df = preprocess_dataframe(df)
            meeting_dfs.append(df)
        except Exception as e:
            print(f"Error processing {file}: {e}")

    if not meeting_dfs:
        print("No valid meetings found.")
        return

    # Aggregate metrics across all meetings
    combined_df, agg_metrics_df = aggregate_metrics(meeting_dfs)
    agg_metrics_df.to_csv(output_eval_csv, index=False)
    print(f"Aggregated metrics saved to: {output_eval_csv}")

    # Consolidate all meetings into a single CSV file
    consolidated_df = consolidate_meetings(meeting_dfs)
    consolidated_df.to_csv(output_agg_csv, index=False)
    print(f"Consolidated meetings saved to: {output_agg_csv}")

if __name__ == "__main__":
    # Define paths as needed
    input_folder = "./output/final_fn/missed_eng"  # Folder containing individual meeting CSV files
    output_eval_csv = "./output/final_fn/metrics/missing_english_meetings_evaluation.csv"  # Output CSV for aggregated metrics
    output_agg_csv = "./output/final_fn/metrics/missing_english_meetings_aggregated.csv"   # Output CSV for consolidated meetings

    process_directory(input_folder, output_eval_csv, output_agg_csv)
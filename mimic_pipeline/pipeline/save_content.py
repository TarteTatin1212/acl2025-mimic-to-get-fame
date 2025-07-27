import pandas as pd
import json

class Saver:
    @staticmethod
    def save_csv(
        title,
        article,
        tags,
        personas,
        summary,
        meeting_plan,
        meeting,
        file_path='output.csv',
        basic_evaluation=None,
        psychology_evaluation=None,
    ):
        """
        Save meeting content and evaluations to CSV.
        
        Args:
            title (str): Article title
            article (str): Original article text
            tags (list): Article tags
            personas (str): Meeting participants/personas
            summary (str): Meeting summary
            meeting_plan (list): Planned meeting structure
            meeting (str): Generated meeting transcript
            basic_evaluation (dict): Basic LLM evaluation results
            psychology_evaluation (dict): Psychology-based evaluation results
            file_path (str): Output file path
        """
        # ---------- 1.  Build the core data ----------
        data = {
            'Title': [title],
            'Article': [article],
            'Tags': [json.dumps(tags)],        # list → JSON string
            'Personas': [personas],
            'Summary': [summary],
            'Meeting_Plan': [json.dumps(meeting_plan)],
            'Meeting': [meeting],
        }

        # ---------- 2.  Optional: basic evaluation ----------
        if basic_evaluation is not None:
            basic_eval_formatted = {
                f"Basic_{crit}_{k}": v
                for crit, res in basic_evaluation.items()
                for k, v in res.items()
            }
            data.update({k: [v] for k, v in basic_eval_formatted.items()})

        # ---------- 3.  Optional: psychology evaluation ----------
        if psychology_evaluation is not None:
            psych_eval_formatted = {
                f"Psych_{crit}_{k}": v
                for crit, res in psychology_evaluation.items()
                for k, v in res.items()
            }
            data.update({k: [v] for k, v in psych_eval_formatted.items()})

        # ---------- 4.  Save ----------
        df = pd.DataFrame(data)
        print(f"Saving the final meeting at: {file_path}")
        df.to_csv(file_path, index=False)

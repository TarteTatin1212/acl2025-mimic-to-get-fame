import re

class Utils():
    @staticmethod
    def clean_summary(text):
        lines = text.split("\n")
        start_index = next((i for i, line in enumerate(lines) if not line.startswith(("Here is", "Here's"))), 0)
        end_index = next((i for i, line in enumerate(lines) if line.startswith(("This summary"))), -1)
        summary_lines = lines[start_index: end_index]
        summary = "".join(summary_lines)
        return summary.strip()
    
    @staticmethod
    def clean_model_output(model_output):
        json_part = model_output[model_output.find('{'):model_output.rfind('}')+1]
        return json_part

    @staticmethod
    def chunk_meeting_transcript(transcript, max_chunk_size=500):
        chunks = []
        speaker_turn_pattern = re.compile(r'([A-Za-z ]{1,}(?: [A-Za-z\.\(\),\-]*)*):\s+')
        segments = speaker_turn_pattern.split(transcript.strip())
        speaker_turns = [f'{segments[i]}: {segments[i + 1]}' for i in range(1, len(segments) - 1, 2)]
        current_chunk = ""
        current_chunk_word_count = 0

        for turn in speaker_turns:
            turn_word_count = len(turn.split())
            if current_chunk_word_count + turn_word_count > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = turn
                current_chunk_word_count = turn_word_count
            else:
                current_chunk += " " + turn
                current_chunk_word_count += turn_word_count

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks
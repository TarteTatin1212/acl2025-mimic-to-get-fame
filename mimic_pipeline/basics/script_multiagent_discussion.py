import openai
# import tiktoken
import json
from openai import OpenAI
from collections import Counter
import re
import evaluate
import transformers
import pandas as pd

## Global Variables
# Initialize the OPEN AI API client
api_key = 'OPEN_AI_KEY'
client = OpenAI(api_key=api_key)
model_id = 'gpt-4-turbo'  # Model ID for GPT-4-Turbo
num_agents = 3
max_chunk_size = 5000


# encoding = tiktoken.get_encoding('cl100k_base')
# def count_tokens(text):
#     return len(encoding.encode(text))


def clean_model_output(model_output):
    json_part = model_output[model_output.find('{'):model_output.rfind('}')+1]
    return json_part


class Coordinator:
    def __init__(self, client, model_id, base_prompt):
        self.client = client
        self.model_id = model_id
        self.base_prompt = base_prompt

    def generate_personas(self, task_description, meeting_transcript, num_agents):
        participants = []
        for _ in range(num_agents):
            current_prompt = [
                self.base_prompt,
                {
                    "role": "user",
                    "content": f"\nNow generate a participant to discuss the following task:\nTask: {task_description}\nInitial Meeting Transcript: {meeting_transcript}\n",
                }
            ]
            if participants:
                current_prompt.append({
                    "role": "user",
                    "content": f"Already Generated Participants:\n{json.dumps(participants, indent=2)}\n"
                })

            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=current_prompt
            )
            new_participant = json.loads(clean_model_output(response.choices[0].message.content))
            participants.append(new_participant)

        return participants


class DiscussionCoordinator:
    def __init__(self, client, model_id, agents, token_limit):
        self.client = client
        self.model_id = model_id
        self.agents = agents
        self.memories = [[] for _ in agents]
        self.token_limit = token_limit
        self.processed_tokens = 0
        self.global_summary = ""


    def chunk_meeting_transcript(self, transcript, max_chunk_size=500):
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


    def get_memory_string(self, agent_index, context_length):
        memory_string = " ".join([" ".join(map(str, item)) for item in self.memories[agent_index][-context_length:]]) if self.memories[agent_index] else ""
        current_draft = self.memories[agent_index][-1] if self.memories[agent_index] else "Initial draft content here"
        return memory_string, current_draft


    def update_memories(self, agent_index, new_memory):
        self.memories[agent_index].append(new_memory)


    def participate(self, template_filling):
        task_instruction = (
            "You are {persona}, tasked with summarizing the meeting transcript. "
            "Focus on your unique perspective or expertise as {role} to enhance the summary. "
            "Utilize all fields of the provided context, including the current draft, the original meeting transcript, "
            "previous summaries, and feedback from all agents. "
            "Even if the current chunk/ meeting transcript does not have some details, use the information from the currentDraft and previousSummary "
            "to create a comprehensive and cohesive summary. "
            "Ensure your summary is coherent, cohesive, and incorporates the best points from each agent. "
            "Do not include any introductory or closing statements; provide only the summary text. "
            "Start your summary directly with the content without any preamble."
        )
        template_filling["taskInstruction"] = task_instruction.format(persona=template_filling["persona"], role=template_filling["personaDescription"])
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "system", "content": json.dumps(template_filling)}],
            # max_tokens=1500
        )
        # self.processed_tokens += 1500
        draft = response.choices[0].message.content
        return draft


    def vote_best_summary(self, buffer):
        votes = []
        for agent_index, agent in enumerate(self.agents):
            memory_string, current_draft = self.get_memory_string(agent_index, context_length=5)
            template_filling = {
                "taskInstruction": """Vote for the best summary from the provided list. Your vote should be the index number of the best summary.
                                    e.g, if the summary at the index location 1 is the best, your response should be just 1, NOTHING more!
                                    When voting, please ensure you use zero-based indexing. For example, if you are choosing the first summary, vote '0'.
                                    If you are choosing the second summary, vote '1', and so on.""",
                "summaries": buffer,
                "persona": agent["role"],
                "personaDescription": agent["description"],
                "agentMemory": memory_string
            }
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "system", "content": json.dumps(template_filling)}],
                # max_tokens=100
            )
            # self.processed_tokens += 100
            vote = int(response.choices[0].message.content.strip())
            votes.append(vote)

        # Determine the most voted summary
        vote_count = Counter(votes)
        best_summary_index = vote_count.most_common(1)[0][0]
        best_summary = buffer[best_summary_index]

        return best_summary


    def discuss(self, task_instruction, input_str, prev_summary="", max_turns=3, context_length=5):
        turn = 0
        decision = False
        current_draft = ""

        while not decision and turn < max_turns:
            turn += 1
            buffer = []
            for agent_index, agent in enumerate(self.agents):
                memory_string, current_draft = self.get_memory_string(agent_index, context_length)
                template_filling = {
                    "taskInstruction": task_instruction,
                    "input": input_str,
                    "currentDraft": current_draft,
                    "persona": agent["role"],
                    "personaDescription": agent["description"],
                    "agentMemory": memory_string,
                    "previousSummary": prev_summary
                }
                response = self.participate(template_filling)
                buffer.append(response)

            for agent_index in range(len(self.agents)):
                self.update_memories(agent_index, buffer)

            current_draft = self.vote_best_summary(buffer)

            if turn >= max_turns:
                decision = True

        final_draft = current_draft if current_draft else "No summary generated."
        return final_draft, turn
        

    def process_transcript(self, transcript, max_chunk_size=500):
        chunks = self.chunk_meeting_transcript(transcript, max_chunk_size)
        global_summary = ""

        # Define initial and interim prompts
        task_instruction_init = """
        Below is the beginning segment of a meeting transcript:

        ---

        {}

        ---

        We are summarizing a meeting transcript in segments to create a comprehensive summary of the entire discussion. Provide a summary for the excerpt above, focusing on:

        1. Key discussion points and decisions
        2. Action items or tasks assigned
        3. Important questions raised or issues identified
        4. Participant contributions and their roles (if mentioned)
        5. Any background information or context provided

        Introduce participants, projects, or technical terms if they are mentioned for the first time. The meeting may include non-linear discussions, tangents, or revisiting of previous topics. Organize the summary to present a logical flow of information.

        Create a summary that reads as if written in one cohesive piece, despite the segmented nature of this process. The summary may consist of multiple paragraphs if needed.

        Summary:
        """

        task_instruction_interim = """
        Below is a segment from a meeting transcript:

        ---

        {}

        ---

        Here is the summary of the meeting up to this point:

        ---

        {}

        ---

        We are summarizing a meeting transcript in segments to create a comprehensive summary of the entire discussion. Update the existing summary to incorporate new relevant information from the current segment, including:

        1. New or expanded discussion points
        2. Additional decisions made or action items assigned
        3. Further questions raised or issues identified
        4. New participant contributions or changes in discussion dynamics
        5. Any clarifications or updates to previously mentioned information

        Introduce new participants, projects, or technical terms if they appear for the first time. The meeting may include non-linear discussions, tangents, or revisiting of previous topics. Maintain a logical flow of information in your summary.

        Ensure the updated summary reads as a cohesive piece, integrating the new information seamlessly. The summary may consist of multiple paragraphs if needed.

        Updated summary:
        """

        # Process each chunk sequentially
        for i, chunk in enumerate(chunks):
            if i == 0:
                task_instruction = task_instruction_init.format(chunk)
            else:
                task_instruction = task_instruction_interim.format(chunk, global_summary)

            chunk_summary, turns_taken = self.discuss(task_instruction, chunk, global_summary)
            global_summary = chunk_summary  # Update global summary with the chunk summary

        return global_summary.strip()


def clean_summary(text):
    # Split the text into lines
    lines = text.split("\n")

    # Find the index of the first line that doesn't start with "Here is"
    start_index = next((i for i, line in enumerate(lines) if not line.startswith(("Here is", "Here's"))), 0)

    # Find the index of the first line that starts with "This summary"
    end_index = next((i for i, line in enumerate(lines) if line.startswith(("This summary"))), -1)

    # Extract the summary lines
    summary_lines = lines[start_index: end_index]

    # Join the summary lines back into a single string
    summary = "".join(summary_lines)

    return summary.strip()


# Load the evaluation metrics
rouge = evaluate.load('rouge')
bertscore = evaluate.load('bertscore')
def evaluate_summaries(references, predictions):
    # Calculate ROUGE scores
    rouge_scores = rouge.compute(predictions=predictions, references=references, use_aggregator=True)

    # Calculate BERTScore
    bertscore_results = bertscore.compute(predictions=predictions, references=references, model_type="bert-base-uncased", rescale_with_baseline=True, lang="en")

    # Extract relevant ROUGE scores
    rouge_1 = rouge_scores['rouge1']
    rouge_2 = rouge_scores['rouge2']
    rouge_lsum = rouge_scores['rougeLsum']

    # Extract BERTScore
    bertscore_f1 = bertscore_results['f1']

    # Print results
    print(f"BERTScore (reweighted): {sum(bertscore_f1)/len(bertscore_f1)}")
    print(f"ROUGE-1: {rouge_1}")
    print(f"ROUGE-2: {rouge_2}")
    print(f"ROUGE-LSum: {rouge_lsum}")

    return {
        "BERTScore (reweighted)": sum(bertscore_f1)/len(bertscore_f1),
        "ROUGE-1": rouge_1,
        "ROUGE-2": rouge_2,
        "ROUGE-LSum": rouge_lsum
    }


# Define the evaluation prompts based on the referenced paper
INF_PROMPT = (
    "A summary should convey the main idea and the most important details of the original article in a concise and clear way. "
    "A summary should avoid repeating information that has already been mentioned or is irrelevant to the article’s main point. "
    "A summary should use accurate and specific words to describe the article’s content, and avoid vague or ambiguous expressions. "
    "A summary should maintain the same tone and perspective as the original article, and avoid adding personal opinions or interpretations. "
    "A summary should follow the logical order and structure of the original article, and use transition words or phrases to connect sentences if needed. "
    "Rate the summary on a scale of 1 to 5, where 1 means the summary meets none of the criteria and 5 means the summary meets all the criteria without significant flaws or errors. "
    "Output only a float between 1 and 5 as the score. "
    "Summary: {}"
)

CON_PROMPT = (
    "A summary is consistent with the article if it accurately and faithfully reflects the main points, facts, and tone of the original article, without changing, adding, or omitting any significant information. "
    "A summary should avoid introducing any errors, contradictions, or distortions of the original article, unless they are explicitly marked as the summary writer’s opinions or interpretations. "
    "A summary should use clear and precise language that matches the style and genre of the article, and avoid any vague or ambiguous expressions that could mislead the reader or obscure the meaning of the article. "
    "Rate the summary on a scale of 1 to 5, where 1 means the summary meets none of the criteria and 5 means the summary meets all the criteria without significant flaws or errors. "
    "Output only a float between 1 and 5 as the score. "
    "Summary: {}"
)

COH_PROMPT = (
    "Coherence is the quality of being consistent, logical, and well-organized in the summary. "
    "A summary is coherent if it accurately captures the main ideas and key information from the article, and presents them in a clear and concise manner. "
    "A summary is not coherent if it omits important details, contradicts the article, or introduces irrelevant or confusing information. "
    "Rate the summary on a scale of 1 to 5, where 1 means the summary meets none of the criteria and 5 means the summary meets all the criteria without significant flaws or errors. "
    "Output only a float between 1 and 5 as the score. "
    "Summary: {}"
)

FLU_PROMPT = (
    "A fluent summary should reflect the main content and structure of the original article, using clear and coherent language that avoids redundancy and errors. "
    "A fluent summary should retain the key information and details from the article, without introducing any irrelevant or inaccurate information that distorts the meaning of the original text. "
    "Rate the summary on a scale of 1 to 5, where 1 means the summary meets none of the criteria and 5 means the summary meets all the criteria without significant flaws or errors. "
    "Output only a float between 1 and 5 as the score. "
    "Summary: {}"
)

REL_PROMPT = (
    "A summary is relevant if it captures the main points of the most relevant information from the article, without leaving out any crucial details or adding any unnecessary or inaccurate information. "
    "A summary is more relevant if it uses the same or similar terms and expressions as the article, as long as they are accurate and concise. "
    "Rate the summary on a scale of 1 to 5, where 1 means the summary meets none of the criteria and 5 means the summary meets all the criteria without significant flaws or errors. "
    "Output only a float between 1 and 5 as the score. "
    "Summary: {}\nOriginal transcript: {}"
)


def llm_based_evaluation(original_transcript, generated_summary, client, model_id):

    criteria = ['INF', 'COH', 'CON', 'FLU', 'REL']
    prompts = {
        'INF': f"""Original transcript:\n\n{original_transcript}\n\nGenerated summary:\n\n{generated_summary}\n\nEvaluate the informativeness of the summary based on the following criteria:
- A summary should convey the main idea and the most important details of the original article in a concise and clear way.
- A summary should avoid repeating information that has already been mentioned or is irrelevant to the article's main point.
- A summary should use accurate and specific words to describe the article's content, and avoid vague or ambiguous expressions.
- A summary should maintain the same tone and perspective as the original article, and avoid adding personal opinions or interpretations.
- A summary should follow the logical order and structure of the original article, and use transition words or phrases to connect sentences if needed.

Score the summary on a scale of 1 to 5, where:
5: The summary meets all the criteria and has no significant flaws or errors.
4: The summary meets most of the criteria and has minor flaws or errors that do not affect the overall comprehension.
3: The summary meets some of the criteria and has moderate flaws or errors that affect the comprehension of some parts.
2: The summary meets few of the criteria and has major flaws or errors that affect the comprehension of most parts.
1: The summary meets none of the criteria and has severe flaws or errors that make it incomprehensible.

Output only a single float number between 1 and 5 as the score, with up to one decimal place if needed.""",

        'COH': f"""Original transcript:\n\n{original_transcript}\n\nGenerated summary:\n\n{generated_summary}\n\nEvaluate the coherence of the summary based on the following criteria:
Coherence is the quality of being consistent, logical, and well-organized in the summary. A summary is coherent if it accurately captures the main ideas and key information from the article, and presents them in a clear and concise manner. A summary is not coherent if it omits important details, contradicts the article, or introduces irrelevant or confusing information.

Score the summary on a scale of 1 to 5, where:
5: The summary is very coherent, with no errors or flaws.
4: The summary is mostly coherent, with only minor errors or gaps.
3: The summary is somewhat coherent, but has some significant errors or omissions.
2: The summary is poorly coherent, with many errors, inconsistencies, or redundancies.
1: The summary is not coherent at all, with little or no relation to the article.

Output only a single float number between 1 and 5 as the score, with up to one decimal place if needed.""",

        'CON': f"""Original transcript:\n\n{original_transcript}\n\nGenerated summary:\n\n{generated_summary}\n\nEvaluate the consistency of the summary based on the following criteria:
- A summary is consistent with the article if it accurately and faithfully reflects the main points, facts, and tone of the article without changing, adding, or omitting any significant information.
- A summary should avoid introducing any errors, contradictions, or distortions of the original article, unless they are explicitly marked as the summary writer's opinions or interpretations.
- A summary should use clear and precise language that matches the style and genre of the article, and avoid any vague or ambiguous expressions that could mislead the reader or obscure the meaning of the article.
- A summary should maintain the logical structure and coherence of the article, and present the information in a well-organized and easy-to-follow manner.
- A summary should be concise and avoid any unnecessary or redundant details that do not contribute to the main purpose or message of the article.

Score the summary on a scale of 1 to 5, where 5 is perfectly consistent and 1 is completely inconsistent.

Output only a single float number between 1 and 5 as the score, with up to one decimal place if needed.""",

        'FLU': f"""Original transcript:\n\n{original_transcript}\n\nGenerated summary:\n\n{generated_summary}\n\nEvaluate the fluency of the summary based on the following criteria:
- A fluent summary should reflect the main content and structure of the original article, using clear and coherent language that avoids redundancy and errors.
- A fluent summary should retain the key information and details from the article, without introducing any irrelevant or inaccurate information that distorts the meaning of the original text.
- A fluent summary should use appropriate transition words, connectors, and referents to ensure the logical flow and cohesion of the summary, and avoid abrupt or confusing shifts in topic or perspective.
- A fluent summary should use varied and precise vocabulary and grammar that suits the tone and style of the article, and avoid repetition or ambiguity.
- A fluent summary should use correct spelling, punctuation, and capitalization throughout the summary, and follow the conventions of standard written English.

Score the summary on a scale of 1 to 5, where:
5: The summary is fluent and meets all the criteria listed above.
4: The summary is mostly fluent and meets most of the criteria listed above.
3: The summary is somewhat fluent and meets some of the criteria listed above.
2: The summary is not very fluent and meets few of the criteria listed above.
1: The summary is not fluent and meets none of the criteria listed above.

Output only a single float number between 1 and 5 as the score, with up to one decimal place if needed.""",

        'REL': f"""Original transcript:\n\n{original_transcript}\n\nGenerated summary:\n\n{generated_summary}\n\nEvaluate the relevance of the summary based on the following criteria:
- A summary is relevant if it captures the main points or the most important information from the article, without leaving out any crucial details or adding any unnecessary or inaccurate ones.
- A summary is more relevant if it uses the same or similar terms and expressions as the article, as long as they are clear and concise.
- A summary is less relevant if it omits or misrepresents some of the key facts or arguments from the article, or if it introduces irrelevant or erroneous information that is not supported by the article.
- A summary is irrelevant if it does not correspond to the article at all, or if it only mentions a minor or peripheral aspect of the article.

Score the summary on a scale of 1 to 5, where 5 is highly relevant and 1 is completely irrelevant.

Output only a single float number between 1 and 5 as the score, with up to one decimal place if needed."""
    }

    results = {}

    for criterion in criteria:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "You are an expert in evaluating text summaries. Provide only the numerical score as requested."},
                {"role": "user", "content": prompts[criterion]}
            ]
        )
        score_str = response.choices[0].message.content.strip()
        try:
            score = float(score_str)
            results[criterion] = round(max(1.0, min(5.0, score)), 1)  # Ensure score is between 1 and 5
        except ValueError:
            results[criterion] = "Error: Invalid score"

    return results


def process_and_evaluate(df, client, model_id, num_agents, max_chunk_size=500):
    results = []
    for index, row in df.iterrows():
        transcript = row['transcript']
        original_summary = row['summary']
        base_prompt = {
            "role": "system",
            "content": """
            When faced with a task, begin by identifying the participants who will contribute to solving the task. Provide role and description of the participants, describing their expertise or needs, formatted using the provided JSON schema.
            Generate one participant at a time, complementing the existing participants to foster a rich discussion.
            Task: Explain the basics of machine learning to high school students.
            New Participant:
            {"role": "Educator", "description": "An experienced teacher who simplifies complex topics for teenagers."}

            Example 2:
            Task: Develop a new mobile app for tracking daily exercise.
            Already Generated Participants:
            {"role": "Fitness Coach", "description": "A person that has high knowledge about sports and fitness."}
            New Participant:
            {"role": "Software Developer", "description": "A creative developer with experience in mobile applications and user interface design."}

            Example 3:
            Task: Write a guide on how to cook Italian food for beginners.
            Already Generated Participants:
            {"role": "Italian Native", "description": "An average home cook that lived in Italy for 30 years."}
            {"role": "Food Scientist", "description": "An educated scientist that knows which flavour combinations result in the best taste."}
            New Participant:
            {"role": "Chef", "description": "A professional chef specializing in Italian cuisine who enjoys teaching cooking techniques."}
            """
        }

        coordinator = Coordinator(client, model_id, base_prompt)
        task_description = "Summarize a given meeting transcript."
        agents = coordinator.generate_personas(task_description, transcript, num_agents)

        # Initialize the Discussion Coordinator
        discussion_coordinator = DiscussionCoordinator(client, model_id, agents,
                                            #    token_limit=2048
                                            )

        # Process the transcript to get the generated summary
        generated_summary = clean_summary(discussion_coordinator.process_transcript(transcript, max_chunk_size))

        # Evaluate the generated summary using LLM-based evaluation
        llm_evaluation_results = llm_based_evaluation(generated_summary, transcript, client, model_id)

        # Evaluate the generated summary using traditional metrics (ROUGE and BERTScore)
        traditional_evaluation_results = evaluate_summaries([original_summary], [generated_summary])

        # Store the results
        results.append({
            'transcript': transcript,
            'original_summary': original_summary,
            'generated_summary': generated_summary,
            'llm_informativeness': llm_evaluation_results['INF'],
            'llm_conciseness': llm_evaluation_results['CON'],
            'llm_coherence': llm_evaluation_results['COH'],
            'llm_fluency': llm_evaluation_results['FLU'],
            'llm_relevance': llm_evaluation_results['REL'],
            'bert_score': traditional_evaluation_results['BERTScore (reweighted)'],
            'rouge_1': traditional_evaluation_results['ROUGE-1'],
            'rouge_2': traditional_evaluation_results['ROUGE-2'],
            'rouge_lsum': traditional_evaluation_results['ROUGE-LSum']
        })

    return pd.DataFrame(results)


qmsum_df = pd.read_csv('qmsum_test.csv')
evaluation_df = process_and_evaluate(qmsum_df, OpenAI(api_key=api_key), model_id, num_agents, max_chunk_size)
evaluation_df.to_csv('evaluation_results.csv', index=False)



from collections import Counter
import json
from scripts.model_handler import ModelHandler
from scripts.memory_handler import MemoryHandler
import logging
import re

class AgreementProtocol:
    
    def __init__(self, client, model_id, agents, memory, agreement="vote", voting_criteria=""):
        self.client = client
        self.model_id = model_id
        self.agents = agents
        self.memory = memory
        self.agreement = agreement
        self.agreement_protocol = {
            "vote": self.vote_best_summary,
            "stop_dialogue_vote": self.vote_dialogue_end,
        }
        self.voting_criteria = voting_criteria
    
    
    def run_protocol(self, input):
        return self.agreement_protocol[self.agreement](input)
    
    def vote_dialogue_end(self, input):
        dialogue_draft = input.get('dialogue_draft', '')
        discussion_plan = input.get('discussion_plan', '')
        related_article = input.get('related_article', '')
        votes = []
        for agent_index, agent in enumerate(self.agents):
            system_prompt = (
                f"You are an actor, tasked to play {agent['role']} and participate in a staged discussion. "
                f"Focus on your unique perspective or expertise as {agent['description']}"
                f"Please vote if you want to continue the discussion. {self.voting_criteria}\n\n"
            )
            
            user_prompt = (
                f"Here is the discussion so far: \n{dialogue_draft}.\n"
                f"For your decision, consider if the discussion so far covers the outline for the dialogue: \n{discussion_plan}.\n"
                f"Assess whether all points in the discussion plan have been adequeatly covered in the discussion so far. "
                f"If and only if you identify  that some points are missing, you can consider if something can be added from the related article. "
                f"Otherwise, you can conclude that the discussion has sufficiently covered all imprtant points.\n"
                f"Related article:\n{related_article}.\n"
                f"Definitely think step by step here (Chain of thought) before you vote.\n\n"
                "Respond **ONLY** with a valid JSON object strictly in the following format, without any additional text or explanation:\n"
                "```json\n"
                "{\n"
                '  "reasoning": "<your chain of thought process>",\n'
                '  "vote": <your vote, 0 for stop, 1 for continue>\n'
                "}\n"
                "```"
            )
            
            message = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
            
            response = ModelHandler.call_model_with_retry(self.client, message, self.model_id)
            response = response.choices[0].message.content.strip()
            response = response.replace('```json', '').replace('```python', '').replace('```', '')
            
            response = self.extract_json_from_text(response)
            
            vote = response.get('vote')
            votes.append(vote)
        
        votes_sum = sum(votes)
        vote_avg = votes_sum/len(self.agents)
        if vote_avg < 0.5:
            return True
        else:
            return False
    
    def vote_best_summary(self, buffer):
        votes = []
        for agent_index, agent in enumerate(self.agents):
            memory_string, _ = self.memory.get_memory_string(agent_index, context_length=5)
            max_index = len(buffer) - 1
            template_filling = {
                "taskInstruction": f"""Vote for the best summary from the provided list. Your vote should be the index number of the best summary.
                                    e.g, if the summary at the index location 1 is the best, your response should be just 1, NOTHING more!
                                    When voting, please ensure you use zero-based indexing. For example, if you are choosing the first summary, vote '0'.
                                    If you are choosing the second summary, vote '1', and so on.
                                    The highest number you can vote is {max_index}""",
                "summaries": buffer,
                "persona": agent["role"],
                "personaDescription": agent["description"],
                "agentMemory": memory_string
            }
            
            response = ModelHandler.call_model_with_retry(self.client, [{"role": "system", "content": json.dumps(template_filling)}], self.model_id)
            
            vote = int(response.choices[0].message.content.strip())
            votes.append(vote)

        # Determine the most voted summary
        vote_count = Counter(votes)
        best_summary_index = vote_count.most_common(1)[0][0]
        logging.info(best_summary_index)
        best_summary = buffer[best_summary_index]

        return best_summary

    def extract_json_from_text(self, text):
        """
        Extracts the first valid JSON object from a string of text.
        Handles potential formatting issues and invalid control characters.
    
        :param text: The text to search for a JSON object.
        :return: Parsed JSON object if found, or a default error message.
        """
        # Remove leading and trailing whitespace
        text = text.strip()
    
        # Find the first occurrence of '{' and the last occurrence of '}'
        start = text.find('{')
        end = text.rfind('}')
    
        if start != -1 and end != -1 and start < end:
            json_string = text[start:end+1]
        
        
            # Remove any invalid control characters
            json_string = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', json_string)
            try:
                return json.loads(json_string)
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError: {str(e)}")
                print(f"Problematic JSON snippet: {json_string}")
    
        print("Error: No valid JSON object found in the text.")
        return {
            "reasoning": "Failed to parse JSON from model response.",
            "vote": 0
        }
import json
import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from basics.scripts.model_handler import ModelHandler
from basics.scripts.utils import Utils
import pprint
# from scripts.model_handler import ModelHandler
# from scripts.utils import Utils

from pydantic import BaseModel
from typing import List, Optional

class SpeakingStyle(BaseModel):
    tone: str
    language_complexity: str
    communication_style: str
    sentence_structure: str
    formality: str
    other_traits: str

class PersonalizedVocabulary(BaseModel):
    filler_words: List[str]
    catchphrases: List[str]
    speech_patterns: List[str]
    emotional_expressions: List[str]


class SpeakingStyleProfile(BaseModel):
    speaking_style: SpeakingStyle
    personalized_vocabulary: PersonalizedVocabulary

class PersonaGenerator:
    def __init__(self, client, model_id):
        self.client = client
        self.model_id = model_id
        self.participants_info = ""
        self.base_prompt = {
            "role": "system",
            "content": """
            When faced with a task, begin by identifying the participants who will contribute to solving the task. Provide **role** and **description** of the participants, describing their expertise or needs, formatted using the provided JSON schema.
            Generate one participant at a time, ensuring that they complement the existing participants to foster a rich and balanced discussion. Each participant should bring a unique **perspective** and **expertise** that enhances the overall discussion, avoiding redundancy.
            Task: Explain the basics of machine learning to high school students.
            New Participant:
            {"role": "Educator", "description": "An experienced teacher who simplifies complex topics for teenagers.", "expertise_area": "Education", "perspective": "Simplifier"}
            Example 2:
            Task: Develop a new mobile app for tracking daily exercise.
            Already Generated Participants:
            {"role": "Fitness Coach", "description": "A person that has high knowledge about sports and fitness.", "expertise_area": "Fitness", "perspective": "Practical Implementation"}
            New Participant:
            {"role": "Software Developer", "description": "A creative developer with experience in mobile applications and user interface design.", "expertise_area": "Software Development", "perspective": "Technical Implementation"}

            Example 3:
            Task: Write a guide on how to cook Italian food for beginners.
            Already Generated Participants:
            {"role": "Italian Native", "description": "An average home cook that lived in Italy for 30 years.", "expertise_area": "Culinary Arts", "perspective": "Cultural Authenticity"}
            {"role": "Food Scientist", "description": "An educated scientist that knows which flavour combinations result in the best taste.", "expertise_area": "Food Science", "perspective": "Scientific Analysis"}
            New Participant:
            {"role": "Chef", "description": "A professional chef specializing in Italian cuisine who enjoys teaching cooking techniques.", "expertise_area": "Culinary Arts", "perspective": "Practical Execution"}
            
            Example 4:
            Task: Strategize the expansion of a retail business into new markets.
            Already Generated Participants:
            {"role": "Market Analyst", "description": "An expert in analyzing market trends and consumer behavior.", "expertise_area": "Market Analysis", "perspective": "Data-Driven Insight"}
            {"role": "Financial Advisor", "description": "A specialist in financial planning and budgeting for business expansions.", "expertise_area": "Finance", "perspective": "Financial Feasibility"}
            New Participant:
            {"role": "Operations Manager", "description": "An experienced manager who oversees daily operations and ensures efficient implementation of strategies.", "expertise_area": "Operations", "perspective": "Operational Efficiency"}
            """
        }

    def generate_debators(self, task_description, meeting_transcript, num_agents):
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
            current_prompt.append({
                    "role": "user",
                    "content": (
                        "Only return a processable json. It should follow this format:\n" 
                        "{ \n"
                        "\"role\": \"<role name>\","
                        "\"description\": \"<description>\"\n"
                        "}"
                    )
            })

            response = ModelHandler.call_model_with_retry(self.client, current_prompt, self.model_id)
            generated_answer = Utils.clean_model_output(response.choices[0].message.content)
            try:
                new_participant = json.loads(generated_answer)
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {e}")
            
            participants.append(new_participant)

        return participants
    
    def generate_debators_from_article(self, task_description, article_title, article, tags, num_agents, meeting_type, language='English'):
        participants = []
        print(f"Article: {article_title}\nArticle Tags: {tags}\n")
        for _ in range(num_agents):
            current_prompt = [
                self.base_prompt,
                {
                    "role": "user",
                    "content": (
                        f"\nNow generate a participant to discuss the following task:\n"
                        f"Task: {task_description}\n"
                        f"Initial Article Title: {article_title}\n"
                        f"Article Content:\n{article}\n\n"
                        f"Some of the tags for this article to orient the participant selection on are: {tags}.\n"
                        f"In case the article tags aren't available/helpful, default to the article title and text for choosing the participants.\n"
                        f"Additionally, generate the participant roles in the target language - **{language}**\n"
                        f"Meeting Type: {meeting_type}"
                    )
                }
            ]
            if participants:
                current_prompt.append({
                    "role": "user",
                    "content": f"Already Generated Participants:\n{json.dumps(participants, indent=2)}\n"
                })
            current_prompt.append({
                    "role": "user",
                    "content": (
                        "Only return a processable json. It should follow this format:\n" 
                        "{ \n"
                        "\"role\": \"<role name>\",\n"
                        "\"description\": \"<description>\",\n"
                        "\"expertise_area\": \"<expertise_area>\",\n"
                        "\"perspective\": \"<perspective>\"\n"
                        "}"
                    )
            })

            response = ModelHandler.call_model_with_retry(self.client, current_prompt, self.model_id)
            generated_answer = Utils.clean_model_output(response.choices[0].message.content)
            try:
                new_participant = json.loads(generated_answer)
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {e}")
            
            print(f"New participant:")
            print(new_participant)
            updated_participant = self.generate_speaking_style_profile(new_participant, meeting_type, language)
            participants.append(updated_participant)

            self.participants_info += f"**{updated_participant.get('role', '')}**:\n"
            self.participants_info += f"  - Description/ Expertise: {updated_participant.get('description', '')}\n"
            self.participants_info += f"  - Speaking Style:\n"
            self.participants_info += f"     - Tone: {updated_participant.get('speaking_style', '').get('tone', '')}\n"
            self.participants_info += f"     - Language Complexity: {updated_participant.get('speaking_style', '').get('language_complexity', '')}\n"
            self.participants_info += f"     - Communication Style: {updated_participant.get('speaking_style', '').get('communication_style', '')}\n"
            self.participants_info += f"     - Sentence Structure: {updated_participant.get('speaking_style', '').get('sentence_structure', '')}\n"
            self.participants_info += f"     - Formality: {updated_participant.get('speaking_style', '').get('formality', '')}\n"
            self.participants_info += f"     - Other Traits: {updated_participant.get('speaking_style', '').get('other_traits', '')}\n"
            self.participants_info += f"  - Personalized Vocabulary:\n"
            self.participants_info += f"     - Filler Words: {'; '.join(updated_participant.get('personalized_vocabulary', []).get('filler_words', []))}\n"
            self.participants_info += f"     - Catchphrases: {'; '.join(updated_participant.get('personalized_vocabulary', []).get('catchphrases', []))}\n"
            # self.participants_info += f"     - Preferred Words: {'; '.join(updated_participant.get('personalized_vocabulary', []).get('preferred_words', []))}\n"
            self.participants_info += f"     - Speech Patterns: {'; '.join(updated_participant.get('personalized_vocabulary', []).get('speech_patterns', []))}\n"
            self.participants_info += f"     - Emotional Expressions: {'; '.join(updated_participant.get('personalized_vocabulary', []).get('emotional_expressions', []))}\n\n"

        return participants


    def generate_speaking_style_profile(self, participant, meeting_type, language='English'):
        # System prompt as defined above
        system_prompt = (
            f"You are an assistant tasked with creating detailed speaking style profiles for participants in a {meeting_type}. "
            f"All profiles should be generated considering the agent has to speak in **{language}**. "
            "For each participant, generate a comprehensive speaking style profile focusing on the following key attributes. "
            "Ensure that each profile is unique and diverse, trying to avoid repitition of traits across different participants. "
            "Include multiple options or details within each sub-field to capture a wide range of characteristics:\n\n"
            "1. **Tone and Emotional Expressiveness**: Describe the general tone and level of emotional expressiveness (e.g., casual and enthusiastic, formal and reserved, etc.).Also consider some of the nuances such as sarcasm, optimism, seriousness, humor, etc.\n"
            "2. **Language Complexity and Vocabulary Preference**: Specify the complexity of language and any preferred types of vocabulary (e.g., simple language with common terms, technical language with industry jargon, use of metaphors, analogies, storytelling, etc.).\n"
            "3. **Communication Style**: Outline how the participant communicates with others (e.g., direct and assertive, collaborative and inquisitive, uses rhetorical questions, prefers active listening, etc.).\n"
            "4. **Sentence Structure and Length**: Indicate their typical sentence length and structure (e.g., short and concise sentences, long and complex sentences with subordinate clauses, frequent use of exclamations or questions, varied, etc.).\n"
            "5. **Formality Level**: State the level of formality in their speech (e.g., informal, semi-formal, formal).\n"
            "6. **Other Notable Traits**: Include any additional traits such as rhythm, use of rhetorical devices, or unique interaction styles (e.g., interrupts frequently, uses pauses effectively,etc.).\n\n"
            f"Additionally, for **personalized_vocabulary**, include a wider range of elements within each field, specific to the target language: **{language}**:\n" 
            "1. **Filler Words**: List any **language-specific** filler words or phrases they frequently use (as an example, for English \"um\", \"you know\", \"like\", \"I mean\"...; for Spanish: \"eh\", \"pues\", \"este\", ...; for German: \"Ähm\", \"Also\", \"Halt\", \"Na\", \"Ja\",... and likewise for other language ).\n" 
            f"2. **Catchphrases and Idioms**: Include unique expressions, idioms, or sayings they often use in {language}.\n"  
            "3. **Speech Patterns**: Describe any distinctive speech patterns (e.g., varies sentence starters, unique ways of posing quetions, etc.), uses rhetorical questions, or other other distinctive patterns).\n" 
            "4. **Emotional Expressions**: Note any common expressions of emotion (e.g., laughter, sighs, exclamations like \'Wow!\', \'Amazing!\' (likewise for other language-specific exclamations), and several other emotional expressions).\n\n"
            "Importantly, ensure that the **personalized_vocabulary**, such as **filler words** and other related fields vary significantly between different participants to enhance their uniqueness. Avoid using similar phrases or patterns across multiple profiles.\n"
            "### **Important Instructions for JSON Formatting:**\n"
            "- Use **double quotes** (`\"`) for all keys and string values as per JSON standards.\n"
            "- **Do not** use single quotes (`'`) in the JSON output.\n"
            "- **Escape** any single/double quotes within string values using a backslash (`\"`, `\'`). For example: `\"Indeed!\"`, `\'Definitely!\'`.\n"
            "- Use an **escaped new line character** within string values instead of natural line breaks.\n"
            "- Ensure that there are **no trailing commas** after the last item in objects or arrays.\n"
            "- **Do not** include any additional text outside the JSON object. The output should be **only** the JSON object.\n"
            "- **Each item in the lists** (e.g., in `filler_words`, `catchphrases`, etc.) should be properly enclosed in double quotes.\n"
            "- Follow proper JSON syntax to ensure the output is **processable by Python's `json` module**.\n\n"
            "Provide the speaking style profile in a JSON format as shown below, ensuring that each field includes multiple entries where appropriate to capture a rich and detailed profile."
            "Make sure we have a diverse set of participants' styles and characteristics - use previous particpants' info to not make styles of different participants redundant and diversify styles of newer participants."

        )

        user_prompt = (
        f"Info of participants until now:\n{self.participants_info}"
        f"Participant Information:\n"
        f"Role: {participant['role']}\n"
        f"Description: {participant.get('description', '')}\n\n"
        f"Please generate a comprehensive speaking style profile for this participant, focusing on the key attributes mentioned. "
        f"For each sub-field, include multiple options or details to provide a rich and detailed profile. "
        f"Format the output as a JSON object like this:\n\n"
        "{{\n"
        '  "speaking_style": {{\n'
        '    "tone": "<Tone and Emotional Expressiveness>",\n'
        '    "language_complexity": "<Language Complexity and Vocabulary Preference>",\n'
        '    "communication_style": "<Communication Style>",\n'
        '    "sentence_structure": "<Sentence Structure and Length>",\n'
        '    "formality": "<Formality Level>",\n'
        '    "other_traits": "<Other Notable Traits>"\n'
        '  }},\n'
        '  "personalized_vocabulary": {{\n'
        '    "filler_words": ["<Filler Word 1>", "<Filler Word 2>", ...],\n'
        '    "catchphrases": ["<Catchphrase 1>", "<Catchphrase 2>", ...],\n'
        # '    "preferred_words": ["<Preferred Word 1>", "<Preferred Word 2>", ...],\n'
        '    "speech_patterns": ["<Speech Pattern 1>", "<Speech Pattern 2>", ...],\n'
        '    "emotional_expressions": ["<Emotional Expression 1>", "<Emotional Expression 2>", ...]\n'
        '  }}\n'
        "}}\n\n"
        "Ensure that the JSON is valid, properly formatted and includes all the specified fields with multiple entries where applicable. Do not include any additional text. " 
    )


        # Construct messages for the API call
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]


        # Call the model
        response = ModelHandler.call_model_with_retry(
            self.client,
            messages,
            self.model_id,
            max_tokens=2000,
            response_model=SpeakingStyleProfile
        )

        profile = response.model_dump()
        participant['speaking_style'] = profile.get('speaking_style', {})
        participant['personalized_vocabulary'] = profile.get('personalized_vocabulary', {})


        # Extract and parse the generated profile
        # cleaned_answer = response.choices[0].message.content.strip().replace('“', '\"').replace('”', '\"').replace('‘', "\'").replace('’', "\'")
        # generated_answer = cleaned_answer.replace('```json', '').replace('```', '')

        # def fix_json_list_items(json_string):
        #     def fix_line_breaks(match):
        #         return match.group(0).replace('\n', '')


        #     def fix_list(match):
        #         content = match.group(1)
        #         items = []
        #         current_item = ''
        #         in_quotes = False
        #         escape = False

        #         for char in content:
        #             if escape:
        #                 current_item += char
        #                 escape = False
        #             elif char == '\\':
        #                 current_item += char
        #                 escape = True
        #             elif char == '"' and not in_quotes:
        #                 in_quotes = True
        #                 current_item += char
        #             elif char == '"' and in_quotes:
        #                 in_quotes = False
        #                 current_item += char
        #             elif char == ',' and not in_quotes:
        #                 items.append(current_item.strip())
        #                 current_item = ''
        #             else:
        #                 current_item += char

        #         if current_item:
        #             items.append(current_item.strip())

        #         fixed_items = []
        #         for item in items:
        #             if (item.startswith('"') and item.endswith('"')) or (item.startswith('[') and item.endswith(']')):
        #                 fixed_items.append(item)
        #             else:
        #                 # Handle escaped quotes and nested quotes within the item
        #                 fixed_item = item.replace('\\', '\\\\').replace('"', '\\"')
        #                 fixed_items.append(f'"{fixed_item}"')


        #         return '[' + ', '.join(fixed_items) + ']'


        #     # Fix line breaks within string values
        #     json_string = re.sub(r'": "([^"]*)\n([^"]*)"', fix_line_breaks, json_string)


        #     # Fix lists in the JSON string
        #     fixed_json_string = re.sub(r'\[(.*?)\]', fix_list, json_string)

        #     # Parse and re-serialize to ensure valid JSON
        #     parsed_json = json.loads(fixed_json_string)
        #     return json.dumps(parsed_json, indent=2)
        # print(f"generated answer (before fixing):\n{generated_answer}\n")
        # fixed_json = fix_json_list_items(generated_answer)

        # # print(f"Generated social profile in generate_speaking_style_profile(...)\n{fixed_json}")
        # try:
        #     profile = json.loads(fixed_json)
        #     # Update the participant with the speaking style profile
        #     participant['speaking_style'] = profile.get('speaking_style', {})
        #     participant['personalized_vocabulary'] = profile.get('personalized_vocabulary', {})
        # except json.JSONDecodeError as e:
        #     print(f"Failed to parse speaking style profile: {e}")
        #     print(f"Problematic JSON:\n{fixed_json}")
        #     participant['speaking_style'] = {}
        #     participant['personalized_vocabulary'] = {}


        return participant

    
    def generate_moderator(self):
        moderator = {
            "role": "moderator",
            "description": "A super-intelligent individual with critical thinking who has a neutral position at all times. He acts as a mediator between other discussion participants."
        }
        return moderator

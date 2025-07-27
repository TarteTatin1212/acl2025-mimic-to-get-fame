import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from basics.scripts.agreement_protocol import AgreementProtocol
from basics.scripts.model_handler import ModelHandler

import json
import logging
import ast

import pprint
import random

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List

class SocialRoleAssignment(BaseModel):
    """
    Represents a social role assignment for a single participant
    """
    role: str = Field(
        description="The primary role/occupation of the participant",
        min_length=1
    )
    social_roles: List[str] = Field(
        description="List of social/group roles assigned to the participant",
        min_items=1
    )
    social_roles_descr: List[str] = Field(
        description="Descriptions corresponding to the assigned social roles",
        min_items=1
    )

    @model_validator(mode='after')
    def validate_roles_and_descriptions(cls, instance: "SocialRoleAssignment"):
        if len(instance.social_roles) != len(instance.social_roles_descr):
            raise ValueError("Number of role descriptions must match number of roles")
        return instance 


class SocialRoleAssignments(BaseModel):
    """
    Represents the complete set of social role assignments
    """
    assignments: List[SocialRoleAssignment]



class DiscussionProtocol:
    def __init__(self, client, model_id, agents, memory, protocol):
        self.client = client
        self.model_id = model_id
        self.agents = agents
        self.memory = memory
        self.protocol = protocol
        self.discussion_protocols = {
            "dialogue": self.dialogue_discussion_protocol,
        }
        self.social_group_roles = {
            "Initiator-Contributor": "Contributes new ideas and approaches and helps to start the conversation or steer it in a productive direction.",
            "Information Giver": "Shares relevant information, data or research that the group needs to make informed decisions.",
            "Information Seeker": "Asks questions to gain clarity and obtain information from others.",
            "Opinion Giver": "Shares his or her views and beliefs on topics under discussion.",
            "Opinion Seeker": "Encourages others to share their opinions and beliefs in order to understand different perspectives.",
            "Coordinator": "Connects the different ideas and suggestions of the group to ensure that all relevant aspects are integrated.",
            "Evaluator-Critic": "Analyzes and critically evaluates proposals or solutions to ensure their quality and feasibility.",
            "Implementer": "Puts plans and decisions of the group into action and ensures practical implementation.",
            "Recorder": "Documents the group decisions, ideas and actions in order to have a reference for future discussions.",
            "Encourager": "Provides positive feedback and praise to boost the morale and motivation of group members.",
            "Harmonizer": "Mediates in conflicts and ensures that tensions in the group are reduced to promote a harmonious working environment.",
            "Compromiser": "Helps the group find a middle ground when there are differences of opinion and encourages compromise in order to move forward.",
            "Gatekeeper": "Ensures that all group members have the opportunity to express their opinions and encourages participation.", 
            "Standard Setter": "Emphasizes the importance of adhering to certain norms and standards within the group to ensure quality and efficiency.",
            "Group Observer": "Monitors the dynamics of the group and provides feedback on how the group is functioning as a whole and what improvements can be made.",
            "Follower": "Supports the group by following the ideas and decisions of others without actively driving the discussions.",
            "Aggressor": "Exhibits hostile behavior, criticizes others, or attempts to undermine the contributions of others.",
            "Blocker": "Frequently opposes ideas and suggestions without offering constructive alternatives and delays the group's progress.",
            "Recognition Seeker": "Tries to draw attention to himself by emphasizing his own successes or focusing on his own importance.",
            "Dominator": "Tries to control the group by dominating the flow of conversation and imposing his/her own views.",
            "Help Seeker": "Seeks sympathy or support by presenting as insecure or helpless, often to avoid responsibility.",
            "Special Interest Pleader": "Brings own interests or concerns to the discussion that do not align with the goals of the group." 
        }

        print()
        memory.print_memories()
        print()
    
    def participate(self, system_template, user_template, language="English"):
        
        system_prompt = system_template["taskInstruction"].format(
            persona=system_template['persona'], 
            role=system_template['personaDescription'],
            expertise={system_template['expertise']},
            perspective={system_template['perspective']},
            social_roles=system_template['socialRoles'], 
            social_roles_descr=system_template["socialRolesDescr"],
            tone=system_template["tone"],
            language_complexity=system_template["languageComplexity"],
            communication_style=system_template["communicationStyle"],
            sentence_structure=system_template["sentenceStructure"],
            formality=system_template["formality"],
            other_traits=system_template["otherTraits"],
            filler_words=system_template["fillerWords"],
            catchphrases=system_template["catchphrases"],
            # preferred_words=system_template["preferredWords"],
            speech_patterns=system_template["speechPatterns"],
            emotional_expressions=system_template["emotionalExpressions"],
        )
        
        user_prompt = (
            "You are now being provided with all supplementary material we have for this scene:\n"
            f"- **Scene description**:\n <{user_template['sceneDescription']}>\n"
            f"- **Director's Comments and Feedback with some examples:\n <{user_template['directorComments']}>.\n "
            f"- **Current Scene Draft**:\n <{user_template['currentScene']}>\n"
            f"- This scene builds on the following **Summaries of Previous Scenes**:\n <{user_template['prevScene']}>\n"
            f"- For your turn, you may want to consider this **Knowledge Source**:\n {user_template['additionalInput']}\n"
            f"- **Your Area of Expertise**: {system_template['expertise']}, with your **Unique Perspective** being: {system_template['perspective']}.\n"
            f"Your task is to generate your dialogue turn in **{language}** based  on the current scene context.\n\n"
            "Some additional guidelines:\n"
            
            "- **Utilize Director's Comments Effectively:**\n"
            "    - **Rejected Scene(s) Example:** Understand step-by-step why certain scenes were rejected to avoid similar issues in your dialogue.\n"
            "    - **Feedback for the Rejected Scene:** Incorporate constructive feedback to enhance the quality and relevance of your contributions.\n\n"
            
            "- Make sure to use your personalized filler words naturally and authentically to enhance the realism of your dialogues.\n"
            "- **Output Format:**\n"
           f"Please structre the turn you generate in the following format:\n {user_template['outputFormat']}\n"
           "'Note:**Ensure appropriate and diverse next speaker selection from the list of available participants, depending on the context of the scene."
        )
        if user_template['currentScene'] == '':
            user_prompt += ( 
                f"\n**Last Dialogue of the Immediate Previous Scene**: \n<{user_template.get('lastDialogue', 'N/A')}>\n"
                f"Please generate your dialogue turn in a way that maintains the natural flow of the conversation. "
                f"Your response should be **coherent with the immediate previous scene's dialogue** but does not have to directly respond to it **unless contextually appropriate.**\n"
                )


        message = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            },
        ]

        response = ModelHandler.call_model_with_retry(
            self.client, message, self.model_id, max_tokens=500
        )
        
        return response


    
    def discuss(self, scene_counter, scene_description, scene_director_notes, additional_input, meeting_type, last_speaker, language="English"):
        final_draft, turn, last_speaker = self.discussion_protocols[self.protocol](scene_counter, scene_description, scene_director_notes, additional_input, meeting_type, last_speaker, language=language)
        return final_draft, turn, last_speaker
    

    def dialogue_discussion_protocol(self, scene_counter, scene_description, scene_director_notes, additional_input, meeting_type, last_speaker=None, soft_max_turns=40, _hard_max_turns=45, language='English'):
        turn = 0
        agreement = False
        
        voting_criteria = (
            "Please vote with 0 if you consider that the scene already covers all important points and you have nothing to add."
            "Vote 1 if you want to keep the discussion going and further develop the scene."
            "You will not know what the other agents will vote."
            "We will do a majority vote."
        )
        
        
        task_instruction = (
            "You are an actor, tasked to play {persona} and participate in a staged discussion as naturally as possible"
            f" in **{language}**.\n"
            "Focus on your unique perspective and expertise as {role} to enhance the conversation and provide a realistic acting. "
            "Specifically, your area of expertise is **{expertise}**, with your unique perspective being: **{perspective}**."
            "In addition to your expertise, you have the following social/ group role(s): {social_roles}. "
            "Your social roles are described as: {social_roles_descr}. "
            "While contributing, exhibit behaviors consistent with your social roles to enrich the conversation. "
            "Additionally, your speaking style is characterized by:\n"
            "- **Tone**: {tone}\n"
            "- **Language Complexity**: {language_complexity}\n"
            "- **Communication Style**: {communication_style}\n"
            "- **Sentence Structure**: {sentence_structure}\n"
            "- **Formality**: {formality}\n"
            "- **Other Traits**: {other_traits}\n"
            "Your personalized vocabulary includes:\n"
            "- **Filler Words**: {filler_words}\n"
            "- **Catchphrases**: {catchphrases}\n"
            "- **Speech Patterns**: {speech_patterns}\n"
            "- **Emotional Expressions**: {emotional_expressions}\n"
            "Utilize all fields of the provided context including your speaking style and your personalized vocabulary. "
            " **However. make sure to use catchphrases, speech patterns and other personalized elements sparingly and when contextually appropriate to avoid overuse.**." 
            "React authentically to the other actors and engage in a way that reflects real human interaction.\n\n"
            "**Guidelines for Crafting Your Dialogue Turn:**\n"
            "- **Engage Naturally in the Conversation:**\n"
            "    - React authentically to what has been said so far.\n"
            "    - Use natural, conversational language, including hesitations, fillers, and incomplete sentences.\n"
            "    - Incorporate appropriate emotional responses, humor, or empathy where fitting.\n"
            "    - Feel free to share personal anecdotes or experiences when relevant.\n"
            "    - Show uncertainty or confusion if you don't fully understand something.\n"
            "    - Allow for natural interruptions or overlapping speech when appropriate.\n"
            "    - Include mundane or tangential remarks to add authenticity.\n"
            "    - Avoid overly polished or scripted language.\n\n"
            "- **Language and Cultural Nuances:**\n"
            f"    - Speak naturally in **{language}** ensuring that your dialogue:\n"
            f"    - Sounds like it was originally created in {language}, not translated from another language.\n"
            f"    - Reflects the **cultural norms, communication styles, and nuances typical of native {language} speakers.**\n"
            f"    - Uses idioms, expressions, and phrases common in {language}.\n"
            f"    - Avoid literal translations or phrases that would not make sense culturally in {language}.\n"
            "- **Use Personalized Elements Sparingly:**\n"
            "    - Use natural, conversational language as humans do in real meetings.\n"
            "    - Incorporate appropriate emotional responses, humor, or empathy where fitting.\n" # Experimental
            "    - Feel free to use **contractions**, **colloquial expressions**, and **interjections**, **once in a while.**\n"
            "    - However, use personalized and **target language-specific filler words** freely and naturally (such as 'um/ uh', 'hmmm', 'You know', 'I mean', etc. for English; likewise other language-specific fillers) and pauses (such as pauses after thinking, false starts, etc.) to enhance realism without hindering clarity.\n"
            "    - **Catchphrases:** Incorporate your catchphrases **only when they naturally fit the conversation.**\n"
            "    - **Speech Patterns:** Use your unique speech patterns **sparingly**, ensuring they enhance rather than dominate your dialogue.\n"
            "    - **Personalized Vocabulary:** Integrate personalized vocabulary elements **contextually and infrequently** to reflect your individuality without overwhelming the conversation.\n"
            "    - **Note:** Personalized vocabulary elements are different from common filler words; feel free to use your personalized filler words naturally.\n\n"
            
            "- **Maintain Dialogue Quality:**\n"
            "    - Express your ideas clearly, but don't be overly formal or polished.\n"
            "    - Allow your speech to include natural pauses, hesitations, and informal markers.\n"
            "    - Build upon your previous points organically without unnecessary summaries.\n"
            "    - Ensure your dialogue advances the conversation and feels spontaneous.\n"
            "    - Avoid repeating information that has already been discussed unless adding new insight.\n"
            "    - Reference previous points to add depth or advance the conversation.\n"
            "    - Feel free to ask questions or seek clarification when appropriate.\n\n"

            "- Ensure what you say is realistic and fits to the current scene. "
            "- Ensure your dialogue feels **natural and human-like**, fitting seamlessly into the ongoing conversation. "
            "- **Avoid overly  formal and robotic language.**\n " # Experimental
            "- Express your ideas **clearly without unnecessary verbosity**"
            "- Build upon your previous points organically without unnecessary summaries.\n"
            "- Ensure your dialogue advances the conversation and feels spontaneous. Your dialogue should be **contextually appropriate** and logically follow from the previous dialogues (which you can reference from the **current scene draft**).\n"
            "- Build upon the points made by others, contribute meaningfully to the conversation and ensure smooth transistions.\n"
            
            "-**Behavior Based on unique Expertise and Perspective:**\n"
            "   - **If the current topic is within your `expertise_area`**, you should:\n"
            "       - Speak authoritatively and provide detailed information with your unique `perspective`.\n"
            "       - Answer questions posed by other participants.\n"
            "       - Correct inaccuracies or misunderstandings related to your expertise.\n"
            "   - **If the current topic is outside your `expertise_area`**, you should:\n"
            "       - Ask clarifying questions to understand the topic better.\n"
            "       - Express uncertainty, or seek more information. seek additional information without asserting expertise.\n"
            "       - **Bring in Personal Experiences:** Share relevant experiences that enrich the conversation.\n"
            "       - Offer related insights that are tangentially connected to your expertise, if applicable.\n\n"
            "- **Include Spontaneity and Humor:**\n"
            "    - Incorporate humor or offhand comments when fitting.\n"
            "    - Allow for moments of spontaneity that make the conversation feel more real.\n\n"
    
            "- **Allow for Confusion and Uncertainty:**\n"
            "    - It's okay to not have all the answers. Express doubts or uncertainties naturally.\n"
            "    - Show genuine curiosity and willingness to learn from others.\n\n"
    
            "- **Interaction Dynamics:**\n"
            "    - Engage with other participants' contributions.\n"
            "    - Interrupt politely if you have something urgent to add.\n"
            "    - Respond naturally if interrupted by others.\n"
            "    - Allow the conversation to flow without rigid structure.\n\n"
    
            "- **Avoid Overly Formal or Prepared Speeches:**\n"
            "    - Your contributions should feel spontaneous, not like pre-written statements.\n"
            "    - Use natural language, and avoid overly technical or formal language unless appropriate.\n\n"
    
            "- **Emphasize Interaction Over Information:**\n"
            "    - Focus on engaging with others rather than delivering monologues.\n"
            "    - Ask questions, seek opinions, and build on others' ideas.\n"
            "    - Share your thoughts and feelings, not just facts.\n\n"

            "Do not include any introductory or closing statements.Just speak freely without any preamble. Keep your replies realistic, "
            " varying in length as appropriate, but keep it strictly between 1-3 sentences. Your response should feel spontaneous and unscripted. "
            "Drive the meeting forward with your contributions, but don't be afraid to explore tangents or side topics briefly if they add value.\n"
            "Some additional guidelines:\n"
            "- Reference ** *previous scenes' summaries* and the *scene draft so far* to prevent topic redundancy** unless adding a new perspective or depth to the conversation.\n"
            "- Reference **previous points** to add value or advance the conversation. "
            "- Drive the meeting forward with your contributions.\n"
            "- **Director's Comments and Feedback:**\n"
            "   - **Review the director's comments and feedback carefully.**\n"
            "   - **Ensure that your dialogue aligns with the feedback to avoid rejection.**\n"
            "   - **Address any specific issues mentioned in the feedback while crafting your response.**\n\n"
        )
        
        prev_scenes = ""
        last_dialog = ""
        if (scene_counter) > 0:
            prev_scenes = self.memory.get_mem_str(scene_counter-1)
            last_dialog = self.memory.get_last_dialog(scene_counter - 1)
            last_speaker = last_dialog.split(':')[0]

        self.assign_social_roles(scene_description, prev_scenes)
        

        
        agreement_protocol = AgreementProtocol(self.client, self.model_id, self.agents, self.memory, voting_criteria=voting_criteria, agreement="stop_dialogue_vote")
        
        # agent_index = first_agent

        # Determine eligible agents for starting the scene
        if scene_counter == 0 or last_speaker is None:
            # First scene or no last speaker, all agents are eligible
            eligible_agents = self.agents
        else:
            # Exclude the last speaker from the list of agents
            eligible_agents = [agent for agent in self.agents if agent['role'] != last_speaker]

        # Prompt the model to select the most suitable agent to start the scene
        starting_agent_index = self.select_starting_agent(scene_description, eligible_agents, scene_counter)
        # starting_agent_index = random.randint(0, len(eligible_agents) - 1)
        agent = eligible_agents[starting_agent_index]
        agent_index = self.agents.index(agent)

        scene_draft = ''
        while (turn < soft_max_turns and soft_max_turns < _hard_max_turns) and not agreement:
            turn += 1
            
            logging.info((f"Agent {agent_index} ({agent['role']}) is participating."))
            logging.info("\n"+"*" * 20 + f" Turn {turn} " + "*" * 20+"\n")
            
            # prepare prompts
            system_template = {
                "taskInstruction": task_instruction,
                "persona": agent["role"],
                "personaDescription": agent["description"],
                "expertise": agent["expertise_area"],
                "perspective": agent["perspective"],
                "socialRoles": ", ".join(agent.get('social_roles', [])),
                "socialRolesDescr": "; ".join(agent.get('social_roles_descr', [])),
                "tone": agent.get('speaking_style', '').get('tone', ''),
                "languageComplexity": agent.get('speaking_style', '').get('language_complexity', ''),
                "communicationStyle": agent.get('speaking_style', '').get('communication_style', ''),
                "sentenceStructure": agent.get('speaking_style', '').get('sentence_structure', ''),
                "formality": agent['speaking_style'].get('formality', ''),
                "otherTraits": agent.get('speaking_style', '').get('other_traits', ''),
                "fillerWords": agent.get('personalized_vocabulary', []).get('filler_words', []),
                "catchphrases": agent.get('personalized_vocabulary', []).get('catchphrases', []),
                "speechPatterns": agent.get('personalized_vocabulary', []).get('speech_patterns', []),
                "emotionalExpressions": agent.get('personalized_vocabulary', []).get('emotional_expressions', []),

            }


            remaining_agents = list(filter(lambda p: p["role"] != agent["role"], self.agents))

            # output_format = (
            # "For the output, please follow this format to produce a json that can later be processed in python:\n"
            # '{"turn": <generated sentence or sentences in the target language>, "wants_vote": <true or false, depending on if you believe the scene should end after your turn (true, otherwise false) — base your decision on the **scene draft so far**, the **scene description** and your **current turn**>, "next_speaker": <select index of the speaker who should speak next. Consider the list of other participants: <'
            # f"{remaining_agents}>"
            # " and **report with a number from 1 to "
            # f"{len(remaining_agents)} (inclusive)**. "
            # 'Note:**Ensure appropriate and diverse next speaker selection from the list of available participants, depending on the context of the scene.>"}\n'
            # )
            indexed_remaining_agents = "\n".join(f" {i+1}. {agent['role']}; Participant info: {agent}" for i, agent in enumerate(remaining_agents))
            output_format = (
                "Please produce your output in strict and valid JSON format as described below so that it can be processed by our Python script:\n\n"
                "{\n"
                '  "turn": "<your generated dialogue turn (sentence(s)) in the target language>",\n'
                '  "wants_vote": <true or false>,\n'
                '  "next_speaker": <an integer representing the next speaker>\n'
                "}\n\n"
                "Instructions:\n"
                "1. **turn**:\n"
                "   - Provide your dialogue turn in the target language.\n\n"
                "2. **wants_vote**:\n"
                "   - Use **true** if you believe the scene should end after your turn; otherwise, use **false**. "
                "Base this decision on the fulfillment of the scene requirements as specified by the **scene description** and whether the **current scene draft** including **your current turn** cover all the required points of the scene.\n\n"
                "3. **next_speaker**:\n"
                "   - This should be an integer corresponding to the index of the next speaker from the following list:\n"
                f"       {indexed_remaining_agents}\n"
                f"  - Report a number from **1** to **{len(remaining_agents)}** (inclusive).\n"
                "   - Ensure that your selection is appropriate and diverse given the scene context – take into consideration **all the info for each of the available participants**, & avoid repeatedly selecting the same index/participant, prompte variety in speakers.\n"
                "   - When choosing, also consider which participants have spoken least recently in the current scene draft to promote active participation.\n\n"
                f"4. **Important:** Do not output any number outside the range 1 to {len(remaining_agents)} for the `next_speaker`."
            )
            user_template = {
                "currentScene": scene_draft,
                "sceneDescription": scene_description,
                "directorComments": scene_director_notes,
                "additionalInput": additional_input,  # Wikipedia article
                "prevScene": prev_scenes,  # For connectiong the scenes
                "lastDialogue": last_dialog, # For propely generating the very first dialogue of each scene taking into account the immediate prev scene's last dialog
                "outputFormat": output_format,
            }

            # print("$"*120)
            # keys_to_exclude = {"additionalInput"}
            # print(f"Evolution of User Template (excluded the `additionalInput`):") # Debug
            # pprint.pprint({k: v for k, v in user_template.items() if k not in keys_to_exclude})
            # print("$"*120)

            # extract generated content
            response = self.participate(system_template, user_template, language)
            response = response.choices[0].message.content.strip()
            response = response.replace('```python', '').replace('```json', '').replace('```', '')

            # print()
            print("Turn Response:")
            print(response, flush=True)
            # print()
            
            #response = ast.literal_eval(response)
            response = json.loads(response)
            
            new_turn = response.get('turn', '')
            scene_draft += f"\n>>{agent.get('role', '')}: {new_turn}"
            # Get the next speaker
            print()
            next_speaker_idx = response.get('next_speaker', 0) - 1
            next_speaker = remaining_agents[next_speaker_idx]
            agent_index = self.agents.index(next_speaker)
            agent = self.agents[agent_index]
            
            # voting and agreement handling
            want_vote = response.get('wants_vote', True)
            if want_vote is True:                        
                logging.info("Agreement Protocol is running.")
                input = {
                    "dialogue_draft": scene_draft,
                    "discussion_plan": scene_description,
                    "related_article": additional_input
                }
                agreement = agreement_protocol.run_protocol(input)

            if not agreement and not (turn < soft_max_turns-1):
                soft_max_turns += 10
            
            # max turn handling
            if not turn < _hard_max_turns:
                agreement = True
                break
                
        final_scene_draft = scene_draft if scene_draft else "Scene failed."
        return final_scene_draft, turn, last_speaker
        # memory has to be updated by the DIRECTOR!!

    def assign_social_roles(self, scene_description, previous_scenes_tldr):
        system_prompt = (
            "You are a meeting coordinator responsible for assigning social/group roles to participants in a meeting simulation. "
            "Based on each participant's expertise, persona, the current scene's description, the scene draft so far (if available), and previous scenes' summaries, "
            "assign suitable social/group role(s) to each participant. Ensure that contradictorty roles are not assigned to the same participant."
        )


        # Prepare the user prompt
        participants_info = ""
        for idx, agent in enumerate(self.agents, start=1):
            participants_info += f"{idx}. **Participant**: {agent['role']}\n"
            participants_info += f"   - **Description/ Expertise**: {agent['description']}\n"


        social_roles_info = ""
        for role, description in self.social_group_roles.items():
            social_roles_info += f"- **{role}**: {description}\n"


        user_prompt = (
            f"**Participants**:\n{participants_info}\n"
            f"**Available Social/Group Roles and Descriptions**:\n{social_roles_info}\n"
            f"**Scene Description**:\n{scene_description}\n"
            f"**Previous Scenes' Summaries**:\n{previous_scenes_tldr}\n\n"
            "**Instructions**:\n"
            "- Assign one or more suitable social/group roles to each participant.\n"
            "- **Aim to assign a diverse set of roles across all participants so that different roles are represented, including roles that introduce constructive conflict or challenge.**\n"
            "- **Include at least one participant with a conflict-oriented role (e.g., Aggressor, Blocker) to simulate realistic meeting dynamics.**\n" # Experimental
            "- **Avoid assigning the same combination of roles to multiple participants unless necessary.**\n"
            "- Base your assignments on the participants' **expertise**, descriptions, and the scene context.\n"
            "- Ensure that contradictory roles are not assigned to the same participant.\n"
            "- Provide brief reasoning for each assignment (optional, for internal use).\n\n"
            "**Output Format**:\n"
            "Provide the assignments as a JSON-formatted list of dictionaries, where each dictionary contains:\n\n"
            "- \"role\": \"<Participant>\"\n"
            "- \"social_roles\": [List of assigned social role(s)]\n"
            "- \"social_roles_descr\": [List of corresponding descriptions for each role]\n\n"
            "Example:\n\n"
            "```json\n"
            "[\n"
            "  {\n"
            "    \"role\": \"Researcher\",\n"
            "    \"social_roles\": [\"Initiator-Contributor\", \"Information Giver\",...],\n"
            "    \"social_roles_descr\": [\n"
            "      \"Contributes new ideas and approaches and helps to start the conversation or steer it in a productive direction.\",\n"
            "      \"Shares relevant information, data or research that the group needs to make informed decisions.\"\n"
            "    ]\n"
            "  },\n"
            "  {\n"
            "    \"role\": \"Ethicist\",\n"
            "    \"social_roles\": [\"Evaluator-Critic\", \"Harmonizer\",...],\n"
            "    \"social_roles_descr\": [\n"
            "      \"Analyzes and critically evaluates proposals or solutions to ensure their quality and feasibility.\",\n"
            "      \"Mediates in conflicts and ensures that tensions in the group are reduced to promote a harmonious working environment.\"\n"
            "    ]\n"
            "  },\n"
            "  {\n"
            "    \"role\": \"Developer\",\n"
            "    \"social_roles\": [\"Aggressor\", \"Blocker\",...],\n"
            "    \"social_roles_descr\": [\n"
            "      \"Exhibits hostile behavior, criticizes others, or attempts to undermine the contributions of others.\",\n"
            "      \"Frequently opposes ideas and suggestions without offering constructive alternatives and delays the group's progress.\"\n"
            "    ]\n"
            "  }\n"
            "]\n"
            "```\n\n"
            "Do not include any additional commentary or explanations."
        )


        # Call the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]


        # response = ModelHandler.call_model_with_retry(
        #     client=self.client,
        #     messages=messages,
        #     model=self.model_id,
        #     max_tokens=1500  # Experimental
        # )


        # Parse the response to extract role assignments
        # assigned_roles_text = response.choices[0].message.content.strip()
        # self.parse_and_update_agents(assigned_roles_text)

        response = ModelHandler.call_model_with_retry(
            client=self.client,
            messages=messages,
            model=self.model_id,
            max_tokens=2500,  # Experimental
            response_model=SocialRoleAssignments
        )


        # Parse the response to extract role assignments
        # assigned_roles_text = response.choices[0].message.content.strip()
        print(f"Social Roles' Assignment response: \n{response}\n")
        assigned_roles = response.assignments
        # self.parse_and_update_agents(assigned_roles_text)
        self.update_agents(assigned_roles)
        
        
    def update_agents(self, assigned_roles):
        try:
            for assignment in assigned_roles:
                for agent in self.agents:
                    if agent['role'] == assignment.role:
                        agent['social_roles'] = assignment.social_roles
                        agent['social_roles_descr'] = assignment.social_roles_descr
                        break
        except Exception as e:
            print(f"Error in social role assignment: {e}")

    def parse_and_update_agents(self, assigned_roles_text):

        # Attempt to parse the JSON
        try:
            # Extract the JSON part
            json_start = assigned_roles_text.find('[')
            json_end = assigned_roles_text.rfind(']') + 1
            json_text = assigned_roles_text[json_start:json_end]


            assigned_roles = json.loads(json_text)
        except json.JSONDecodeError as e:
            print("Error parsing JSON:", e)
            print("Raw LLM output:", assigned_roles_text)
            # Handle the error (e.g., retry, skip, or attempt to fix the JSON)
            assigned_roles = []  # Or handle accordingly


        # Update self.agents with the assigned roles
        for assignment in assigned_roles:
            participant_name = assignment.get('role')
            social_roles = assignment.get('social_roles', [])
            social_roles_descr = assignment.get('social_roles_descr', [])
            # Find the agent in self.agents
            for agent in self.agents:
                if agent['role'] == participant_name:
                    agent['social_roles'] = social_roles
                    agent['social_roles_descr'] = social_roles_descr
                    break
        # print(f"self.agents at the end of parse_and_update_agents(...):\n{self.agents}")



    def select_starting_agent(self, scene_description, eligible_agents, scene_counter):
        # Prepare the prompt for the model
        num_agents = len(eligible_agents)
        system_prompt = (
        "You are a meeting coordinator tasked with selecting the most suitable participant to start the scene discussion. "
        "Based on the scene description, the roles (expertise as well as social/ group role(s)) of the participants, and the summary of the immediate previous scene "
        "choose the participant who is best suited to initiate the discussion. "
        f"Provide your answer as a single integer corresponding to the participant's number from the provided list. "
        f"The number should be between 1 and {num_agents}. "
        "Do not include any additional text or explanation."
        )

        # Retrieve only the immediate previous scene's enriched TL;DR
        if scene_counter > 0:
            prev_scene = self.memory.get_mem_str(scene_counter - 1, only_prev=True)
        else:
            prev_scene = ""


    
        agent_list = "\n".join([f"{i+1}. {agent['role']}: {agent['description']}" for i, agent in enumerate(eligible_agents)])
    
        user_prompt = (
            f"Scene Description:\n{scene_description}\n\n"
            f"Eligible Participants:\n{agent_list}\n\n"
            f"Previous Scene summary:\n{prev_scene}\n\n"
            "Please provide the number corresponding to the most suitable participant to start the scene."
            " Remember, only provide the number (e.g., '1')."
        )
    
        message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    
        response = ModelHandler.call_model_with_retry(
            client=self.client,
            messages=message,
            model=self.model_id,
            max_tokens=5
        )
    
        # Extract the integer from the model response
        response_text = response.choices[0].message.content.strip()
        try:
            selected_index = int(response_text) - 1  # Convert to zero-based index
            if selected_index < 0 or selected_index >= num_agents:
                raise ValueError("Selected index out of range.")
        except ValueError as e:
            print(f"Error parsing model response: {e}")
            # Handle the error appropriately, e.g., default to the first eligible agent
            selected_index = 0
        return selected_index  # Index within eligible_agents

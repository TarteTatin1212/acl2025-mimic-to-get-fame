import sys
import os
import ast
import json
import re
import random
import csv


from pipeline.discussion_protocol import DiscussionProtocol

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from basics.scripts.discussion_coordinator import DiscussionCoordinator
from basics.scripts.model_handler import ModelHandler
from basics.scripts.memory_handler import MemoryHandler

class MeetingGenerator:
    def __init__(self, client, model_id, agents, scene_descriptions, article_text, article_title, meeting_type, article_domain=None, language="English") -> None:
        self.client = client
        self.model_id = model_id
        self.agents = agents
        self.scene_descriptions = scene_descriptions
        self.scene_generation_retries = 0
        self.memory = MemoryHandler(memories=[[] for _ in scene_descriptions])
        self.article_text = article_text
        self.article_title = article_title
        self.meeting_type = meeting_type
        if article_domain:
            self.article_domain = article_domain

        # Create directory if it doesn't exist
        if language == "English":
            output_dir = "./output/final_corpora/English/scenes_evolution/"
        else:
            output_dir = "./output/final_corpora/German/scenes_evolution/"
        os.makedirs(output_dir, exist_ok=True)



        safe_article_title = self.article_title.replace(' ', '_').replace('/', '_')
        safe_meeting_type = self.meeting_type.replace(' ', '_').replace('/', '_')
        if article_domain:
            safe_domain = self.article_domain.replace(' ', '_').replace('/', '_')

        self.csv_file_path = os.path.join(
            output_dir, 
            f"Scenes_{safe_domain}_{safe_meeting_type}_{safe_article_title}.csv"
            # f"Scenes_{safe_meeting_type}_{safe_article_title}.csv"
        )
        if not os.path.exists(self.csv_file_path):
            with open(self.csv_file_path, mode='w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=["original_scene", "refined_scene", "ai_feedback", "finalized_scene"])
                writer.writeheader()

        # Separate CSV to store rejections/feedback
        self.rejections_csv_file_path = os.path.join(
            output_dir, 
            f"Rejections_{self.meeting_type}_{self.article_title}.csv"
        )
        if not os.path.exists(self.rejections_csv_file_path):
            with open(self.rejections_csv_file_path, mode='w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=[
                    "scene_counter", 
                    "rejected_scene_snippet", 
                    "director_feedback"
                ])
                writer.writeheader()

    def generate_scene(self, scene_counter, scene_description, scene_director_notes, additional_input, discussion_coordinator, discussion_protocol, rejected_feedback, rejected_scene, meeting_type, last_speaker = None, language="English"):
        # Increment retry counter if this is a retry attempt
        if rejected_feedback and rejected_scene:
            self.scene_generation_retries += 1
            print(f"Scene Generation Retry #{self.scene_generation_retries}")
        
        # Check if we've exceeded max retries
        if self.scene_generation_retries >= 3:
            print(f"Warning: Maximum retries ({self.scene_generation_retries}) reached for scene {scene_counter + 1}. Using last generated version.")
            self.scene_generation_retries = 0  # Reset for next scene
            # Instead of returning directly, proceed with the rejected scene
            sub_meeting = rejected_scene
            print("Proceeding with refinement of the last rejected scene...")
        else:
            scene_director_notes += (
                f"**Rejected Scene (snippet):** \n{rejected_scene[:200]}\n...\n{rejected_scene[-200:]}\n"
                f"**Feedback for the above rejected scene:**\n {rejected_feedback}"
                f"---"*50
            ) if rejected_feedback and rejected_scene else ""
            
            sub_meeting, last_speaker = discussion_coordinator.process_meeting_generation(
                scene_counter = scene_counter,
                scene_description = scene_description,
                scene_director_notes = scene_director_notes,
                additional_input = additional_input,
                last_speaker = last_speaker,
                discussion_protocol = discussion_protocol,
                meeting_type = meeting_type,
                language = language
            )
            
            scene_accepted, scene_feedback = self.check_scene(sub_meeting, scene_description, language=language)
            
            if not scene_accepted:

                # Log the rejected scene snippet + feedback to separate CSV
                with open(self.rejections_csv_file_path, mode='a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=[
                        "scene_counter", 
                        "rejected_scene_snippet", 
                        "director_feedback"
                    ])
                    row = {
                        "scene_counter": scene_counter + 1,
                        "rejected_scene_snippet": sub_meeting,
                        "director_feedback": scene_feedback
                    }
                    writer.writerow(row)

                print("#"*100)
                print("#"*100)
                print(f"Re-shooting the scene...Scene {scene_counter + 1} (Attempt #{self.scene_generation_retries + 1})")
                print(f"Rejected Scene and Feedback:\n{sub_meeting}\n")
                print(f"---"*30)
                print(f"{scene_feedback}")
                print("#"*100)
                print("#"*100)
                return self.generate_scene(
                    scene_counter, 
                    scene_description, 
                    scene_director_notes, 
                    additional_input, 
                    discussion_coordinator, 
                    discussion_protocol, 
                    scene_feedback, 
                    sub_meeting, 
                    meeting_type, 
                    last_speaker, 
                    language=language
                )
        
        # Reset retry counter upon successful generation or max retries
        self.scene_generation_retries = 0
        
        original_scene = sub_meeting
        
        # Continue with scene refinement pipeline regardless of how we got the scene
        special_effects_prob = 0.25
        special_effects_flag = False   # exp - later implement for ensuring special effects are onjected just once per meeting rather than scene
        if random.random() < special_effects_prob:
            print("!!!!Introducing special effects...")
            sub_meeting = self.apply_special_effects(sub_meeting, meeting_type, language)

        # Pass director's feedback to refine_scene only if we're using a rejected scene
        director_feedback = None
        if self.scene_generation_retries >= 3:
            director_feedback = rejected_feedback
        
        refined_sub_meeting = self.refine_scene(
            sub_meeting, 
            scene_description, 
            scene_counter, 
            meeting_type, 
            director_feedback=director_feedback,  # New parameter
            language=language
        )

        # Detect AI-generated content issues
        ai_feedback = self.detect_ai_content(refined_sub_meeting, language=language)

        # Humanize the scene based on AI feedback
        humanized_scene = self.humanize_scene(refined_sub_meeting, ai_feedback, language=language)

        self.save_scene_to_csv(
            original_scene=original_scene,
            refined_scene=refined_sub_meeting,
            ai_feedback=ai_feedback,
            finalized_scene=humanized_scene
        )

        return humanized_scene, last_speaker
        
    def check_scene(self, sub_meeting, sub_summary, language='English'):
        system_prompt = (
            "You are an experienced movie director evaluating if a scene matches its intended script and narrative. "
            "Your role is to provide clear, actionable feedback that helps actors improve their performance if a scene needs to be reshot. "
            "Therefore, you try a very neat trick: You have a summary given of what the scene should be about and the transcript of the dialogue. "
            "Break down the summary into atomic facts. Then break down the transcript into atomic facts. See if the summary facts are present in the transcript facts. "
            "Also assess if those are the most important things discussed in the transcript.\n\n"
            "Important Guidelines for Evaluation:\n"
            "1. Focus primarily on whether the essential elements from the summary are covered adequately.\n"
            "2. Be flexible about additional content or tangential discussions that:\n"
            "   - Add depth or context to the main topics\n"
            "   - Make the conversation more natural and engaging\n"
            "   - Provide relevant examples or analogies\n"
            "   - Create authentic human interaction\n"
            "3. Accept natural deviations that:\n"
            "   - Don't detract from the main points\n"
            "   - Help build rapport between participants\n"
            "   - Add realism to the conversation\n"
            "4. Only reject scenes if:\n"
            "   - Core requirements from the summary are missing\n"
            "   - The conversation strays too far from the intended topics\n"
            "   - The dialogue is incoherent or poorly structured\n"
            "   - Participants are not engaging meaningfully\n\n"
            f"The scene needs to be in {language}.\n"
            "For the task, think step by step. Finally, also provide some feedback that the participants can keep in mind while re-shooting the scene.\n"
            "Report your answer strictly as a JSON object with the following format:"
            "```json\n"
            " {\n"
            "   \"explanation\": \"your step-by-step/ chain-of-thought reasoning for accepting/rejecting the scene and feedback for improvement. "
            "If accepting despite minor issues, explain why the scene works overall. "
            "If rejecting, provide clear guidance on what must change while acknowledging what worked well.\","
            "   \"accept_scene\": true or false\n"
            "}\n"
            "```\n"
            " Ensure that the JSON object is properly formatted with double quotes, no additional text, no unescaped newlines, and no control characters."
            " Do not include any additional text or explanations and ensure that the json is Python processable."
        )
        
        user_prompt = (
            "Hi director, here is the new material for your evaluation:\n"
            f"The generated transcript:\n {sub_meeting} \n"
            f"And the related part in the summary: {sub_summary}\n\n"
            "Remember to be flexible about additional content or natural conversation elements that enhance the scene "
            "while ensuring the core requirements are met. Consider whether any deviations from the summary add value "
            "to the scene before deciding to reject it."
        )
        
        message = [
            {"role": "system",
             "content": system_prompt
            },
            {"role": "user",
             "content": user_prompt
            }
        ]
    
        response = ModelHandler.call_model_with_retry(client=self.client, messages=message, model=self.model_id, max_tokens=4000)

        director_comment = response.choices[0].message.content.strip()

        director_comment = director_comment.replace('```python', '').replace('```json', '').replace('```', '').strip()

        director_comment = self.extract_json_from_text(director_comment)
        return director_comment.get('accept_scene', False), director_comment.get('explanation', 'No explanation found!')


    def detect_ai_content(self, scene_text, language="English"):
        """
        Detects AI-generated content that doesn't feel realistic in the meeting scene.
        Provides thorough reasoning and feedback to humanize the scene.

        :param scene_text: The refined meeting scene text.
        :param language: The language of the scene.
        :return: String containing feedback enclosed within <feedback></feedback> tags.
        """
        system_prompt = (
            "You are an AI-generated content detector specializing in identifying elements in meeting dialogues that do not feel realistic or human-like. "
            "Your task is to analyze the provided meeting scene and identify any parts that seem unnatural, overly formal, repetitive, lacking in authenticity, or any other similar issues "
            f" when considered in the context of a typical meeting conducted in **{language}**. "
            f"This means you must use the communication styles, cultural nuances, conversational patterns, and interaction norms common in {language}-speaking environments as your frame of reference.\n"
            "Think step by step and provide thorough reasoning for each point you identify.\n\n"
            "For each identified issue, provide the following in your response:\n"
            "1. **Issue Description:** A brief description of the unrealistic element.\n"
            "2. **Reasoning:** Detailed explanation of why this element feels unnatural.\n"
            "3. **Suggested Improvement:** Recommendations on how to revise the element to enhance realism.\n\n"
            "Enclose all your feedback within <feedback></feedback> tags.\n"
            "Ensure the feedback is well-structured, clear, and concise."
            " Do not include any explanations outside of the feedback tags."
        )
        
        user_prompt = (
            "Please analyze the following meeting scene and identify any content that does not feel realistic or human-like:\n\n"
            f"{scene_text}\n\n"
            "Provide your analysis within <feedback></feedback> tags."
        )
        
        message = [
            {"role": "system",
             "content": system_prompt
            },
            {"role": "user",
             "content": user_prompt
            }
        ]
    
        response = ModelHandler.call_model_with_retry(
            client=self.client,
            messages=message,
            model=self.model_id,
            max_tokens=2000
        )
        
        model_output = response.choices[0].message.content.strip()
        
        # Extract content within <feedback></feedback> tags
        feedback = self.extract_content_between_tags(model_output, "feedback")
        print("-+"*60)
        print(f"AI Feedback:\n{feedback}")
        print("-+"*60)
        return feedback


    def humanize_scene(self, scene_text, feedback, language="English"):
        """
        Humanizes the meeting scene by addressing issues identified by the AI Content Detector.

        :param scene_text: The refined meeting scene text.
        :param feedback: String containing feedback within <feedback></feedback> tags.
        :param language: The language of the scene.
        :return: Revised (humanized) meeting scene text enclosed within <final_scene></final_scene> tags.
        """
        system_prompt = (
            "You are an experienced Editor fluent in **{language}**, tasked with humanizing a meeting scene based on feedback. "
            "Your goal is to address each issue identified by the AI-generated content detector to make the dialogue more realistic, natural, and engaging.\n\n"
            "For each issue provided, perform the following steps:\n"
            "1. **Identify** the part of the dialogue that needs revision.\n"
            "2. **Revise** the dialogue to address the issue, ensuring it aligns with the feedback.\n"
            "3. **Maintain** the original intent and key points of the conversation.\n\n"
            "Ensure that the revised scene maintains coherence, natural flow, and authenticity. "
            "Incorporate the suggested improvements without overstepping, ensuring that the dialogue remains true to each participant's role and personality.\n"
            " Additionally, ensure you preserve the existing formatting of the dialogues: `>>Role: Dialogue`.\n\n"
            "Enclose the final edited scene within <final_scene></final_scene> tags.\n"
            "Ensure the scene is properly formatted and free from any additional explanations or text outside the tags."
        )
        
        user_prompt = (
            f"The following is the refined meeting scene:\n\n{scene_text}\n\n"
            f"Based on the feedback below, please revise the scene to make it more realistic and human-like:\n\n{feedback}\n\n"
            "Provide your revisions within <final_scene></final_scene> tags."
        )
        
        # Format the system prompt with the correct language
        system_prompt = system_prompt.format(language=language)
        
        message = [
            {"role": "system",
             "content": system_prompt
            },
            {"role": "user",
             "content": user_prompt
            }
        ]
        
        response = ModelHandler.call_model_with_retry(
            client=self.client,
            messages=message,
            model=self.model_id,
            max_tokens=3000
        )
        
        model_output = response.choices[0].message.content.strip()
        
        # Extract content within <final_scene></final_scene> tags
        final_scene = self.extract_content_between_tags(model_output, "final_scene")
        print("+-"*60)
        print(f"Humanized Scene:\n{final_scene}")
        print("+-"*60)
        return final_scene
    
    def save_scene_to_csv(self, original_scene, refined_scene, ai_feedback, finalized_scene):
        """
        Saves the original, refined, AI feedback, and finalized scenes to a CSV file.

        :param original_scene: The original meeting scene text.
        :param refined_scene: The refined meeting scene text.
        :param ai_feedback: Feedback from the AI content detector.
        :param finalized_scene: The final humanized meeting scene text.
        """
        # Prepare the row data
        row = {
            "original_scene": original_scene,
            "refined_scene": refined_scene,
            "ai_feedback": ai_feedback,
            "finalized_scene": finalized_scene
        }
        
        # Write to CSV
        try:
            with open(self.csv_file_path, mode='a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=["original_scene", "refined_scene", "ai_feedback", "finalized_scene"])
                writer.writerow(row)
            print(f"Scene {len(self.scene_descriptions)} saved to {self.csv_file_path}.")
        except Exception as e:
            print(f"Error writing to CSV: {e}")



    def extract_content_between_tags(self, text, tag):
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


    def refine_scene(self, approved_scene, scene_description, scene_counter, meeting_type, director_feedback=None, language="English"):
        # Retrieve only the immediate previous scene's enriched TL;DR
        if scene_counter > 0:
            prev_scene_tldr = self.memory.get_mem_str(scene_counter - 1, only_prev=True)
        else:
            prev_scene_tldr = ""
        
        # Add director's feedback section to system prompt if available
        director_feedback_section = ""
        if director_feedback:
            director_feedback_section = (
                "\nSPECIAL INSTRUCTIONS FOR REJECTED SCENE:\n"
                "You are refining a scene that was rejected by the director. Pay special attention to these issues:\n"
                f"{director_feedback}\n"
                "While applying your regular refinement process:\n"
                "1. Prioritize addressing the specific issues mentioned in the director's feedback\n"
                "2. Ensure the refined version maintains any positive aspects noted by the director\n"
                "3. Pay extra attention to the core requirements that led to the scene's rejection\n"
                "4. Make more substantial improvements while keeping the scene's essential elements\n"
                "5. Focus on making the dialogue more natural and engaging while addressing the director's concerns\n"
            )
        
        system_prompt = (
            f"You are an experienced Editor fluent in **{language}**, tasked with editing and refining a meeting scene "
            "to enhance its naturalness, cultural fluency, coherence, and human-like qualities. "
            f"It's supposed to be a scene from a {meeting_type}, so edit accordingly.\n"
            f"{director_feedback_section}"  # Add director's feedback if available
            "While editing, your responsibilities include:\n\n"
            "1. **Avoiding Repitition and Redundancy**:\n"
            "   - Identify and address both topic-level and grammatical redundancies.\n"
            "       - **Rewrite** or **refine** dialogues that are excessively redundant, either in terms of word choices or just unnecessarily repeating discussed topics.\n"
            "       - **Remove** dialogues only if they do not contribute meaningfully to the scene. However, make sure the overall flow isn't dirupted.\n"
            "       - Remove mechanical repitition and ensure that ideas are not reiterated without adding new value.\n"
            "   - **Reduce Repetitive and Excessive Affirmations and Acknowledgments**:\n"
            "       - Avoid the unnecessary, repetitive and excessive use of short affirmations and acknowledgments (e.g., 'Absolutely!', 'Right!', 'Exactly!', From a _ perspective, etc.) especially at the beginning of dialogues.\n"
            "       - Use a variety of acknowledgments appropriately and contextually to maintain a natural and engaging conversational flow.\n"
            "       - Ensure that affirmations and acknowledgments are used sparingly and fit seamlessly within the context of the conversation to enhance authenticity.\n"
            "   - **Address Overuse of Speech Patterns and Catchphrases**:\n"
            "       - **Identify Repetitive Elements**: Detect any repetitive or excessive use of specific speech patterns or catchphrases by participants.\n"
            "       - **Vary Expressions**: Replace repetitive speech patterns and catchphrases with alternative expressions to enhance dialogue diversity and naturalness. You may also **remove unnessecary phrases if they're excessively repeated across scenes.**\n"
            "       - **Maintain Participant Voice**: Ensure that any modifications retain the unique voice and personality of the participant, avoiding significant changes to their overall speaking style or the topics being discussed.\n"
            "       - **Contextual Relevance**: Ensure that the substituted phrases or patterns fit seamlessly within the context of the conversation, maintaining coherence and relevance.\n"
            "2. **Enhancing Conversational Naturalness**:\n"
            "   - Introduce **natural speech patterns**, including **hesitations**, particpant-specific **fillers**, and **incomplete sentences** where appropriate.\n"
            "   - Allow for or introduce, if not present already,  **interruptions**, **overlapping speech**, and occasional **spontaneous topic shifts** to mimic real human interactions.\n"
            "   - Incorporate **emotional expressions**, **humor**, and **off hand comments** to add depth and authenticity.\n"
            "   - Ensure that these elements are used judiciously to enhance realism withoutcausing confusion.\n"
            "3. **Adjusting Language Style and Fluency**:\n"
            "   - Avoid overly formal or polished speech, use conversational & infromal language instead.\n"
            "   - Reflect the natural flow of dialogue, including pauses and self-corrections.\n"
            f"   - Incorporate idomatic expressions, slang, and colloqualisms appropriate to **{language}**.\n"
            "4. **Ensuring Alignment with Expertise, Perspective and Social Roles**:\n"
            "   - Ensure that each participant's dialogue is consistent with their **expertise area**, **description** and assigned **social/group roles**.\n"
            "   - Adjust dialogues if necessary (while sticking to the scene description and the topics covered in the original dialogues) to better reflect each participant's **unique perspective** and role in the group.\n"
            "       - **For topics within their Expertise:** We want the participants to provide detailed information, answer questions, and correct inaccuracies, while offering their unique perspective.\n"
            "       - **For topics outside their Expertise:** We want them to ask clarifying questions, seek additional information, and offer related but non-expert insights.\n"
            "5. **Enhancing Human-Like Qualities and Cultural Fluency**:\n"
            f"  - Ensure the language is conversational and mimics real human speech patterns in **{language}**.\n"
            f"  - Adjust dialogues, if necessary, to reflect the cultural norms, communication styles, and nuances typical of native **{language} speakers.\n"
            f"  - Use idiomatic expressions, colloquialisms, and phrases that are natural in **{language}**\n"
            "   - **Avoid Over-Enthusiasm** — Avoid language that is excessively enthusiastic, exaggerated, or unnatural for the context.\n"
            "   - **Introduce Natural Conversational Elements**:\n"
            "       - Incorporate **pauses**, **language-specific filler words** (e.g., examples for English 'um', 'you know', etc.), and **interjections**. However, **don't overuse** them to the point that the dialogues don't sound natural.\n"
            "       - Use a diverse-set of **target language-specific filler words** (such as 'um/ uh', 'like', 'You know', 'I mean', etc. for English) and pauses/hesitation (such as pauses after thinking, false starts, etc.) **occasionally** to enhance realism without hindering clarity.\n"
            "       - While making dialogue adjustments, also take into account each of the participant's *speaking style* and *personalized vocabulary*. However, make sure the dialogues in the overall scene are naturally clear, coherent and refined, without unnecessary repitions.\n"
            "   - **Maintaining Interaction Dynamics**:\n"
            "       - Emphasize interactive dialogues over monologues.\n"
            "       - Encourage participants to ask questions, seek opinions, and build on others' ideas.\n"
            "   - **Vary Sentence Structures**:\n"
            "       - Use a mix of short, medium, and long sentences/dialogues/exchanges to create a natural rhythm.\n"
            "       - Incorporate different sentence types (declarative, interrogative, exclamatory) to add variety.\n"
            "       - Avoid starting multiple sentences in a row with the same word or phrase.\n"
            "       - **Occasional Acknowledgments** (e.g., 'I see', 'Got it', 'Makes sense.', etc. for English; similary, use target-language specific acknowledgements). However, limit to only when contextually appropriate intead of overusing them.\n"
            "       - **Brief questions** (e.g., 'Can you elaborate?', 'What do you think?', ...; adjust to the target language)\n" 
            "       - **Expressions of thought or hesitation (**target language-specific**) ** (e.g., 'Hmm...', 'Well...', 'I\'m not sure...' for English; similary use target language-specific expressionss)\n" 
            "   - **Encourage Dynamic Dialogue Flow**:\n"
            "       - Allow for natural interruptions, overlapping speech, and spontaneous topic shifts where appropriate.\n"
            "       - Ensure that these elements enhance the realism of the conversation without causing confusion or disrupting the overall flow.\n"
            "   - Ensure language is conversational and mimics real human speech patterns.\n"
            "   - Make sure that the dialogues **aren't overly enthusiatic**, and that the agents don't go overboard with using the above elements. We want more balanced and natural incorporation of any of the above elements into the dialogues and not in every single dialogue.\n"
            "6. **Contextual Use of Catchphrases and Speech Patterns**:\n"
            "   - Ensure that each participant's  **catchphrases** and **speech patterns** are used **only in contextually appropriate scenarios**, enhancing the natural flow of conversation.\n"
            "   - Avoid inserting these elements solely for uniqueness; their usage should be appropriate in the context of the ongoing discussion or participant's role.\n"
            "   - Evaluate the context before incorporating these elements to ensure it aligns with the topic and the speaker's intent.\n"
            "   - Avoid overuse to prevent the dialogues from feeling scripted.\n"
            "7. **Maintaining Contextual Appropriateness and Smooth Transitions**:\n"
            "   - Ensure that each dialogue logically follows from the previous ones.\n"
            "   - Dialogues should build upon previous points and contribute meaningfully to the conversation.\n"
            "   - Implement smooth transitions between topics when necessary.\n\n"
            "8. **Introducing Human Meeting Characteristics**:\n"
            "   - Occasionally include **interruptions**, **overlapping speech**, or **disruptions** typical in human meetings.\n"
            "   - Reflect natural dynamics without causing confusion or derailing the conversation.\n\n"
            "9. **Ensuring Coherence and Natural Flow**:\n"
            "   - Maintain the logical progression of the conversation.\n"
            "   - Ensure the scene is cohesive and the conversation flows smoothly.\n\n"
            "10. **Reflecting Real Meeting Dynamics**:\n"
            "   - Include mundane and tangential remarks occasionally to add authenticity.\n"
            "   - Allow for brief deviations from the main topic that naturally occur in real meetings.\n"
            "11. **Allowing for Confusion and Uncertainty**:\n"
            "   - Include moments where participants express uncertainty or ask for clarification.\n"
            "   - Reflect natural human tendencies to not always have immediate answers.\n"
            "**Instructions and Guidelines**:\n"
            "- Use the provided **Scene Description** to align the scene with its intended purpose.\n"
            "- Reference the **Immediate Previous Scene's TL;DR** to maintain continuity and prevent unnecessary repetition.\n"
            "- Preserve the key points and intentions of the original dialogues.\n"
            "- **Dialogue Variety:** Ensure that each participant expresses their ideas uniquely, reflecting their individual communication styles.\n"
            "- **Avoid Repetition:** If you notice that multiple dialogues present ideas in a similar way (for each participant), rephrase them to introduce diversity.\n"
            "- **Maintain Coherence:** While diversifying dialogues, ensure that the conversation remains coherent and flows naturally.\n"
            "- **Respect Original Intent:** Do not alter the fundamental ideas or messages being conveyed by the participants.\n"
            "- **Ensure that we don't leave any questions, clarification requests or any points/ dialogues that need addressal unanswered.**\n"
            "- **Limit the use of catchphrases to no more than twice per participant per meeting.** Replace repetitive catchphrases with varied expressions that convey similar meanings.\n"
            "- **Limit the use of short affirmations** like 'Absolutely!', 'Right!', 'Exactly', ...** to only when contextually appropriate**. Introduce a variety of acknowledgments to avoid monotony.\n"
            "- Introduce **filler words, pauses and hesitations** freely and in a natural way to enhance authenticity.\n"
            "- **Vary sentence structures** and **introduce dynamic dialogue elements** to enhance the natural flow of conversation.\n"
            "- Ensure **culturally authentic communication** by using language and expressions that are congruent with the target culture's communication styles.\n"
            "- Do not over-polish; retain natural imperfections in speech.\n"
            "- Ensure that the dialogues feel spontaneous and unscripted.\n"
            "- Make sure the refined scene remains within a reasonable length and does not omit essential information.\n"
            "- **Do not include any explanations, comments, or notes in your response. Output only the refined scene in the original format.\n**"
            "Produce the refined scene in the same format, using `>>Role: Dialogue`."
        )

        participants_info = ""
        for agent in self.agents:
            participants_info += f"- **{agent['role']}**:\n"
            participants_info += f"  - Description: {agent.get('description', agent['role'])}\n"
            participants_info += f"  - Expertise Area: {agent.get('expertise_area', agent['role'])}\n"
            participants_info += f"  - Unique Perspective: {agent.get('perspective', '')}\n"
            participants_info += f"  - Social Role(s): {', '.join(agent.get('social_roles', []))}\n"
            participants_info += f"  - Social Role(s) Descriptions: {'; '.join(agent.get('social_roles_descr', []))}\n"
            participants_info += f"  - Speaking Style:\n"
            participants_info += f"     - Tone: {agent['speaking_style'].get('tone', '')}\n"
            participants_info += f"     - Language Complexity: {agent.get('speaking_style', '').get('language_complexity', '')}\n"
            participants_info += f"     - Communication Style: {agent.get('speaking_style', '').get('communication_style', '')}\n"
            participants_info += f"     - Sentence Structure: { agent.get('speaking_style', '').get('sentence_structure', '')}\n"
            participants_info += f"     - Formality: {agent.get('speaking_style', '').get('formality', '')}\n"
            participants_info += f"     - Other Traits: {agent.get('speaking_style', '').get('other_traits', '')}\n"
            participants_info += f"  - Personalized Vocabulary:\n"
            participants_info += f"     - Filler Words: {'; '.join(agent.get('personalized_vocabulary', []).get('filler_words', []))}\n"
            # participants_info += f"     - Catchphrases: {'; '.join(agent.get('personalized_vocabulary', []).get('catchphrases', []))}\n"
            # participants_info += f"     - Preferred Words: {'; '.join(agent.get('personalized_vocabulary', []).get('preferred_words', []))}\n"
            # participants_info += f"     - Speech Patterns: {'; '.join(agent.get('personalized_vocabulary', []).get('speech_patterns', []))}\n"
            # participants_info += f"     - Emotional Expressions: {'; '.join(agent.get('personalized_vocabulary', []).get('emotional_expressions', []))}\n\n"

        user_prompt = (
            f"**Participants' Information**:\n{participants_info}\n"
            f"**Scene Description**:\n{scene_description}\n"
            f"**Immediate Previous Scene's Summary**:\n{prev_scene_tldr}\n"
            f"**Approved Scene Draft**:\n{approved_scene}\n"
            + (f"\n**Director's Feedback to Address:**\n{director_feedback}\n" if director_feedback else "")  # Add feedback to user prompt if available
            + "Please refine the above scene according to your responsibilities and instructions. "
            "Make sure to insert **filler words** naturally for each participant (as specified in the participants' information) "
            "to enhance the authenticity and realism of the overall conversation.\n"
            "Ensure that you follow all the instructions and guidelines provided properly.\n"
            "Respond strictly using the following delimiter-based format, with no additional comments or explanations of your changes:\n"
            "###Refined Scene###:\n"
            "<Refined scene dialogues with all the necessary modifications as per the specified instructions and guidelines.>"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = ModelHandler.call_model_with_retry(
            client=self.client,
            messages=messages,
            model=self.model_id,
            max_tokens=4000 # Experimental
        )

        response = response.choices[0].message.content.strip()
        delimiter = "###Refined Scene###:"
        refined_scene = self.extract_scene(response, delimiter)

        print("="*130)
        print(f"Original Scene {scene_counter+1}: \n{approved_scene}")
        print("-"*130)
        print(f"Refined Scene {scene_counter+1}:\n{refined_scene}")
        print("="*130)

        return refined_scene


    def apply_special_effects(self, scene, meeting_type, language='English'):
        system_prompt = (
        "You are an expert editor tasked with enhancing a meeting scene by introducing natural special effects "
        "such as interruptions, overlapping speech and brief tangents. The goal is to make the conversation more realistic and "
        "reflect common dynamicsf in human meetings without derailing the main discussion."
        " Consider the type of meeting to tailor special effects accordingly. "
        "**Ensure that any special effects introduced do not cause inconsistencies in the dialogue.**"
        " **If a participant interrupts with a question or seeks clarification, make sure that another participant addresses it appropriately.**\n"
        f"**Ensure that any effects introdcued are in {language}.**\n"
        f"Furthermore, this is a scene from a **{meeting_type}** - so add special effects tailored to this setting."
        )

        participants_info = ""
        for agent in self.agents:
            participants_info += f"- **{agent['role']}**:\n"


        user_prompt = (
            f"Original Scene:\n{scene}\n\n"
            f"For some context, here are all the meeting participants:\n{participants_info}"
            "Instructions:\n"
            f"- Introduce **at most one** special effect into the scene. Adapt the effect(s) to the target language - **{language}**.\n"
            "- Choose from the following list of common disruptions in human meetings:\n"
            "  - Polite interruptions to add a point or seek clarification.\n"
            "  - Participants speaking over each other briefly.\n"
            "  - Side comments or asides related to the main topic.\n"
            "  - Brief off-topic remarks or questions.\n"
            "  - Moments of confusion requiring clarification.\n"
            "  - Laughter or reactions to a humorous comment.\n"
            "  - Time-checks or agenda reminders.\n"
            "  - Casual side comments or friendly banter.\n"
            "  - Time-checks or agenda reminders.\n"
            "  - Casual side comments or friendly banter.\n"
            "  - Rapid-fire idea contributions.\n"
            "  - Instructional interruptions to provide examples.\n"
            "  - Light-hearted jokes or humorous reactions.\n"
            "  - Strategic questions about project goals.\n"
            "  - Feedback requests on presented material.\n"
            "  - Technical difficulties (Problems with audio, video, or presentation equipment — e.g., 'You're on mute.', ...).\n"
            "  - Checking the time or mentioning scheduling constraints.\n"
            "  - Misunderstandings that are quickly resolved.\n"
            "  - External diruptions such as Phone calls, notifications, etc."
            "- Ensure the special effect fits naturally into the conversation and is contextually appropriate.\n"
            "- **If you introduce a disruption that requires a response (like a question, clarification, or interruption), make sure that the subsequent dialogue includes an appropriate response from another participant.**\n"
            "- Maintain the overall flow and coherence of the scene.\n"
            "- Do not change the main topics or key points being discussed.\n"
            "- Output only the modified scene without any additional explanations.\n"
            f"- Make sure that any effects introduced are adapted to the target language: **{language}**.\n"
            "Respond strictly using the following delimiter-based format, and no additional comments and explanations of your changes:\n"
            "###Modified Scene###:\n"
            "<Modified scene dialogues with **one special effect** introduced and well-integerated.>"
        )


        # Construct the messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]


        # Call the model (assuming you have a ModelHandler similar to previous code)
        response = ModelHandler.call_model_with_retry(
            self.client,
            messages,
            self.model_id,
            max_tokens=2000
        )


        # Extract the modified scene from the response
        modified_scene = response.choices[0].message.content.strip()
        delimiter = "###Modified Scene###:"
        modified_scene = self.extract_scene(modified_scene, delimiter)
        print("v"*130)
        print(f"Modified Scene:\n{modified_scene}")
        print("^"*130)
        return modified_scene



    def extract_scene(self, model_response, delimiter):
        match = re.search(f'{delimiter}\s*(.*)', model_response, re.DOTALL)

        if match:
            refined_scene = match.group(1).strip()
            return refined_scene
        else:
            return model_response

    
    @staticmethod
    def post_process(accepted_scenes):
        whole_meeting = " \n ".join(accepted_scenes)
        return whole_meeting

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
            "explanation": "Failed to parse JSON from model response.",
            "accept_scene": False
        }

    def generate_tldr(self, scene_text, language="English"):
        system_prompt = (
        "You are an expert meeting summarizer. "
        f"Given the transcript of a single scene from a meeting, provide a TL;DR summary in **{language}** that comprehensively captures the following aspects:\n\n"
        "1. **All Topics Discussed**: List and briefly describe each topic covered in the scene.\n"
        "2. **Angles or Perspectives**: For each topic, outline the different angles, viewpoints, or approaches through which it was discussed.\n"
        "3. **Key Decisions Made**: Highlight any significant decisions that were reached during the scene.\n"
        "4. **Roles of Participants**: Identify the roles of each participant involved in the scene.\n"
        "5. **Last Speaker and Their Contribution**: Specify who was the last speaker and provide a brief summary of their final contribution to the discussion.\n\n"
        "Use 'the scene' instead of 'the meeting' when referring to the discussion. "
        "Ensure the summary is concise yet comprehensive, ideally spanning only a few sentences, providing enough detail to inform subsequent scenes without being overly verbose."
    )
        user_prompt = f"Scene transcript:\n{scene_text}\n\nPlease provide the TL;DR summary of **this scene**:"


        message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]


        response = ModelHandler.call_model_with_retry(
            client=self.client,
            messages=message,
            model=self.model_id,
            max_tokens=350
        )


        tldr_summary = response.choices[0].message.content.strip()
        return tldr_summary



    def generate_meeting(self, meeting_type, language="English"):
        # Initialize the Discussion Coordinator
        moderator = None
        discussion_protocol = DiscussionProtocol(self.client, self.model_id, self.agents, self.memory, protocol="dialogue")
        discussion_coordinator = DiscussionCoordinator(self.client, self.model_id, moderator, self.agents, token_limit=2048, memory_handler=self.memory)
        accepted_scenes = []
        last_speaker = None

        for index, scene in enumerate(self.scene_descriptions):
            sub_scene, last_speaker = self.generate_scene(index, scene, "", self.article_text, discussion_coordinator, discussion_protocol, "", None, meeting_type, last_speaker, language)
            # Store the accepted scene
            accepted_scenes.append(sub_scene)

            scene_last_dialogue = sub_scene.split('>>')[-1]

            # Generate TL;DR of the accepted scene
            tldr_summary = self.generate_tldr(sub_scene, language)

            # Update memories with the TL;DR summary at the correct index
            self.memory.update_mems(index, tldr_summary, scene_last_dialogue)
            

        return self.post_process(accepted_scenes)
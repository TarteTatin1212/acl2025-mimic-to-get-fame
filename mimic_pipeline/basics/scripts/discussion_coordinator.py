import logging

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from basics.scripts.utils import Utils
from basics.scripts.memory_handler import MemoryHandler
from basics.scripts.discussion_protocol import DiscussionProtocol

class DiscussionCoordinator:
    def __init__(self, client, model_id, moderator, agents, token_limit, memory_handler=None):
        self.client = client
        self.model_id = model_id
        self.moderator = moderator
        self.agents = agents
        self.memory = memory_handler if memory_handler is not None else MemoryHandler(memories=[[] for _ in agents])
        self.token_limit = token_limit
        self.processed_tokens = 0
        self.global_summary = ""


        
    def process_transcript(self, transcript, max_chunk_size=500):
        chunks = Utils.chunk_meeting_transcript(transcript, max_chunk_size)
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

            discussion_protocol = DiscussionProtocol(self.client, self.model_id, self.agents, self.memory, protocol="simple")
            chunk_summary, turns_taken = discussion_protocol.discuss(task_instruction, chunk, global_summary)
            global_summary = chunk_summary  # Update global summary with the chunk summary

        return global_summary.strip()
    
    def process_meeting_generation(self, scene_counter, scene_description, scene_director_notes, additional_input, meeting_type, last_speaker, discussion_protocol, language="English"):
        # discussion_protocol = DiscussionProtocol(self.client, self.model_id, self.agents, self.memory, protocol="simple")
        played_scene, turns_taken, last_speaker = discussion_protocol.discuss(scene_counter, scene_description, scene_director_notes, additional_input, meeting_type, last_speaker, language)
        return played_scene, last_speaker
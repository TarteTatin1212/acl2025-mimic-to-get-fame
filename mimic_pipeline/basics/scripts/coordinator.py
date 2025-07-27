from scripts.discussion_coordinator import DiscussionCoordinator
from scripts.utils import Utils

class Coordinator():
    def __init__(self, client, model_id, persona_generator, include_moderator=False, task_description="Summarize a given meeting transcript."):
        self.client = client
        self.model_id = model_id
        self.persona_generator = persona_generator
        self.include_moderator = include_moderator
        self.task_description = task_description

    def coordinate(self, row, num_agents, max_chunk_size=500):
        transcript = row['transcript']
        original_summary = row['summary']

        agents = self.persona_generator.generate_debators(self.task_description, transcript, num_agents)
        moderator = self.persona_generator.generate_moderator()

        # Initialize the Discussion Coordinator
        discussion_coordinator = DiscussionCoordinator(self.client, self.model_id, moderator, agents, token_limit=2048)

        # Process the transcript to get the generated summary
        generated_summary = discussion_coordinator.process_transcript(transcript, max_chunk_size)
        generated_summary = Utils.clean_summary(generated_summary)
        
        return transcript, original_summary, generated_summary
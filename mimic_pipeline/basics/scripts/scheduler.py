from scripts.persona_generator import PersonaGenerator
from scripts.coordinator import Coordinator

import pandas as pd

class Scheduler: 
    def __init__(self, client, model_id, num_agents, max_chunk_size=100000):
        self.client = client
        self.model_id = model_id
        self.num_agents = num_agents
        self.max_chunk_size = max_chunk_size
        
    def schedule(self, df):
        summaries = []
        persona_generator = PersonaGenerator(self.client, self.model_id)
        coordinator = Coordinator(self.client, self.model_id, persona_generator)
        for _, row in df.iterrows():
            transcript, original_summary, generated_summary = coordinator.coordinate(row, self.num_agents, self.max_chunk_size)
            
            # Store the results
            summaries.append({
                'transcript': transcript,
                'original_summary': original_summary,
                'generated_summary': generated_summary,
            })
        return pd.DataFrame(summaries)

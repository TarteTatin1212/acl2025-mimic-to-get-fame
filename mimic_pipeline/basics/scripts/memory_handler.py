class MemoryHandler:
    def __init__(self, memories):
        self.memories = memories
        self.last_dialogues = [[] for _ in range(len(self.memories))]
    
    def print_memories(self):
        for idx, memory in enumerate(self.memories):
            print(f"Scene {idx+1} memories: {memory}")
    
    
    def get_mem_str(self, upto_idx, only_prev=False):
        """
        For conv_genearion: Returns a concatenated string of TL;DR summaries of scenes up to and including upto_index.
        """
        if upto_idx < 0:
            return ""
        else:
            # Return only the prev. scene's tl;dr and not of all the prev. ones
            if only_prev:
                return self.memories[upto_idx][0]
            # Collect TL;DR summaries up to the specified index
            summaries = []
            for i in range(upto_idx + 1):
                if self.memories[i]:
                    scene_number = i + 1
                    summary = self.memories[i][0] # Get the TL;DR summary
                    summaries.append(f">Scene {scene_number} {summary}")
            
            memory_string = "\n".join(summaries)
            return memory_string

    def get_last_dialog(self, scene_idx):
        return self.last_dialogues[scene_idx][0]


    def update_mems(self, index, new_memory, scene_last_dialog):
        """
        For conv_genearion: Appends the new TL;DR summary to the sublist at the specified index.
        """
        self.memories[index].append(new_memory)
        self.last_dialogues[index].append(scene_last_dialog)


    def get_memory_string(self, agent_index, context_length):
        memory_string = " ".join([" ".join(map(str, item)) for item in self.memories[agent_index][-context_length:]]) if self.memories[agent_index] else ""
        current_draft = self.memories[agent_index][-1] if self.memories[agent_index] else "Initial draft content here"
        return memory_string, current_draft

    def update_memories(self, agent_index, new_memory):
        self.memories[agent_index].append(new_memory)
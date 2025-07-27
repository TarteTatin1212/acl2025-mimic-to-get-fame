from scripts.agreement_protocol import AgreementProtocol
from scripts.model_handler import ModelHandler

import json
import logging

class DiscussionProtocol:
    def __init__(self, client, model_id, agents, memory, protocol):
        self.client = client
        self.model_id = model_id
        self.agents = agents
        self.memory = memory
        self.protocol = protocol
        self.discussion_protocols = {
            "simple": self.simple_discussion_protocol,
            "complex": self.complex_discussion_protocol,
            "dialogue": self.dialogue_discussion_protocol,
        }
        
        print()
        memory.print_memories()
        print()
    
    def participate(self, template_filling):
        task_instruction = (
            "You are {persona}, tasked with summarizing the meeting transcript and generate an abstractive summary. "
            "Focus on your unique perspective or expertise as {role} to enhance the summary. "
            "Utilize all fields of the provided context, including the current draft, the original meeting transcript, "
            "previous summaries, and feedback from all agents. "
            "Even if the current chunk/ meeting transcript does not have some details, use the information from the currentDraft and previousSummary "
            "to create a comprehensive and cohesive summary. "
            "Ensure your summary is coherent, cohesive, and incorporates the best points from each agent. "
            "Do not include any introductory or closing statements; provide only the summary text. "
            "Start your summary directly with the content without any preamble."
            "Your summary can be at most 200 words."
        )
        template_filling["taskInstruction"] = task_instruction.format(persona=template_filling["persona"], role=template_filling["personaDescription"])
        
        response = ModelHandler.call_model_with_retry(
            self.client, [{"role": "system", "content": json.dumps(template_filling)}], self.model_id, max_tokens=250
        )
        
        draft = response.choices[0].message.content
        return draft



    
    def discuss(self, task_instruction, input_str, prev_summary="", max_turns=3, context_length=5):
        final_draft, turn = self.discussion_protocols[self.protocol](task_instruction, input_str, prev_summary, max_turns, context_length)
        return final_draft, turn
    
    def simple_discussion_protocol(self, task_instruction, input_str, prev_summary="", max_turns=3, context_length=5):
        turn = 0
        decision = False
        current_draft = ""
        agreement_protocol = AgreementProtocol(self.client, self.model_id, self.agents, self.memory, agreement="vote")

        while not decision and turn < max_turns:
            turn += 1
            buffer = []
            logging.info("\n"+"*" * 50 + f" Turn {turn} " + "*" * 50+"\n")
            for agent_index, agent in enumerate(self.agents):
                logging.info(f"Agent {agent_index} ({agent['role']}) is participating.")
                memory_string, current_draft = self.memory.get_memory_string(agent_index, context_length)
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
                self.memory.update_memories(agent_index, buffer)

            logging.info("Agreement Protocol is running.")
            current_draft = agreement_protocol.run_protocol(buffer)

            logging.info("Current draft after agreement: %s", current_draft)

            if turn >= max_turns:
                decision = True

        final_draft = current_draft if current_draft else "No summary generated."
        return final_draft, turn
    
    def complex_discussion_protocol(self, task_instruction, input_str, prev_summary="", max_turns=3, context_length=5):
        return "Complex discussion protocol is not yet implemented.", 0
    
    def dialogue_discussion_protocol(self, task_instruction, max_turns=100):
        ...
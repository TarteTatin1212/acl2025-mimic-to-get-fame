import sys
import os
import ast
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from basics.scripts.model_handler import ModelHandler
from basics.scripts.persona_generator import PersonaGenerator


meeting_types = {
    "Brainstorming Session": {
        "id": "mt_001",
        "description": "A meeting focused on generating creative ideas and solutions through open and free-flowing discussions.",
        "objectives": [
        "Generate a wide range of ideas",
        "Encourage creative thinking",
        "Foster a collaborative environment"
        ],
        "expected_outcomes": [
        "List of potential ideas",
        "Prioritized concepts for further exploration"
        ]
    },
    "Decision-Making Meeting": {
        "id": "mt_002",
        "description": "A structured meeting aimed at making specific decisions through analysis and consensus-building.",
        "objectives": [
        "Evaluate options",
        "Weigh pros and cons",
        "Reach a consensus or make a definitive decision"
        ],
        "expected_outcomes": [
        "Finalized decision",
        "Action items with assigned responsibilities"
        ]
    },
    "Problem-Solving Meeting": {
        "id": "mt_003",
        "description": "A meeting dedicated to identifying, analyzing, and finding solutions to specific problems or challenges.",
        "objectives": [
        "Identify the root cause of the problem",
        "Analyze potential solutions",
        "Implement actionable solutions"
        ],
        "expected_outcomes": [
        "Clear understanding of the problem",
        "Viable solutions identified",
        "Action plan for implementation"
        ]
    },
    "Training and Workshop Session": {
        "id": "mt_004",
        "description": "A structured meeting aimed at educating participants on specific skills, knowledge areas, or tools.",
        "objectives": [
        "Educate participants on new skills or knowledge",
        "Provide hands-on training and practice",
        "Assess participant understanding and proficiency"
        ],
        "expected_outcomes": [
        "Enhanced participant skills",
        "Increased knowledge in specific areas",
        "Preparedness to apply new skills"
        ]
    },
    "Strategic Planning Meeting": {
        "id": "mt_005",
        "description": "A high-level meeting focused on setting long-term goals, defining strategies, and allocating resources to achieve organizational objectives.",
        "objectives": [
        "Define long-term organizational goals",
        "Develop strategies to achieve goals",
        "Allocate resources effectively"
        ],
        "expected_outcomes": [
        "Comprehensive strategic plan",
        "Defined organizational objectives",
        "Resource allocation roadmap"
        ]
    },
    "Committee or Board Meeting": {
        "id": "mt_006",
        "description": "A formal meeting of a committee or board to discuss policies, make decisions, and oversee organizational governance.",
        "objectives": [
        "Review and discuss policies",
        "Make governance decisions",
        "Oversee organizational performance"
        ],
        "expected_outcomes": [
        "Approved or revised policies",
        "Governance decisions made",
        "Reviewed organizational performance"
        ]
    },
    "Innovation Forum": {
        "id": "mt_007",
        "description": "A meeting focused on fostering innovative ideas, encouraging out-of-the-box thinking, and exploring new opportunities.",
        "objectives": [
        "Encourage innovative thinking",
        "Explore new opportunities and ideas",
        "Foster a culture of innovation"
        ],
        "expected_outcomes": [
        "Generated innovative ideas",
        "Identified new opportunities",
        "Enhanced culture of innovation"
        ]
    },
    "Agile/Scrum Meeting": {
        "id": "mt_008",
        "description": "A set of meetings within the Agile/Scrum framework, including daily stand-ups, sprint planning, sprint reviews, and retrospectives.",
        "objectives": [
        "Facilitate daily progress updates",
        "Plan and prioritize sprint tasks",
        "Review sprint outcomes",
        "Reflect on process improvements"
        ],
        "expected_outcomes": [
        "Daily progress transparency",
        "Well-defined sprint plans",
        "Reviewed sprint deliverables",
        "Identified process improvements"
        ]
    },
    "Remote or Virtual Meeting": {
        "id": "mt_009",
        "description": "A meeting conducted via digital platforms, allowing participants from different locations to collaborate in real-time.",
        "objectives": [
        "Facilitate collaboration among remote participants",
        "Share information and updates",
        "Coordinate tasks and projects virtually"
        ],
        "expected_outcomes": [
        "Effective virtual collaboration",
        "Shared information and updates",
        "Coordinated tasks and projects"
        ]
    },
    "Project Kick-Off Meeting": {
        "id": "mt_010",
        "description": "A meeting held at the beginning of a project to outline objectives, assign roles, and establish timelines.",
        "objectives": [
        "Introduce project goals and objectives",
        "Define team roles and responsibilities",
        "Establish project timelines and milestones"
        ],
        "expected_outcomes": [
        "Clear project roadmap",
        "Assigned roles and responsibilities",
        "Initial project timeline established"
        ]
    },
    "Stakeholder Meeting": {
        "id": "mt_011",
        "description": "A meeting involving key stakeholders to discuss project progress, gather feedback, and ensure alignment with stakeholder expectations.",
        "objectives": [
        "Update stakeholders on project progress",
        "Gather stakeholder feedback",
        "Ensure alignment with stakeholder expectations"
        ],
        "expected_outcomes": [
        "Informed stakeholders",
        "Collected valuable feedback",
        "Aligned project goals with stakeholder expectations"
        ]
    },
    "Casual Catch-Up": {
        "id": "mt_012",
        "description": "An informal meeting aimed at fostering relationships and sharing personal or professional updates.",
        "objectives": [
        "Build team rapport",
        "Share updates",
        "Discuss non-work-related topics"
        ],
        "expected_outcomes": [
        "Strengthened team relationships",
        "Shared personal and professional insights"
        ]
    },
    "Cross-Functional Meeting": {
        "id": "mt_013",
        "description": "A meeting that brings together members from different departments or functions to collaborate on shared objectives or projects.",
        "objectives": [
        "Facilitate collaboration across departments",
        "Align on shared project objectives",
        "Resolve interdepartmental issues"
        ],
        "expected_outcomes": [
        "Aligned project objectives",
        "Resolved cross-departmental issues",
        "Enhanced interdepartmental collaboration"
        ]
    },
    "Retrospective Meeting": {
        "id": "mt_014",
        "description": "A meeting held after a project phase to reflect on what went well, what didn't, and how processes can be improved.",
        "objectives": [
        "Reflect on past performance",
        "Identify successes and areas for improvement",
        "Implement process enhancements"
        ],
        "expected_outcomes": [
        "Documented lessons learned",
        "Actionable improvement plans",
        "Enhanced future project processes"
        ]
    }
}


class MeetingPlanner:
    def __init__(self, client, model_id, article_title, article, summary, meeting_type):
        self.client = client
        self.model_id = model_id
        self.article_title = article_title
        self.article = article
        self.summary = summary
        self.meeting_type = meeting_type
        self.tags = []


    def plan_meeting(self, language="English"):

        self.extract_tags()

        # Fetch meeting type attributes
        meeting_info = meeting_types[self.meeting_type]
        objectives = meeting_info['objectives']
        expected_outcomes = meeting_info['expected_outcomes']
        
        persona_generator = PersonaGenerator(self.client, self.model_id)
        task_description = "The participants will simulate a meeting based on a given meeting outline, that has to be as realistic as possible. The meeting's content will be a Wikipedia article."

        num_agents = random.randint(3, 6)
        participants = persona_generator.generate_debators_from_article(task_description=task_description, article_title=self.article_title, article=self.article, tags=self.tags, num_agents=num_agents, meeting_type=self.meeting_type, language=language)

        print("-" * 20)
        print(participants)
        print()
        
        system_prompt = (
            f"Based on the following summary and corresponding Wikipedia article, plan a realistic {self.meeting_type} including the below participants and create a flexible agenda that allows for spontaneous discussion and natural flow of conversation."
            " The participants are professionals who are familiar with each other, so avoid lengthy self-introductions." # Experimental
            " The meeting should focus on the key points from the summary and align overall with the meeting's objectives, but also allow for flexibility and unplanned topics."
            " Think of it as if you were writing a script for a movie, so break the meeting into scenes."
            " Describe what each scene is about in a TL;DR style and include bullet points for what should be covered in each scene."
            " Ensure that the first scene includes, among other things, a brief greeting among participants without excessive details." # Experimental
            " Output the meeting plan as a Python list, where each element is one string describing the scene.\n"
            "Additional Guidelines:\n"
            "- Avoid rigid scene structures\n"
            "- Allow for natural topic evolution\n"
            "- Include opportunities for spontaneous contributions\n"
            "- Plan for brief off-topic moments as well\n"
            "- Include some points where personal experiences could be relevant\n"
            "- Allow for natural diagreement and resolution\n"
            "Follow these strict formatting rules:\n"
            " 1. Use only single quotes for strings\n"
            " 2. Use '\\n' for line breaks within strings\n"
            " 3. Escape any single quotes within strings using backslash\n"
            " 4. Do not use triple quotes or raw strings\n"
            " 5. Each scene must follow this exact format:\n"
            "     'Scene X': <Scene Title>\\nTLDR: <Brief Overview>\\n- <Bullet Point 1>\\n- <Bullet Point 2> ...'\n"
            " 6. The output should start with '[' and end with ']'\n"
            " 7. Scenes should be separatedby commas\n\n"
            # " If a scene description is multi-line, keep it as a single string in the list, using '\\n' for line breaks if necessary."
            " Return the output as a valid Python list in the following format:\n"
            "['<description scene 1 including TLDR and bullet points>', '<description scene 2 including TLDR and bullet points>', ...]" 
            "Do not include any additional text or code block markers. Ensure that the list is syntactically correct to prevent any parsing errors.\n"
        )


        user_prompt = (
            "Here are the materials for you to consider to plan the whole meeting outline and structure. \n"
            f"Meeting Type: {self.meeting_type}\n"
            f"Meeting Objectives: {'; '.join(objectives)}\n\n"
            f"Expected Outcomes: {'; '.join(expected_outcomes)}\n\n"
            f"**Article Title: {self.article_title}**\n\n"
            f"Summary:\n {self.summary}\n\n"
            f"Tags: {self.tags}\n\n"
            f"Participants: {participants}\n\n"
            "Additional Notes:\n"
            "- The participants are familiar with each other — so avoid length self-introductions.\n"
            "- Focus on the meeting agenda and key discussion points.\n\n"
            f"Meeting Plan:"
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

        response = ModelHandler.call_model_with_retry(self.client, message, self.model_id, max_tokens=4000)
        scenes_list = response.choices[0].message.content.strip()
        
        print(scenes_list)
        scenes_list = scenes_list.replace('```python', '').replace('```', '').strip()
        scenes_list = ast.literal_eval(scenes_list)
        scenes_list = [scene.strip() for scene in scenes_list]
        return scenes_list, self.tags, participants
    
    def extract_tags(self):
        
        system_prompt = (
            "You are a Wikipedia Editor tasked with assigning five highly relevant and specific tags to a given Wikipedia article. "
            "The tags should accurately reflect the main topics, themes, and subjects covered in the article."
        )
        
        user_prompt = (
            "Here is the Wikipedia article. Only return a python list of strings including the five most relevant tags for the specified article, reflecting the main topics, themes and subjects covered in it.\n\n"
            f"Wikipedia article: < {self.article} >"
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
        
        response = ModelHandler.call_model_with_retry(self.client, message, self.model_id, max_tokens=100)
        extracted_list = response.choices[0].message.content.strip()
        print(f"Tags response: {extracted_list}")
        extracted_list = extracted_list.replace('```python', '').replace('```', '')
        self.tags = ast.literal_eval(extracted_list)
        
import sys
import os
import re
from typing import Dict, List, Tuple

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from basics.scripts.model_handler import ModelHandler

class MeetingEvaluator:
    def __init__(self, client, model_id):
        self.client = client
        self.model_id = model_id
        # Define psychological criteria with detailed descriptions
        self.psychological_criteria = {
            "Information Exchange": """Instances where participants share knowledge, facts, or expertise with others. This includes explaining concepts, sharing experiences, or providing data.
### Rating 1 (Rarely Observed)\n
**(Emma)**: *“Does anyone have the quarterly numbers?”*
**(Liam)**: *“I haven’t looked them up yet.”*\n
*Minimal detail; participants do not provide factual updates beyond a simple query and a short response.*
### Rating 5 (Prominent Case)
**(Emma)**: *“I’ve compiled last quarter’s sales: total revenue increased by 8%. Additionally, the new subscription model brought 200 new customers.”*  
**(Liam)**: *“Interesting. Our customer retention rate also jumped by 5%. Here’s the Excel sheet with a breakdown by region.”*  
*Rich data sharing with specific facts and clarifications.*""",
            
            "Knowledge Seeking": """Moments when participants actively ask questions to gain understanding, request clarification, or seek others' expertise.
### Rating 1 (Rarely Observed)
**(Sophie)**: *“What’s the plan for social media?”*  
**(Max)**: *“Not sure yet.”*  

*Only a superficial question without follow-up.*

### Rating 5 (Prominent Case)
**(Sophie)**: *“Could you explain the rationale behind using Twitter ads over LinkedIn ads for our B2B campaigns? I’m trying to understand the audience overlap.”*  
**(Max)**: *“Sure. Our data show a 30% higher engagement rate on Twitter, which translates to more click-throughs. I can share the report after the meeting if you’d like a deeper look.”*  

*A clear, detailed inquiry is made, prompting an in-depth, clarifying response.*""",
            
            "Explanation Provision": """When participants elaborate on concepts, provide detailed explanations, or clarify points upon request.
### Rating 1 (Rarely Observed)
**(Noah)**: *“Why did we switch to the new software?”*  
**(Ava)**: *“It seemed better.”*  

*Vague, minimal explanation offered.*

### Rating 5 (Prominent Case)
**(Noah)**: *“Why did we switch to the new software?”*  
**(Ava)**: *“We were exceeding the user limits on the old tool, which caused frequent downtime. The new one offers unlimited user access, integrates with Slack for real-time notifications, and reduces our monthly costs by 15%.”*  

*Detailed rationale and specifics are provided.*""",
            
            "Influence Attempts": """Instances where participants try to persuade others, change opinions, or guide the conversation in a particular direction.
### Rating 1 (Rarely Observed)
**(Olivia)**: *“I think we should postpone the product launch.”*  
**(Ethan)**: *“Okay.”*  

*No evident persuasion; the statement is accepted without argument.*

### Rating 5 (Prominent Case)
**(Olivia)**: *“I strongly recommend postponing the product launch. Our beta tests indicate a 30% bug rate, which could damage brand trust if we go live now. Let’s resolve these issues and aim for a two-week delay.”*  
**(Ethan)**: *“I see your point. The potential support costs could skyrocket if we launch prematurely. Let’s finalize a revised timeline by close of day.”*  

*Clear and forceful persuasion with supportive data.*""",
            "Topic Control": """How participants manage conversation flow, introduce new topics, or steer discussions toward specific outcomes.
### Rating 1 (Rarely Observed)
**(Mia)**: *“Should we talk about the budget next?”*  
**(Lucas)**: *“Uh, not sure.”*  

*Minimal steering; no decisive introduction or redirection.*

### Rating 5 (Prominent Case)
**(Mia)**: *“All right, we’ve settled the marketing plan. Next, let’s move on to budgeting. We’ll start with fixed costs, then variable expenses, and we’ll aim to finalize by the end of this session.”*  
**(Lucas)**: *“Agreed. Let me open the spreadsheet so we can tackle fixed costs first.”*  

*Strong direction provided to guide the meeting’s flow.*""",
            
            "Power Dynamics": """Observable patterns of authority, leadership, or deference between participants, including who leads discussions or makes final decisions.
### Rating 1 (Rarely Observed)
**(Sophia)**: *“Should we ask the boss for approval?”*  
**(Ethan)**: *“Not necessary, I guess.”*  

*No clear hierarchical influence or leadership exerted.*

### Rating 5 (Prominent Case)
**(Sophia - Team Lead)**: *“I need everyone’s final input by noon. Then I’ll inform upper management of our decision.”*  
**(Ethan)**: *“Understood, Sophia. I’ll adjust the figures and send them your way.”*  

*A clear demonstration of authority and deference.*""",
            
            "Response Patterns": """Whether participants engage with or respond to others' suggestions
### Rating 1 (Rarely Observed)
**(Hannah)**: *“Let’s schedule a brainstorming session.”*  
*(Group remains silent.)*  

*No acknowledgment or feedback on the suggestion.*

### Rating 5 (Prominent Case)
**(Hannah)**: *“Let’s schedule a brainstorming session to refine our marketing angles.”*  
**(Michael)**: *“Great idea! How about we block an hour tomorrow morning? I can prepare some initial prompts.”*  
**(Lily)**: *“I’m in. Let’s finalize a time.”*  

*Immediate, enthusiastic engagement with the suggestion.*""",
            
            "Standpoint Maintenance": """Cases where participants firmly hold their position or defend their viewpoint, especially in face of disagreement.
### Rating 1 (Rarely Observed)
**(Charlie)**: *“I think we should keep the old design.”*  
**(Amelia)**: *“We have a new one.”*  
**(Charlie)**: *“That’s fine. Let’s use the new design.”*  

*No real defense; quickly yielding.*

### Rating 5 (Prominent Case)
**(Charlie)**: *“The old design is tested and aligns with our brand identity. Changing it introduces unnecessary risk.”*  
**(Amelia)**: *“But feedback shows the old look is outdated.”*  
**(Charlie)**: *“I acknowledge that feedback, but our current clientele values consistency. Let’s conduct a quick A/B test to confirm before we abandon the old design entirely.”*  

*Firm stance maintained despite counterarguments.*""",
            
            "Recognition Expression": """Moments when participants acknowledge others' contributions, express appreciation, or show respect for others' expertise.
### Rating 1 (Rarely Observed)
**(Victoria)**: *“Thanks, I guess.”*  
*(Conversation moves on.)*  

*Minimal or lukewarm acknowledgment.*

### Rating 5 (Prominent Case)
**(Victoria)**: *“James, your data analysis was spot-on. It helped us spot key trends we were overlooking.”*  
**(James)**: *“Thanks, Victoria. I’m glad it was useful.”*  

*Open, positive, and explicit recognition of contributions.*            
""",
            
            "Dependency Expression": """Instances where participants show reliance on others' input, expertise, or approval.
### Rating 1 (Rarely Observed)
**(Nathan)**: *“So, can you check the script?”*  
**(Ava)**: *“Uh, maybe.”*  

*Indifferent request; minimal sense of reliance.*

### Rating 5 (Prominent Case)
**(Nathan)**: *“Ava, I can’t finalize this script without your technical input on the backend processes. Could you walk me through the integration points?”*  
**(Ava)**: *“Sure. I’ll clarify how each component interacts with our existing infrastructure.”*  

*Clear demonstration of needing and depending on someone else’s expertise.*            
""",
            
            "Support Offering": "When participants volunteer help, provide assistance, or show willingness to support others' ideas or needs.",
            
            "Shared Interests": """Moments revealing common goals, mutual understanding, or aligned objectives between participants.
### Rating 1 (Rarely Observed)
**(Chloe)**: *“We have different deliverables, so let’s just finish our own tasks.”*  
**(Ryan)**: *“Yeah, I’ll handle mine. You do yours.”*  

*No recognition of common goals.*

### Rating 5 (Prominent Case)
**(Chloe)**: *“Both teams want to increase user retention. Even though our tasks differ, we can coordinate to ensure consistent user experience.”*  
**(Ryan)**: *“Exactly. If we unify our approach, we can boost engagement for both our products.”*  

*Explicit alignment on a shared objective.* """,
            
            "View Alignment": """Instances where participants express similar perspectives, agree on points, or show unified understanding.
### Rating 1 (Rarely Observed)
**(Grace)**: *“I prefer a conservative budget.”*  
**(Jack)**: *“I don’t.”*  

*Participants simply state differing views.*

### Rating 5 (Prominent Case)
**(Grace)**: *“We should keep a conservative budget until Q4.”*  
**(Jack)**: *“I completely agree. Let’s minimize risk now, then ramp up spending if revenue picks up in Q3.”*  

*Clear consensus and alignment.*""",
            
            "Mood Management": """How participants handle meeting atmosphere, including attempts to lighten mood, reduce tension, or maintain positivity.
### Rating 1 (Rarely Observed)
**(Ellie)**: *“The numbers are bad.”*  
**(Kevin)**: *“Let’s move on.”*  

*No effort to lighten mood or address concerns.*

### Rating 5 (Prominent Case)
**(Ellie)**: *“We’ve had a tough quarter, but let’s look at the bright side: user engagement is improving. I’m confident we can turn this around.”*  
**(Kevin)**: *“Agreed. Let’s brainstorm a few quick-win solutions to boost morale and fix the shortfalls.”*  

*Deliberate positivity and constructive tone.*""",
            
            "Social Interaction": """Non-task-related exchanges, including small talk, personal anecdotes, or relationship-building conversations.
### Rating 1 (Rarely Observed)
**(Harper)**: *“Let’s start with the agenda.”*  
**(Mason)**: *“Sure.”*  

*Strictly task-focused; no personal or social chit-chat.*

### Rating 5 (Prominent Case)
**(Harper)**: *“Hey everyone, how was your weekend? I tried that new sushi place downtown.”*  
**(Mason)**: *“Oh, I went there too—loved the spicy rolls! Let’s catch up after we go through the agenda.”*  

*Friendly small talk that strengthens interpersonal bonds.*""",
            
            "Opinion Divergence": """Cases where participants express contrasting viewpoints or disagreements on topics.
### Rating 1 (Rarely Observed)
**(Zoe)**: *“I think we should hire a new consultant.”*  
**(Ethan)**: *“Okay, that’s fine.”*  

*Little to no disagreement.*

### Rating 5 (Prominent Case)
**(Zoe)**: *“I strongly advocate hiring a new consultant for project oversight.”*  
**(Ethan)**: *“I disagree. We can’t afford extra fees and already have enough internal expertise.”*  
**(Zoe)**: *“But external insight might save us in the long run—let’s discuss a cost-benefit analysis.”*  

*Clear clash of opinions.*""",
            
            "Conflict Presence": """Instances of tension, disagreement, or conflicting interests between participants.
### Rating 1 (Rarely Observed)
**(Kayla)**: *“Let’s do it your way.”*  
**(Dylan)**: *“Great.”*  

*No tension or dispute.*

### Rating 5 (Prominent Case)
**(Kayla)**: *“I believe your approach is too risky for our budget constraints.”*  
**(Dylan)**: *“You’re overly cautious and stifling innovation!”*  
**(Kayla)**: *“That’s not fair. We need to balance risk with realism.”*  

*Heightened tension and direct conflict.*""",
            
            "Discussion Dynamics": """Overall patterns in how participants engage, including turn-taking, interruptions, and conversation flow.
            **Description**  
> Overall patterns of engagement, including turn-taking, interruptions, and flow.

### Rating 1 (Rarely Observed)
**(Madison)**: *“We need to finalize the schedule.”*  
*(Long silence, no contributions.)*  
**(Oliver)**: *“Sure.”*  

*Very sparse interaction with minimal turn-taking.*

### Rating 5 (Prominent Case)
**(Madison)**: *“Let’s finalize the schedule. Who wants to start?”*  
**(Oliver)**: *“I’ll go first. We should block two weeks for testing.”*  
**(Madison, interrupting politely)**: *“Before we confirm that, can we hear from marketing?”*  
**(Olivia)**: *“Yes, marketing needs at least three weeks’ notice to run promotions.”*  

*Active, structured turn-taking, clear flow, and polite interruption indicating high engagement.*"""
        }

    def extract_tagged_content(self, text: str, tag: str) -> str:
        """Extract content between XML-style tags."""
        pattern = f"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else ""

    def basic_llm_evaluation(self, meeting_transcript: str) -> Dict[str, Dict[str, str]]:
        """
        Evaluate meeting based on naturalness, coherence, interesting content, and consistency.
        Returns dict with scores and reasoning for each criterion.
        """
        criteria = {
            "Naturalness": "How natural the conversation flows, like native English speakers (1-5)",
            "Coherence": "How well the conversation maintains logical flow and connection (1-5)",
            "Interesting": "How engaging and content-rich the conversation is (1-5)",
            "Consistency": "How consistent each speaker's contributions are (1-5)"
        }

        results = {}
        
        for criterion, description in criteria.items():
            system_prompt = (
                f"You are an expert conversation analyst evaluating meeting transcripts. "
                f"Evaluate the following meeting transcript thoroughly for **{criterion}**: {description}. \n"
                "- **Rating 1**: Highlights minimal or absent behavior for each criterion.\n"  
                "- **Rating 5**: Showcases strong, explicit demonstration of the behavior.\n"
                "Provide your step-by-step reasoning, a confidence score (0-100%), and a final score as a decimal number between 1.0 and 5.0, demonstrating the degree to which the chosen criterion is satisfied. "
                "Format your response using XML tags: "
                "<reasoning>detailed step-by-step analysis</reasoning> "
                "<confidence_score>your confidence percentage</confidence_score> "
                "<score>decimal number between 1.0 and 5.0</score>"
            )

            user_prompt = f"Please evaluate this meeting transcript for {criterion}:\n\n{meeting_transcript}"

            message = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = ModelHandler.call_model_with_retry(self.client, message, self.model_id)
            response_text = response.choices[0].message.content.strip()

            results[criterion] = {
                "reasoning": self.extract_tagged_content(response_text, "reasoning"),
                "confidence": self.extract_tagged_content(response_text, "confidence_score"),
                "score": self.extract_tagged_content(response_text, "score")
            }

        return results

    def psychology_based_llm_evaluation(self, meeting_transcript: str) -> Dict[str, Dict[str, str]]:
        """
        Perform psychology-based evaluation of the meeting using a three-step process.
        Returns detailed analysis and scores for each psychological criterion.
        """
        results = {}

        for criterion, description in self.psychological_criteria.items():
            # Step 1: Identify instances
            identify_prompt = (
                f"You are analyzing a meeting transcript to identify specific instances of **{criterion}**.\n\n"
                f"Definition of **{criterion}** with some examples to illustrate how the criteria might manifest in a real meeting context: {description}\n\n"
                "The difference in rating is reflected by the intensity, clarity, or frequency of the behavior.\n"
                "Your task is to carefully examine the transcript and identify concrete examples that demonstrate this characteristic. "
                "For each instance you identify, you must:\n"
                "1. Quote the relevant part of the transcript directly\n"
                "2. Explain why this quote demonstrates the characteristic\n\n"
                "Format your response as follows:\n"
                "<instances>\n"
                "1. Quote: \"[exact quote from transcript]\"\n"
                "   Explanation: [why this demonstrates the characteristic]\n"
                "2. Quote: \"[exact quote from transcript]\"\n"
                "   Explanation: [why this demonstrates the characteristic]\n"
                "[continue for all identified instances]\n"
                "</instances>\n\n"
                "If you cannot find any instances, respond with:\n"
                "<instances>No specific instances of this characteristic were identified in the transcript.</instances>\n\n"
                "Important:\n"
                "- Include ONLY concrete examples with direct quotes\n"
                "- Do not include general observations without specific quotes\n"
                "- Ensure each instance clearly demonstrates the characteristic\n"
                f"Analyze this transcript for instances of {criterion}:\n\n{meeting_transcript}"
            )

            # Step 2: Rate instances
            rate_prompt = (
                f"You are rating the identified instances of **{criterion}** from the meeting transcript.\n\n"
                "Your task is to rate how strongly each identified instance demonstrates this characteristic on a scale of 1-5, where:\n"
                "1 = Weakly demonstrates the characteristic\n"
                "5 = Strongly demonstrates the characteristic\n\n"
                "For each instance, provide:\n"
                "1. The instance quote\n"
                "2. A numerical rating/decimal (1.0-5.0)\n"
                "3. Justification for the rating\n\n"
                "Format your response as:\n"
                "<rating>\n"
                "Instance 1:\n"
                "Quote: \"[quote from instance]\"\n"
                "Rating: [1-5]\n"
                "Justification: [explanation of rating]\n\n"
                "Instance 2:\n"
                "[continue for all instances]\n"
                "</rating>\n\n"
                "If no instances were identified, respond with:\n"
                "<rating>No instances available to rate.</rating>"
            )

            # Step 3: Overall score
            score_prompt = (
                f"Based on the identified instances and their ratings for **{criterion}**, "
                "provide an overall evaluation.\n\n"
                "Your response must include:\n"
                "1. A detailed analysis of how the characteristic manifests in the meeting\n"
                "2. Your confidence level in the assessment (0-100%)\n"
                "3. A final score as a decimal number between 1.0 and 5.0\n\n"
                "Format your response using these tags:\n"
                "<reasoning>\n"
                "- Summary of all instances found\n"
                "- Analysis of their collective impact\n"
                "- Justification for the final score\n"
                "</reasoning>\n\n"
                "<confidence_score>\n"
                "Percentage between 0-100\n"
                "</confidence_score>\n\n"
                "<score>\n"
                "Decimal number between 1.0 and 5.0\n"
                "</score>"
            )

            prompts = [identify_prompt, rate_prompt, score_prompt]
            step_results = []

            for step, prompt in enumerate(prompts, 1):
                message = [
                    {"role": "system", "content": (
                        f"You are conducting step {step} of a psychological analysis of a meeting transcript. "
                        "You must follow the exact format specified in the prompt. "
                        "Do not include any additional text or explanations outside the specified tags. "
                        "Ensure all required information is placed within the appropriate tags."
                    )},
                    {"role": "user", "content": f"{prompt}\n\nTranscript:\n{meeting_transcript}"}
                ]
                if step > 1:
                    # Include previous step results in the context
                    message[1]["content"] += f"\n\nPrevious step results:\n{step_results[-1]}"

                response = ModelHandler.call_model_with_retry(self.client, message, self.model_id)
                step_results.append(response.choices[0].message.content.strip())

            # Extract final results
            results[criterion] = {
                "instances": self.extract_tagged_content(step_results[0], "instances"),
                "instance_ratings": self.extract_tagged_content(step_results[1], "rating"),
                "reasoning": self.extract_tagged_content(step_results[2], "reasoning"),
                "confidence": self.extract_tagged_content(step_results[2], "confidence_score"),
                "score": self.extract_tagged_content(step_results[2], "score")
            }

        return results
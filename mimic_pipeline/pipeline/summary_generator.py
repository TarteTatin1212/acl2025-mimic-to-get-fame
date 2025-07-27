import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from basics.scripts.model_handler import ModelHandler

from pydantic import BaseModel

class MeetingSummary(BaseModel):
    summary: str

def generate_meeting_summary(article_title, content, client, model_id, meeting_type, max_tokens=350, language="English"):
    num_words = int(max_tokens * 0.66)

    system_prompt = (f"You are a professional meeting summarizer, drawing inspiration from the QMSUM dataset's organized and concise style. "
        "Your task is to summarize a Wikipedia article as if the various facts in the article were discussed in a meeting, "
        "now being summarized for participants or readers. The summary should:\n\n"
        "1. **Reflect a 'Meeting Summary' Style**: Adopt a systematic structure, clearly presenting main points, relevant decisions, and/or action items.\n"
        "2. **Remain Concise Yet Sufficiently Detailed**: Aim for brevity but do not omit crucial details needed to understand the discussion.\n"
        "3. **Stay True to the Article**: Ensure accuracy by covering the principal topics while preserving the meeting context.\n"
        f"4. **Match {language}-speaking Conventions**: Generate the summary in {language}, mirroring the phrasing and cultural norms typical of real meetings in that language.\n\n"
        "Follow these rules:\n\n"
        "**Structural Requirements**:\n"
        "1. **Opening**: Start with the meeting's primary objective or central topic (e.g., 'The meeting focused on standardizing...').\n"
        "2. **Flow**: Group related points into logical sequences (e.g., proposals → concerns → resolutions).\n"
        "3. **Decisions/Actions**: Conclude each topic with clear outcomes (e.g., 'agreed to explore alternatives').\n"
        "4. **Paragraphs**: Use 1-2 dense paragraphs without section headers, bullets, or lists.\n\n"

        "**Language Requirements**:\n"
        "- **Avoid**: Phrases like 'we discussed,' 'the meeting covered,' or 'participants mentioned.'\n"
        "- **Use Direct Language**: Frame points as decisions or facts (e.g., 'The team proposed...' instead of 'They talked about...').\n"
        "- **Tense**: Use past tense and passive voice where appropriate (e.g., 'It was agreed...').\n"
        "- **Concision**: Omit filler words (e.g., 'then,' 'next').\n\n"
        "Below are several example meeting summaries illustrating the level of clarity, organization, and balance between detail and concision:\n"
        "**Examples of QMSUM Style Summaries** (Note Structure & Tone):\n"
        "--------------------------------------------------\n"
        "> Meeting participants wanted to agree upon a standard database to link up different components of the transcripts. The current idea was to use an XML script, but it quickly seemed that other options, like a pfile or ATLAS, are more suitable. The reason being that they would make it easier to deal with different linguistic units, like frames and utterances. Eventually, the team was skeptical of using something that would be hard to learn, like ATLAS. Nonetheless, they wanted to explore their options. The meeting finished with some discussion about handling annotations.\n\n"
        "> The meeting discussed the progress of the transcription, the DARPA demos, tools to ensure meeting data quality, data standardization, backup tools, and collecting tangential meeting information. The team was making good progress on the transcription but was still concerned with correcting some of the data. Besides that, they were working on adapting the THISL GUI for their project and figuring out visual tools for meeting participants to help them know when their recording equipment was failing. The team also discussed collecting additional information, like laughter and breath data as well as meeting notes.\n\n"
        "> The meeting was about the potential consequences of the COVID-19 in Canada. The members put forward several petitions to ask for further attention for the people in need, say, the children, the workers who would suffer unemployment, and the creators who made a living on artworks, and also many other stakeholders from all walks of life, trying to ensure the life quality of their people during such a harsh time. Some of the group members mentioned some social problems, including the economic depression, racial discrimination, social security, and the environmental pollution,to call for a maintenance of the wealthy and healthy community in Canada. Through the discussion, it could be found that fortunately, some of the problems had been dealt with extra funds and cooperation with other related organizations.\n\n"
        "--------------------------------------------------\n"
        "These examples demonstrate an orderly, concise approach. Summarize the Wikipedia article **stricktly** as a QMSUM-style meeting summary  — presenting the main topics, relevant decisions, key points of contention, "
        "and concluding remarks in cohesive paragraph(s) **without using bullet points**.\n\n"
        f"Generate an abstractive summary with **at most {num_words} words** in **{language}**. Ensure it is systematically organized and remains consistent with the meeting type: {meeting_type}.\n"

        )

    user_prompt=(
        f"Meeting Type: {meeting_type} \n\n"
        f"Article Title: {article_title} \n\n"
        f"Content: {content} \n\n"
        f"Now generate an abstractive meeting Summary in **{language}**:\n"
    )
    
    
    message = [
        {"role": "system",
        "content": system_prompt
        },
        {"role": "user",
        "content": user_prompt
        }
    ]
    
    response = ModelHandler.call_model_with_retry(client=client, messages=message, model=model_id, max_tokens=max_tokens, response_model=MeetingSummary )
    return response.summary.strip()

def transform_to_meeting_summary(article_title, article, client, model_id, meeting_type, language="English"):
    try:
        meeting_summary = generate_meeting_summary(article_title, article, client, model_id, meeting_type, language=language)
        return meeting_summary
    except ValueError as e:
        return str(e)
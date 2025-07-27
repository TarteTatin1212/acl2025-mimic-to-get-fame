import sys

sys.path.append("../")

from basics.scripts.model_handler import ModelHandler
from basics.scripts.memory_handler import MemoryHandler


import json
import pandas as pd

from openai import AzureOpenAI


meeting_path = "./output/revised/Decision-Making Meeting_English_Globalization.csv"
meeting_df = pd.read_csv(meeting_path)

system_prompt = ("You're tasked to act as an AI-generated content detectore, specialized in detecting content that doesn't feel realistic."
)

meeting = """
>>Public Health Official: Well, it's great to see everyone here today. I think we all know how important our discussion on vaccination programs is, especially considering the community impact. So, let's dive right in and outline what we aim to achieve today. How does that sound?

>>Medical Expert: Yes, we need to make sure our vaccination programs are based on solid science and that we communicate them well. What specific objectives do we have for today's discussion?

>>Ethicist: From an ethical standpoint, it's essential to balance individual autonomy with public health benefits. How do we ensure we're respecting personal freedoms while also protecting the community? What are the ethical implications of mandatory vaccination programs?

>>Medical Expert: That's a good point. But don't you think mandatory vaccinations might be necessary in certain situations? We need to address public concerns and misinformation too. How can we better communicate these scientific facts to foster trust and acceptance?

>>Public Health Official: Right! Dr. Smith, your point about addressing public concerns is spot on. You see, community engagement is crucial here. When we involved local leaders in the recent flu vaccination drive in Springfield, it really helped boost participation. What steps can we take next? Maybe organizing town hall meetings or creating informative social media campaigns could help.

>>Ethicist: Those are great ideas! And perhaps we could also work with schools and workplaces to provide more accessible information sessions.

>>Medical Expert: Absolutely! And let's not forget about training healthcare providers to handle questions and concerns effectively.

>>Public Health Official: Agreed. So, our action plan includes town hall meetings, social media campaigns, working with schools and workplaces, and training healthcare providers. Anything else?

>>Ethicist: We should also consider feedback mechanisms so people feel heard and valued.

>>Medical Expert: Yes, a feedback loop is essential for continuous improvement.

>>Public Health Official: Perfect! Let's get started on implementing these steps. 
 >>Medical Expert: To put it simply, the history and significance of vaccination cannot be overstated. Vaccines have been instrumental in eradicating diseases like smallpox and controlling others such as polio and measles. We also discussed various types of vaccines, including live-attenuated, inactivated, subunit, conjugate, and mRNA vaccines. Each type has its unique mechanism and application. However, one of the major challenges we face is vaccine hesitancy fueled by misinformation. How can we address this issue effectively?

>>Public Health Official: Addressing vaccine hesitancy is crucial. From a public health perspective, community engagement plays a significant role here. We need to build trust through transparent communication and by involving local leaders who can influence their communities positively. This means we need to be proactive in dispelling myths and providing accurate information.

>>Medical Expert: Right, addressing vaccine hesitancy requires a multifaceted approach. Misinformation often stems from a lack of understanding about how vaccines work and their safety profiles. We need to leverage scientific data and real-world evidence to counteract these myths effectively. For instance, sharing success stories of vaccination programs can be quite powerful in changing perceptions.

>>Public Health Official: Exactly! One effective way is through initiatives that involve local leaders and trusted figures advocating for vaccination; it significantly influences public perception. Organizing town hall meetings where people can ask questions directly fosters trust and transparency.

>>Ethicist: Um, I think it's important to consider the ethical implications as well. While promoting vaccination is essential for public health, we must also respect individual autonomy and address concerns respectfully rather than dismissively.

>>Medical Expert: Absolutely! Education is key here—people often fear what they don't fully understand. By providing clear information about how vaccines are developed and tested for safety through rigorous clinical trials and continuous monitoring processes, we can help alleviate some fears.

>>Public Health Official: Furthermore, we've seen great success with grassroots efforts! In one recent campaign at my old job, we collaborated with local schools and workplaces to host vaccination drives with impressive turnout! These kinds of efforts really help build trust.

>>Ethicist: You know, while these efforts are commendable—and I agree they're necessary—we also need to ensure inclusivity so no group feels marginalized or coerced into getting vaccinated.

>>Medical Expert: That's a good point! Inclusivity is crucial for building trust across different communities. 
 >>Public Health Official: Inclusivity is indeed vital. When we engage communities directly and involve local leaders, the impact is profound. For instance, in one of our recent campaigns, we partnered with community influencers to spread awareness about the benefits of vaccination. The result? A significant increase in vaccination rates and a stronger sense of trust within the community. These grassroots efforts can make all the difference.

>>Ethicist: Absolutely, involving local leaders can really help build trust. But we also need to be careful not to push too hard and respect people's personal beliefs and choices. How do we balance promoting vaccinations without making anyone feel forced or left out?

>>Medical Expert: I see your point. It's important to remember that vaccines have saved countless lives. For example, since the measles vaccine was introduced, global deaths from measles dropped by 73% between 2000 and 2018. This shows just how essential these programs are for public health.

>>Public Health Official: That's interesting! And it really shows how effective these programs are. When people see fewer disease outbreaks and healthier children, it builds trust and encourages more participation in vaccination programs. So what steps can we take next—

>>Ethicist: —to ensure these successes continue? Yes, that's crucial... We need to think about how our efforts might affect different communities differently and make sure we're not putting too much pressure on any one group.

>>Medical Expert: Moreover, it's important to consider broader implications like herd immunity which protects those who cannot be vaccinated due to medical reasons as well as those who are vaccinated. This collective protection is a testament to community-wide immunization efforts.

>>Public Health Official: Community engagement doesn't just stop at increasing vaccination rates; it fosters ownership and responsibility within the community too. When people feel they are part of the solution, they're more likely to advocate for and sustain these health initiatives themselves.

>>Ethicist: Exactly! While herd immunity is powerful, we must also consider its ethical implications if relied upon too heavily. What happens when certain communities are disproportionately burdened with achieving this collective protection? How do we ensure our strategies don't place undue pressure on specific groups potentially at the expense of their autonomy and cultural values?

>>Medical Expert: Herd immunity is a cornerstone of public health strategy but achieving it requires high vaccination coverage across all communities. If certain groups are left behind, everyone remains at risk.

>>Public Health Official: Good point! So how can we ensure equitable access to vaccines for everyone?

>>Ethicist: Maybe we could start by identifying barriers specific communities face in accessing vaccines—like transportation issues or misinformation—and work on targeted solutions for those problems. 
 >>Medical Expert: It's crucial to understand that addressing vaccine hesitancy requires a multifaceted approach. We have strong evidence showing vaccines are safe because they go through lots of tests before approval, and we keep checking for any issues even after they're out. For example, the eradication of smallpox and the near-elimination of polio are direct results of widespread vaccination efforts. Communicating these successes effectively can help counteract misinformation.

>>Public Health Official: Absolutely! From a public health perspective, community engagement is key. Involving local leaders and trusted figures within communities helps build trust and credibility. For instance, organizing town hall meetings where people can ask questions directly to healthcare professionals fosters transparency and open dialogue.

>>Ethicist: That's a great point. But we also need to consider the ethical implications of mandatory vaccination policies. While protecting public health is important, we must respect individual autonomy and personal freedoms. How do we navigate this without infringing on personal rights or alienating certain groups?

>>Public Health Official: Right, it's not just about organizing events; it's about creating continuous dialogue with the community. Regular updates through local media and social platforms where trusted figures share accurate information can keep everyone informed and involved.

>>Medical Expert: Exactly! And building on that, it's important people understand the rigorous processes involved in vaccine development—multiple phases of clinical trials designed meticulously to assess safety and efficacy—and ongoing monitoring for any adverse effects.

>>Ethicist: Yes, but let's also think about how our communication strategies might impact different communities differently. Some groups may have historical reasons for distrusting medical authorities or may feel targeted by mandatory policies. How do we ensure we're being inclusive while promoting public health?

>>Public Health Official: That's why involving local leaders who understand their communities' unique concerns is so important. They can help tailor our messages in ways that resonate more effectively with those specific groups.

>>Medical Expert: Absolutely! And sharing real-life success stories from various communities can be powerful too. For example, in some areas where local leaders actively promoted vaccination, we've seen significant increases in vaccine uptake.

>>Ethicist: Agreed. As we move forward with these strategies, let's keep reflecting on how best to balance promoting vaccinations while respecting individual choices—ensuring no one feels coerced but rather well-informed about making decisions beneficial both personally and communally. 
 >>Medical Expert: You know, the advancements in mRNA technology have been nothing short of revolutionary! This platform allows for quick development and adaptability, which is crucial when dealing with emerging diseases like COVID-19. We're also seeing promising results with other novel approaches such as vector-based vaccines and protein subunit vaccines. What does this mean for us? It means we can potentially respond to future pandemics more swiftly and effectively.

>>Public Health Official: Absolutely, these advancements are groundbreaking. From a public health perspective, it's vital that we focus on building strong global distribution networks to ensure equitable access. We need a solid plan to make sure all communities, especially underserved ones, get these life-saving vaccines.

>>Ethicist: Right, while these advancements are impressive, we must consider the implications for equitable access. How do we ensure that these innovations don't exacerbate existing inequalities? And what about prioritizing certain populations over others when distributing these vaccines? It's crucial to navigate this thoughtfully to uphold both justice and public health.

>>Public Health Official: Furthermore, the success of these innovative vaccine technologies hinges on our ability to implement them effectively within communities. Community engagement and education are key here. We need everyone to understand the benefits and safety of these new vaccines by involving local leaders who can build trust and credibility.

>>Medical Expert: Indeed! The rapid adaptability of mRNA technology not only allows us to respond swiftly to emerging diseases but also opens up possibilities for personalized vaccines tailored to individual genetic profiles. This could revolutionize how we approach not just pandemics but also other infectious diseases and even some cancers! Leveraging this potential while ensuring equitable access is a challenge we'll need to address collaboratively.

>>Public Health Official: And let's not forget that community engagement is essential for any vaccination program's success. By involving local leaders who can build trust and credibility, we can increase vaccination rates significantly.

>>Ethicist: It's important to reflect on how these technological advancements intersect with ethical considerations. For instance, if we're developing personalized vaccines based on genetic profiles, how do we handle privacy concerns or potential discrimination issues?

>>Medical Expert: Good point! We need comprehensive policies in place to protect individuals' privacy while maximizing the benefits of personalized medicine. It's a delicate balance but one that's necessary for progress.

>>Public Health Official: Exactly! As we move forward with implementing these technologies globally, continuous dialogue with communities will be crucial. We must listen to their concerns and provide clear information about vaccine safety and efficacy.

>>Ethicist: Yes... engaging in open dialogue is essential for maintaining public trust. We should also consider historical contexts where medical interventions have led to distrust in certain communities.

>>Medical Expert: Absolutely! Addressing past wrongs transparently will help build trust moving forward. Our goal should always be inclusive healthcare that respects individual rights while promoting public health. 
 >>Public Health Official: Alright, let's wrap up by summarizing our key decisions and assigning responsibilities. Enhancing public education campaigns is crucial. I'll coordinate with local leaders to ensure they have what they need for effective community engagement. How about we set a deadline of two weeks to finalize these plans? Thoughts?

>>Ethicist: From an ethical standpoint, it's essential that while enhancing public education campaigns, we ensure the information provided is accurate and respectful of diverse cultural contexts. We should develop guidelines that allow for cultural adaptations without imposing external values. How can we balance guidance with respect for unique circumstances?

>>Medical Expert: Absolutely! Providing local leaders with accurate data and training is fundamental. By integrating scientific insights into our framework, we can ensure these leaders are well-equipped to make informed decisions. How can we best tailor this training to address both scientific and cultural aspects effectively?

*Phone rings loudly*

>>Public Health Official: Oh dear, sorry about that.
*Silences phone quickly*
Alright, where was I? Yes—enhancing public education campaigns is crucial. I'll work with local leaders on this and aim for a two-week deadline to finalize our plans.

>>Ethicist: And let's not forget those guidelines—we need them to be both scientifically accurate and culturally sensitive.

>>Medical Expert: Agreed! Let's integrate these insights effectively so our community engagement strategies align with both public health goals and community values. 
 >>Public Health Official: Well, it's been a productive discussion today. We've covered some crucial points about community engagement and inclusivity in our vaccination programs. How does everyone feel about setting our next meeting for two weeks from now? This will give us time to implement some strategies we've discussed and come back with updates.

>>Ethicist: I think that's a good idea. We need to make sure we're hearing from those most affected by our policies. What specific steps can we take to ensure their voices are included in our next actions?

>>Medical Expert: Absolutely, inclusivity is key. We also need to provide local leaders with accurate data and training to combat misinformation effectively. What kind of support do they need from us?

>>Public Health Official: Right, we should empower local leaders with both the right information and communication tools tailored to their communities' needs. How does everyone feel about creating a dedicated task force to oversee this process?

>>Community Leader: A task force sounds like a solid plan. We should also consider regular check-ins with these leaders to address any new challenges that arise.

>>Medical Expert: Agreed, ongoing support is crucial. Maybe we could set up a system where local leaders can easily reach out for help or resources as needed.

>>Public Health Official: Great suggestions! Let's finalize the details for the task force and set up our next meeting for two weeks from now so we can review progress and adjust as necessary. Thanks again for all your valuable input; we're making real strides here.
"""
        
user_prompt = (f"""Is the following meeting AI generated or a real meeting? Provide a thorough reasoning for your answer and think step by step.\n
Meeting:\n{meeting}\n
"""
        
)


message = [
            {"role": "system",
            "content": system_prompt
            },
            {"role": "user",
            "content": user_prompt
            }
        ]


MODEL_CONFIG_PATH = "./../config_gpt.json"


# Example usage

with open(MODEL_CONFIG_PATH) as config_file:
    config = json.load(config_file)

API_KEY = config["api_key"]
API_VERSION = config["api_version"]
ENDPOINT = config["endpoint"]
MODEL_NAME = config["model"]

CLIENT = AzureOpenAI(
    api_key=API_KEY,
    api_version= API_VERSION,
    azure_endpoint=ENDPOINT,
)


    
response = ModelHandler.call_model_with_retry(client=CLIENT, messages=message, model=MODEL_NAME, max_tokens=4000)

print(response.choices[0].message.content.strip())
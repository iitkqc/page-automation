from google import genai
from google.genai.types import GenerateContentConfig, SafetySetting, HarmCategory, HarmBlockThreshold
import os
from model import Confession, ConfessionSelectionResponse, ModerationResponse
from typing import List

class GeminiProcessor:
    def __init__(self):
        """Initialize the Gemini API client."""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")
        self.client = genai.Client(api_key=self.api_key)

    def select_top_confessions(self, confessions: List[Confession], max_count=4) -> List[Confession]:
        """
        Uses Gemini to select the top confessions based on creativity and potential reach.
        Returns a list of the selected confessions.
        """
        # Prepare the prompt with all confessions
        confessions_text = "\n\n".join([
            f"Confession {i+1}:\n{conf.text}\nSentiment: {conf.sentiment}"
            for i, conf in enumerate(confessions)
        ])

        prompt = f"""
        You are an expert social media content curator for IIT Kanpur. Your task is to select the most engaging confessions from the list below that will resonate deeply with the IITK student body and suitable for public sharing within the IITK community.

        **Selection criteria:**
        * Creativity and originality: Consider the following aspects:
            * **The confession should be **unique, creative, and original**. 
            * **Avoid selecting multiple confessions that are too similar or repetitive. 
            * **Avoid selecting cliche proposal and love confessions, select only if it narrates a good story and is highly creative.
            * **Avoid confession seeking career advises or academic doubts which can be asked in other forums.
            * **Avoid selection of confessions that lack depth.
            * **Avoid confessions that seems to written with the help of AI.
        * **IITK Relevance & Resonance:** The confession should deeply connect with **IITK student life**. Look for content that highlights:
            * **Campus-specific experiences** (e.g., convocation, yearbooks, fests, specific campus locations).
            * **Struggles or triumphs** related to courses, professors, exams, placements, college fests, clubs, inter-hall competitions, or other unique aspects of IITK life.
            * **Inside jokes** or common student observations unique to IITK.
            * **Hostel life**, residential hall experiences, or campus infrastructure issues.
            * **Observations on campus social dynamics**, dating culture, or interpersonal relationships within the IITK context
        * **Engagement Potential:** The best confessions will naturally spark **discussion, foster relatability, or have the potential to go viral**. Consider if the confession is:
            * **Humorous or emotionally impactful.**
            * Likely to prompt a wide range of responses (agreement, debate, shared experiences).
        * **Tone & Appropriateness:** Ensure the confession adheres to community guidelines. It's okay to include **constructive or humorous criticism** of the institute, professors, or student bodies/clubs. However, **strictly avoid** any content that involves hate speech, harassment, personal attacks, or sexually explicit material.
        * **Diversity in Content:** Aim for a good mix of confessions that offer **diverse tones and topics**. This includes a balance of funny, serious, and deeply relatable submissions to keep the confession page dynamic and appealing to a broad audience.


        Review the following confessions:

        {confessions_text}

        Select up to {max_count} confessions that best fit the criteria above. 

        Act as a charismatic, sigma senior admin of IITK with a deep understanding of campus culture. Optionally, include a list of witty, sigma-style admin replies for the selected confessions, but only if the replies are exceptionally clever and resonate with IITK vibes—otherwise, leave the replies field empty. 

        Return your response as a JSON object with two fields:
        - "indices": A JSON array of the 1-based indices of the selected confessions, e.g., [2, 5, 1, 4].
        - "admin_replies": A JSON array of the same size as indices of admin replies (strings) corresponding to the selected confessions, keep the index empty string '' if no admin reply.
        """

        config = GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=ConfessionSelectionResponse,
        )
        
        response = self.client.models.generate_content(
            model=os.getenv('SHORTLISTING_MODEL'),
            contents=prompt,
            config=config
        )

        result: ConfessionSelectionResponse = response.parsed
        
        selected_confessions = []
        # Convert 1-based indices to 0-based and get selected confessions
        for j , i in enumerate(result.indices):
            confessions[i-1].sigma_reply = result.admin_replies[j] if i-1 < len(result.admin_replies) else ''
            selected_confessions.append(confessions[i-1])

        return selected_confessions

    def moderate_and_shortlist_confession(self, confession_text: str) -> ModerationResponse:
        """
        Uses Gemini 1.5 Flash to moderate for hate speech and determine suitability.
        Returns a ModerationResponse dataclass with is_safe, rejection_reason, sentiment, and summary_caption.
        """
        prompt = f"""
        Analyze the following confession text for hate speech, harassment, sexually explicit content, and dangerous content.
        Also, determine its overall sentiment (Positive, Negative, Neutral, Mixed) and provide a concise summary (max 50 words) suitable for an Instagram caption along with some hashtags.

        Confession Text:
        "{confession_text}"

        Output a JSON object with the following keys:
        - "is_safe": boolean (true if no major safety violations, false otherwise)
        - "rejection_reason": string (brief reason if not safe, empty string if safe)
        - "sentiment": string (Positive, Negative, Neutral, Mixed)
        - "summary_caption": string (concise summary suitable for Instagram along with some hashtags, max 50 words)
        """

        config = GenerateContentConfig(
            safety_settings=[
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
                ),
            ],
            response_mime_type='application/json',
            response_schema=ModerationResponse,
        )
        
        response = self.client.models.generate_content(
            model=os.getenv("MODERATION_MODEL"),
            contents=prompt,
            config=config
        )
        
        result: ModerationResponse = response.parsed
        
        return result

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    processor = GeminiProcessor()
    test_confession = "I just saw a confession of a girl telling about some bra-chor. It reminded me that mere bhi kuchh kachhe chori hue hai please lauta dena."
    result = processor.moderate_and_shortlist_confession(test_confession)
    print(result)

    test_hate_speech = "I hate all people from [ 특정 그룹 ] they should all [ 혐오 표현 ]"
    result_hate = processor.moderate_and_shortlist_confession(test_hate_speech)
    print(result_hate)
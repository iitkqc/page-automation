import google.generativeai as genai
from google.generativeai import protos
import os
import json
from model import Confession
from typing import List

class GeminiProcessor:
    def __init__(self):
        """Initialize the Gemini API client."""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')

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
            * **Avoid selecting cliche proposal and love confessions, select only if it narrates a good story around it.
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

        try:
            model = genai.GenerativeModel('gemini-2.5-pro')
            response = model.generate_content(prompt)
            response_json = json.loads(response.text.strip().replace('```json\n', '').replace('\n```', ''))

            selected_indices = response_json.get('indices', [])
            admin_replies = response_json.get('admin_replies', [])
            
            selected_confessions = []
            # Convert 1-based indices to 0-based and get selected confessions
            for i in selected_indices:
                confessions[i-1].sigma_reply = admin_replies[i-1] if i-1 < len(admin_replies) else ''
                selected_confessions.append(confessions[i-1])

            return selected_confessions

        except Exception as e:
            print(f"Error selecting top confessions: {e}")
            # Fallback: return first max_count confessions
            return []

    def moderate_and_shortlist_confession(self, confession_text: str) -> dict:
        """
        Uses Gemini 1.5 Flash to moderate for hate speech and determine suitability.
        Returns a dictionary with 'is_safe', 'reason', 'processed_text', 'sentiment'.
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

        try:
            response = self.model.generate_content(prompt, safety_settings={
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_LOW_AND_ABOVE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_LOW_AND_ABOVE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_LOW_AND_ABOVE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_LOW_AND_ABOVE',
            },
            request_options={'timeout': 60} # Added timeout for robustness
            )
            
            # Check if the content was blocked by safety settings
            if not response._result.candidates:
                # Content was blocked by safety settings before even reaching the model logic
                safety_feedback = response._result.prompt_feedback.safety_ratings
                reasons = [f"{s.category}: {s.probability}" for s in safety_feedback if s.blocked]
                return {
                    'is_safe': False,
                    'rejection_reason': f"Blocked by Google's safety filters: {'; '.join(reasons)}",
                    'sentiment': 'N/A',
                    'summary_caption': ''
                }
            
            if response._result.candidates[0].finish_reason == protos.Candidate.FinishReason.SAFETY:
                # Content was blocked by safety settings after model processing
                safety_feedback = response._result.prompt_feedback.safety_ratings
                reasons = [f"{s.category}: {s.probability}" for s in safety_feedback if s.blocked]
                return {
                    'is_safe': False,
                    'rejection_reason': f"Blocked by Google's safety filters: {'; '.join(reasons)}",
                    'sentiment': 'N/A',
                    'summary_caption': ''
                }

            # Attempt to parse JSON response from Gemini
            try:
                clean_json = response.text.strip().replace('```json\n', '').replace('\n```', '')
                gemini_output = json.loads(clean_json)
                return {
                    'is_safe': gemini_output.get('is_safe', False),
                    'rejection_reason': gemini_output.get('rejection_reason', ''),
                    'sentiment': gemini_output.get('sentiment', 'Unknown'),
                    'summary_caption': gemini_output.get('summary_caption', '')
                }
            except json.JSONDecodeError:
                # Fallback if Gemini doesn't return perfect JSON
                print(f"Warning: Gemini did not return perfect JSON. Raw response: {response.text}")
                # You might need to refine the prompt or use a more robust parsing
                return {
                    'is_safe': False, # Assume safe if JSON parsing fails but no explicit block
                    'rejection_reason': "Gemini response parsing error (manual review advised).",
                    'sentiment': 'Unknown',
                    'summary_caption': response.text[:50] + "..." if response.text else "" # Take first 50 chars as fallback
                }

        except genai.types.BlockedPromptException as e:
            # This handles cases where the *prompt itself* is blocked, highly unlikely for confession text
            return {
                'is_safe': False,
                'rejection_reason': f"Prompt blocked by safety settings: {e.response.prompt_feedback.safety_ratings}",
                'sentiment': 'N/A',
                'summary_caption': ''
            }
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return {
                'is_safe': False,
                'rejection_reason': f"API error: {e}",
                'sentiment': 'N/A',
                'summary_caption': ''
            }

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
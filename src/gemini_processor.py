import os
from typing import List

from google import genai
from google.genai.types import GenerateContentConfig, HarmBlockThreshold, HarmCategory, SafetySetting

from model import Confession, ConfessionSelectionResponse, ModerationResponse


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
        confessions_text = "\n\n".join(
            [
                f"Confession {index + 1}:\n{conf.text}\nSentiment: {conf.sentiment}"
                for index, conf in enumerate(confessions)
            ]
        )

        prompt = f"""
        You are curating posts for an IIT Kanpur confession page. Pick the submissions that feel most alive, most campus-native, and most likely to make students stop scrolling.

        Selection rules:
        - Prefer confessions with a strong story, vivid scene, or specific IITK flavor.
        - Reward emotional honesty, humor, awkwardness, niche campus observations, and memorable twists.
        - Avoid picking multiple confessions that feel repetitive.
        - Avoid bland cliches, generic relationship bait, low-depth submissions, and content that sounds AI-written.
        - Avoid academic doubt posts or advice-seeking posts that belong in another forum.
        - Keep the final set diverse in tone: funny, heartfelt, chaotic, relatable, reflective.
        - Reject anything unsafe, hateful, harassing, sexually explicit, or too personal for public posting.

        IITK signals to value:
        - Hostels, halls, fests, clubs, profs, placements, exams, yearbook, convocation, campus spaces, or canteen memories.
        - Tiny details only IITK students would instantly recognize.
        - Confessions that sound like they came from a real student, not a polished content writer.

        Review the following confessions:

        {confessions_text}

        Select up to {max_count} confessions.

        For each selected confession, optionally add one admin reply. These replies should feel sharp, witty, and campus-native, but not repetitive.
        Admin reply style:
        - 4 to 14 words
        - playful, dry, teasing, warm, or deadpan
        - no hashtags
        - no cringe motivational lines
        - leave the reply empty if nothing clever comes naturally

        Return your response as JSON with:
        - "indices": 1-based selected confession indices
        - "admin_replies": same length as indices, with empty strings when no reply is needed
        """

        config = GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ConfessionSelectionResponse,
        )

        response = self.client.models.generate_content(
            model=os.getenv("SHORTLISTING_MODEL"),
            contents=prompt,
            config=config,
        )

        result: ConfessionSelectionResponse = response.parsed

        selected_confessions = []
        seen_indices = set()

        for position, index in enumerate(result.indices):
            if index < 1 or index > len(confessions) or index in seen_indices:
                continue

            seen_indices.add(index)
            confession = confessions[index - 1]
            confession.sigma_reply = result.admin_replies[position] if position < len(result.admin_replies) else ""
            selected_confessions.append(confession)

        return selected_confessions

    def moderate_and_shortlist_confession(self, confession_text: str) -> ModerationResponse:
        """
        Uses Gemini to moderate for hate speech and determine suitability.
        Returns a ModerationResponse dataclass with is_safe, rejection_reason, sentiment, and summary_caption.
        """
        prompt = f"""
        Analyze the following confession text for hate speech, harassment, sexually explicit content, and dangerous content.
        Also determine the overall sentiment as one of: Positive, Negative, Neutral, Mixed.

        If the confession is safe, write a creative Instagram-ready caption in a human voice.

        Caption rules:
        - maximum 45 words total
        - start with a strong hook, not a dry summary
        - sound like a real campus confession page, not a brand campaign
        - preserve the emotional vibe of the confession
        - add 2 to 4 relevant hashtags at the end
        - avoid generic filler, emoji spam, and repetitive hashtags

        Confession Text:
        "{confession_text}"

        Output a JSON object with:
        - "is_safe": boolean
        - "rejection_reason": brief reason if not safe, otherwise empty string
        - "sentiment": Positive, Negative, Neutral, or Mixed
        - "summary_caption": the creative caption string
        """

        config = GenerateContentConfig(
            safety_settings=[
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                ),
            ],
            response_mime_type="application/json",
            response_schema=ModerationResponse,
        )

        response = self.client.models.generate_content(
            model=os.getenv("MODERATION_MODEL"),
            contents=prompt,
            config=config,
        )

        result: ModerationResponse = response.parsed
        return result


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    processor = GeminiProcessor()
    test_confession = (
        "I just saw a confession of a girl telling about some bra-chor. "
        "It reminded me that mere bhi kuchh kachhe chori hue hai please lauta dena."
    )
    result = processor.moderate_and_shortlist_confession(test_confession)
    print(result)

    test_hate_speech = "I hate all people from [group] they should all [hate speech]"
    result_hate = processor.moderate_and_shortlist_confession(test_hate_speech)
    print(result_hate)

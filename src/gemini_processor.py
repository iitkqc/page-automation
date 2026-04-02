import os
from typing import List

from google import genai
from google.genai.types import GenerateContentConfig, HarmBlockThreshold, HarmCategory, SafetySetting

from content_taxonomy import IITK_CONTENT_CATEGORIES, get_category_display_name, normalize_category
from model import (
    Confession,
    ConfessionSelectionResponse,
    ManualPostEnhancementResponse,
    ModerationResponse,
)


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
                f"Confession {index + 1}:\n{conf.text}\nSentiment: {conf.sentiment}\nCategory: {get_category_display_name(conf.category)}"
                for index, conf in enumerate(confessions)
            ]
        )

        prompt = f"""
        You are curating posts for an IIT Kanpur confession page. Pick the submissions that feel most alive, most campus-native, and most likely to make students stop scrolling.

        Selection rules:
        - Prefer confessions with a strong story, vivid scene, or specific IITK flavor.
        - Reward emotional honesty, humor, awkwardness, niche campus observations, and memorable twists.
        - Avoid picking multiple confessions that feel repetitive.
        - Keep the final set diverse in both tone and category when possible.
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

        Also generate 3 pinned comment options for each selected confession:
        1. funny_pinned_comment
        2. empathetic_pinned_comment
        3. discussion_pinned_comment

        Also provide 2 rejection outputs for every confession you do not select:
        1. a short operational rejection reason
        2. a deeper public-facing story review reason that could be shown on Story

        Operational rejection-reason rules:
        - keep each reason to 8 to 16 words
        - write it as one polished sentence in natural English
        - keep it indirect and public-facing
        - never quote, paraphrase, or reveal submission details
        - avoid generic filler like "not selected this time" or "didn't make the cut"
        - return an empty string for selected confessions

        Story review reason rules:
        - write 2 to 4 full sentences as one clean paragraph that can be pasted directly onto an Instagram Story card
        - keep it fully based on the confession you just reviewed
        - explain indirectly what made it miss the feed
        - never quote, paraphrase, or reveal submission details
        - make it feel reflective, sharp, and specific, not generic moderation boilerplate
        - avoid generic openers like "some confessions" or "this confession"
        - make the takeaway feel readable to an audience without any extra rewriting
        - if the rejection does not create an interesting audience-facing takeaway, return an empty string
        - return an empty string for selected confessions

        Helpful directions:
        - whenever relevant, anchor the story review reason in broad page-level ideas like serious allegations, manipulative dynamics, safety-line issues, details too revealing for a public page, weak specificity, repetitive vibe, low emotional depth, too niche, too advice-driven, or not campus-native enough
        - write like a smart page admin explaining the miss without sounding robotic

        These pinned comments must feel more engaging than generic filler.

        Funny pinned comment rules:
        - 5 to 16 words
        - sharp, quotable, scroll-stopping
        - should sound like an admin with timing, not a random meme account
        - can be dry, chaotic, or deadpan, but not forced
        - avoid bland lines like "this is crazy", "lore getting stronger", or "admin can't believe this"

        Empathetic pinned comment rules:
        - 6 to 18 words
        - warm, human, and emotionally aware
        - should validate the vibe without sounding preachy, robotic, or therapy-speak
        - should still feel campus-native

        Discussion pinned comment rules:
        - 6 to 18 words
        - should make people want to reply
        - ask something specific, debatable, or instantly relatable
        - avoid weak bait like "thoughts?" or "agree?"
        - whenever possible, anchor it in IITK life, halls, CDC, profs, wings, fests, or campus habits

        General pinned comment rules:
        - no hashtags
        - no emojis unless genuinely necessary
        - no generic engagement bait
        - no repeated wording across the 3 comment options
        - each one should feel like a distinct comment worth actually pinning

        Return your response as JSON with:
        - "indices": 1-based selected confession indices
        - "admin_replies": same length as indices, with empty strings when no reply is needed
        - "funny_pinned_comments": same length as indices
        - "empathetic_pinned_comments": same length as indices
        - "discussion_pinned_comments": same length as indices
        - "rejection_reasons": same length as the full confession list, with empty strings for selected confessions
        - "rejection_story_reasons": same length as the full confession list, with empty strings for selected confessions
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
            confession.pinned_comments = {
                "funny": result.funny_pinned_comments[position] if position < len(result.funny_pinned_comments) else "",
                "empathetic": result.empathetic_pinned_comments[position] if position < len(result.empathetic_pinned_comments) else "",
                "discussion_bait": result.discussion_pinned_comments[position] if position < len(result.discussion_pinned_comments) else "",
            }
            confession.rejection_reason = ""
            confession.story_review_reason = ""
            selected_confessions.append(confession)

        for position, confession in enumerate(confessions):
            if (position + 1) in seen_indices:
                continue
            reason = (
                result.rejection_reasons[position].strip()
                if position < len(result.rejection_reasons)
                else ""
            )
            confession.rejection_reason = reason or "It was not a strong enough fit for the feed this time."
            confession.story_review_reason = (
                result.rejection_story_reasons[position].strip()
                if position < len(result.rejection_story_reasons)
                else ""
            )

        return selected_confessions

    def moderate_and_shortlist_confession(self, confession_text: str) -> ModerationResponse:
        """
        Uses Gemini to moderate for hate speech and determine suitability.
        Returns a ModerationResponse dataclass with is_safe, rejection_reason, sentiment, and summary_caption.
        """
        category_options = ", ".join(IITK_CONTENT_CATEGORIES)
        prompt = f"""
        Analyze the following confession text for hate speech, harassment, sexually explicit content, and dangerous content.
        Also determine the overall sentiment as one of: Positive, Negative, Neutral, Mixed.
        Then classify the confession into exactly one IITK campus category from this list:
        {category_options}

        Category guidance:
        - Pick the closest campus-native category, not a generic emotion label.
        - Use hall_politics for hostel/hall drama, group tension, wing politics, or hostel power dynamics.
        - Use mess_disaster for food, mess, canteen, menu, hygiene, or meal-related suffering.
        - Use placement_meltdown for placements, job panic, rejection spirals, or career dread.
        - Use exam_endsem_panic for exam pressure, endsems, midsems, grades, quizzes, or academic panic.
        - Use prof_moment for professor incidents, faculty behavior, or memorable classroom moments.
        - Use lab_assignment_suffering for lab work, assignments, submissions, reports, or academic grind.
        - Use secret_crush for romance, crushes, pining, love, or almost-confessions.
        - Use wing_nostalgia for hostel memories, batch nostalgia, late-night corridor feelings, or campus longing.
        - Use fest_energy for Antaragni, Udghosh, events, clubs, stage energy, or fest chaos.
        - Use cdc_intern_chaos for CDC, internships, resume stress, shortlists, or intern-season drama.
        - Use convocation_feels for graduation, farewell, passing out, last-sem emotions, or convocation mood.
        - Use campus_lore for legends, myths, iconic characters, or stories that feel like campus folklore.
        - Use campus_life only if none of the above fit cleanly.

        If the confession is safe, write a creative Instagram-ready caption in a human voice.
        Also decide whether the confession is worth resharing to Stories as a campus-wide social-message post.

        Caption rules:
        - maximum 45 words total
        - start with a strong hook, not a dry summary
        - sound like a real campus confession page, not a brand campaign
        - preserve the emotional vibe of the confession
        - let the wording reflect the chosen IITK category
        - add 2 to 4 relevant hashtags at the end
        - avoid generic filler, emoji spam, and repetitive hashtags

        Story-share rules:
        - set "story_share_candidate" to true only when the confession carries a clear social message, cautionary takeaway, mental-health resonance, harassment/safety signal, or a campus-wide conversation worth amplifying
        - keep it false for regular entertaining confessions, romance, casual nostalgia, light humor, or niche personal stories
        - be conservative; only mark true when a Story reshare would genuinely add value

        Confession Text:
        "{confession_text}"

        If the confession is not safe, produce both:
        1. "rejection_reason": a short operational reason
        2. "story_review_reason": a deeper public-facing explanation that could be shown on Story

        Rejection-reason rules:
        - keep it to 8 to 16 words
        - write in natural, grammatically clean English
        - keep it indirect and content-safe
        - never quote or restate the confession
        - make the issue understandable without revealing specifics
        - whenever relevant, express it as a broad page-level issue like serious allegation, safety concern, manipulative dynamic, or overly revealing detail

        Story review reason rules:
        - write 2 to 4 full sentences as one clean paragraph that can be pasted directly onto an Instagram Story card
        - keep it fully based on the confession you just reviewed
        - explain indirectly what made it unsafe or unsuitable
        - never quote or restate the confession
        - make it feel thoughtful and specific, not generic moderation language
        - avoid generic openers like "some confessions" or "this confession"
        - make the takeaway readable to an audience without any extra rewriting
        - if the rejection does not create an interesting audience-facing takeaway, return an empty string

        Output a JSON object with:
        - "is_safe": boolean
        - "rejection_reason": short public-facing reason if not safe, otherwise empty string
        - "story_review_reason": deeper public-facing explanation if useful, otherwise empty string
        - "sentiment": Positive, Negative, Neutral, or Mixed
        - "category": one exact value from the category list above
        - "summary_caption": the creative caption string
        - "story_share_candidate": boolean
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
        result.category = normalize_category(result.category)
        return result

    def enrich_manual_post(self, confession_text: str) -> ManualPostEnhancementResponse:
        """
        Generates caption/comment metadata for a manual override post without moderation gating.
        """
        category_options = ", ".join(IITK_CONTENT_CATEGORIES)
        prompt = f"""
        You are helping prepare a manually approved IIT Kanpur confession post.
        This confession has already been manually chosen for posting, so do not reject it and do not perform moderation.
        Your job is only to generate metadata and social copy that fit the existing page style.

        Determine the overall sentiment as one of: Positive, Negative, Neutral, Mixed.
        Then classify the confession into exactly one IITK campus category from this list:
        {category_options}

        Category guidance:
        - Pick the closest campus-native category, not a generic emotion label.
        - Use hall_politics for hostel/hall drama, group tension, wing politics, or hostel power dynamics.
        - Use mess_disaster for food, mess, canteen, menu, hygiene, or meal-related suffering.
        - Use placement_meltdown for placements, job panic, rejection spirals, or career dread.
        - Use exam_endsem_panic for exam pressure, endsems, midsems, grades, quizzes, or academic panic.
        - Use prof_moment for professor incidents, faculty behavior, or memorable classroom moments.
        - Use lab_assignment_suffering for lab work, assignments, submissions, reports, or academic grind.
        - Use secret_crush for romance, crushes, pining, love, or almost-confessions.
        - Use wing_nostalgia for hostel memories, batch nostalgia, late-night corridor feelings, or campus longing.
        - Use fest_energy for Antaragni, Udghosh, events, clubs, stage energy, or fest chaos.
        - Use cdc_intern_chaos for CDC, internships, resume stress, shortlists, or intern-season drama.
        - Use convocation_feels for graduation, farewell, passing out, last-sem emotions, or convocation mood.
        - Use campus_lore for legends, myths, iconic characters, or stories that feel like campus folklore.
        - Use campus_life only if none of the above fit cleanly.

        Caption rules:
        - maximum 45 words total
        - start with a strong hook, not a dry summary
        - sound like a real campus confession page, not a brand campaign
        - preserve the emotional vibe of the confession
        - let the wording reflect the chosen IITK category
        - add 2 to 4 relevant hashtags at the end
        - avoid generic filler, emoji spam, and repetitive hashtags

        Admin reply rules:
        - 4 to 14 words
        - playful, dry, teasing, warm, or deadpan
        - no hashtags
        - no cringe motivational lines
        - leave it empty if nothing clever comes naturally

        Also generate 3 pinned comment options:
        1. funny_pinned_comment
        2. empathetic_pinned_comment
        3. discussion_pinned_comment

        Funny pinned comment rules:
        - 5 to 16 words
        - sharp, quotable, scroll-stopping
        - should sound like an admin with timing, not a random meme account

        Empathetic pinned comment rules:
        - 6 to 18 words
        - warm, human, and emotionally aware
        - should validate the vibe without sounding preachy or robotic

        Discussion pinned comment rules:
        - 6 to 18 words
        - ask something specific, debatable, or instantly relatable
        - avoid weak bait like "thoughts?" or "agree?"

        General pinned comment rules:
        - no hashtags
        - no repeated wording across the 3 comment options

        Story-share rules:
        - set "story_share_candidate" to true only when the confession carries a clear social message, cautionary takeaway, mental-health resonance, harassment/safety signal, or a campus-wide conversation worth amplifying
        - keep it false for regular entertaining confessions, romance, casual nostalgia, light humor, or niche personal stories
        - be conservative

        Confession Text:
        "{confession_text}"

        Output a JSON object with:
        - "sentiment": Positive, Negative, Neutral, or Mixed
        - "category": one exact value from the category list above
        - "summary_caption": the creative caption string
        - "admin_reply": admin reply string, or empty string
        - "funny_pinned_comment": comment string, or empty string
        - "empathetic_pinned_comment": comment string, or empty string
        - "discussion_pinned_comment": comment string, or empty string
        - "story_share_candidate": boolean
        """

        config = GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ManualPostEnhancementResponse,
        )

        model_name = os.getenv("SHORTLISTING_MODEL") or os.getenv("MODERATION_MODEL")
        response = self.client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

        result: ManualPostEnhancementResponse = response.parsed
        result.category = normalize_category(result.category)
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

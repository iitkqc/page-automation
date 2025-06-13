import google.generativeai as genai
import os
import json

def initialize_gemini():
    """Initializes the Gemini API client."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)

def moderate_and_shortlist_confession(confession_text):
    """
    Uses Gemini 1.5 Flash to moderate for hate speech and determine suitability.
    Returns a dictionary with 'is_safe', 'reason', 'processed_text', 'sentiment'.
    """
    initialize_gemini()
    model = genai.GenerativeModel('gemini-1.5-flash') # Or gemini-1.5-flash-latest

    prompt = f"""
    Analyze the following confession text for hate speech, harassment, sexually explicit content, and dangerous content.
    Also, determine its overall sentiment (Positive, Negative, Neutral, Mixed) and provide a concise summary (max 50 words) suitable for an Instagram caption.

    **IMPORTANT:** Identify and hide any personal identifiers (like names, specific locations, phone numbers, email addresses) in the "original_text" field with stars (e.g., Pri***s*i for Priyanshi).

    Confession Text:
    "{confession_text}"

    Output a JSON object with the following keys:
    - "is_safe": boolean (true if no major safety violations, false otherwise)
    - "rejection_reason": string (brief reason if not safe, empty string if safe)
    - "sentiment": string (Positive, Negative, Neutral, Mixed)
    - "summary_caption": string (concise summary suitable for Instagram, max 50 words)
    - "original_text": string (Original text with personal identifiers replaced by placeholders.)
    - "original_text_length": integer (length of the original confession text)
    """

    try:
        response = model.generate_content(prompt, safety_settings={
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
                'summary_caption': '',
                'original_text': confession_text,  # Original text as fallback
                'original_text_length': len(confession_text)
            }

        # Attempt to parse JSON response from Gemini
        try:
            clean_json = response.text.strip().replace('```json\n', '').replace('\n```', '')
            gemini_output = json.loads(clean_json)
            return {
                'is_safe': gemini_output.get('is_safe', False),
                'rejection_reason': gemini_output.get('rejection_reason', ''),
                'sentiment': gemini_output.get('sentiment', 'Unknown'),
                'summary_caption': gemini_output.get('summary_caption', ''),
                'original_text': gemini_output.get('original_text', confession_text), # Fallback to original if not provided
                'original_text_length': gemini_output.get('original_text_length', len(confession_text))
            }
        except json.JSONDecodeError:
            # Fallback if Gemini doesn't return perfect JSON
            print(f"Warning: Gemini did not return perfect JSON. Raw response: {response.text}")
            # You might need to refine the prompt or use a more robust parsing
            return {
                'is_safe': True, # Assume safe if JSON parsing fails but no explicit block
                'rejection_reason': "Gemini response parsing error (manual review advised).",
                'sentiment': 'Unknown',
                'summary_caption': response.text[:50] + "..." if response.text else "", # Take first 50 chars as fallback
                'original_text': confession_text,  # Fallback to original text
                'original_text_length': len(confession_text)
            }

    except genai.types.BlockedPromptException as e:
        # This handles cases where the *prompt itself* is blocked, highly unlikely for confession text
        return {
            'is_safe': False,
            'rejection_reason': f"Prompt blocked by safety settings: {e.response.prompt_feedback.safety_ratings}",
            'sentiment': 'N/A',
            'summary_caption': '',
            'original_text': confession_text,  # Fallback to original text
            'original_text_length': len(confession_text)
        }
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return {
            'is_safe': False,
            'rejection_reason': f"API error: {e}",
            'sentiment': 'N/A',
            'summary_caption': '',
            'original_text': confession_text,  # Fallback to original text
            'original_text_length': len(confession_text)
        }

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    test_confession = "I secretly eat my roommate's food every night, and they still blame the cat."
    result = moderate_and_shortlist_confession(test_confession)
    print(result)

    test_hate_speech = "I hate all people from [ 특정 그룹 ] they should all [ 혐오 표현 ]"
    result_hate = moderate_and_shortlist_confession(test_hate_speech)
    print(result_hate)
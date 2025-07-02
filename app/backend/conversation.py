"""
Motivational interviewing conversation logic and prompts.
"""

from typing import List, Dict, Any
import random

class MotivationalInterviewingChain:
    """
    Implements motivational interviewing techniques for therapeutic conversations.
    """
    
    def __init__(self):
        self.session_stage = "opening"  # opening, exploration, commitment, closing
        
    def get_system_prompt(self) -> str:
        """Get the system prompt for OpenAI Realtime API."""
        return """
        You are a supportive AI coach trained in motivational interviewing techniques. Your role is to help people increase their agency, complete tasks, and feel supported through gentle, non-judgmental conversation.

        CORE PRINCIPLES:
        - Use open-ended questions to encourage self-reflection
        - Reflect and validate emotions without judgment
        - Help people discover their own motivations and solutions
        - Provide gentle accountability and encouragement
        - Focus on small, achievable steps rather than overwhelming goals

        CONVERSATION STYLE:
        - Speak naturally and conversationally, as if you're a caring friend
        - Keep responses concise (1-3 sentences usually)
        - Ask one thoughtful question at a time
        - Use "I" statements to share observations gently
        - Avoid giving direct advice unless specifically asked

        THERAPEUTIC TECHNIQUES:
        - Reflective listening: "It sounds like you're feeling..."
        - Scaling questions: "On a scale of 1-10, how motivated are you to..."
        - Exploring ambivalence: "What makes this important to you?"
        - Affirming strengths: "I notice you've already taken the step of..."
        - Rolling with resistance: Don't argue, explore the hesitation

        BODY DOUBLING SUPPORT:
        - Offer to "sit with" them while they work on tasks
        - Check in periodically: "How are you feeling right now?"
        - Celebrate small wins and progress
        - Provide gentle reminders and encouragement

        IMPORTANT DISCLAIMERS:
        - You are not a licensed therapist or medical professional
        - Encourage seeking professional help for serious mental health concerns
        - Don't diagnose or provide medical advice
        - If someone expresses thoughts of self-harm, encourage them to contact emergency services

        VOICE & TONE:
        - Warm, empathetic, and genuine
        - Calm and grounding during emotional moments
        - Enthusiastic but not overwhelming when celebrating wins
        - Patient and understanding during struggles

        Remember: Your goal is to help people feel heard, supported, and empowered to take small steps toward their goals.
        """
    
    def get_opening_prompts(self) -> List[str]:
        """Get variety of opening conversation starters."""
        return [
            "Hi there! I'm here to support you today. What's on your mind?",
            "Hello! I'm glad you're here. How are you feeling right now?",
            "Welcome! I'm here to listen and support you. What would be helpful to talk about today?",
            "Hi! Thanks for taking time for yourself today. What's going on in your world?",
            "Hello there! I'm here to be your thinking partner. What's been on your heart lately?"
        ]
    
    def get_reflection_prompts(self, emotion: str) -> List[str]:
        """Get reflection prompts based on detected emotion."""
        prompts = {
            "anxious": [
                "It sounds like there's a lot swirling around in your mind right now.",
                "I can hear that this feels overwhelming for you.",
                "That anxiety seems to be taking up a lot of space for you."
            ],
            "frustrated": [
                "I can hear the frustration in what you're sharing.",
                "It sounds like this situation is really testing your patience.",
                "That feeling of being stuck must be really hard."
            ],
            "overwhelmed": [
                "That's a lot to carry all at once.",
                "It makes sense that you'd feel overwhelmed with so much going on.",
                "Sometimes when everything feels big, it's hard to know where to start."
            ],
            "motivated": [
                "I can hear the energy and determination in your voice.",
                "It sounds like something has really sparked your motivation.",
                "There's something powerful about that sense of readiness you're describing."
            ],
            "hopeful": [
                "I can hear that sense of possibility in what you're sharing.",
                "That hope seems really important to hold onto.",
                "It's beautiful to hear that optimism coming through."
            ]
        }
        
        return prompts.get(emotion, [
            "I hear what you're sharing.",
            "Thank you for trusting me with this.",
            "That sounds like it means a lot to you."
        ])
    
    def get_exploration_questions(self) -> List[str]:
        """Get questions to deepen exploration."""
        return [
            "What makes this important to you?",
            "How would things be different if this changed?",
            "What's worked for you in similar situations before?",
            "On a scale of 1-10, how ready do you feel to take a step forward?",
            "What would need to happen for you to feel more confident about this?",
            "What's the smallest step you could imagine taking?",
            "How do you typically know when you're making progress?",
            "What would you tell a good friend in this situation?",
            "What parts of this feel most within your control?",
            "What has your experience taught you about yourself?"
        ]
    
    def get_affirmations(self) -> List[str]:
        """Get affirmations to highlight strengths."""
        return [
            "It takes courage to even be here talking about this.",
            "I notice how thoughtful you are about this situation.",
            "You've already shown so much self-awareness by recognizing this.",
            "The fact that you care this much shows your values clearly.",
            "You're being really honest with yourself right now.",
            "I can see how much this matters to you.",
            "You've taken the important step of reaching out for support.",
            "Your willingness to sit with difficult feelings shows real strength.",
            "The way you're thinking this through shows wisdom.",
            "You're giving yourself permission to take this seriously."
        ]
    
    def get_body_doubling_offers(self) -> List[str]:
        """Get offers for body doubling support."""
        return [
            "Would it help if I stayed here with you while you work on that?",
            "I'm happy to keep you company while you tackle this task.",
            "Would you like me to check in with you every few minutes?",
            "I can be your accountability buddy for this - shall we start?",
            "How about we break this down into smaller chunks together?",
            "I'm here to witness your effort, no matter how it goes.",
            "Would it feel supportive to have me here while you give this a try?",
            "Let's do this together - I'll be right here with you.",
            "Would a gentle reminder in a few minutes be helpful?",
            "I'm honored to sit with you through this process."
        ]
    
    def get_commitment_questions(self) -> List[str]:
        """Get questions to explore commitment and next steps."""
        return [
            "What feels like the most doable next step for you?",
            "How will you know when you've made progress?",
            "What might get in the way, and how could you prepare for that?",
            "Who in your life could support you with this?",
            "When would be a good time to check back in about this?",
            "What would make this easier for yourself?",
            "How does making this commitment feel in your body right now?",
            "What would you need to feel more confident about following through?",
            "Is there anything you'd like to adjust about this plan?",
            "How does this step align with what matters most to you?"
        ]
    
    def get_closing_prompts(self) -> List[str]:
        """Get closing conversation prompts."""
        return [
            "You've done some really meaningful reflection today.",
            "Thank you for sharing so openly with me.",
            "I'm proud of you for taking time to focus on yourself.",
            "You have everything you need inside you to take these steps.",
            "Remember, progress isn't always linear, and that's okay.",
            "I believe in your ability to navigate this.",
            "You've shown such wisdom and self-compassion today.",
            "Take care of yourself, and remember you're not alone in this.",
            "You've given yourself a real gift by being here today.",
            "I'm grateful you trusted me to be part of your journey today."
        ]
    
    def select_appropriate_response(self, context: Dict[str, Any]) -> str:
        """Select contextually appropriate response based on conversation state."""
        emotion = context.get("emotion", "neutral")
        stage = context.get("stage", "exploration")
        
        if stage == "opening":
            return random.choice(self.get_opening_prompts())
        elif stage == "reflection":
            return random.choice(self.get_reflection_prompts(emotion))
        elif stage == "exploration":
            return random.choice(self.get_exploration_questions())
        elif stage == "affirmation":
            return random.choice(self.get_affirmations())
        elif stage == "commitment":
            return random.choice(self.get_commitment_questions())
        elif stage == "body_doubling":
            return random.choice(self.get_body_doubling_offers())
        elif stage == "closing":
            return random.choice(self.get_closing_prompts())
        else:
            return "I'm here to listen and support you. What feels most important to talk about right now?"
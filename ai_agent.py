"""
LVS Call Screening - AI Agent Powered by Gemini API (Google GenAI SDK)
Handles:
1. Dynamic conversational response generation in natural Telugu & English.
2. Intelligent intent extraction & urgency evaluation (forwarding vs owner alert).
3. Post-call structured summary generation matching the exact format:
   "హాయ్ బాస్, ఈ పర్సన్ ఫోన్ చేశాడు, అతని పేరు ఇది, మరియు ఈ విషయంలో మాట్లాడాడు"
"""

import os
import json
from typing import List, Dict, Any, Optional
from .schemas import (
    CallerCategory,
    CallAction,
    TranscriptTurn,
    CallScreeningState
)

# Owner Information Constant
OWNER_NAME = "Sudheer"
OWNER_TITLE = "బాస్ (Boss)"

class LvsAiCallAgent:
    """
    Intelligent Conversational Screening Agent leveraging Google GenAI SDK
    with smart prompt engineering and high-availability fallback.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.client = None
        self._init_genai_client()

    def _init_genai_client(self):
        """Initializes google-genai client if installed and API key is present."""
        if not self.api_key:
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        except Exception:
            # Fallback will seamlessly operate for offline/simulated screening
            self.client = None

    def generate_initial_greeting(
        self,
        caller_name: str,
        category: CallerCategory
    ) -> str:
        """
        Produces the immediate opening line when LVS answers the call.
        - Family: Polite explanation that Sudheer is busy.
        - Friends: Warm, respectful greeting asking for purpose.
        - Delivery: Quick practical inquiry about parcel/location.
        - General Public: Formal, professional screening greeting.
        """
        if category == CallerCategory.FAMILY:
            return (
                f"నమస్కారం అండి! నేను సుధీర్ గారి LVS పర్సనల్ AI అసిస్టెంట్‌ని. "
                f"సుధీర్ గారు ప్రస్తుతం ఒక ముఖ్యమైన మీటింగ్‌లో బిజీగా ఉన్నారు. "
                f"మీరేమైనా అత్యవసర సందేశం చెప్పాలనుకుంటున్నారా? నేను వెంటనే వారికి అందిస్తాను."
            )
        elif category == CallerCategory.FRIEND:
            return (
                f"హలో {caller_name}! నేను సుధీర్ గారి LVS అసిస్టెంట్‌ని. "
                f"సుధీర్ గారు చిన్న పనిలో ఉన్నారు. ఏం విషయం మాట్లాడాలి? "
                f"అత్యవసరమైతే వెంటనే కనెక్ట్ చేస్తాను లేదా మెసేజ్ ఇవ్వమంటారా?"
            )
        elif category == CallerCategory.DELIVERY:
            return (
                f"హలో అండి! నేను సుధీర్ గారి LVS అసిస్టెంట్‌ని. డెలివరీ కోసమా అండి? "
                f"ఎక్కడి నుంచి వచ్చారు? పార్సెల్ సెక్యూరిటీ దగ్గర పెట్టమంటారా లేక డోర్ వద్ద ఉంచమంటారా?"
            )
        else:
            return (
                f"నమస్కారం అండి. నేను సుధీర్ గారి LVS పర్సనల్ అసిస్టెంట్‌ని. "
                f"సుధీర్ గారు ప్రస్తుతం అందుబాటులో లేరు. దయచేసి మీ పేరు మరియు కాల్ చేసిన ఉద్దేశం చెప్పండి."
            )

    def generate_agent_response(
        self,
        state: CallScreeningState,
        latest_caller_utterance: str
    ) -> Dict[str, Any]:
        """
        Generates conversational response using Gemini API or rule-based fallback,
        and determines whether to forward the call or alert the owner.
        """
        category = state.category
        caller_name = state.caller_name

        # If caller is FAMILY, enforce the polite busy protocol
        if category == CallerCategory.FAMILY:
            return self._handle_family_response(latest_caller_utterance)

        # For FRIEND, DELIVERY, GENERAL_PUBLIC, use Gemini or high-accuracy intelligence
        if self.client:
            try:
                gemini_result = self._call_gemini_conversational_screening(state, latest_caller_utterance)
                if gemini_result:
                    return gemini_result
            except Exception as e:
                print(f"[LvsAiCallAgent] Gemini API call exception: {e}")

        # Robust heuristic fallback
        return self._rule_based_response(state, latest_caller_utterance)

    def _handle_family_response(self, utterance: str) -> Dict[str, Any]:
        """Specific polite protocol for close relatives: politely answers, states Sudheer is busy, and logs intent."""
        u_lower = utterance.lower()
        # Strictly for life-critical medical emergencies will it escalate to forwarding
        is_emergency = any(w in u_lower for w in ["emergency", "hospital", "హాస్పిటల్", "ఆసుపత్రి", "యాక్సిడెంట్", "accident"])

        if is_emergency:
            response_text = (
                "అర్థమైంది అండి! ఇది అత్యవసర మెడికల్ విషయం అని చెప్పారు కాబట్టి, "
                "నేను వెంటనే సుధీర్ గారికి హై-ప్రయారిటీ అలర్ట్ పంపి కాల్ కనెక్ట్ చేస్తున్నాను. ఒక్క క్షణం లైన్‌లో ఉండండి."
            )
            return {
                "agent_response": response_text,
                "action": CallAction.FORWARD_CALL,
                "should_forward": True,
                "should_alert_owner": True,
                "intent": f"అత్యవసర కుటుంబ కాల్: {utterance}"
            }

        else:
            response_text = (
                "సరే అండి, మీరు చెప్పిన విషయం నోట్ చేసుకున్నాను. "
                "సుధీర్ గారు మీటింగ్ పూర్తి కాగానే వెంటనే మీకు తిరిగి కాల్ చేసేలా చూస్తాను. ధన్యవాదాలు!"
            )
            return {
                "agent_response": response_text,
                "action": CallAction.POLITE_BUSY_NOTE,
                "should_forward": False,
                "should_alert_owner": True,
                "intent": utterance
            }

    def _rule_based_response(
        self,
        state: CallScreeningState,
        utterance: str
    ) -> Dict[str, Any]:
        """Heuristic response generator for when Gemini is offline or unconfigured."""
        u_lower = utterance.lower()
        category = state.category
        caller_name = state.caller_name

        is_urgent = any(w in u_lower for w in ["urgent", "emergency", "immediately", "త్వరగా", "అత్యవసరం", "కలవాలి", "call now"])
        is_delivery_arrived = any(w in u_lower for w in ["gate", "security", "door", "వచ్చాను", "గేట్", "సెక్యూరిటీ", "డెలివరీ", "పార్సెల్", "parcel", "food"])

        if category == CallerCategory.DELIVERY:
            if is_delivery_arrived:
                response_text = (
                    "సరే అండి, పార్సెల్ ని గేట్ వద్ద ఉన్న సెక్యూరిటీ గార్డ్ కి లేదా డోర్ దగ్గర ఇచ్చేయండి. "
                    "నేను సుధీర్ గారికి వెంటనే అలర్ట్ పంపిస్తున్నాను. ధన్యవాదాలు!"
                )
                action = CallAction.ALERT_OWNER
            else:
                response_text = (
                    "అవునండి, అడ్రస్ లేదా లొకేషన్ లో ఏమైనా సమస్య ఉందా? "
                    "నేను సుధీర్ గారికి వెంటనే మీ లొకేషన్ అలర్ట్ ఇస్తాను."
                )
                action = CallAction.CONVERSE_AND_SCREEN

            return {
                "agent_response": response_text,
                "action": action,
                "should_forward": is_urgent,
                "should_alert_owner": True,
                "intent": f"డెలివరీ: {utterance}"
            }

        elif category == CallerCategory.FRIEND:
            if is_urgent:
                response_text = (
                    f"{caller_name}, మీరు అర్జంట్ అన్నందున నేను సుధీర్ గారికి వెంటనే కాల్ కనెక్ట్ చేస్తున్నాను. "
                    f"ఒక్క సెకను ఆగండి."
                )
                return {
                    "agent_response": response_text,
                    "action": CallAction.FORWARD_CALL,
                    "should_forward": True,
                    "should_alert_owner": True,
                    "intent": f"స్నేహితుడి అర్జంట్ విషయం: {utterance}"
                }
            else:
                response_text = (
                    f"సరే {caller_name}, మీరు చెప్పిన ఉద్దేశం ({utterance}) నోట్ చేసుకున్నాను. "
                    f"సుధీర్ గారికి వెంటనే యాప్ లో నోటిఫికేషన్ వెళ్తుంది. కాసేపట్లో మిమ్మల్ని సంప్రదిస్తారు."
                )
                return {
                    "agent_response": response_text,
                    "action": CallAction.ALERT_OWNER,
                    "should_forward": False,
                    "should_alert_owner": True,
                    "intent": utterance
                }

        else: # GENERAL_PUBLIC
            if is_urgent:
                response_text = (
                    "మీరు చాలా అత్యవసరమని చెప్పారు కాబట్టి సుధీర్ గారికి వెంటనే మీ సమాచారం ఫార్వర్డ్ చేస్తున్నాను."
                )
                action = CallAction.FORWARD_CALL
            else:
                response_text = (
                    "మీరు చెప్పిన సమాచారం నోట్ చేసాను. సుధీర్ గారు ఫ్రీ అయిన వెంటనే చూసుకుంటారు. ధన్యవాదాలు."
                )
                action = CallAction.ALERT_OWNER

            return {
                "agent_response": response_text,
                "action": action,
                "should_forward": is_urgent,
                "should_alert_owner": True,
                "intent": utterance
            }

    def _call_gemini_conversational_screening(
        self,
        state: CallScreeningState,
        latest_utterance: str
    ) -> Optional[Dict[str, Any]]:
        """Invokes Gemini 2.5/Gemini API via google-genai SDK for real-time conversation."""
        transcript_history = "\n".join(
            [f"{t.speaker}: {t.text}" for t in state.transcript]
        )

        prompt = f"""
You are LVS, a smart Telugu and English personal AI assistant for Sudheer (the phone owner).
You are currently screening an incoming phone call on behalf of Sudheer.

Caller Details:
- Name: {state.caller_name}
- Category: {state.category.value} (FAMILY, FRIEND, DELIVERY, GENERAL_PUBLIC)
- Owner Status: Sudheer is currently in a meeting/busy.

Past Conversation:
{transcript_history}

Latest Caller Speech: "{latest_utterance}"

Tasks:
1. Generate the natural Telugu or bilingual (Telugu + English) voice response that LVS should speak to the caller.
   - If FRIEND or DELIVERY: Be conversational, ask what parcel/topic it is, or acknowledge and explain you will alert Sudheer.
   - If URGENT: Offer to connect or immediately alert Sudheer.
2. Extract the core intent/purpose of the call in a concise phrase.
3. Determine if the call should be forwarded (should_forward: true/false) and if an instant alert must be sent to Sudheer (should_alert_owner: true/false).

Return ONLY valid JSON with keys:
"agent_response": (string in natural Telugu/English),
"action": ("CONVERSE_AND_SCREEN", "FORWARD_CALL", "ALERT_OWNER", "POLITE_BUSY_NOTE"),
"should_forward": (boolean),
"should_alert_owner": (boolean),
"intent": (short string description)
"""
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )

        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text.strip("```json").strip("```").strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.strip("```").strip()

        data = json.loads(raw_text)
        action_str = data.get("action", "CONVERSE_AND_SCREEN")
        try:
            action = CallAction(action_str)
        except ValueError:
            action = CallAction.CONVERSE_AND_SCREEN

        return {
            "agent_response": data.get("agent_response", ""),
            "action": action,
            "should_forward": bool(data.get("should_forward", False)),
            "should_alert_owner": bool(data.get("should_alert_owner", True)),
            "intent": data.get("intent", latest_utterance)
        }

    def generate_call_summary_report(
        self,
        caller_name: str,
        caller_phone: str,
        category: CallerCategory,
        full_transcript: List[TranscriptTurn],
        extracted_intent: Optional[str] = None
    ) -> str:
        """
        Generates the structured post-call notification report.
        Strict requirement format:
        "హాయ్ బాస్, ఈ పర్సన్ ఫోన్ చేశాడు, అతని పేరు ఇది, మరియు ఈ విషయంలో మాట్లాడాడు"
        Tailored with real extracted values:
        "హాయ్ బాస్, ఈ పర్సన్ ఫోన్ చేశాడు, అతని పేరు [Name/Phone], మరియు [Intent/Topic] విషయంలో మాట్లాడాడు."
        """
        # Determine intent
        intent_description = extracted_intent
        if not intent_description and full_transcript:
            # Extract from caller turns
            caller_texts = [t.text for t in full_transcript if t.speaker == "caller"]
            if caller_texts:
                intent_description = " / ".join(caller_texts[-2:])
            else:
                intent_description = "కాల్ మాట్లాడారు"
        elif not intent_description:
            intent_description = "సాధారణ సమాచారం"

        display_name = caller_name if caller_name and caller_name != "Unknown" else caller_phone

        # If Gemini is available, we can also generate an enriched context,
        # but ALWAYS include the exact requested phrasing!
        exact_formatted_report = (
            f"హాయ్ బాస్, ఈ పర్సన్ ఫోన్ చేశాడు, అతని పేరు {display_name}, "
            f"మరియు {intent_description} విషయంలో మాట్లాడాడు."
        )

        return exact_formatted_report

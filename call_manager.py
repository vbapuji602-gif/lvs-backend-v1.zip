"""
LVS Call Screening & Routing - Call Manager
Manages:
1. Contact Database Lookup (`contacts_db.json`) with phone number normalization.
2. Caller Classification (Family, Friend, Delivery, General Public, Spam).
3. Call State Machine (Ringing -> Screening -> Forwarded / Completed).
4. Audio transcript turns logging and live coordination with LvsAiCallAgent.
5. Instant owner notification generation and delivery queue.
"""

import json
import os
import re
import time
from typing import Dict, List, Optional, Any
from .schemas import (
    CallerCategory,
    CallAction,
    CallStatus,
    ContactModel,
    TranscriptTurn,
    CallScreeningState,
    CallReportSummary
)
from .ai_agent import LvsAiCallAgent

DEFAULT_CONTACTS_DB_PATH = os.path.join(os.path.dirname(__file__), "contacts_db.json")

class CallManager:
    """
    Coordinates contact filtering, call state tracking, AI screening responses,
    and alert dispatching for the LVS assistant.
    """

    def __init__(self, contacts_db_path: Optional[str] = None, ai_agent: Optional[LvsAiCallAgent] = None):
        self.contacts_db_path = contacts_db_path or DEFAULT_CONTACTS_DB_PATH
        self.ai_agent = ai_agent or LvsAiCallAgent()
        self.contacts: Dict[str, ContactModel] = {}
        self.owner_info: Dict[str, Any] = {}
        self.active_calls: Dict[str, CallScreeningState] = {}
        self.call_history: List[CallScreeningState] = []
        self.owner_alerts: List[Dict[str, Any]] = []

        self.load_contacts()

    def normalize_phone(self, phone: str) -> str:
        """Removes spaces, hyphens, parentheses, and standardizes +91 / local numbers."""
        cleaned = re.sub(r"[^\d+]", "", phone.strip())
        if cleaned.startswith("0") and len(cleaned) == 11:
            cleaned = "+91" + cleaned[1:]
        elif not cleaned.startswith("+") and len(cleaned) == 10:
            cleaned = "+91" + cleaned
        return cleaned

    def load_contacts(self):
        """Loads contacts and owner metadata from JSON file."""
        if not os.path.exists(self.contacts_db_path):
            print(f"[CallManager] Warning: {self.contacts_db_path} not found. Using empty registry.")
            return

        try:
            with open(self.contacts_db_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.contacts.clear()
            for c in data.get("contacts", []):
                norm_phone = self.normalize_phone(c["phone"])
                category = CallerCategory(c.get("category", "GENERAL_PUBLIC"))
                self.contacts[norm_phone] = ContactModel(
                    phone=norm_phone,
                    name=c["name"],
                    relationship=c.get("relationship", "Unknown"),
                    category=category,
                    priority=c.get("priority", "MEDIUM"),
                    notes=c.get("notes")
                )

            self.owner_info = data.get("owner", {
                "name": "Sudheer",
                "title": "Boss",
                "primary_language": "Telugu"
            })
            print(f"[CallManager] Loaded {len(self.contacts)} verified contacts for Owner: {self.owner_info.get('name')}")
        except Exception as e:
            print(f"[CallManager] Failed loading contacts: {e}")

    def lookup_contact(self, phone: str) -> Optional[ContactModel]:
        """Finds contact by normalized phone number or fallback pattern."""
        norm = self.normalize_phone(phone)
        if norm in self.contacts:
            return self.contacts[norm]

        # Check last 10 digits match
        last_10 = norm[-10:] if len(norm) >= 10 else norm
        for stored_phone, contact in self.contacts.items():
            if stored_phone.endswith(last_10):
                return contact
        return None

    def classify_caller(self, phone: str, caller_name_hint: Optional[str] = None) -> (CallerCategory, str):
        """
        Categorizes caller into:
        - FAMILY (Close relatives)
        - FRIEND (Venkat, Rishi, etc.)
        - DELIVERY (Swiggy, Amazon, Zomato, etc.)
        - GENERAL_PUBLIC (Unknown or unsaved numbers)
        """
        contact = self.lookup_contact(phone)
        if contact:
            return contact.category, contact.name

        # If name is provided via caller-ID / TrueCaller metadata
        if caller_name_hint:
            name_lower = caller_name_hint.lower()
            if any(w in name_lower for w in ["delivery", "swiggy", "zomato", "amazon", "flipkart", "courier", "dunzo"]):
                return CallerCategory.DELIVERY, caller_name_hint
            elif any(w in name_lower for w in ["amma", "nanna", "sister", "brother", "mom", "dad", "uncle", "aunty"]):
                return CallerCategory.FAMILY, caller_name_hint
            elif any(w in name_lower for w in ["venkat", "rishi", "friend"]):
                return CallerCategory.FRIEND, caller_name_hint

        return CallerCategory.GENERAL_PUBLIC, caller_name_hint or "Unknown Caller"

    def handle_incoming_call(
        self,
        call_id: str,
        caller_phone: str,
        caller_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Entrypoint for incoming call webhook:
        1. Classifies caller against contacts_db.json.
        2. Sets up initial screening state.
        3. Formulates opening spoken line and primary recommended action.
        """
        category, resolved_name = self.classify_caller(caller_phone, caller_name)

        # Determine primary action rule
        if category == CallerCategory.FAMILY:
            primary_action = CallAction.POLITE_BUSY_NOTE
        else:
            primary_action = CallAction.CONVERSE_AND_SCREEN

        # Generate initial voice response
        initial_greeting = self.ai_agent.generate_initial_greeting(resolved_name, category)

        state = CallScreeningState(
            call_id=call_id,
            caller_phone=self.normalize_phone(caller_phone),
            caller_name=resolved_name,
            category=category,
            status=CallStatus.SCREENING,
            recommended_action=primary_action
        )
        # Record initial agent speech turn
        state.transcript.append(
            TranscriptTurn(speaker="lvs_agent", text=initial_greeting)
        )
        self.active_calls[call_id] = state

        return {
            "call_id": call_id,
            "caller_name": resolved_name,
            "caller_phone": state.caller_phone,
            "category": category.value,
            "initial_agent_speech": initial_greeting,
            "recommended_action": primary_action.value
        }

    def process_caller_utterance(
        self,
        call_id: str,
        caller_speech: str
    ) -> Dict[str, Any]:
        """
        Handles real-time transcribed voice from caller:
        1. Records turn in state transcript.
        2. Generates conversational reply via Gemini AI / screening logic.
        3. Dynamically triggers owner alert or call forwarding if requested or urgent.
        """
        state = self.active_calls.get(call_id)
        if not state:
            raise ValueError(f"Call ID '{call_id}' not found in active calls.")

        # Record caller speech
        state.transcript.append(
            TranscriptTurn(speaker="caller", text=caller_speech)
        )

        # Generate agent conversational reply
        ai_result = self.ai_agent.generate_agent_response(state, caller_speech)
        agent_reply = ai_result["agent_response"]
        action = ai_result["action"]
        should_forward = ai_result["should_forward"]
        should_alert = ai_result["should_alert_owner"]
        intent = ai_result.get("intent", caller_speech)

        state.detected_intent = intent
        state.recommended_action = action

        # Record agent turn
        state.transcript.append(
            TranscriptTurn(speaker="lvs_agent", text=agent_reply)
        )

        # Handle forwarding state transition
        if should_forward:
            state.status = CallStatus.FORWARDED
            self._queue_owner_alert(
                call_id=call_id,
                alert_type="CALL_FORWARDING",
                title="🚨 Urgent Call Forwarding to Sudheer",
                message=f"Connecting {state.caller_name} ({state.category.value}) - Purpose: {intent}"
            )

        elif should_alert:
            self._queue_owner_alert(
                call_id=call_id,
                alert_type="CALL_SCREENING_UPDATE",
                title=f"📞 Call Screening: {state.caller_name}",
                message=f"{state.caller_name} ({state.category.value}): {intent}"
            )

        return {
            "call_id": call_id,
            "agent_response": agent_reply,
            "recommended_action": action.value,
            "should_forward": should_forward,
            "should_alert_owner": should_alert,
            "detected_intent": intent
        }

    def end_call(self, call_id: str) -> CallReportSummary:
        """
        Finalizes call screening session:
        1. Generates structured post-call notification report:
           'హాయ్ బాస్, ఈ పర్సన్ ఫోన్ చేశాడు, అతని పేరు ఇది, మరియు ఈ విషయంలో మాట్లాడాడు'
        2. Archives session into call_history.
        3. Returns structured summary for mobile UI/Notification center.
        """
        state = self.active_calls.get(call_id)
        if not state:
            # Check history if already completed
            for past in self.call_history:
                if past.call_id == call_id:
                    state = past
                    break

        if not state:
            raise ValueError(f"Call ID '{call_id}' not found.")

        state.ended_at = time.time()
        state.status = CallStatus.COMPLETED

        duration = max(1.0, state.ended_at - state.created_at)

        # Generate formatted summary report
        report_text = self.ai_agent.generate_call_summary_report(
            caller_name=state.caller_name,
            caller_phone=state.caller_phone,
            category=state.category,
            full_transcript=state.transcript,
            extracted_intent=state.detected_intent
        )
        state.summary_report = report_text

        # Queue final push notification alert to owner
        self._queue_owner_alert(
            call_id=call_id,
            alert_type="CALL_SUMMARY_REPORT",
            title="LVS Call Summary (బాస్)",
            message=report_text
        )

        # Archive call
        if call_id in self.active_calls:
            del self.active_calls[call_id]
        self.call_history.append(state)

        return CallReportSummary(
            call_id=call_id,
            caller_name=state.caller_name,
            caller_phone=state.caller_phone,
            category=state.category,
            intent=state.detected_intent or "సమాచారం",
            telugu_formatted_report=report_text,
            duration_seconds=duration,
            recommended_action=state.recommended_action
        )

    def _queue_owner_alert(self, call_id: str, alert_type: str, title: str, message: str):
        """Appends alert to in-memory notifications for owner poll/WebSocket push."""
        self.owner_alerts.append({
            "call_id": call_id,
            "type": alert_type,
            "title": title,
            "message": message,
            "timestamp": time.time()
        })

    def get_owner_alerts(self) -> List[Dict[str, Any]]:
        """Returns pending notifications for owner."""
        return self.owner_alerts

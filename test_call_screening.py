"""
Unit tests for LVS Call Screening, Routing, and AI Reporting Module.
Validates:
1. Contact DB loading & normalization (+91 / local 10 digits).
2. Category classification (Family, Friend, Delivery, General Public).
3. Family polite busy note logic (owner Sudheer is busy).
4. Friend (Venkat, Rishi) screening & urgent forwarding.
5. Delivery partner (Swiggy, Amazon) screening & parcel drop handling.
6. Post-call structured Telugu summary format:
   "హాయ్ బాస్, ఈ పర్సన్ ఫోన్ చేశాడు, అతని పేరు ఇది, మరియు ఈ విషయంలో మాట్లాడాడు"
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.call_screening.schemas import (
    CallerCategory,
    CallAction,
    CallStatus,
    TranscriptTurn
)
from app.call_screening.call_manager import CallManager
from app.call_screening.ai_agent import LvsAiCallAgent

class TestCallScreeningModule(unittest.TestCase):

    def setUp(self):
        self.manager = CallManager()
        self.ai_agent = self.manager.ai_agent

    def test_contacts_loaded_and_normalized(self):
        """Verifies contacts_db.json is loaded and phone numbers are normalized."""
        self.assertGreaterEqual(len(self.manager.contacts), 7)
        self.assertEqual(self.manager.owner_info.get("name"), "Sudheer")

        # Check Amma (Family)
        contact_amma = self.manager.lookup_contact("+919876543210")
        self.assertIsNotNone(contact_amma)
        self.assertEqual(contact_amma.name, "Amma")
        self.assertEqual(contact_amma.category, CallerCategory.FAMILY)

        # Check Venkat (Friend) using local 10-digit format
        contact_venkat = self.manager.lookup_contact("9123456780")
        self.assertIsNotNone(contact_venkat)
        self.assertEqual(contact_venkat.name, "Venkat")
        self.assertEqual(contact_venkat.category, CallerCategory.FRIEND)

        # Check Swiggy (Delivery)
        contact_delivery = self.manager.lookup_contact("+919800112233")
        self.assertIsNotNone(contact_delivery)
        self.assertEqual(contact_delivery.category, CallerCategory.DELIVERY)

    def test_family_caller_polite_busy_handling(self):
        """
        Requirement: If the caller is a Close Relative (Family):
        The AI agent must politely answer, notify that the owner (Sudheer) is currently busy, and log the intent.
        """
        incoming = self.manager.handle_incoming_call(
            call_id="call_amma_01",
            caller_phone="+919876543210"
        )
        self.assertEqual(incoming["category"], CallerCategory.FAMILY.value)
        self.assertEqual(incoming["recommended_action"], CallAction.POLITE_BUSY_NOTE.value)
        self.assertIn("సుధీర్", incoming["initial_agent_speech"])
        self.assertIn("బిజీగా", incoming["initial_agent_speech"])

        # Amma responds with non-emergency message
        turn = self.manager.process_caller_utterance(
            call_id="call_amma_01",
            caller_speech="సాయంత్రం ఇంటికి త్వరగా రమ్మని చెప్పు సుధీర్ కి"
        )
        self.assertEqual(turn["recommended_action"], CallAction.POLITE_BUSY_NOTE.value)
        self.assertFalse(turn["should_forward"])
        self.assertTrue(turn["should_alert_owner"])

        # End call and verify summary report
        report = self.manager.end_call("call_amma_01")
        self.assertIn("హాయ్ బాస్, ఈ పర్సన్ ఫోన్ చేశాడు, అతని పేరు Amma", report.telugu_formatted_report)
        self.assertIn("విషయంలో మాట్లాడాడు", report.telugu_formatted_report)

    def test_friend_conversational_screening_and_forwarding(self):
        """
        Requirement: If the caller is a Friend (e.g., Venkat, Rishi):
        The AI agent must converse with them, determine purpose, and forward/alert owner.
        """
        incoming = self.manager.handle_incoming_call(
            call_id="call_venkat_02",
            caller_phone="+919123456780"
        )
        self.assertEqual(incoming["category"], CallerCategory.FRIEND.value)
        self.assertEqual(incoming["recommended_action"], CallAction.CONVERSE_AND_SCREEN.value)
        self.assertIn("Venkat", incoming["initial_agent_speech"])

        # Case A: Normal inquiry -> alerts owner
        turn_normal = self.manager.process_caller_utterance(
            call_id="call_venkat_02",
            caller_speech="ప్రాజెక్ట్ కోడ్ రివ్యూ గురించి మాట్లాడాలి రేపు"
        )
        self.assertEqual(turn_normal["should_forward"], False)
        self.assertEqual(turn_normal["should_alert_owner"], True)

        # End call
        summary = self.manager.end_call("call_venkat_02")
        self.assertIn("హాయ్ బాస్, ఈ పర్సన్ ఫోన్ చేశాడు, అతని పేరు Venkat", summary.telugu_formatted_report)
        self.assertIn("విషయంలో మాట్లాడాడు", summary.telugu_formatted_report)

        # Case B: Urgent inquiry from Rishi -> triggers call forwarding
        self.manager.handle_incoming_call(
            call_id="call_rishi_urgent",
            caller_phone="+919123456781"
        )
        turn_urgent = self.manager.process_caller_utterance(
            call_id="call_rishi_urgent",
            caller_speech="Sudheer, it's very urgent! Production server down, please connect immediately!"
        )
        self.assertTrue(turn_urgent["should_forward"])
        self.assertEqual(turn_urgent["recommended_action"], CallAction.FORWARD_CALL.value)

    def test_delivery_personnel_screening(self):
        """
        Requirement: Delivery Person screening (Swiggy/Amazon).
        Converse, determine intent, and alert owner instantly.
        """
        incoming = self.manager.handle_incoming_call(
            call_id="call_swiggy_03",
            caller_phone="+919800112233"
        )
        self.assertEqual(incoming["category"], CallerCategory.DELIVERY.value)
        self.assertEqual(incoming["recommended_action"], CallAction.CONVERSE_AND_SCREEN.value)
        self.assertIn("డెలివరీ", incoming["initial_agent_speech"])

        # Delivery partner indicates arrived at gate
        turn = self.manager.process_caller_utterance(
            call_id="call_swiggy_03",
            caller_speech="స్విగ్గీ ఫుడ్ డెలివరీ అండి, గేట్ సెక్యూరిటీ దగ్గరకు వచ్చాను"
        )
        self.assertEqual(turn["recommended_action"], CallAction.ALERT_OWNER.value)
        self.assertTrue(turn["should_alert_owner"])
        self.assertIn("సెక్యూరిటీ", turn["agent_response"])

        report = self.manager.end_call("call_swiggy_03")
        self.assertIn("హాయ్ బాస్, ఈ పర్సన్ ఫోన్ చేశాడు", report.telugu_formatted_report)
        self.assertIn("విషయంలో మాట్లాడాడు", report.telugu_formatted_report)

    def test_exact_required_telugu_summary_format(self):
        """
        Requirement: Exactly match Telugu notification report:
        "హాయ్ బాస్, ఈ పర్సన్ ఫోన్ చేశాడు, అతని పేరు ఇది, మరియు ఈ విషయంలో మాట్లాడాడు"
        """
        report_text = self.ai_agent.generate_call_summary_report(
            caller_name="Rishi",
            caller_phone="+919123456781",
            category=CallerCategory.FRIEND,
            full_transcript=[
                TranscriptTurn(speaker="lvs_agent", text="హలో రిషి"),
                TranscriptTurn(speaker="caller", text="LVS AI ప్రాజెక్ట్ డెమో డిస్కషన్")
            ],
            extracted_intent="LVS AI ప్రాజెక్ట్ డెమో డిస్కషన్"
        )

        expected_prefix = "హాయ్ బాస్, ఈ పర్సన్ ఫోన్ చేశాడు, అతని పేరు Rishi, మరియు LVS AI ప్రాజెక్ట్ డెమో డిస్కషన్ విషయంలో మాట్లాడాడు."
        self.assertEqual(report_text, expected_prefix)

if __name__ == '__main__':
    unittest.main()

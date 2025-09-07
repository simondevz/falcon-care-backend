"""
Mock payer service for simulating real payer API interactions
"""

import random
import string
from typing import Dict, Any, Optional
from datetime import datetime, date, timedelta
from uuid import UUID


class MockPayerService:
    """Mock service to simulate payer API interactions"""

    def __init__(self):
        self.payers = {
            "ADNIC": {
                "name": "Abu Dhabi National Insurance Company",
                "coverage_types": ["individual", "family", "corporate"],
                "requires_pre_auth": ["surgery", "mri", "ct_scan"],
                "copay_amount": 25.00,
            },
            "DAMAN": {
                "name": "Daman National Health Insurance",
                "coverage_types": ["basic", "enhanced", "premium"],
                "requires_pre_auth": ["specialist_referral", "surgery"],
                "copay_amount": 20.00,
            },
            "THIQA": {
                "name": "Thiqa Insurance",
                "coverage_types": ["essential", "comprehensive"],
                "requires_pre_auth": ["emergency_abroad", "surgery"],
                "copay_amount": 30.00,
            },
        }

    async def check_eligibility(
        self, patient_id: UUID, payer_id: str, service_date: date
    ) -> Dict[str, Any]:
        """
        Mock eligibility check
        """
        if payer_id not in self.payers:
            return {
                "eligible": False,
                "error": "Unknown payer",
                "confidence_score": 0.0,
            }

        payer = self.payers[payer_id]

        # Simulate random eligibility (90% success rate)
        eligible = random.random() > 0.1

        if eligible:
            return {
                "patient_id": str(patient_id),
                "payer_id": payer_id,
                "eligible": True,
                "coverage_details": {
                    "deductible_remaining": random.uniform(0, 1000),
                    "copay_amount": payer["copay_amount"],
                    "coverage_percentage": random.choice([70, 80, 90, 100]),
                    "requires_prior_auth": False,
                    "max_benefit": 100000.00,
                    "policy_status": "active",
                    "effective_date": "2024-01-01",
                    "expiry_date": "2024-12-31",
                },
                "confidence_score": random.uniform(0.85, 0.98),
                "response_time": random.uniform(0.5, 2.0),
            }
        else:
            return {
                "patient_id": str(patient_id),
                "payer_id": payer_id,
                "eligible": False,
                "reason": random.choice(
                    [
                        "Policy expired",
                        "Premium not paid",
                        "Service not covered",
                        "Waiting period not completed",
                    ]
                ),
                "confidence_score": 0.95,
            }

    async def submit_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock claim submission
        """
        claim_id = claim_data.get("claim_id")
        payer_id = claim_data.get("payer_id")

        if payer_id not in self.payers:
            return {
                "status": "rejected",
                "error": "Unknown payer",
                "claim_id": claim_id,
            }

        # Generate reference number
        reference_number = "REF" + "".join(random.choices(string.digits, k=10))

        # Simulate processing (80% acceptance rate)
        if random.random() > 0.2:
            return {
                "claim_id": claim_id,
                "status": "submitted",
                "reference_number": reference_number,
                "estimated_processing_days": random.randint(3, 10),
                "tracking_number": "TRK" + "".join(random.choices(string.digits, k=8)),
                "submission_timestamp": datetime.utcnow().isoformat(),
                "payer_response": {
                    "code": "ACCEPTED",
                    "message": "Claim submitted successfully",
                },
            }
        else:
            return {
                "claim_id": claim_id,
                "status": "rejected",
                "reference_number": reference_number,
                "rejection_reason": random.choice(
                    [
                        "Missing documentation",
                        "Invalid procedure codes",
                        "Patient not eligible",
                        "Prior authorization required",
                    ]
                ),
                "submission_timestamp": datetime.utcnow().isoformat(),
                "payer_response": {
                    "code": "REJECTED",
                    "message": "Claim rejected - see reason",
                },
            }

    async def check_claim_status(self, reference_number: str) -> Dict[str, Any]:
        """
        Mock claim status check
        """
        # Simulate different claim statuses
        statuses = ["processing", "approved", "denied", "pending_review"]
        status = random.choice(statuses)

        base_response = {
            "reference_number": reference_number,
            "status": status,
            "last_updated": datetime.utcnow().isoformat(),
        }

        if status == "approved":
            base_response.update(
                {
                    "approved_amount": random.uniform(100, 5000),
                    "payment_date": (
                        datetime.utcnow() + timedelta(days=random.randint(1, 5))
                    )
                    .date()
                    .isoformat(),
                    "explanation_of_benefits": "Claim approved for payment",
                }
            )
        elif status == "denied":
            base_response.update(
                {
                    "denial_reason": random.choice(
                        [
                            "Service not covered under policy",
                            "Missing required documentation",
                            "Duplicate claim",
                            "Provider not in network",
                        ]
                    ),
                    "denial_code": random.choice(["D001", "D002", "D003", "D004"]),
                    "appeal_deadline": (datetime.utcnow() + timedelta(days=30))
                    .date()
                    .isoformat(),
                }
            )
        elif status == "pending_review":
            base_response.update(
                {
                    "review_reason": "Additional documentation required",
                    "required_documents": ["medical_records", "referral_letter"],
                    "due_date": (datetime.utcnow() + timedelta(days=7))
                    .date()
                    .isoformat(),
                }
            )

        return base_response

    async def submit_prior_authorization(
        self, patient_id: UUID, procedure_codes: list, payer_id: str
    ) -> Dict[str, Any]:
        """
        Mock prior authorization submission
        """
        if payer_id not in self.payers:
            return {"status": "rejected", "error": "Unknown payer"}

        auth_number = "PA" + "".join(random.choices(string.digits, k=8))

        # 70% approval rate for prior auth
        if random.random() > 0.3:
            return {
                "authorization_number": auth_number,
                "status": "approved",
                "valid_until": (datetime.utcnow() + timedelta(days=30))
                .date()
                .isoformat(),
                "approved_procedures": procedure_codes,
                "conditions": ["Must be performed by network provider"],
                "estimated_coverage": random.uniform(70, 100),
            }
        else:
            return {
                "authorization_number": auth_number,
                "status": "denied",
                "denial_reason": random.choice(
                    [
                        "Medical necessity not established",
                        "Alternative treatment required first",
                        "Procedure not covered",
                        "Insufficient documentation",
                    ]
                ),
                "suggested_alternatives": [
                    "conservative_treatment",
                    "outpatient_option",
                ],
            }


# Global instance
mock_payer_service = MockPayerService()

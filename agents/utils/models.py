"""
RCM Agent data models and state management
"""

from pydantic import BaseModel, Field
from typing import TypedDict, Optional, List, Dict, Any
from enum import Enum
from langchain.schema.messages import BaseMessage


# --- Enums ---
class WorkflowStep(str, Enum):
    INITIALIZATION = "initialization"
    DATA_COLLECTION = "data_collection"
    DATA_STRUCTURING = "data_structuring"
    MEDICAL_CODING = "medical_coding"
    ELIGIBILITY_CHECKING = "eligibility_checking"
    CLAIM_PROCESSING = "claim_processing"
    COMPLETED = "completed"


class DecisionAction(str, Enum):
    ASK_USER = "ask_user"
    PROCEED = "proceed"
    FINALIZE = "finalize"
    ERROR = "error"
    RETRY = "retry"


class ConfidenceLevel(str, Enum):
    LOW = "low"  # < 0.7
    MEDIUM = "medium"  # 0.7 - 0.9
    HIGH = "high"  # > 0.9


# --- Data Models ---
class PatientData(BaseModel):
    patient_id: Optional[str] = None
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    insurance_provider: Optional[str] = None
    policy_number: Optional[str] = None
    mrn: Optional[str] = None


class EncounterData(BaseModel):
    encounter_type: Optional[str] = None
    service_date: Optional[str] = None
    chief_complaint: Optional[str] = None
    raw_clinical_notes: Optional[str] = None
    provider_name: Optional[str] = None
    location: Optional[str] = None


class StructuredClinicalData(BaseModel):
    patient_info: Optional[Dict[str, Any]] = None
    encounter_details: Optional[Dict[str, Any]] = None
    diagnoses: Optional[List[str]] = None
    procedures: Optional[List[str]] = None
    medications: Optional[List[str]] = None
    vital_signs: Optional[Dict[str, Any]] = None
    assessment_and_plan: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None


class MedicalCode(BaseModel):
    code: str
    description: str
    confidence: float
    rationale: str
    modifier: Optional[str] = None


class SuggestedCodes(BaseModel):
    icd10_codes: List[MedicalCode] = Field(default_factory=list)
    cpt_codes: List[MedicalCode] = Field(default_factory=list)
    overall_confidence: Optional[float] = None
    requires_human_review: bool = False


class EligibilityResult(BaseModel):
    eligible: bool
    payer_id: str
    coverage_details: Dict[str, Any] = Field(default_factory=dict)
    copay_amount: Optional[float] = None
    deductible_remaining: Optional[float] = None
    requires_prior_auth: bool = False
    confidence_score: Optional[float] = None
    verification_date: Optional[str] = None


class ClaimData(BaseModel):
    claim_number: Optional[str] = None
    total_amount: Optional[float] = None
    patient_responsibility: Optional[float] = None
    payer_id: Optional[str] = None
    diagnosis_codes: List[Dict[str, Any]] = Field(default_factory=list)
    procedure_codes: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "draft"
    submission_ready: bool = False


class UserAgentDecision(BaseModel):
    action: DecisionAction
    message: str
    next_step: Optional[WorkflowStep] = None
    confidence: Optional[float] = None


class DataStructuringDecision(BaseModel):
    action: DecisionAction
    structured_data: Optional[StructuredClinicalData] = None
    message: str
    confidence_score: Optional[float] = None


class CodingDecision(BaseModel):
    action: DecisionAction
    suggested_codes: Optional[SuggestedCodes] = None
    message: str
    requires_approval: bool = False


class EligibilityDecision(BaseModel):
    action: DecisionAction
    eligibility_result: Optional[EligibilityResult] = None
    message: str
    requires_verification: bool = False


class ClaimProcessingDecision(BaseModel):
    action: DecisionAction
    claim_data: Optional[ClaimData] = None
    message: str
    ready_for_submission: bool = False


# --- Main State ---
class RCMAgentState(TypedDict):
    # Core conversation
    messages: List[BaseMessage]

    # Data entities
    patient_data: Optional[PatientData]
    encounter_data: Optional[EncounterData]
    structured_data: Optional[StructuredClinicalData]
    suggested_codes: Optional[SuggestedCodes]
    eligibility_result: Optional[EligibilityResult]
    claim_data: Optional[ClaimData]

    # Workflow state
    status: str  # collecting | processing | reviewing | completed | error
    workflow_step: WorkflowStep
    question_to_ask: Optional[str]
    ready_for_processing: bool
    need_user_input: bool
    done: bool
    exit_requested: bool
    result: Optional[str]
    error_message: Optional[str]

    # AI confidence tracking
    confidence_scores: Dict[str, float]

    # User context
    user_context: Dict[str, Any]


# --- Validation Models ---
class RCMWorkflowInput(BaseModel):
    """Input for starting RCM workflow"""

    patient_id: Optional[str] = None
    raw_input: str = Field(..., min_length=1)
    encounter_type: Optional[str] = None
    payer_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class RCMWorkflowOutput(BaseModel):
    """Output from RCM workflow"""

    status: str
    workflow_step: WorkflowStep
    patient_data: Optional[PatientData] = None
    encounter_data: Optional[EncounterData] = None
    structured_data: Optional[StructuredClinicalData] = None
    suggested_codes: Optional[SuggestedCodes] = None
    eligibility_result: Optional[EligibilityResult] = None
    claim_data: Optional[ClaimData] = None
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    message: Optional[str] = None
    requires_human_review: bool = False

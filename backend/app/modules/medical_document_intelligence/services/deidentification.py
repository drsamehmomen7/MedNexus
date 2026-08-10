from __future__ import annotations

from typing import Any

from backend.app.core.base_service import BaseService
from backend.app.core.engine_manager import EngineManager

from backend.app.modules.medical_document_intelligence.intelligence.deterministic_identifier_detector import (
    DeterministicIdentifierDetector,
)
from backend.app.modules.medical_document_intelligence.intelligence.context_rule_candidate_adapter import (
    ContextRuleCandidateAdapter,
)
from backend.app.modules.medical_document_intelligence.intelligence.intelligence_orchestrator import (
    MedNexusIntelligenceOrchestrator,
)
from backend.app.modules.medical_document_intelligence.intelligence.output_builder import (
    MedNexusOutputBuilder,
)
from backend.app.modules.medical_document_intelligence.policies.clinical_context import (
    ClinicalContextProtector,
)
from backend.app.modules.medical_document_intelligence.policies.context_rules import (
    ContextRuleEngine,
)
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
    get_policy_definition,
)


class DeidentificationService(BaseService):
    """
    Business layer for MedNexus Medical Document De-identification.

    OpenMed is used only as an AI candidate-detection engine.

    MedNexus owns:

        - deterministic healthcare-context detection
        - clinical terminology protection
        - deterministic structured-identifier detection
        - external-engine candidate interpretation
        - role resolution
        - context validation
        - false-positive rejection
        - candidate merging
        - final output construction

    The final de-identified document is built by MedNexus and is not
    copied from the external engine's deidentified_text output.
    """

    def __init__(
        self,
        *,
        engine_manager: Any | None = None,
    ) -> None:
        """
        Initialize the de-identification service.

        Args:
            engine_manager:
                Optional engine-manager dependency.

                When omitted, the production EngineManager is created.

                Dependency injection is supported for isolated tests and
                future engine implementations.
        """

        if engine_manager is None:
            engine_manager = EngineManager()

        self.engine_manager = engine_manager

    def process(
        self,
        text: str,
        policy: PolicyProfile = PolicyProfile.MEDNEXUS_CLINICAL,
    ):
        """
        De-identify medical text through the MedNexus-controlled pipeline.

        Processing flow:

            Original text
                ↓
            Clinical vocabulary protection
                ↓
            Context rules + deterministic identifiers + OpenMed
                ↓
            Unified MedNexus Intelligence Core
                ↓
            Selected policy + MedNexus Output Builder
                ↓
            Restore protected clinical vocabulary
                ↓
            Final MedNexus-controlled output
        """

        if not isinstance(text, str):
            raise TypeError(
                "text must be a string."
            )

        if not text.strip():
            raise ValueError(
                "text cannot be empty."
            )

        if not isinstance(
            policy,
            PolicyProfile,
        ):
            raise TypeError(
                "policy must be an instance of PolicyProfile."
            )

        start = self.start_timer()

        # --------------------------------------------------
        # Step 1: Build the common exact-offset detection representation
        # --------------------------------------------------

        (
            detection_text,
            clinical_mapping,
        ) = ClinicalContextProtector.protect(
            text
        )

        # --------------------------------------------------
        # Step 2: Collect all candidate sources on one coordinate system
        # --------------------------------------------------

        context_entities = ContextRuleEngine.detect(
            detection_text
        )
        context_candidates = (
            ContextRuleCandidateAdapter.adapt_many(
                detections=context_entities,
                source_text=detection_text,
            )
        )

        deterministic_candidates = (
            DeterministicIdentifierDetector.detect(
                detection_text
            )
        )

        engine_result = (
            self.engine_manager.deidentify(
                detection_text
            )
        )

        # --------------------------------------------------
        # Step 3: One MedNexus intelligence-decision path
        # --------------------------------------------------
        #
        # OpenMed objects stop at this boundary.
        #
        # MedNexus now:
        #   - adapts OpenMed entities
        #   - canonicalizes labels
        #   - resolves clinical roles
        #   - validates context
        #   - rejects false positives
        #   - merges detections
        # --------------------------------------------------

        intelligence_result = (
            MedNexusIntelligenceOrchestrator
            .process_openmed_result(
                engine_result=engine_result,
                source_text=detection_text,
                context_candidates=context_candidates,
                mednexus_candidates=(
                    deterministic_candidates
                ),
            )
        )

        # --------------------------------------------------
        # Step 4: Apply the selected policy and build MedNexus output
        # --------------------------------------------------
        #
        # The OpenMed deidentified_text is deliberately not used.
        #
        # ACCEPT:
        #   transformed by MedNexus
        #
        # KEEP:
        #   original source value preserved
        #
        # REJECT:
        #   false-positive source value preserved
        #
        # REVIEW_REQUIRED / PENDING:
        #   source preserved and warning recorded
        # --------------------------------------------------

        mednexus_output = (
            MedNexusOutputBuilder.build(
                source_text=detection_text,
                candidates=(
                    intelligence_result.all_candidates
                ),
                profile=policy,
            )
        )

        # --------------------------------------------------
        # Step 5: Restore protected clinical terminology
        # --------------------------------------------------

        final_deidentified_text = (
            ClinicalContextProtector.restore(
                mednexus_output.text,
                clinical_mapping,
            )
        )

        elapsed = self.stop_timer(start)

        # Maintain compatibility with the current ProcessingResponse and
        # API contract while replacing the engine-owned output with the
        # MedNexus-controlled final document.
        engine_result.deidentified_text = (
            final_deidentified_text
        )

        requires_review = (
            not intelligence_result
            .is_safe_for_automatic_output
            or mednexus_output.requires_review
        )

        if requires_review:
            message = (
                "De-identification completed with "
                "MedNexus review warnings."
            )
        else:
            message = (
                "De-identification completed successfully "
                "by the MedNexus Intelligence Core."
            )

        return self.create_response(
            success=True,
            message=message,
            data=engine_result,
            context_entities=context_entities,
            processing_time=elapsed,
            engine_name=(
                self.engine_manager.get_engine_name()
            ),
            engine_version=(
                self.engine_manager.get_engine_version()
            ),
            module_name=(
                "medical_document_intelligence"
            ),
            metadata={
                # ------------------------------------------
                # Policy
                # ------------------------------------------
                "policy": policy.value,
                "policy_definition": get_policy_definition(policy).to_dict(),

                # ------------------------------------------
                # Unified detection representation and provenance
                # ------------------------------------------
                "detection_text": detection_text,
                "context_candidates": [
                    candidate.to_dict()
                    for candidate in context_candidates
                ],
                "deterministic_candidates": [
                    candidate.to_dict()
                    for candidate in deterministic_candidates
                ],
                "clinical_context_mapping": (
                    clinical_mapping
                ),

                # ------------------------------------------
                # MedNexus Intelligence metadata
                # ------------------------------------------
                "output_owner": "MedNexus",
                "external_engine_role": (
                    "candidate_detector"
                ),
                "privacy_decision_path": "unified",
                "intelligence_core_enabled": True,
                "intelligence_result": (
                    intelligence_result.to_dict()
                ),
                "mednexus_output": (
                    mednexus_output.to_dict()
                ),
                "requires_review": requires_review,
                "review_warnings": list(
                    mednexus_output.warnings
                ),

                # ------------------------------------------
                # Audit counts
                # ------------------------------------------
                "candidate_counts": {
                    "context": len(context_candidates),
                    "deterministic": len(
                        deterministic_candidates
                    ),
                    "total": (
                        intelligence_result.total_count
                    ),
                    "accepted": (
                        intelligence_result
                        .accepted_count
                    ),
                    "kept": (
                        intelligence_result.kept_count
                    ),
                    "rejected": (
                        intelligence_result
                        .rejected_count
                    ),
                    "review_required": (
                        intelligence_result
                        .review_required_count
                    ),
                    "pending": (
                        intelligence_result.pending_count
                    ),
                    "replaced": (
                        mednexus_output.replaced_count
                    ),
                },
            },
        )

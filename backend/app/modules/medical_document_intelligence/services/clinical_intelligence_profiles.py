"""Small, explicit Clinical Intelligence Profile registry; no free-form mining."""

from backend.app.modules.medical_document_intelligence.contracts.clinical_intelligence import (
    ClinicalInsightDefinition as Definition,
    ClinicalInsightReference as Reference,
    ClinicalInsightSupport as Support,
    ClinicalInsightVariable as Variable,
    ClinicalIntelligenceProfile as Profile,
    ClinicalIntelligenceProfileRegistry,
)


_US_REFERENCE = Reference(
    "ACR–AIUM–SPR–SRU",
    "Practice Parameter for the Performance of an Ultrasound Examination of the Abdomen and/or Retroperitoneum",
    "https://gravitas.acr.org/PPTS/GetDocumentView?docId=189&releaseId=2",
    "Revised 2021 (Resolution 32)",
    "VERIFIED",
    "Defines the abdominal ultrasound exam scope and documentation basis; it is not a clinical relationship reference.",
    role="EXAM_PROFILE_REFERENCE",
)
_MRI_REFERENCE = Reference(
    "ACR–SPR–SSR",
    "Practice Parameter for the Performance and Interpretation of Magnetic Resonance Imaging (MRI) of the Shoulder",
    "https://gravitas.acr.org/PPTS/GetDocumentView?docId=45",
    None,
    "TITLE_URL_VERIFIED_DATE_PENDING",
    "Defines the shoulder MRI exam scope and documentation basis; it is not a clinical relationship reference.",
    role="EXAM_PROFILE_REFERENCE",
)
_STEATOSIS_GALLSTONES_REFERENCE = Reference(
    "Chang et al.",
    "Bidirectional Association between Nonalcoholic Fatty Liver Disease and Gallstone Disease: A Cohort Study",
    "https://pubmed.ncbi.nlm.nih.gov/30469392/", "2018", "VERIFIED",
    "A primary ultrasound-based cohort study examined fatty liver and gallstone disease; it motivates asking the documentation question, without validating this Collection result.",
    role="CLINICAL_RELATIONSHIP_REFERENCE",
)
_CUFF_RETRACTION_REFERENCE = Reference(
    "Bierry and Palmer",
    "Patterns of tendon retraction in full-thickness rotator cuff tear: comparison of delaminated and nondelaminated tendons",
    "https://pubmed.ncbi.nlm.nih.gov/29982855/", "2019", "VERIFIED",
    "A primary MRI study examined tendon retraction in full-thickness cuff tears; it motivates documenting retraction separately from the tear.",
    role="CLINICAL_RELATIONSHIP_REFERENCE",
)
_CUFF_MUSCLE_REFERENCE = Reference(
    "Matsumura et al.",
    "Quantitative evaluation of natural progression of fatty infiltration and muscle atrophy in chronic rotator cuff tears without tear extension using magnetic resonance imaging",
    "https://pubmed.ncbi.nlm.nih.gov/38707576/", "2024", "VERIFIED",
    "A primary MRI study evaluated cuff tears with muscle fat and atrophy; it motivates a separate muscle-degeneration question.",
    role="CLINICAL_RELATIONSHIP_REFERENCE",
)
_COMPARE = Support("MRJ_INSIGHT_SUPPORT_V0_1", 6, 2, 2)
_CONTEXT = Support("MRJ_INSIGHT_SUPPORT_V0_1", 3, 1, 2)
_QUALITY = Support("MRJ_INSIGHT_SUPPORT_V0_1", 5, 1, 0)
_US_SCOPES = ("COMPLETE", "LIMITED_OR_FOCUSED")
_MRI_SCOPES = ("ROUTINE_MRI", "MR_ARTHROGRAM", "UNKNOWN")

HEPATOMEGALY = Variable("HEPATOMEGALY", ("hepatomegaly", "hepatic enlargement", "enlarged liver"))
ASCITES = Variable("ASCITES", ("ascites",))
STEATOSIS = Variable("HEPATIC_STEATOSIS", ("hepatic steatosis", "steatosis", "fatty liver"))
GALLSTONES = Variable("GALLSTONES", ("gallstones", "gallstone", "cholelithiasis"))
RENAL_CALCULUS = Variable("RENAL_CALCULUS", ("renal calculus", "renal calculi", "nephrolithiasis", "kidney stone"), ("kidney", "renal"), True)
HYDRONEPHROSIS = Variable("HYDRONEPHROSIS", ("hydronephrosis",), ("kidney", "renal"), True)
PANCREAS = Variable("PANCREAS_VISUALIZATION", ("pancreas", "pancreatic"))
LABRAL_TEAR = Variable("LABRAL_TEAR", ("labral tear", "labrum tear"), ("labrum", "labral"))
HILL_SACHS = Variable("HILL_SACHS", ("hill sachs", "hill-sachs"))
BANKART = Variable("BANKART_GLENOID_INJURY", ("bankart", "glenoid fracture", "glenoid bone loss"))
CUFF_TEAR = Variable("ROTATOR_CUFF_TEAR", ("rotator cuff tear", "supraspinatus tear", "infraspinatus tear", "subscapularis tear", "teres minor tear"))
RETRACTION = Variable("TENDON_RETRACTION", ("tendon retraction", "cuff retraction", "supraspinatus retraction", "retraction"), ("tendon", "cuff", "supraspinatus", "infraspinatus", "subscapularis", "teres minor"))
MUSCLE_DEGENERATION = Variable("CUFF_MUSCLE_DEGENERATION", ("muscle atrophy", "fatty degeneration", "fatty infiltration", "supraspinatus atrophy", "infraspinatus atrophy"), ("muscle", "supraspinatus", "infraspinatus", "subscapularis", "teres minor"))

US_ABDOMEN_INTELLIGENCE = Profile(
    "MRJ_INTEL_US_ABDOMEN", "0.1", "MRJ_RAD_US_ABDOMEN", ("0.1",), "ACTIVE", (
        Definition("US_HEPATOMEGALY_ASCITES", "0.1", "Hepatomegaly + ascites",
                   "Is ascites documented differently in eligible US Abdomen reports with versus explicitly without hepatomegaly?",
                   "CO_DOCUMENTATION", "Predefined liver/peritoneal documentation comparison.",
                   HEPATOMEGALY, ASCITES, None, _US_SCOPES, True, False, _COMPARE, _US_REFERENCE),
        Definition("US_STEATOSIS_GALLSTONES", "0.1", "Hepatic steatosis + gallstones",
                   "Are gallstones documented differently in eligible reports with versus explicitly without hepatic steatosis?",
                   "CO_DOCUMENTATION", "Predefined liver/gallbladder documentation comparison.",
                   STEATOSIS, GALLSTONES, None, _US_SCOPES, True, False, _COMPARE, _US_REFERENCE,
                   clinical_relationship_reference=_STEATOSIS_GALLSTONES_REFERENCE,
                   relationship_reference_status="VERIFIED"),
        Definition("US_RENAL_CALCULUS_HYDRONEPHROSIS", "0.1", "Renal calculus + hydronephrosis",
                   "Among eligible reports with a renal calculus, how often is same-side hydronephrosis documented?",
                   "FINDING_CONTEXT", "Predefined same-side renal documentation question.",
                   RENAL_CALCULUS, HYDRONEPHROSIS, None, _US_SCOPES, False, True, _CONTEXT, _US_REFERENCE),
        Definition("US_PANCREAS_VISUALIZATION", "0.1", "Pancreas visualization",
                   "How often was the pancreas documented versus limited or not visualized in applicable reviewed reports?",
                   "COVERAGE_QUALITY", "Predefined ultrasound completeness question.",
                   None, PANCREAS, "pancreas.visualization", _US_SCOPES, False, False, _QUALITY, _US_REFERENCE),
    ),
)

MRI_SHOULDER_INTELLIGENCE = Profile(
    "MRJ_INTEL_MRI_SHOULDER", "0.1", "MRJ_RAD_MRI_SHOULDER", ("0.1",), "ACTIVE", (
        Definition("MRI_LABRAL_TEAR_HILL_SACHS", "0.1", "Labral tear + Hill-Sachs lesion",
                   "Among eligible MRI Shoulder reports with a labral tear, how often is a Hill-Sachs lesion documented?",
                   "FINDING_CONTEXT", "Predefined labral/osseous documentation question.",
                   LABRAL_TEAR, HILL_SACHS, None, _MRI_SCOPES, False, False, _CONTEXT, _MRI_REFERENCE),
        Definition("MRI_BANKART_HILL_SACHS", "0.1", "Bankart or glenoid injury + Hill-Sachs lesion",
                   "Among eligible reports with a Bankart or glenoid injury, how often is a Hill-Sachs lesion documented?",
                   "FINDING_CONTEXT", "Predefined glenoid/osseous documentation question; generic labral tears do not imply Bankart.",
                   BANKART, HILL_SACHS, None, _MRI_SCOPES, False, False, _CONTEXT, _MRI_REFERENCE),
        Definition("MRI_CUFF_TEAR_RETRACTION", "0.1", "Rotator cuff tear + tendon retraction",
                   "Among eligible reports with a rotator cuff tear, how often is tendon retraction documented?",
                   "FINDING_CONTEXT", "Predefined cuff morphology question.",
                   CUFF_TEAR, RETRACTION, None, _MRI_SCOPES, False, False, _CONTEXT, _MRI_REFERENCE,
                   clinical_relationship_reference=_CUFF_RETRACTION_REFERENCE,
                   relationship_reference_status="VERIFIED"),
        Definition("MRI_CUFF_TEAR_MUSCLE", "0.1", "Rotator cuff tear + muscle degeneration",
                   "Among eligible reports with a rotator cuff tear, how often is cuff-muscle atrophy or fatty degeneration documented?",
                   "FINDING_CONTEXT", "Predefined cuff/muscle documentation question.",
                   CUFF_TEAR, MUSCLE_DEGENERATION, None, _MRI_SCOPES, False, False, _CONTEXT, _MRI_REFERENCE,
                   clinical_relationship_reference=_CUFF_MUSCLE_REFERENCE,
                   relationship_reference_status="VERIFIED"),
    ),
)

REGISTRY = ClinicalIntelligenceProfileRegistry(
    (US_ABDOMEN_INTELLIGENCE, MRI_SHOULDER_INTELLIGENCE),
    {US_ABDOMEN_INTELLIGENCE.intelligence_profile_id: "0.1",
     MRI_SHOULDER_INTELLIGENCE.intelligence_profile_id: "0.1"},
)

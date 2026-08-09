from typing import Dict, Set


PROTECTED_TERMS: Dict[str, Set[str]] = {

    "gross_description": {

        "white",
        "pink",
        "brown",
        "yellow",
        "firm",
        "soft",
        "friable",
        "necrosis",
        "necrotic",
        "capsule",
        "capsular",
        "fibrotic",
        "calcified",
        "calcification",
        "margin",
        "margins",
        "lymphovascular",
        "specimen",
        "tissue",

    },

    "microscopic_description": {

        "ductal",
        "carcinoma",
        "grade",
        "margins",
        "lymphovascular",
        "invasion",
        "positive",
        "negative",
        "cells",

    },

    "diagnosis": {

        "carcinoma",
        "adenocarcinoma",
        "sarcoma",
        "lymphoma",
        "metastatic",
        "positive",
        "negative",
        "er",
        "pr",
        "her2",
        "ki67",

    }

}
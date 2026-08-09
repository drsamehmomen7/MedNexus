from enum import Enum


class PolicyAction(str, Enum):

    KEEP = "keep"

    REPLACE = "replace"

    HASH = "hash"

    MASK = "mask"

    GENERALIZE = "generalize"

    SHIFT_DATE = "shift_date"

    REMOVE = "remove"
from backend.app.engines.openmed.engine import deidentify_text

sample_text = """
Patient John Smith
MRN: 123456
Date of Birth: 15/02/1985
Phone: +965 99999999
"""

result = deidentify_text(sample_text)

print("Original:")
print(result.original_text)

print("\nDe-identified:")
print(result.deidentified_text)
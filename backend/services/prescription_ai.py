
import json


PRESCRIPTION_PROMPT = """
You are a prescription-document extraction assistant.

Read the attached doctor's prescription image.

The handwriting may be unclear.

Extract only information supported by the image.

Return a JSON object with:

{
  "candidate_medicines": [
    {
      "original_text": "",
      "candidate_name": "",
      "strength": null,
      "dosage_form": null,
      "written_directions": null,
      "confidence": null
    }
  ],
  "uncertain_fields": [],
  "requires_pharmacist_review": true,
  "review_reasons": []
}

Rules:

1. Do not invent medicine names.
2. Do not guess missing strengths or dosage instructions.
3. Preserve the original handwritten text when possible.
4. If a medicine name is unclear, return multiple possible
   readings only when supported by the image.
5. Use null for missing information.
6. Mark uncertain medicine names and strengths.
7. Never recommend a medicine or prescribe a dose.
8. Do not determine legal prescription validity.
9. Return JSON only.
"""


def read_prescription(image_path: str):

    # TODO:
    # 1. Load the prescription image.
    # 2. Send it to your selected vision-capable model.
    # 3. Pass PRESCRIPTION_PROMPT.
    # 4. Parse the model response as JSON.
    # 5. Validate the output using a Pydantic schema.
    # 6. Store the extraction result for pharmacist review.

    raise NotImplementedError(
        "Connect your selected vision model here"
    )

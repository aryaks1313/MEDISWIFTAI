import os

from crewai import Agent, Crew, Process, Task


def analyze_prescription_text(
    extracted_text: str,
    catalogue: list[dict],
    preference: str,
) -> dict:
    """
    Analyze OCR text and medicine catalogue candidates.

    This is an AI-assisted draft only. A pharmacist must review
    the prescription and candidate medicines before dispensing.
    """

    if not extracted_text.strip():
        return {
            "extracted_text": "",
            "candidates": [],
            "review_required": True,
            "message": "No readable prescription text was extracted.",
        }

    # CrewAI needs an LLM provider/API key configured in the environment.
    if not os.getenv("OPENAI_API_KEY"):
        return {
            "extracted_text": extracted_text,
            "candidates": catalogue,
            "review_required": True,
            "message": (
                "AI analysis was not run because OPENAI_API_KEY is missing. "
                "Catalogue candidates are provided for pharmacist review."
            ),
        }

    analyst = Agent(
        role="Prescription Information Analyst",
        goal=(
            "Extract medicine names and written details from OCR text. "
            "Mark uncertain or unreadable details clearly."
        ),
        backstory=(
            "You assist licensed pharmacists. You do not diagnose, "
            "approve prescriptions, or change medication instructions."
        ),
        verbose=False,
        allow_delegation=False,
    )

    matcher = Agent(
        role="Medicine Catalogue Matching Assistant",
        goal=(
            "Compare extracted medicine names against the supplied catalogue. "
            "Return possible catalogue matches and explain uncertainty. "
            "Do not decide clinical equivalence or approve substitutions."
        ),
        backstory=(
            "You support catalogue lookup for pharmacist review. "
            "Brand and generic similarity alone do not establish suitability."
        ),
        verbose=False,
        allow_delegation=False,
    )

    task = Task(
        description=f"""
Review the prescription OCR text below.

OCR TEXT:
{extracted_text}

AVAILABLE CATALOGUE:
{catalogue}

CUSTOMER PREFERENCE:
{preference}

Return a concise draft with:
- extracted medicine name(s)
- readable strength/form/instructions, or mark them unclear
- possible catalogue matches from the supplied catalogue only
- uncertainty flags
- a reminder that pharmacist review is required

Do not invent missing prescription details.
Do not suggest a dosage change.
Do not authorize a medicine substitution.
Do not state that the prescription is approved.
""",
        expected_output=(
            "A clear text draft of extracted details, candidate catalogue "
            "matches, uncertainty flags, and pharmacist review reminder."
        ),
        agent=analyst,
    )

    matching_task = Task(
        description=(
            "Review the previous draft and catalogue. Keep only candidates "
            "that are present in the supplied catalogue. Flag uncertainty. "
            "Do not make a clinical substitution decision."
        ),
        expected_output=(
            "A pharmacist-facing draft containing the extraction, candidates, "
            "and review warnings."
        ),
        agent=matcher,
        context=[task],
    )

    crew = Crew(
        agents=[analyst, matcher],
        tasks=[task, matching_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()

    return {
        "extracted_text": extracted_text,
        "candidates": catalogue,
        "ai_draft": str(result),
        "review_required": True,
        "message": "AI draft created. Pharmacist review is mandatory.",
    }
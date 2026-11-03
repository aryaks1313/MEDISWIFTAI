
from crewai import Agent, Task, Crew, Process


def create_prescription_workflow():

    prescription_agent = Agent(
        role="Prescription Information Analyst",

        goal=(
            "Identify uncertain fields in extracted "
            "prescription information"
        ),

        backstory=(
            "You organize prescription text for review. "
            "You do not prescribe medicine, invent missing "
            "details, or approve prescriptions."
        ),

        verbose=True
    )

    matching_agent = Agent(
        role="Medicine Catalogue Matching Assistant",

        goal=(
            "Find candidate catalogue matches for "
            "customer-confirmed medicine information"
        ),

        backstory=(
            "You compare medicine names and identify "
            "potential brand and generic matches. "
            "You cannot authorize substitutions."
        ),

        verbose=True
    )

    review_task = Task(
        description="""
        Analyze the following extracted prescription text:

        {prescription_text}

        Identify:
        - Candidate medicine names
        - Uncertain fields
        - Missing strength or dosage form
        - Whether pharmacist review is needed

        Never guess missing information.
        """,

        expected_output=(
            "A structured summary of candidate medicine "
            "names, uncertain fields, and review requirements."
        ),

        agent=prescription_agent
    )

    matching_task = Task(
        description="""
        Using the confirmed prescription information:

        {confirmed_medicine}

        Compare the following catalogue candidates:

        {catalogue_candidates}

        Identify possible matching products.

        Do not approve substitutions or determine "
        "prescription validity.
        """,

        expected_output=(
            "A list of candidate products with match "
            "reasons and unresolved questions."
        ),

        agent=matching_agent,

        context=[review_task]
    )

    crew = Crew(
        agents=[
            prescription_agent,
            matching_agent
        ],

        tasks=[
            review_task,
            matching_task
        ],

        process=Process.sequential,

        verbose=True
    )

    return crew

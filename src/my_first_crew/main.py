from my_first_crew.crew import CompetitorResearchCrew
from typing import List


def run(companies: List[str]) -> None:
    """Run the Competitor Research Crew for a list of companies."""
    for company_name in companies:
        inputs = {"company": company_name}
        CompetitorResearchCrew().crew().kickoff(inputs=inputs)
    


if __name__ == "__main__":
    companies = ["OpenAI"]
    run(companies)

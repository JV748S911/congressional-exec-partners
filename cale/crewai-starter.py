from crewai import Agent, Task, Crew
from crewai_tools import tool
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(model="grok-4-1-fast", api_key=os.getenv("XAI_API_KEY"))

@tool("PublicDataScraper")
def scrape_triggers(query: str) -> str:
    """Mock public data scrape for DC triggers."""
    return "Exec X new lobby role (FEC); Y term end (Congress.gov); Z property transfer Kalorama."

# Agents
discovery = Agent(
    role="Discovery Agent",
    goal="Find high-propensity DMV luxury leads from public gov/exec data.",
    backstory="You scan FEC, Congress, records for move triggers.",
    llm=llm,
    tools=[scrape_triggers],
    verbose=True
)

scorer = Agent(
    role="Scoring Agent",
    goal="Score leads 0-1 on move propensity.",
    backstory="Expert in exec churn/politics impact.",
    llm=llm,
    verbose=True
)

personalizer = Agent(
    role="Personalization Agent",
    goal="Craft compliant, hyper-personal emails.",
    backstory="Writes white-glove messages from public data only.",
    llm=llm,
    verbose=True
)

# Tasks
task1 = Task(
    description="Scan today's triggers for DC/MD/VA luxury prospects.",
    agent=discovery
)

task2 = Task(
    description="Score {task1.output} leads.",
    agent=scorer,
    context=[task1]
)

task3 = Task(
    description="Personalize top 3 leads from {task2.output}.",
    agent=personalizer,
    context=[task2]
)

crew = Crew(agents=[discovery, scorer, personalizer], tasks=[task1, task2, task3])

if __name__ == "__main__":
    result = crew.kickoff()
    print(result)

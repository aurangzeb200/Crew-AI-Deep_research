from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from my_first_crew.tools.custom_tool import FlexibleSerperDevTool
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os
from my_first_crew.tools.custom_tool import CrawlWebsiteTool
from dotenv import load_dotenv
from my_first_crew.custom_llm import Gemini

load_dotenv()

gemini_llm = Gemini(
    model=os.getenv("MODEL"),
    api_key=os.getenv("GEMINI_API_KEY", ""),
    temperature=0.5,
)


@CrewBase
class CompetitorResearchCrew():
  """Competitor Research Crew using CrewAI, Gemini, and Custom Tools"""

  agents: List[BaseAgent]
  tasks: List[Task]

  @before_kickoff
  def before_kickoff_function(self, inputs):
    print(f"🚀 Starting Crew with inputs: {inputs}")
    return inputs

  @after_kickoff
  def after_kickoff_function(self, result):
    print(f"✅ Crew completed with result:\n{result}")
    return result

  # Crawler Agent
  @agent
  def crawler_agent(self) -> Agent:
    return Agent(
      config=self.agents_config['crawler_agent'],  # YAML-based config
      verbose=True,
      tools=[CrawlWebsiteTool(),FlexibleSerperDevTool()],
      llm=gemini_llm  
    )

  # News Agent
  @agent
  def news_agent(self) -> Agent:
    return Agent(
      config=self.agents_config['news_agent'],
      verbose=True,
      tools = [FlexibleSerperDevTool()],
      llm=gemini_llm
    )

  # Summarizer Agent
  @agent
  def summarizer_agent(self) -> Agent:
    return Agent(
      config=self.agents_config['summarizer_agent'],
      verbose=True,
      llm=gemini_llm
    )

  # Crawl Task
  @task
  def crawl_task(self) -> Task:
    return Task(
      config=self.tasks_config['crawl_task']
    )

  # News Task
  @task
  def news_task(self) -> Task:
    return Task(
      config=self.tasks_config['news_task']
    )

  # Summary Task
  @task
  def summary_task(self) -> Task:
    return Task(
      config=self.tasks_config['summary_task'],
      context=[self.crawl_task(), self.news_task()],  
      output_file='output/{company}_analysis.md'
    )

  # Crew definition
  @crew
  def crew(self) -> Crew:
    """Creates the Competitor Research Crew"""
    return Crew(
      agents=self.agents,
      tasks=self.tasks,
      process=Process.sequential, 
      verbose=True,
    )

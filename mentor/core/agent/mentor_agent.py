from crewai import Agent

def create_mentor_agent(llm, role, goal, backstory):
    """
    Factory function to create a mentor AI Agent instance with
    given parameters and no additional tools (or add if you want).
    """
    return Agent(
        name="Mentor AI Agent",
        role=role,
        goal=goal,
        backstory=backstory,
        description="An AI mentor that guides learners based on provided topics.",
        tools=[],  # add tools here if needed later
        llm=llm,
        provider="google",
        max_tokens=1000,
        temperature=0.7,
    )

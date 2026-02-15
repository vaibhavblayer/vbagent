"""Example usage of solution orchestrator."""

from vbagent import create_solution_orchestrator

# Create orchestrator
orchestrator = create_solution_orchestrator()

# Generate solution with orchestration
result = orchestrator.generate_solution(
    image_path="solution_image.png",
    problem_context="Mechanics problem on friction",
    question_type="subjective",
    verbose=True,
)

print("\n=== Generated Solution ===")
print(result.latex)

print("\n=== Metadata ===")
print(f"Structure: {result.plan.structure}")
print(f"Steps: {result.plan.steps}")
print(f"Agents used: {[o.agent for o in result.agent_outputs]}")
print(f"Successful: {result.metadata['successful_agents']}/{len(result.agent_outputs)}")

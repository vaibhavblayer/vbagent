"""Example usage of the FBD agent."""

from vbagent import generate_fbd

# Example 1: Generate from description
print("Example 1: From description")
print("-" * 50)

description = """
A block of mass m rests on an inclined plane at angle θ = 30°.
There is friction between the block and the plane.
Show all forces acting on the block.
"""

# Note: This would call the actual API if OPENAI_API_KEY is set
# fbd_code = generate_fbd(description=description)
# print(fbd_code)

print("Would generate FBD with:")
print("- Coordinate system (x along plane, y perpendicular)")
print("- Weight mg pointing downward")
print("- Normal force N perpendicular to plane")
print("- Friction force f along plane (opposing motion)")
print("- Angle θ marked")

# Example 2: Generate from problem text
print("\n\nExample 2: From LaTeX problem")
print("-" * 50)

problem_latex = r"""
\item A block of mass $m = 5$ kg is suspended by two strings making angles 
$\theta_1 = 30°$ and $\theta_2 = 45°$ with the horizontal. Find the tension 
in each string.
"""

# fbd_code = generate_fbd(problem_text=problem_latex)

print("Would generate FBD with:")
print("- Point mass at center")
print("- Weight mg downward")
print("- Tension T₁ at angle θ₁")
print("- Tension T₂ at angle θ₂")
print("- Coordinate system")

# Example 3: With reference context
print("\n\nExample 3: With reference examples")
print("-" * 50)

# If you have FBD examples in a directory:
# fbd_code = generate_fbd(
#     description="Pulley system with two masses",
#     use_context=True,
#     classification=classification_result  # From classify()
# )

print("Would search reference store for similar FBD examples")
print("and use them as style guides")

print("\n✅ FBD Agent is ready for use!")
print("\nTo use with actual API:")
print("1. Set OPENAI_API_KEY environment variable")
print("2. Call generate_fbd() with your description/image/problem")
print("3. Optionally compile with compile_latex() to validate")

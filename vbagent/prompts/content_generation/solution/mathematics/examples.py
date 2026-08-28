"""Complete mathematical examples with restrained specialist diagram specs."""

import json

LOG_DOMAIN_RANGE_EXAMPLE = {
    "solution_latex": r"""\begin{solution}
\begin{align*}
\intertext{Complete the square to find the logarithm's possible arguments and check their positivity.}
3x^2-4x+5 &= 3\left(x-\dfrac{2}{3}\right)^2+\dfrac{11}{3}
\intertext{The square attains every nonnegative value, so the argument ranges over $\left[\dfrac{11}{3},\infty\right)$ and is always positive.}
\operatorname{Domain}(y) &= \mathbb{R}
\intertext{The logarithm is continuous and strictly increasing, so it maps this entire interval to}
\operatorname{Range}(y) &= \left[\ln\left(\dfrac{11}{3}\right),\infty\right).
\end{align*}
% DIAGRAM PLACEHOLDER: graph_main
\end{solution}""",
    "diagram_requirements": [
        {
            "diagram_id": "graph_main",
            "diagram_type": "function_graph",
            "description": "Show the attained minimum and the curve rising on both sides.",
            "context": "Plot y=ln(3x^2-4x+5) for real x. Its minimum is (2/3, ln(11/3)); it tends to infinity as |x| tends to infinity.",
            "values": {
                "function": "ln(3*x^2-4*x+5)",
                "minimum_x": "2/3",
                "minimum_y": "ln(11/3)",
            },
            "labels": [],
            "annotations": [
                "Mark the minimum with a filled point; identify its exact coordinates using axis ticks."
            ],
            "mathematics_context": {
                "show_grid": "no",
                "axis_range": "x: [-2, 10/3], y: [0, 4]",
                "show_asymptotes": "no",
                "domain": "all real numbers",
                "range": "[ln(11/3), infinity)",
            },
        }
    ],
    "answer_type": "subjective",
    "answer_value": None,
    "final_answer_latex": r"Domain: $\mathbb{R}$; range: $\left[\ln\left(\dfrac{11}{3}\right),\infty\right)$.",
    "alternate_solution_recommended": False,
    "alternate_solution_hint": None,
}

LOG_DOMAIN_RANGE_EXAMPLE_JSON = json.dumps(LOG_DOMAIN_RANGE_EXAMPLE, indent=2)

FACTORING_EXAMPLE_JSON = json.dumps(
    {
        "solution_latex": r"""\begin{solution}
\begin{align*}
\intertext{Factor the quadratic to apply the zero-product property.}
(x-2)(x-3) &= 0 \\
x &\in \{2,3\}.
\end{align*}
\end{solution}""",
        "diagram_requirements": [],
        "answer_type": "subjective",
        "answer_value": None,
        "final_answer_latex": r"$x\in\{2,3\}$.",
        "alternate_solution_recommended": False,
        "alternate_solution_hint": None,
    },
    indent=2,
)

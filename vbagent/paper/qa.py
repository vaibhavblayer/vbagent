"""QAPipeline — thin wrapper over existing quality agents."""

from __future__ import annotations

from .models import QACheckResult, QAResult


class QAPipeline:
    """Chains existing quality agents: format → clarity → grammar."""

    def __init__(self, config=None, console=None):
        self.config = config
        self.console = console

    def run(self, problem_tex: str, solution_tex: str = "") -> QAResult:
        checks: list[QACheckResult] = []
        combined = problem_tex + ("\n\n" + solution_tex if solution_tex else "")

        # Format check
        checks.append(self._run_checker("format", combined))
        # Clarity check
        checks.append(self._run_checker("clarity", combined))
        # Grammar check
        checks.append(self._run_checker("grammar", combined))

        all_passed = all(c.passed for c in checks)

        # Auto-fix if any failed
        fixed_tex = None
        if not all_passed:
            fixable = [issue for c in checks if not c.passed for issue in c.issues]
            if fixable:
                fixed_tex = self._try_auto_fix(combined, fixable)
                if fixed_tex:
                    for c in checks:
                        if not c.passed:
                            c.auto_fixed = True

        return QAResult(passed=all_passed, checks=checks, fixed_tex=fixed_tex)

    def _run_checker(self, checker_name: str, tex: str) -> QACheckResult:
        try:
            if checker_name == "format":
                from vbagent.agents.quality.format_checker import check_format
                result = check_format(tex)
            elif checker_name == "clarity":
                from vbagent.agents.quality.clarity_checker import check_clarity
                result = check_clarity(tex)
            elif checker_name == "grammar":
                from vbagent.agents.quality.grammar_checker import check_grammar
                result = check_grammar(tex)
            else:
                return QACheckResult(checker=checker_name, passed=True)

            passed = getattr(result, "passed", True)
            issues = getattr(result, "issues", []) or []
            return QACheckResult(checker=checker_name, passed=passed, issues=issues)
        except Exception as e:
            return QACheckResult(checker=checker_name, passed=False, issues=[str(e)])

    def _try_auto_fix(self, tex: str, issues: list[str]) -> str | None:
        try:
            from vbagent.agents.quality.latex_fixer import fix_latex
            return fix_latex(tex, issues)
        except Exception:
            return None

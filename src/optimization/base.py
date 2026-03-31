from abc import ABC, abstractmethod
from src.schemas.core import StructuredProblem, SolverResult


class BaseSolver(ABC):
    """
    Abstract contract every solver backend must satisfy.
    Enforces a standardised solve() entry-point and output schema.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique solver identifier (matches SolverStrategy names)."""

    @abstractmethod
    def solve(self, problem: StructuredProblem) -> SolverResult:
        """
        Execute the solver against the problem and return a *complete*
        SolverResult. Must never raise an unhandled exception; instead,
        return a result with status='failed' and diagnostics populated.
        """

"""
pawpal_system.py — PawPal+ logic layer

All backend classes live here. The Streamlit UI (app.py) imports from this module.
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes — plain value objects with no behaviour
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """Represents the pet being cared for."""
    name: str
    species: str                          # e.g. "dog", "cat", "rabbit"
    special_needs: list[str] = field(default_factory=list)  # e.g. ["diabetes", "senior"]


@dataclass
class Task:
    """A single care activity that can appear in a daily plan."""
    title: str
    duration_minutes: int
    priority: str                         # "low" | "medium" | "high"
    fixed_time: Optional[str] = None      # e.g. "08:00" — None means flexible


@dataclass
class Owner:
    """The pet owner, including how much time they have today."""
    name: str
    available_minutes: int = 120          # total time budget for the day


@dataclass
class ScheduledTask:
    """A Task that has been placed into the plan with a start time."""
    task: Task
    start_time: str                       # e.g. "08:00"
    reason: str                           # plain-language explanation of why it was scheduled


@dataclass
class DailyPlan:
    """The output of the Scheduler — an ordered list of scheduled tasks."""
    pet: Pet
    owner: Owner
    scheduled_tasks: list[ScheduledTask] = field(default_factory=list)
    unscheduled_tasks: list[Task] = field(default_factory=list)  # didn't fit in the time budget

    def summary(self) -> str:
        """Return a human-readable summary of the plan."""
        pass


# ---------------------------------------------------------------------------
# Scheduler — the core logic class
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Builds a DailyPlan for a given owner and pet from a list of tasks.

    Scheduling strategy (to be implemented):
    - Fixed-time tasks are placed first.
    - Remaining tasks are sorted by priority (high → medium → low).
    - Tasks are added in order until the owner's time budget is exhausted.
    """

    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

    def __init__(self, owner: Owner, pet: Pet, tasks: list[Task]):
        self.owner = owner
        self.pet = pet
        self.tasks = tasks

    def build_plan(self) -> DailyPlan:
        """
        Generate and return a DailyPlan.

        Steps:
        1. Separate fixed-time tasks from flexible tasks.
        2. Sort flexible tasks by priority.
        3. Greedily schedule tasks until the time budget runs out.
        4. Attach a plain-language reason to each scheduled task.
        5. Return a DailyPlan with scheduled and unscheduled tasks.
        """
        pass

    def _sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted high → medium → low."""
        pass

    def _make_reason(self, task: Task, rank: int) -> str:
        """Produce a short explanation of why this task was included."""
        pass

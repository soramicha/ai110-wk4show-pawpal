"""
pawpal_system.py — PawPal+ logic layer

All backend classes live here. The Streamlit UI (app.py) imports from this module.

Architecture:
  Task       — a single care activity owned by a Pet
  Pet        — holds pet details and a list of Tasks
  Owner      — manages multiple Pets; exposes all tasks in one call
  Scheduler  — the "brain"; asks Owner for tasks, builds a DailyPlan
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from itertools import combinations
from typing import Optional


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """
    A single care activity.

    Attributes:
        title             — short description, e.g. "Morning walk"
        duration_minutes  — how long the task takes
        priority          — HIGH / MEDIUM / LOW
        fixed_time        — HH:MM string if the task must start at a specific time;
                            None means the Scheduler can place it anywhere
        completed         — True once the owner marks it done for the day
        frequency         — None (one-off), "daily", or "weekly".
                            When mark_complete() is called, next_due is set
                            automatically using timedelta.
        next_due          — the date this task should next appear in the schedule.
                            Set automatically by mark_complete(); None until first completion.
    """
    title: str
    duration_minutes: int
    priority: Priority
    fixed_time: Optional[str] = None
    completed: bool = False
    frequency: Optional[str] = None   # None | "daily" | "weekly"
    next_due: Optional[date] = None   # auto-set by mark_complete()

    _FREQ_DELTA: dict = field(default_factory=lambda: {
        "daily":  timedelta(days=1),
        "weekly": timedelta(weeks=1),
    }, init=False, repr=False, compare=False)

    def mark_complete(self, today: Optional[date] = None) -> None:
        """
        Mark this task done and, for recurring tasks, schedule the next occurrence.

        Uses timedelta to calculate next_due:
          daily  → today + 1 day
          weekly → today + 7 days
        """
        self.completed = True
        if self.frequency is not None:
            ref = today or date.today()
            delta = self._FREQ_DELTA.get(self.frequency)
            if delta:
                self.next_due = ref + delta

    def reset(self) -> None:
        """Clear completion status so the task appears pending again."""
        self.completed = False


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """
    Stores a pet's details and the list of care tasks that belong to it.

    Attributes:
        name          — the pet's name
        species       — e.g. "dog", "cat", "rabbit"
        special_needs — free-text tags, e.g. ["diabetes", "senior"]
        tasks         — all care tasks registered for this pet
    """
    name: str
    species: str
    special_needs: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, title: str) -> bool:
        """
        Remove the first task whose title matches.
        Returns True if a task was removed, False if none matched.
        """
        for i, t in enumerate(self.tasks):
            if t.title == title:
                self.tasks.pop(i)
                return True
        return False

    def pending_tasks(self) -> list[Task]:
        """Return only tasks that have not been marked complete."""
        return [t for t in self.tasks if not t.completed]

    def filter_tasks(
        self,
        priority: Optional[Priority] = None,
        completed: Optional[bool] = None,
    ) -> list[Task]:
        """
        Return tasks matching the given filters.                        (improvement 2)

        Args:
            priority   — if set, only return tasks with this priority level
            completed  — if True/False, filter by completion status;
                         if None, return tasks regardless of status
        """
        result = self.tasks
        if priority is not None:
            result = [t for t in result if t.priority == priority]
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        return result

    def get_task(self, title: str) -> Optional[Task]:
        """Return the first task whose title matches, or None."""
        return next((t for t in self.tasks if t.title == title), None)


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """
    Manages one or more pets and provides the Scheduler with a unified
    view of all tasks across those pets.

    Attributes:
        name               — owner's name
        available_minutes  — total time budget for the day (across all pets)
        day_start          — HH:MM when the scheduling window opens
        pets               — the pets this owner is responsible for
    """
    name: str
    available_minutes: int = 120
    day_start: str = "08:00"
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner."""
        self.pets.append(pet)

    def remove_pet(self, name: str) -> bool:
        """Remove the first pet whose name matches. Returns True on success."""
        for i, p in enumerate(self.pets):
            if p.name == name:
                self.pets.pop(i)
                return True
        return False

    def get_all_tasks(self) -> list[tuple["Pet", Task]]:
        """
        Return every (pet, task) pair across all registered pets.
        This is the primary interface the Scheduler uses to retrieve tasks.
        """
        return [(pet, task) for pet in self.pets for task in pet.tasks]

    def get_pending_tasks(self) -> list[tuple["Pet", Task]]:
        """Return only incomplete (pet, task) pairs — useful for daily scheduling."""
        return [(pet, task) for pet in self.pets for task in pet.pending_tasks()]

    def reset_day(self, today: Optional[date] = None) -> int:
        """
        Reset recurring tasks whose next_due date has arrived.

        Call this at the start of each day.  Uses task.next_due (set by
        mark_complete + timedelta) to decide whether a task should become
        pending again.  Tasks without a frequency are never reset here.

        Args:
            today — the date to compare against; defaults to date.today()

        Returns the number of tasks reset.
        """
        ref = today or date.today()
        count = 0
        for pet in self.pets:
            for task in pet.tasks:
                if (
                    task.frequency is not None
                    and task.completed
                    and task.next_due is not None
                    and task.next_due <= ref
                ):
                    task.reset()
                    count += 1
        return count


# ---------------------------------------------------------------------------
# Scheduler output types
# ---------------------------------------------------------------------------

@dataclass
class ConflictWarning:
    """
    Records why a fixed-time task was dropped from the plan.  (improvement 3)

    blocked_task   — the task that could not be placed
    blocking_task  — the already-scheduled task that occupies the same window
    pet            — the pet the blocked task belongs to
    """
    blocked_task: Task
    blocking_task: Task
    pet: Pet


@dataclass
class ScheduledTask:
    """A Task placed in the plan with an absolute start/end time and a reason."""
    task: Task
    pet: Pet
    start_time: str    # HH:MM
    end_time: str      # HH:MM — derived from start_time + task.duration_minutes
    reason: str        # plain-language explanation shown in the UI


@dataclass
class DailyPlan:
    """
    The Scheduler's output for a single day.

    scheduled_tasks   — tasks that fit, ordered by start time
    unscheduled_tasks — (pet, task) pairs dropped because they exceeded the budget
    conflict_warnings — structured records explaining fixed-time conflicts (improvement 3)
    """
    owner: Owner
    scheduled_tasks: list[ScheduledTask] = field(default_factory=list)
    unscheduled_tasks: list[tuple[Pet, Task]] = field(default_factory=list)
    conflict_warnings: list[ConflictWarning] = field(default_factory=list)  # improvement 3

    def tasks_by_time(self) -> list[ScheduledTask]:
        """Return scheduled tasks sorted chronologically by start time."""        # improvement 4
        return sorted(
            self.scheduled_tasks,
            key=lambda st: (int(st.start_time[:2]), int(st.start_time[3:]))
        )

    def summary(self) -> str:
        """Return a human-readable summary of the plan for terminal or UI display."""
        lines = [f"=== Today's Schedule for {self.owner.name} ===\n"]

        if not self.scheduled_tasks:
            lines.append("  No tasks scheduled.")
        else:
            for st in self.tasks_by_time():
                tag = f"[{st.task.priority.value.upper()}]"
                lines.append(
                    f"  {st.start_time} – {st.end_time}  {tag:<8}  "
                    f"{st.task.title}  ({st.pet.name})"
                )
                lines.append(f"    ↳ {st.reason}")

        if self.conflict_warnings:
            lines.append("\n  Fixed-time conflicts (task dropped):")
            for cw in self.conflict_warnings:
                lines.append(
                    f"    ✗ '{cw.blocked_task.title}' ({cw.pet.name}) blocked by "
                    f"'{cw.blocking_task.title}' at {cw.blocking_task.fixed_time}"
                )

        if self.unscheduled_tasks:
            lines.append("\n  Could not fit into today's schedule:")
            for pet, task in self.unscheduled_tasks:
                lines.append(
                    f"    – {task.title} ({pet.name}, {task.duration_minutes} min, "
                    f"{task.priority.value})"
                )

        total = sum(st.task.duration_minutes for st in self.scheduled_tasks)
        lines.append(f"\n  Total scheduled time: {total} / {self.owner.available_minutes} min")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scheduler  — the "brain"
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Retrieves all tasks from the Owner's pets and builds a DailyPlan.

    Strategy:
      1. Ask Owner.get_pending_tasks() for all (pet, task) pairs.
      2. Separate fixed-time tasks from flexible tasks.
      3. Check fixed-time tasks for conflicts; record ConflictWarnings for drops.
      4. Sort flexible tasks by priority (HIGH → MEDIUM → LOW).
      5. Greedily place flexible tasks into gaps until the budget runs out.
      6. Return a DailyPlan ordered chronologically.
    """

    PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}

    def __init__(self, owner: Owner):
        self.owner = owner

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_plan(self) -> DailyPlan:
        """Generate and return a DailyPlan for today."""
        all_pairs = self.owner.get_pending_tasks()

        fixed = [(p, t) for p, t in all_pairs if t.fixed_time is not None]
        flexible = [(p, t) for p, t in all_pairs if t.fixed_time is None]

        fixed.sort(key=lambda pt: self._time_to_minutes(pt[1].fixed_time))
        flexible = self._sort_by_priority(flexible)

        plan = DailyPlan(owner=self.owner)
        budget = self.owner.available_minutes
        occupied: list[tuple[int, int, Task]] = []  # (start, end, task) for conflict lookup

        # --- fixed-time tasks first ---
        for pet, task in fixed:
            start = self._time_to_minutes(task.fixed_time)
            end = start + task.duration_minutes
            blocker = self._find_blocker(start, end, occupied)
            if blocker is not None:
                # improvement 3 — named ConflictWarning instead of silent drop
                plan.conflict_warnings.append(
                    ConflictWarning(blocked_task=task, blocking_task=blocker, pet=pet)
                )
                continue
            occupied.append((start, end, task))
            plan.scheduled_tasks.append(ScheduledTask(
                task=task,
                pet=pet,
                start_time=self._minutes_to_time(start),
                end_time=self._minutes_to_time(end),
                reason=f"Fixed appointment at {task.fixed_time} — cannot be moved.",
            ))
            budget -= task.duration_minutes

        # --- flexible tasks, greedy by priority ---
        cursor = self._time_to_minutes(self.owner.day_start)

        for pet, task in flexible:
            if task.duration_minutes > budget:
                plan.unscheduled_tasks.append((pet, task))
                continue
            start = self._find_next_free_slot(cursor, task.duration_minutes, occupied)
            end = start + task.duration_minutes
            occupied.append((start, end, task))
            occupied.sort(key=lambda x: x[0])
            plan.scheduled_tasks.append(ScheduledTask(
                task=task,
                pet=pet,
                start_time=self._minutes_to_time(start),
                end_time=self._minutes_to_time(end),
                reason=self._make_reason(task, pet),
            ))
            budget -= task.duration_minutes
            cursor = end

        return plan

    def check_conflicts(self) -> list[tuple[Task, Task]]:
        """
        Return pairs of fixed-time tasks (across all pets) whose windows overlap.

        Uses itertools.combinations to generate every unique (a, b) pair without
        repeats — cleaner than a manual nested range loop and expresses the intent
        directly: "check every combination of two fixed tasks".

        Call this before build_plan() to surface problems early.
        """
        fixed = [
            (self._time_to_minutes(t.fixed_time),
             self._time_to_minutes(t.fixed_time) + t.duration_minutes,
             t)
            for _, t in self.owner.get_pending_tasks()
            if t.fixed_time is not None
        ]
        return [
            (t1, t2)
            for (s1, e1, t1), (s2, e2, t2) in combinations(fixed, 2)
            if not (e1 <= s2 or s1 >= e2)
        ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _sort_by_priority(
        self, pairs: list[tuple[Pet, Task]]
    ) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs sorted HIGH → MEDIUM → LOW."""
        return sorted(pairs, key=lambda pt: self.PRIORITY_ORDER[pt[1].priority])

    def _conflicts(
        self, start: int, end: int, occupied: list[tuple[int, int, Task]]
    ) -> bool:
        """Return True if [start, end) overlaps any interval in occupied."""
        return any(not (end <= s or start >= e) for s, e, _ in occupied)

    def _find_blocker(
        self, start: int, end: int, occupied: list[tuple[int, int, Task]]
    ) -> Optional[Task]:
        """Return the first Task in occupied that overlaps [start, end), or None."""
        for s, e, task in occupied:
            if not (end <= s or start >= e):
                return task
        return None

    def _find_next_free_slot(
        self, from_min: int, duration: int, occupied: list[tuple[int, int, Task]]
    ) -> int:
        """Return the earliest start (>= from_min) where duration minutes are free."""
        start = from_min
        while True:
            end = start + duration
            if not self._conflicts(start, end, occupied):
                return start
            # Jump past whichever occupied block is in the way
            blocking_ends = [e for s, e, _ in occupied if not (end <= s or start >= e)]
            start = max(blocking_ends)

    def _compute_end_time(self, start_time: str, duration_minutes: int) -> str:
        """Return the HH:MM end time given a start time string and duration."""
        return self._minutes_to_time(
            self._time_to_minutes(start_time) + duration_minutes
        )

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert a HH:MM string to an integer number of minutes since midnight."""
        h, m = map(int, time_str.split(":"))
        return h * 60 + m

    def _minutes_to_time(self, minutes: int) -> str:
        """Convert an integer number of minutes since midnight to a HH:MM string."""
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def _make_reason(self, task: Task, pet: Pet) -> str:
        """Build a plain-English explanation of why this task was included in the plan."""
        label = task.priority.value.capitalize()
        return (
            f"{label} priority task for {pet.name}; "
            f"scheduled within the {self.owner.available_minutes}-min daily budget."
        )

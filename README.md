# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Smarter Scheduling

The logic layer (`pawpal_system.py`) goes beyond a basic task list:

| Feature | How it works |
|---|---|
| **Priority-aware scheduling** | The `Scheduler` places fixed-time tasks first, then fills remaining time with flexible tasks sorted `HIGH → MEDIUM → LOW`. |
| **Conflict detection** | `check_conflicts()` scans all fixed-time tasks and returns overlapping pairs before the plan is built. `ConflictWarning` objects inside `DailyPlan` record which task was dropped and why — no silent failures. |
| **Sorting by time** | `DailyPlan.tasks_by_time()` returns scheduled tasks in chronological order using a lambda key on `HH:MM` strings. |
| **Filtering** | `Pet.filter_tasks(priority, completed)` returns a filtered list — e.g. only pending HIGH-priority tasks for a given pet. |
| **Recurring tasks** | `Task.frequency` accepts `"daily"` or `"weekly"`. Calling `mark_complete(today=...)` automatically sets `task.next_due` using `timedelta`. `Owner.reset_day(today=...)` resets only tasks whose `next_due` has arrived — daily tasks reset the next morning, weekly tasks reset 7 days later. |

Run the CLI demo to see all features in action:

```bash
source .venv/bin/activate
python3 main.py
```

Run tests:

```bash
python3 -m pytest tests/test_pawpal.py -v
```

---

## Testing PawPal+

Run the full test suite:

```bash
python -m pytest tests/test_pawpal.py -v
```

The suite contains **32 tests** across these areas:

| Area | What is tested |
|---|---|
| **Task lifecycle** | `mark_complete()` sets `completed = True`; `reset()` clears it; one-off tasks never get a `next_due` |
| **Recurrence logic** | Daily tasks set `next_due = today + 1 day`; weekly tasks set `next_due = today + 7 days`; calling `mark_complete` twice always updates `next_due` to the latest date |
| **Reset day** | `reset_day()` only resets tasks whose `next_due ≤ today`; tasks not yet due stay completed; non-recurring tasks are never reset |
| **Pet & Owner** | `add_task` / `remove_task` change the list; `pending_tasks` excludes completed tasks; `get_all_tasks` aggregates across all pets |
| **Filtering** | `filter_tasks(priority=...)` and `filter_tasks(completed=...)` return correct subsets; combined filters work together |
| **Sorting** | `tasks_by_time()` returns tasks in chronological order; works correctly when all tasks share the same priority; returns `[]` on an empty plan |
| **Conflict detection** | `check_conflicts()` returns `[]` when there are no fixed tasks or when fixed tasks don't overlap; detects partial overlap; returns all three pairs for a three-way clash at the same time |
| **Scheduler / budget** | High-priority tasks are scheduled before low; a task exactly filling the budget is included; a task exceeding the budget by one minute is dropped; `ConflictWarning` is recorded when a fixed-time task is blocked |
| **Edge cases** | Plan with no pets returns empty; plan where all tasks are completed returns empty |

**Confidence level: ★★★★☆**

The scheduler's core behaviors — priority ordering, time-budget enforcement, conflict detection, and recurring-task automation — are all covered with both happy-path and edge-case tests. One star is held back because the greedy placement algorithm has not been tested against schedules with interleaved fixed and flexible tasks at the boundary of the budget.

---

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

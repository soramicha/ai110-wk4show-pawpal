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

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

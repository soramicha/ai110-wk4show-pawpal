# PawPal+ Project Reflection

## 1. System Design

**a. Core user actions**

The three core actions a user should be able to perform in PawPal+:

1. **Add a pet** — The user enters their pet's name, species, and any special needs (e.g., medical conditions, dietary restrictions). This creates the context the scheduler uses to personalize the care plan. Without a pet profile, there is nothing to plan around.

2. **Add or edit care tasks** — The user creates tasks such as a morning walk, feeding, medication, or grooming session. Each task has at minimum a duration (how long it takes) and a priority level (how important or time-sensitive it is). Users should also be able to edit or remove tasks as their pet's routine changes.

3. **Generate today's schedule** — The user triggers the scheduler to produce a daily plan. The scheduler considers the available time window, task priorities, and any constraints (e.g., tasks that must happen at a specific time) to output an ordered list of care activities along with a brief explanation of why that plan was chosen.

**b. Initial design**

The initial design has five classes and one enum:

| Class / Enum | Responsibility |
|---|---|
| `Priority` (Enum) | Defines the valid priority levels (`HIGH`, `MEDIUM`, `LOW`) as a type-safe constant rather than a raw string |
| `Pet` | Holds the pet's identity — name, species, and a list of special needs (e.g. `"diabetes"`, `"senior"`). Read by the Scheduler to personalize reasoning. |
| `Task` | Represents one care activity. Stores title, duration in minutes, a `Priority` value, and an optional fixed start time for time-locked tasks like medication. |
| `Owner` | Stores the owner's name, total available minutes for the day, and the time the scheduling window opens (`day_start`). The Scheduler reads these to set the time budget and anchor point. |
| `ScheduledTask` | A `Task` that has been committed to the plan. Adds `start_time`, `end_time`, and a plain-language `reason` so the UI can explain the plan. |
| `DailyPlan` | The Scheduler's output. Holds a list of `ScheduledTask` objects (what fits) and a list of unscheduled `Task` objects (what was dropped). Exposes a `summary()` method for the UI. |
| `Scheduler` | The only class with real logic. Takes an `Owner`, `Pet`, and task list; produces a `DailyPlan`. Internally separates fixed-time vs flexible tasks, checks for conflicts, sorts by priority, and greedily fills the time budget. |

**c. Design changes**

After an AI review of the initial skeleton, three changes were made:

1. **Added `Priority` enum** — The original design used raw strings (`"low"`, `"medium"`, `"high"`). The AI flagged that a typo like `"hight"` would fail silently. Replacing strings with a `Priority` enum makes invalid values a caught error rather than a quiet bug. `PRIORITY_ORDER` on `Scheduler` was updated to key on `Priority` members instead of strings.

2. **Added `end_time` to `ScheduledTask`** — The original `ScheduledTask` only had `start_time`. The AI noted that without an end time, the scheduler has no way to detect whether two fixed-time tasks overlap. Adding `end_time` (computed from start + duration) enables a dedicated `_check_fixed_time_conflicts()` helper.

3. **Added `day_start` to `Owner` and `_compute_end_time()` to `Scheduler`** — The original `Owner` only had `available_minutes` with no anchor. The AI pointed out that placing flexible tasks at absolute times (e.g. "09:40") requires knowing when the day begins. `day_start` (default `"08:00"`) was added to `Owner`, and a `_compute_end_time()` stub was added to `Scheduler` to handle the HH:MM arithmetic.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers three constraints, in this order:

1. **Fixed time** — tasks with a `fixed_time` (e.g. medication at 09:00) are placed first and cannot be moved. This is the hardest constraint; nothing else can displace a fixed-time task.
2. **Priority** — among flexible tasks, `HIGH` comes before `MEDIUM`, which comes before `LOW`. Priority was chosen as the second constraint because it directly reflects the owner's stated importance, not just convenience.
3. **Time budget** — tasks are added greedily until `available_minutes` is exhausted. Any task that doesn't fit is recorded in `unscheduled_tasks` with no further attempt to reorder.

Fixed time was ranked first because a pet medication has a clinical reason for its exact time — rescheduling it would be wrong, not just inconvenient.

**b. Tradeoffs**

**Tradeoff: greedy scheduling does not backtrack.**

The scheduler picks tasks in priority order and commits each one immediately. If a 30-minute HIGH task is placed at 08:10, and a 25-minute gap appears later that could fit two MEDIUM tasks but not the HIGH one, the MEDIUM tasks are still scheduled after the HIGH one — even if swapping them would fit more total tasks in the day.

*Why this is reasonable:* For a daily pet care routine, correctness of priority matters more than maximising the number of tasks completed. A greedy approach is also simple to understand and test: the owner can predict exactly which tasks will be included based on priority order. A backtracking or bin-packing solver would be harder to explain ("why did the scheduler skip my HIGH walk?") and harder to debug when it makes a surprising choice.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

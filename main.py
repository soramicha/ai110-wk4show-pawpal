"""
main.py — manual testing ground for PawPal+ logic

Demonstrates:
  - Sorting tasks by time (tasks_by_time)
  - Filtering by priority and completion status (filter_tasks)
  - Recurrence / reset_day
  - ConflictWarning structured conflict reporting

Run with:  python3 main.py
"""

from datetime import date, timedelta

from pawpal_system import Owner, Pet, Task, Priority, Scheduler


def section(title: str) -> None:
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


def main():
    owner = Owner(name="Jordan", available_minutes=180, day_start="08:00")

    # ------------------------------------------------------------------
    # Tasks added INTENTIONALLY OUT OF ORDER to show sorting
    # Fixed times are non-sequential; priorities are mixed.
    # ------------------------------------------------------------------
    mochi = Pet(name="Mochi", species="dog")
    mochi.add_task(Task("Evening brush",   10, Priority.LOW,    fixed_time="18:00"))                   # one-off
    mochi.add_task(Task("Lunch walk",      20, Priority.MEDIUM, fixed_time="12:00", frequency="daily"))
    mochi.add_task(Task("Breakfast",       10, Priority.HIGH,   fixed_time="08:00", frequency="daily"))
    mochi.add_task(Task("Playtime",        15, Priority.MEDIUM, frequency="daily"))
    mochi.add_task(Task("Nail trim",       10, Priority.LOW,    frequency="weekly"))                    # weekly

    luna = Pet(name="Luna", species="cat")
    luna.add_task(Task("Medication",  5,  Priority.HIGH,   fixed_time="09:00", frequency="daily"))
    luna.add_task(Task("Wet food",    5,  Priority.HIGH,   fixed_time="08:00"))   # conflicts with Mochi's Breakfast
    luna.add_task(Task("Grooming",    15, Priority.MEDIUM))                        # one-off
    luna.add_task(Task("Window time", 10, Priority.LOW,    frequency="daily"))

    owner.add_pet(mochi)
    owner.add_pet(luna)

    # ------------------------------------------------------------------
    # Demo 1: Sorting — tasks_by_time()
    # Show tasks as added (insertion order) vs. sorted by start time
    # ------------------------------------------------------------------
    section("Demo 1: Sorting with tasks_by_time()")

    plan = Scheduler(owner).build_plan()

    print("\n  Insertion order (raw scheduled_tasks list):")
    for st in plan.scheduled_tasks:
        print(f"    {st.start_time}  {st.task.title}")

    print("\n  Sorted chronologically (tasks_by_time):")
    for st in plan.tasks_by_time():
        print(f"    {st.start_time}  {st.task.title}")

    # ------------------------------------------------------------------
    # Demo 2: Filtering — filter_tasks(priority, completed)
    # ------------------------------------------------------------------
    section("Demo 2: Filtering with filter_tasks()")

    # All of Mochi's tasks
    print("\n  Mochi — all tasks:")
    for t in mochi.tasks:
        print(f"    [{t.priority.value:<6}]  {t.title}")

    # Filter: only HIGH priority
    print("\n  Mochi — HIGH priority only:")
    for t in mochi.filter_tasks(priority=Priority.HIGH):
        print(f"    {t.title}")

    # Mark a few complete, then filter by pending
    mochi.get_task("Breakfast").mark_complete()
    mochi.get_task("Lunch walk").mark_complete()

    print("\n  Mochi — pending tasks only (after completing Breakfast + Lunch walk):")
    for t in mochi.filter_tasks(completed=False):
        print(f"    {t.title}  (priority: {t.priority.value})")

    # Filter by pet name at the Owner level — get all pending tasks for Luna only
    print("\n  Owner-level filter: all pending tasks for Luna:")
    luna_pending = [(p, t) for p, t in owner.get_pending_tasks() if p.name == "Luna"]
    for _, t in luna_pending:
        print(f"    {t.title}  (priority: {t.priority.value})")

    # ------------------------------------------------------------------
    # Demo 3: Conflict detection — two levels
    #
    # Level A: scheduler.check_conflicts() — call BEFORE building the plan
    #          to get pairs of clashing fixed-time tasks up front.
    #
    # Level B: plan.conflict_warnings — ConflictWarning objects embedded
    #          in the DailyPlan after build_plan() runs; each records
    #          *which* task was blocked and *by which* task, so the UI
    #          can print a human-readable reason rather than crashing.
    # ------------------------------------------------------------------
    section("Demo 3: Conflict detection")

    # Add a second deliberate same-time conflict so we have two to show
    luna.add_task(Task("Morning meds",  5, Priority.HIGH, fixed_time="08:00"))  # also conflicts at 08:00

    scheduler = Scheduler(owner)

    # --- Level A: pre-check ---
    print("\n  [A] Pre-check with check_conflicts() (before building plan):")
    conflicts = scheduler.check_conflicts()
    if conflicts:
        for t1, t2 in conflicts:
            print(f"      ⚠  '{t1.title}' at {t1.fixed_time} overlaps '{t2.title}' at {t2.fixed_time}")
    else:
        print("      No clashing fixed-time tasks found.")

    # --- Level B: in-plan ConflictWarning objects ---
    fresh_plan = scheduler.build_plan()
    print("\n  [B] ConflictWarnings inside DailyPlan (after build_plan):")
    if fresh_plan.conflict_warnings:
        for cw in fresh_plan.conflict_warnings:
            print(
                f"      ✗ '{cw.blocked_task.title}' ({cw.pet.name}) "
                f"was dropped — blocked by '{cw.blocking_task.title}' "
                f"already occupying {cw.blocking_task.fixed_time}"
            )
    else:
        print("      No conflicts.")

    print(f"\n  Scheduled despite conflicts: {len(fresh_plan.scheduled_tasks)} task(s)")
    print(f"  Dropped (conflict or budget): "
          f"{len(fresh_plan.conflict_warnings) + len(fresh_plan.unscheduled_tasks)} task(s)")

    # ------------------------------------------------------------------
    # Demo 4: Recurrence — reset_day() only resets recurring=True tasks
    # ------------------------------------------------------------------
    section("Demo 4: Recurring tasks — mark_complete + timedelta + reset_day()")

    today = date(2026, 3, 12)
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(weeks=1)

    # Simulate completing all tasks at end of today
    for _, t in owner.get_all_tasks():
        t.mark_complete(today=today)

    total_done = sum(1 for _, t in owner.get_all_tasks() if t.completed)
    print(f"\n  All tasks marked done: {total_done} completed")
    print(f"\n  next_due dates set by timedelta:")
    for pet in owner.pets:
        for t in pet.tasks:
            due = str(t.next_due) if t.next_due else "—  (one-off, never resets)"
            freq = f"[{t.frequency}]" if t.frequency else "[one-off]"
            print(f"    {pet.name:<6}  {t.title:<22} {freq:<10}  next due: {due}")

    # Next morning — reset_day on tomorrow resets daily tasks
    print(f"\n  Calling reset_day(today={tomorrow}) ...")
    reset_count = owner.reset_day(today=tomorrow)
    print(f"  → {reset_count} task(s) reset (daily only; weekly not yet due)\n")

    print("  Status after reset:")
    for pet in owner.pets:
        for t in pet.tasks:
            status = "PENDING" if not t.completed else "still done"
            print(f"    {pet.name:<6}  {t.title:<22} → {status}")

    # One week later — weekly tasks now reset too
    print(f"\n  Calling reset_day(today={next_week}) ...")
    reset_count2 = owner.reset_day(today=next_week)
    print(f"  → {reset_count2} additional task(s) reset (weekly tasks now due)")


if __name__ == "__main__":
    main()

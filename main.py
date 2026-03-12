"""
main.py — manual testing ground for PawPal+ logic

Run with:  python main.py
"""

from pawpal_system import Owner, Pet, Task, Priority, Scheduler


def main():
    # ------------------------------------------------------------------
    # Set up the owner
    # ------------------------------------------------------------------
    owner = Owner(name="Jordan", available_minutes=120, day_start="08:00")

    # ------------------------------------------------------------------
    # Create two pets with tasks
    # ------------------------------------------------------------------
    mochi = Pet(name="Mochi", species="dog")
    mochi.add_task(Task("Breakfast",     10, Priority.HIGH,   fixed_time="08:00"))
    mochi.add_task(Task("Morning walk",  30, Priority.HIGH))
    mochi.add_task(Task("Playtime",      20, Priority.MEDIUM))
    mochi.add_task(Task("Evening brush", 10, Priority.LOW))

    luna = Pet(name="Luna", species="cat")
    luna.add_task(Task("Medication",  5,  Priority.HIGH,   fixed_time="09:00"))
    luna.add_task(Task("Wet food",    5,  Priority.HIGH,   fixed_time="08:00"))
    luna.add_task(Task("Grooming",    15, Priority.MEDIUM))
    luna.add_task(Task("Window perch enrichment", 10, Priority.LOW))

    owner.add_pet(mochi)
    owner.add_pet(luna)

    # ------------------------------------------------------------------
    # Optional: surface fixed-time conflicts before building the plan
    # ------------------------------------------------------------------
    scheduler = Scheduler(owner)
    conflicts = scheduler.check_conflicts()
    if conflicts:
        print("⚠  Fixed-time conflicts detected:")
        for t1, t2 in conflicts:
            print(f"   – '{t1.title}' overlaps with '{t2.title}'")
        print()

    # ------------------------------------------------------------------
    # Build and print the daily plan
    # ------------------------------------------------------------------
    plan = scheduler.build_plan()
    print(plan.summary())

    # ------------------------------------------------------------------
    # Demonstrate mark_complete
    # ------------------------------------------------------------------
    print("\n--- Marking 'Breakfast' complete ---")
    mochi.tasks[0].mark_complete()
    print(f"Mochi's pending tasks: {[t.title for t in mochi.pending_tasks()]}")


if __name__ == "__main__":
    main()

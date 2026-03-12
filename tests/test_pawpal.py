"""
tests/test_pawpal.py — unit tests for PawPal+ core logic
"""

from pawpal_system import Owner, Pet, Task, Priority, Scheduler, ConflictWarning


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status():
    """Calling mark_complete() should set task.completed to True."""
    task = Task("Morning walk", 30, Priority.HIGH)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_reset_clears_completion():
    """Calling reset() after mark_complete() should set completed back to False."""
    task = Task("Feeding", 10, Priority.HIGH)
    task.mark_complete()
    task.reset()
    assert task.completed is False


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

def test_add_task_increases_count():
    """Adding a task to a Pet should increase its task list length by one."""
    pet = Pet(name="Mochi", species="dog")
    assert len(pet.tasks) == 0
    pet.add_task(Task("Morning walk", 30, Priority.HIGH))
    assert len(pet.tasks) == 1
    pet.add_task(Task("Evening brush", 10, Priority.LOW))
    assert len(pet.tasks) == 2


def test_remove_task_decreases_count():
    """Removing a task by title should decrease the task list length."""
    pet = Pet(name="Luna", species="cat")
    pet.add_task(Task("Grooming", 15, Priority.MEDIUM))
    pet.add_task(Task("Medication", 5, Priority.HIGH))
    removed = pet.remove_task("Grooming")
    assert removed is True
    assert len(pet.tasks) == 1
    assert pet.tasks[0].title == "Medication"


def test_remove_task_returns_false_when_not_found():
    """remove_task() should return False when no task matches the given title."""
    pet = Pet(name="Biscuit", species="rabbit")
    result = pet.remove_task("Nonexistent")
    assert result is False


def test_pending_tasks_excludes_completed():
    """pending_tasks() should only return tasks that are not yet completed."""
    pet = Pet(name="Mochi", species="dog")
    walk = Task("Morning walk", 30, Priority.HIGH)
    brush = Task("Evening brush", 10, Priority.LOW)
    pet.add_task(walk)
    pet.add_task(brush)
    walk.mark_complete()
    pending = pet.pending_tasks()
    assert len(pending) == 1
    assert pending[0].title == "Evening brush"


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------

def test_get_all_tasks_aggregates_across_pets():
    """get_all_tasks() should return tasks from all of the owner's pets."""
    owner = Owner(name="Jordan")
    mochi = Pet(name="Mochi", species="dog")
    luna = Pet(name="Luna", species="cat")
    mochi.add_task(Task("Walk", 30, Priority.HIGH))
    luna.add_task(Task("Medication", 5, Priority.HIGH))
    luna.add_task(Task("Grooming", 15, Priority.MEDIUM))
    owner.add_pet(mochi)
    owner.add_pet(luna)
    assert len(owner.get_all_tasks()) == 3


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

def test_scheduler_respects_time_budget():
    """Scheduler should not schedule more total minutes than available_minutes."""
    owner = Owner(name="Jordan", available_minutes=30, day_start="08:00")
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Walk",  30, Priority.HIGH))
    pet.add_task(Task("Brush", 10, Priority.MEDIUM))  # won't fit
    owner.add_pet(pet)

    plan = Scheduler(owner).build_plan()
    total = sum(st.task.duration_minutes for st in plan.scheduled_tasks)
    assert total <= 30
    assert any(t.title == "Brush" for _, t in plan.unscheduled_tasks)


def test_fixed_time_tasks_are_placed_correctly():
    """A task with fixed_time should appear in the plan at that exact start time."""
    owner = Owner(name="Jordan", available_minutes=60, day_start="08:00")
    pet = Pet(name="Luna", species="cat")
    pet.add_task(Task("Medication", 5, Priority.HIGH, fixed_time="09:00"))
    owner.add_pet(pet)

    plan = Scheduler(owner).build_plan()
    assert len(plan.scheduled_tasks) == 1
    assert plan.scheduled_tasks[0].start_time == "09:00"


def test_high_priority_scheduled_before_low():
    """High-priority flexible tasks should be scheduled before low-priority ones."""
    owner = Owner(name="Jordan", available_minutes=60, day_start="08:00")
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Low task",  10, Priority.LOW))
    pet.add_task(Task("High task", 10, Priority.HIGH))
    owner.add_pet(pet)

    plan = Scheduler(owner).build_plan()
    titles = [st.task.title for st in plan.scheduled_tasks]
    assert titles.index("High task") < titles.index("Low task")


# ---------------------------------------------------------------------------
# Improvement 1: recurrence + reset_day
# ---------------------------------------------------------------------------

def test_reset_day_only_resets_recurring_tasks():
    """reset_day() resets daily/weekly tasks whose next_due has arrived; one-offs stay done."""
    from datetime import date, timedelta
    today = date(2026, 3, 12)
    tomorrow = today + timedelta(days=1)

    owner = Owner(name="Jordan")
    pet = Pet(name="Mochi", species="dog")
    recurring = Task("Walk", 30, Priority.HIGH, frequency="daily")
    one_off = Task("Vet visit", 60, Priority.HIGH)   # no frequency
    pet.add_task(recurring)
    pet.add_task(one_off)
    owner.add_pet(pet)

    recurring.mark_complete(today=today)   # next_due = today + 1 = tomorrow
    one_off.mark_complete()

    # reset_day on tomorrow — recurring task is due, one_off is not
    count = owner.reset_day(today=tomorrow)

    assert count == 1
    assert recurring.completed is False
    assert one_off.completed is True


def test_reset_day_returns_zero_when_nothing_recurring():
    """reset_day() returns 0 when no tasks have a frequency set."""
    from datetime import date
    owner = Owner(name="Jordan")
    pet = Pet(name="Luna", species="cat")
    pet.add_task(Task("Grooming", 15, Priority.LOW))   # frequency=None
    owner.add_pet(pet)
    pet.tasks[0].mark_complete()
    assert owner.reset_day(today=date.today()) == 0


def test_mark_complete_sets_next_due_daily():
    """mark_complete on a daily task sets next_due to today + 1 day."""
    from datetime import date, timedelta
    today = date(2026, 3, 12)
    task = Task("Walk", 30, Priority.HIGH, frequency="daily")
    task.mark_complete(today=today)
    assert task.next_due == today + timedelta(days=1)


def test_mark_complete_sets_next_due_weekly():
    """mark_complete on a weekly task sets next_due to today + 7 days."""
    from datetime import date, timedelta
    today = date(2026, 3, 12)
    task = Task("Bath", 20, Priority.MEDIUM, frequency="weekly")
    task.mark_complete(today=today)
    assert task.next_due == today + timedelta(weeks=1)


def test_reset_day_does_not_reset_task_not_yet_due():
    """reset_day() should NOT reset a task whose next_due is in the future."""
    from datetime import date, timedelta
    today = date(2026, 3, 12)
    owner = Owner(name="Jordan")
    pet = Pet(name="Mochi", species="dog")
    task = Task("Walk", 30, Priority.HIGH, frequency="daily")
    pet.add_task(task)
    owner.add_pet(pet)

    task.mark_complete(today=today)          # next_due = March 13
    count = owner.reset_day(today=today)     # still March 12 — not due yet
    assert count == 0
    assert task.completed is True


# ---------------------------------------------------------------------------
# Improvement 2: filter_tasks
# ---------------------------------------------------------------------------

def test_filter_tasks_by_priority():
    """filter_tasks(priority=HIGH) should return only HIGH-priority tasks."""
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Walk", 30, Priority.HIGH))
    pet.add_task(Task("Brush", 10, Priority.LOW))
    pet.add_task(Task("Feed", 10, Priority.HIGH))
    result = pet.filter_tasks(priority=Priority.HIGH)
    assert len(result) == 2
    assert all(t.priority == Priority.HIGH for t in result)


def test_filter_tasks_by_completed_status():
    """filter_tasks(completed=False) should return only pending tasks."""
    pet = Pet(name="Luna", species="cat")
    done = Task("Medication", 5, Priority.HIGH)
    pending = Task("Grooming", 15, Priority.MEDIUM)
    done.mark_complete()
    pet.add_task(done)
    pet.add_task(pending)
    result = pet.filter_tasks(completed=False)
    assert len(result) == 1
    assert result[0].title == "Grooming"


def test_filter_tasks_combined():
    """filter_tasks with both priority and completed filters both criteria."""
    pet = Pet(name="Biscuit", species="rabbit")
    t1 = Task("Feed", 10, Priority.HIGH)
    t2 = Task("Walk", 20, Priority.HIGH)
    t3 = Task("Brush", 10, Priority.LOW)
    t1.mark_complete()
    pet.add_task(t1)
    pet.add_task(t2)
    pet.add_task(t3)
    result = pet.filter_tasks(priority=Priority.HIGH, completed=False)
    assert len(result) == 1
    assert result[0].title == "Walk"


# ---------------------------------------------------------------------------
# Improvement 3: ConflictWarning in DailyPlan
# ---------------------------------------------------------------------------

def test_conflict_warning_populated_on_fixed_time_clash():
    """Two fixed-time tasks at the same time should produce a ConflictWarning."""
    owner = Owner(name="Jordan", available_minutes=60)
    pet_a = Pet(name="Mochi", species="dog")
    pet_b = Pet(name="Luna", species="cat")
    pet_a.add_task(Task("Breakfast", 10, Priority.HIGH, fixed_time="08:00"))
    pet_b.add_task(Task("Wet food",  10, Priority.HIGH, fixed_time="08:00"))
    owner.add_pet(pet_a)
    owner.add_pet(pet_b)

    plan = Scheduler(owner).build_plan()
    assert len(plan.conflict_warnings) == 1
    cw = plan.conflict_warnings[0]
    assert isinstance(cw, ConflictWarning)
    assert cw.blocked_task.title == "Wet food"
    assert cw.blocking_task.title == "Breakfast"


# ---------------------------------------------------------------------------
# Improvement 4: tasks_by_time
# ---------------------------------------------------------------------------

def test_tasks_by_time_returns_chronological_order():
    """tasks_by_time() should return scheduled tasks sorted by start time."""
    owner = Owner(name="Jordan", available_minutes=60, day_start="08:00")
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Walk",  30, Priority.HIGH))
    pet.add_task(Task("Feed",  10, Priority.MEDIUM))
    pet.add_task(Task("Brush", 10, Priority.LOW))
    owner.add_pet(pet)

    plan = Scheduler(owner).build_plan()
    times = [st.start_time for st in plan.tasks_by_time()]
    assert times == sorted(times)

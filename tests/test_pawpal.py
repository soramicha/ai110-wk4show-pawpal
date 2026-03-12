"""
tests/test_pawpal.py — unit tests for PawPal+ core logic
"""

from pawpal_system import Owner, Pet, Task, Priority, Scheduler


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

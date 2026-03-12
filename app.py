"""
app.py — PawPal+ Streamlit UI

Imports the logic layer (pawpal_system.py) and wires UI actions to class methods.
st.session_state acts as the persistent "vault" so Owner/Pet/Task objects survive
between Streamlit reruns.
"""

import streamlit as st
from pawpal_system import Owner, Pet, Task, Priority, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Initialise session state — only runs the very first time
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None

# ---------------------------------------------------------------------------
# Section 1 — Owner setup
# ---------------------------------------------------------------------------
st.header("1. Owner Setup")

with st.form("owner_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        owner_name = st.text_input("Your name", value="Jordan")
    with col2:
        available_minutes = st.number_input(
            "Available minutes today", min_value=10, max_value=480, value=120
        )
    with col3:
        day_start = st.text_input("Day starts at (HH:MM)", value="08:00")
    submitted_owner = st.form_submit_button("Save owner")

if submitted_owner:
    existing_pets = st.session_state.owner.pets if st.session_state.owner else []
    st.session_state.owner = Owner(
        name=owner_name,
        available_minutes=int(available_minutes),
        day_start=day_start,
        pets=existing_pets,
    )
    st.success(f"Owner '{owner_name}' saved.")

# ---------------------------------------------------------------------------
# Everything below requires an owner — gate on a single None check
# ---------------------------------------------------------------------------
owner: Owner | None = st.session_state.owner

if owner is None:
    st.info("Fill in the owner form above to get started.")
    st.stop()
else:
    # ---------------------------------------------------------------------------
    # Section 2 — Add a pet
    # ---------------------------------------------------------------------------
    st.divider()
    st.header("2. Add a Pet")

    with st.form("pet_form"):
        col1, col2 = st.columns(2)
        with col1:
            pet_name = st.text_input("Pet name", value="Mochi")
        with col2:
            species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
        special_needs_raw = st.text_input(
            "Special needs (comma-separated, optional)", value=""
        )
        submitted_pet = st.form_submit_button("Add pet")

    if submitted_pet:
        special_needs = [s.strip() for s in special_needs_raw.split(",") if s.strip()]
        new_pet = Pet(name=pet_name, species=species, special_needs=special_needs)
        owner.add_pet(new_pet)
        st.success(f"Added {pet_name} the {species}.")

    if owner.pets:
        st.write("**Your pets:**")
        for pet in owner.pets:
            needs = f" — {', '.join(pet.special_needs)}" if pet.special_needs else ""
            st.write(f"- **{pet.name}** ({pet.species}){needs}")
    else:
        st.info("No pets yet. Add one above.")

    # ---------------------------------------------------------------------------
    # Section 3 — Add a task to a pet
    # ---------------------------------------------------------------------------
    st.divider()
    st.header("3. Add a Care Task")

    if not owner.pets:
        st.warning("Add at least one pet before adding tasks.")
    else:
        with st.form("task_form"):
            pet_names = [p.name for p in owner.pets]
            selected_pet_name = st.selectbox("Assign task to", pet_names)
            col1, col2, col3 = st.columns(3)
            with col1:
                task_title = st.text_input("Task title", value="Morning walk")
            with col2:
                duration = st.number_input(
                    "Duration (min)", min_value=1, max_value=240, value=20
                )
            with col3:
                priority_str = st.selectbox("Priority", ["high", "medium", "low"])
            fixed_time_raw = st.text_input(
                "Fixed start time (HH:MM, leave blank for flexible)", value=""
            )
            submitted_task = st.form_submit_button("Add task")

        if submitted_task:
            target_pet = next(p for p in owner.pets if p.name == selected_pet_name)
            fixed_time = fixed_time_raw.strip() if fixed_time_raw.strip() else None
            priority = Priority[priority_str.upper()]
            new_task = Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority,
                fixed_time=fixed_time,
            )
            target_pet.add_task(new_task)
            st.success(f"Added '{task_title}' to {selected_pet_name}.")

        all_pairs = owner.get_all_tasks()
        if all_pairs:
            st.write("**All tasks:**")
            for pet in owner.pets:
                if pet.tasks:
                    st.write(f"**{pet.name}**")
                    rows = [
                        {
                            "Task": t.title,
                            "Duration (min)": t.duration_minutes,
                            "Priority": t.priority.value,
                            "Fixed time": t.fixed_time or "flexible",
                            "Done": "✓" if t.completed else "",
                        }
                        for t in pet.tasks
                    ]
                    st.table(rows)
        else:
            st.info("No tasks yet. Add one above.")

    # ---------------------------------------------------------------------------
    # Section 4 — Generate schedule
    # ---------------------------------------------------------------------------
    st.divider()
    st.header("4. Generate Today's Schedule")

    if st.button("Build schedule"):
        if not owner.pets or not owner.get_pending_tasks():
            st.warning("Add at least one pet with pending tasks first.")
        else:
            scheduler = Scheduler(owner)

            conflicts = scheduler.check_conflicts()
            if conflicts:
                st.warning("Fixed-time conflicts detected — conflicting tasks will be dropped:")
                for t1, t2 in conflicts:
                    st.write(f"  - '{t1.title}' overlaps with '{t2.title}'")

            plan = scheduler.build_plan()

            if plan.scheduled_tasks:
                st.success(f"Scheduled {len(plan.scheduled_tasks)} task(s).")
                rows = [
                    {
                        "Start": st_task.start_time,
                        "End": st_task.end_time,
                        "Priority": st_task.task.priority.value,
                        "Task": st_task.task.title,
                        "Pet": st_task.pet.name,
                        "Why": st_task.reason,
                    }
                    for st_task in plan.scheduled_tasks
                ]
                st.table(rows)

                total = sum(s.task.duration_minutes for s in plan.scheduled_tasks)
                st.caption(
                    f"Total scheduled: {total} min out of {owner.available_minutes} min available."
                )
            else:
                st.info("No tasks could be scheduled.")

            if plan.unscheduled_tasks:
                st.warning("Could not fit the following tasks:")
                for pet, task in plan.unscheduled_tasks:
                    st.write(
                        f"  - {task.title} ({pet.name}, {task.duration_minutes} min, "
                        f"{task.priority.value})"
                    )

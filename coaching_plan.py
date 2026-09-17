import streamlit as st
import csv
import random
from io import StringIO, BytesIO
from datetime import time

# Import your functions from create_timeslots.py
from create_timeslots import (
    make_dict_groups,
    make_dict_coaches,
    create_adjacency_group_graph,
    color_graph_all_optimal,
    printer_functions,
    generate_timeslot_labels,
    export_pdf,
)

def display_timeslot_table_md(timeslots, dict_groups, timeslot_labels=None):
    """Display Table 1: Timeslot view using Markdown table formatting."""
    max_tables = max(len(slot) for slot in timeslots)
    headers = ["Timeslot"] + [f"Table {i+1}" for i in range(max_tables)]

    rows = []
    for i, slot in enumerate(timeslots):
        label = timeslot_labels[i] if timeslot_labels else str(i + 1)
        row = [label]
        for group in slot:
            coaches = [c for c in dict_groups[group].values() if c]
            row.append(f"{group} ({', '.join(coaches)})")
        while len(row) < len(headers):
            row.append("")
        rows.append(row)

    md = "| " + " | ".join(headers) + " |\n"
    md += "| " + " | ".join("---" for _ in headers) + " |\n"
    for row in rows:
        md += "| " + " | ".join(row) + " |\n"

    st.subheader("📋 Table 1: Timeslots and Groups")
    st.markdown(md)


def display_coach_table_md(timeslots, dict_coaches, dict_groups, timeslot_labels=None):
    """Display Table 2: Coach view using Markdown table formatting."""
    if timeslot_labels:
        headers = ["Coach"] + list(timeslot_labels)
    else:
        headers = ["Coach"] + [f"Timeslot {i+1}" for i in range(len(timeslots))]

    rows = []
    for coach, groups in dict_coaches.items():
        row = [coach]
        for slot in timeslots:
            entry = ""
            for group in slot:
                if group in groups:
                    others = [c for c in dict_groups[group].values() if c and c != coach]
                    entry = f"{group} ({', '.join(others) if others else ''})"
            row.append(entry)
        rows.append(row)

    md = "| " + " | ".join(headers) + " |\n"
    md += "| " + " | ".join("---" for _ in headers) + " |\n"
    for row in rows:
        md += "| " + " | ".join(row) + " |\n"

    st.subheader("👥 Table 2: Coaches per Timeslot")
    st.markdown(md)


# --- Streamlit app starts here ---
st.set_page_config(layout="wide")
st.title("📅 Coaching Scheduler")

uploaded_file = st.file_uploader("Upload your groups.csv", type="csv")

if uploaded_file:
    # Read CSV
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    reader = csv.DictReader(stringio)
    data = [row for row in reader]

    # Build dicts
    dict_groups = make_dict_groups(data)
    dict_coaches = make_dict_coaches(data)

    st.success("✅ CSV uploaded successfully. Ready to run!")

    tab1, tab2 = st.tabs(["Check CSV", "Run Scheduler"])

    # ---------------- TAB 1 ----------------
    with tab1:
        st.subheader("👀 Adjust Group Assignments per Coach")

        all_groups = list(dict_groups.keys())

        # Session state for coach assignments
        if "coach_assignments" not in st.session_state:
            st.session_state.coach_assignments = {
                coach: groups[:] for coach, groups in dict_coaches.items()
            }

        # Session state for restrictions
        if "restrictions" not in st.session_state:
            st.session_state.restrictions = {}

        for coach, groups in dict_coaches.items():
            selected = st.multiselect(
                f"Groups for {coach}",
                options=all_groups,
                default=st.session_state.coach_assignments.get(coach, groups),
                key=f"coach_{coach}"
            )
            st.session_state.coach_assignments[coach] = selected

        st.markdown("---")
        st.subheader("⚠️ Extra Restrictions: Fix Group to Timeslot")

        with st.form("add_restriction"):
            col1, col2 = st.columns(2)
            with col1:
                group_choice = st.selectbox("Select Group", all_groups)
            with col2:
                timeslot_choice = st.number_input("Timeslot Number", min_value=1, step=1)
            submitted = st.form_submit_button("Add Restriction")
            if submitted:
                st.session_state.restrictions[group_choice] = timeslot_choice
                st.success(f"Restriction added: {group_choice} → Timeslot {timeslot_choice}")

        if st.session_state.restrictions:
            st.write("Current Restrictions:")
            for g, t in list(st.session_state.restrictions.items()):
                col1, col2 = st.columns([3,1])
                with col1:
                    st.write(f"- {g} must be in Timeslot {t}")
                with col2:
                    if st.button(f"Remove {g}", key=f"remove_{g}"):
                        st.session_state.restrictions.pop(g)
                        st.rerun()

        st.markdown("---")
        st.subheader("⏰ Timeslot Timing")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            start_time = st.time_input("Start time", value=time(9, 0), key="start_time")
        with col2:
            end_time = st.time_input("End time (target)", value=time(12, 0), key="end_time")
        with col3:
            duration_minutes = st.number_input(
                "Timeslot duration (min)", min_value=1, value=20, step=5, key="duration_minutes"
            )
        with col4:
            buffer_minutes = st.number_input(
                "Buffer between timeslots (min)", min_value=0, value=5, step=1, key="buffer_minutes"
            )

    # ---------------- TAB 2 ----------------
    with tab2:
        if st.button("Run Script"):
            # Use updated assignments
            updated_dict_coaches = {
                coach: groups for coach, groups in st.session_state.coach_assignments.items()
            }

            # Rebuild dict_groups based on assignments
            updated_dict_groups = {g: {"coach1": "", "coach2": "", "coach3": ""} for g in all_groups}
            for coach, groups in updated_dict_coaches.items():
                for g in groups:
                    for slot in ["coach1", "coach2", "coach3"]:
                        if updated_dict_groups[g][slot] == "":
                            updated_dict_groups[g][slot] = coach
                            break

            adjacency = create_adjacency_group_graph(updated_dict_groups, updated_dict_coaches)
            timeslots_all = color_graph_all_optimal(adjacency)
            timeslot_choice = random.choice(timeslots_all)

            # Apply restrictions
            for group, fixed_slot in st.session_state.restrictions.items():
                if group in sum(timeslot_choice, []):
                    # Remove from other timeslots
                    for slot in timeslot_choice:
                        if group in slot:
                            slot.remove(group)
                    # Ensure enough slots exist
                    while len(timeslot_choice) < fixed_slot:
                        timeslot_choice.append([])
                    # Place in correct slot
                    timeslot_choice[fixed_slot - 1].append(group)

            # Generate time labels for each timeslot based on Tab 1 settings
            timeslot_labels, fits = generate_timeslot_labels(
                start_time=st.session_state.start_time,
                duration_minutes=st.session_state.duration_minutes,
                buffer_minutes=st.session_state.buffer_minutes,
                n_timeslots=len(timeslot_choice),
                end_time=st.session_state.end_time,
            )

            if not fits:
                st.warning(
                    f"⚠️ {len(timeslot_choice)} timeslots at "
                    f"{st.session_state.duration_minutes} min + "
                    f"{st.session_state.buffer_minutes} min buffer don't fit between "
                    f"{st.session_state.start_time.strftime('%H:%M')} and "
                    f"{st.session_state.end_time.strftime('%H:%M')}. "
                    f"Schedule runs to {timeslot_labels[-1].split('-')[1]} instead."
                )

            # Stash results in session state so the PDF download button
            # (which triggers a rerun) doesn't lose the generated schedule
            st.session_state.last_timeslot_choice = timeslot_choice
            st.session_state.last_dict_coaches = updated_dict_coaches
            st.session_state.last_dict_groups = updated_dict_groups
            st.session_state.last_timeslot_labels = timeslot_labels

        # Display + export whatever was last generated (persists across reruns)
        if "last_timeslot_choice" in st.session_state:
            timeslot_choice = st.session_state.last_timeslot_choice
            updated_dict_coaches = st.session_state.last_dict_coaches
            updated_dict_groups = st.session_state.last_dict_groups
            timeslot_labels = st.session_state.last_timeslot_labels

            display_timeslot_table_md(timeslot_choice, updated_dict_groups, timeslot_labels)
            display_coach_table_md(timeslot_choice, updated_dict_coaches, updated_dict_groups, timeslot_labels)

            st.markdown("---")
            pdf_buffer = BytesIO()
            export_pdf(
                timeslot_choice,
                updated_dict_coaches,
                updated_dict_groups,
                filename=pdf_buffer,
                timeslot_labels=timeslot_labels,
            )
            pdf_buffer.seek(0)

            st.download_button(
                label="📄 Export tables as A4 PDF",
                data=pdf_buffer,
                file_name="coaching_schedule.pdf",
                mime="application/pdf",
            )
import streamlit as st
import csv
import random
from io import StringIO

# Import your functions from create_timeslots.py
from create_timeslots import (
    make_dict_groups,
    make_dict_coaches,
    create_adjacency_group_graph,
    color_graph_all_optimal,
    printer_functions
)

def display_timeslot_table_md(timeslots, dict_groups):
    """Display Table 1: Timeslot view using Markdown table formatting."""
    max_tables = max(len(slot) for slot in timeslots)
    headers = ["Timeslot"] + [f"Table {i+1}" for i in range(max_tables)]

    rows = []
    for i, slot in enumerate(timeslots, start=1):
        row = [str(i)]
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


def display_coach_table_md(timeslots, dict_coaches, dict_groups):
    """Display Table 2: Coach view using Markdown table formatting."""
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

            display_timeslot_table_md(timeslot_choice, updated_dict_groups)
            display_coach_table_md(timeslot_choice, updated_dict_coaches, updated_dict_groups)

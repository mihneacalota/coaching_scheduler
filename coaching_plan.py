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

        # Streamlit session state to persist changes
        if "coach_assignments" not in st.session_state:
            st.session_state.coach_assignments = {
                coach: groups[:] for coach, groups in dict_coaches.items()
            }

        for coach, groups in dict_coaches.items():
            selected = st.multiselect(
                f"Groups for {coach}",
                options=all_groups,
                default=st.session_state.coach_assignments.get(coach, groups),
                key=f"coach_{coach}"
            )
            st.session_state.coach_assignments[coach] = selected

    # ---------------- TAB 2 ----------------
    with tab2:
        if st.button("Run Script"):
            # Use updated assignments from session state
            updated_dict_coaches = {
                coach: groups for coach, groups in st.session_state.coach_assignments.items()
            }

            # Rebuild dict_groups based on updated assignments
            updated_dict_groups = {g: {"coach1": "", "coach2": "", "coach3": ""} for g in all_groups}
            for coach, groups in updated_dict_coaches.items():
                for g in groups:
                    # Put coach in first available slot
                    for slot in ["coach1", "coach2", "coach3"]:
                        if updated_dict_groups[g][slot] == "":
                            updated_dict_groups[g][slot] = coach
                            break

            adjacency = create_adjacency_group_graph(updated_dict_groups, updated_dict_coaches)
            timeslots_all = color_graph_all_optimal(adjacency)
            timeslot_choice = random.choice(timeslots_all)

            display_timeslot_table_md(timeslot_choice, updated_dict_groups)
            display_coach_table_md(timeslot_choice, updated_dict_coaches, updated_dict_groups)

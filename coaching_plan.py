import streamlit as st
import csv
import random
from io import StringIO

# Import your functions from create_timeslots.py
from create_timeslots import (
    make_dict_groups,
    make_dict_coaches,
    create_adjacency_group_graph,
    color_graph_all_optimal,   # or the modified color_graph_first_solution
    printer_functions
)

def display_timeslot_table_md(timeslots, dict_groups):
    """
    Display Table 1: Timeslot view using Markdown table formatting.
    """
    max_tables = max(len(slot) for slot in timeslots)
    headers = ["Timeslot"] + [f"Table {i+1}" for i in range(max_tables)]

    # Build rows
    rows = []
    for i, slot in enumerate(timeslots, start=1):
        row = [str(i)]
        for group in slot:
            coaches = [c for c in dict_groups[group].values() if c]
            row.append(f"{group} ({', '.join(coaches)})")
        while len(row) < len(headers):
            row.append("")
        rows.append(row)

    # Markdown table
    md = "| " + " | ".join(headers) + " |\n"
    md += "| " + " | ".join("---" for _ in headers) + " |\n"
    for row in rows:
        md += "| " + " | ".join(row) + " |\n"

    st.subheader("📋 Table 1: Timeslots and Groups")
    st.markdown(md)


def display_coach_table_md(timeslots, dict_coaches, dict_groups):
    """
    Display Table 2: Coach view using Markdown table formatting.
    """
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

    # Markdown table
    md = "| " + " | ".join(headers) + " |\n"
    md += "| " + " | ".join("---" for _ in headers) + " |\n"
    for row in rows:
        md += "| " + " | ".join(row) + " |\n"

    st.subheader("👥 Table 2: Coaches per Timeslot")
    st.markdown(md)

# Set Streamlit page layout to full width
st.set_page_config(layout="wide")

st.title("📅 Coaching Scheduler")

uploaded_file = st.file_uploader("Upload your groups.csv", type="csv")

if uploaded_file:
    # Read uploaded CSV into list of dicts
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    reader = csv.DictReader(stringio)
    data = [row for row in reader]

    dict_groups = make_dict_groups(data)
    dict_coaches = make_dict_coaches(data)

    st.success("✅ CSV uploaded successfully. Ready to run!")

tab1, tab2 = st.tabs(["Check CSV", "Run Scheduler"])
with tab1:
    st.subheader("👀 Groups and Coaches in CSV")

    headers = ["Group", "Coach1", "Coach2", "Coach3"]
    md = "| " + " | ".join(headers) + " |\n"
    md += "| " + " | ".join("---" for _ in headers) + " |\n"

    for g, coaches in dict_groups.items():
        md += f"| {g} | {coaches['coach1']} | {coaches['coach2']} | {coaches['coach3']} |\n"

    st.markdown(md)

with tab2:
    if st.button("Run Script"):
        dict_groups = make_dict_groups(data)
        dict_coaches = make_dict_coaches(data)
        adjacency = create_adjacency_group_graph(dict_groups, dict_coaches)
        timeslots_all = color_graph_all_optimal(adjacency)
        timeslot_choice = random.choice(timeslots_all)

        # ✅ Use new display functions
        display_timeslot_table_md(timeslot_choice, dict_groups)
        display_coach_table_md(timeslot_choice, dict_coaches, dict_groups)

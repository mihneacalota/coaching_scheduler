import os, random, csv
from datetime import datetime, timedelta

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def read_csv(file_path):
    with open(file_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        data = [row for row in reader]
    return data

def make_dict_groups(data):
    groups = {}
    for row in data:
        key = row["group"]
        groups[key] = {"coach1": row["coach1"], "coach2": row.get("coach2", ""), "coach3": row.get("coach3", "")}
    return groups

def make_dict_coaches(data):
    coaches = {}
    for row in data:
        c1 = row["coach1"]
        c2 = row.get("coach2", "")
        c3 = row.get("coach3", "")
        if c1 not in coaches:
            coaches[c1] = []
        coaches[c1].append(row["group"])
        if c2:
            if c2 and c2 not in coaches:
                coaches[c2] = []
            coaches[c2].append(row["group"])
        if c3:
            if c3 and c3 not in coaches:
                coaches[c3] = []
            coaches[c3].append(row["group"])
    return coaches

def get_stats(dict_groups, dict_coaches):
    stats = {
        "total_groups": len(dict_groups),
        "total_coaches": len(dict_coaches),
        "groups_per_coach": {coach: len(groups) for coach, groups in dict_coaches.items()}
    }
    return stats

def create_adjacency_group_graph(dict_groups, dict_coaches):
    adjacency = {group: {"linked":[], "unlinked":[]} for group in dict_groups}
    for _, groups in dict_coaches.items():
        for group in groups:
            adjacency[group]["linked"].extend([g for g in groups if g != group])
    all_groups = set(dict_groups.keys())
    for group in adjacency:
        linked_set = set(adjacency[group]["linked"])
        adjacency[group]["linked"] = list(linked_set)
        adjacency[group]["unlinked"] = list(all_groups - linked_set - {group})
    return adjacency

def color_graph_all_optimal(adjacency):
    groups = list(adjacency.keys())
    n = len(groups)
    best_colors_used = n
    all_solutions = []

    def backtrack(i, coloring, max_color):
        nonlocal best_colors_used, all_solutions
        if len(all_solutions) >= 10000:  # Limit to 10000 solutions
            return
        if i == n:
            if max_color < best_colors_used:
                best_colors_used = max_color
                all_solutions = [coloring.copy()]
            elif max_color == best_colors_used:
                all_solutions.append(coloring.copy())
            return

        group = groups[i]
        for color in range(max_color):
            if all(coloring.get(neigh) != color for neigh in adjacency[group]["linked"]):
                coloring[group] = color
                backtrack(i + 1, coloring, max_color)
                del coloring[group]

        if max_color + 1 <= best_colors_used:
            coloring[group] = max_color
            backtrack(i + 1, coloring, max_color + 1)
            del coloring[group]

    backtrack(0, {}, 0)

    results = []
    for coloring in all_solutions:
        n_colors = max(coloring.values()) + 1
        timeslots = [[] for _ in range(n_colors)]
        for group, color in coloring.items():
            timeslots[color].append(group)
        results.append(timeslots)

    return results


# ---------------------------------------------------------------------------
# Time-slot scheduling helpers
# ---------------------------------------------------------------------------

def generate_timeslot_labels(start_time, duration_minutes, buffer_minutes, n_timeslots, end_time=None):
    """
    Build a list of "HH:MM-HH:MM" labels, one per timeslot, starting at
    start_time. Each slot is duration_minutes long; buffer_minutes is
    inserted between consecutive slots (not after the last one).

    start_time / end_time: datetime.time objects (end_time is optional and
        only used for validation - it does not change how many labels are
        produced, since that is fixed by n_timeslots).
    duration_minutes / buffer_minutes: int, minutes.
    n_timeslots: number of timeslots that need labels.

    Returns: (labels, fits)
        labels: list[str] of length n_timeslots
        fits: True if the generated schedule ends at or before end_time
              (or True if end_time was not provided)
    """
    # anchor on an arbitrary date since we only care about time-of-day math
    anchor = datetime(2000, 1, 1, start_time.hour, start_time.minute)
    duration = timedelta(minutes=duration_minutes)
    buffer_ = timedelta(minutes=buffer_minutes)

    labels = []
    cursor = anchor
    for i in range(n_timeslots):
        slot_start = cursor
        slot_end = slot_start + duration
        labels.append(f"{slot_start.strftime('%H:%M')}-{slot_end.strftime('%H:%M')}")
        cursor = slot_end + buffer_

    fits = True
    if end_time is not None:
        last_end = anchor + n_timeslots * duration + max(n_timeslots - 1, 0) * buffer_
        end_anchor = datetime(2000, 1, 1, end_time.hour, end_time.minute)
        fits = last_end <= end_anchor

    return labels, fits


# ---------------------------------------------------------------------------
# Shared table-building logic (used by both the .txt printer and the PDF export)
# ---------------------------------------------------------------------------

def build_timeslot_rows(timeslots, dict_groups, timeslot_labels=None):
    """Return (headers, rows) for the 'Timeslots and Groups' table."""
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

    return headers, rows


def build_coach_rows(timeslots, dict_coaches, dict_groups, timeslot_labels=None):
    """Return (headers, rows) for the 'Coaches per Timeslot' table."""
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

    return headers, rows


def printer_functions(timeslots, dict_coaches, dict_groups, filename="Coaching.txt", timeslot_labels=None):
    def format_table(headers, rows):
        """Make an ASCII table with aligned columns."""
        col_widths = [max(len(str(cell)) for cell in col) for col in zip(headers, *rows)]
        sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        header_line = "|" + "|".join(f" {h.ljust(w)} " for h, w in zip(headers, col_widths)) + "|"
        row_lines = [
            "|" + "|".join(f" {cell.ljust(w)} " for cell, w in zip(row, col_widths)) + "|"
            for row in rows
        ]
        return "\n".join([sep, header_line, sep] + row_lines + [sep])

    headers1, rows1 = build_timeslot_rows(timeslots, dict_groups, timeslot_labels)
    headers2, rows2 = build_coach_rows(timeslots, dict_coaches, dict_groups, timeslot_labels)

    with open(filename, "w", encoding="utf-8") as f:
        f.write("TABLE 1: Timeslots and Groups\n")
        f.write(format_table(headers1, rows1))
        f.write("\n\n")

        f.write("TABLE 2: Coaches per Timeslot\n")
        f.write(format_table(headers2, rows2))
        f.write("\n")

    print(f"✅ Plain text tables written to {filename}")

    with open(filename, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# PDF export - both tables stacked on a single A4 page
# ---------------------------------------------------------------------------

def export_pdf(timeslots, dict_coaches, dict_groups, filename="schedule.pdf", timeslot_labels=None):
    """
    Render Table 1 (Timeslots and Groups) and Table 2 (Coaches per Timeslot)
    stacked on a single A4 page and write them to `filename`.

    Font size auto-shrinks based on column/row counts so both tables fit
    on one page regardless of how many groups/coaches/timeslots there are.
    """
    headers1, rows1 = build_timeslot_rows(timeslots, dict_groups, timeslot_labels)
    headers2, rows2 = build_coach_rows(timeslots, dict_coaches, dict_groups, timeslot_labels)

    page_width, page_height = A4
    margin = 12 * mm
    usable_width = page_width - 2 * margin
    usable_height = page_height - 2 * margin

    styles = getSampleStyleSheet()
    title_style = styles["Heading2"]

    # Pick a font size that scales down as content grows, so a large
    # roster still fits on one A4 page instead of overflowing.
    total_cols = max(len(headers1), len(headers2))
    total_rows = len(rows1) + len(rows2)
    base_font_size = 9
    if total_cols > 8 or total_rows > 25:
        base_font_size = 7
    if total_cols > 12 or total_rows > 40:
        base_font_size = 6
    base_font_size = max(base_font_size, 5)  # floor so text stays legible-ish

    def make_table(headers, rows, font_size):
        col_count = len(headers)
        col_width = usable_width / col_count
        data = [headers] + rows
        table = Table(data, colWidths=[col_width] * col_count, repeatRows=1)
        table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        return table

    story = [
        Paragraph("Table 1: Timeslots and Groups", title_style),
        Spacer(1, 4),
        make_table(headers1, rows1, base_font_size),
        Spacer(1, 14),
        Paragraph("Table 2: Coaches per Timeslot", title_style),
        Spacer(1, 4),
        make_table(headers2, rows2, base_font_size),
    ]

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        topMargin=margin,
        bottomMargin=margin,
        leftMargin=margin,
        rightMargin=margin,
    )
    doc.build(story)
    print(f"✅ PDF written to {filename}")
    return filename


if __name__ == "__main__":
    file_path = os.path.join(os.path.dirname(__file__), 'groups.csv')
    data = read_csv(file_path)

    dict_groups = make_dict_groups(data)
    dict_coaches = make_dict_coaches(data)

    adjacency = create_adjacency_group_graph(dict_groups, dict_coaches)

    timeslots = color_graph_all_optimal(adjacency)
    random_timeslot = random.choice(timeslots)

    # Example: 09:00 start, 20 min slots, 5 min buffer between them
    labels, fits = generate_timeslot_labels(
        start_time=datetime(2000, 1, 1, 9, 0).time(),
        duration_minutes=20,
        buffer_minutes=5,
        n_timeslots=len(random_timeslot),
    )

    print_statment = printer_functions(random_timeslot, dict_coaches, dict_groups, timeslot_labels=labels)
    print(print_statment)

    export_pdf(random_timeslot, dict_coaches, dict_groups, filename="schedule.pdf", timeslot_labels=labels)
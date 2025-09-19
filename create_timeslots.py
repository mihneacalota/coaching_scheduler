import os, random, csv

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
        if len(all_solutions) >= 50:  # Limit to 50 solutions
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

def printer_functions(timeslots, dict_coaches, dict_groups, filename="Coaching.txt"):
    def format_table(headers, rows):
        """Make an ASCII table with aligned columns."""
        # calculate column widths
        col_widths = [max(len(str(cell)) for cell in col) for col in zip(headers, *rows)]
        # build separator
        sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        # build header
        header_line = "|" + "|".join(f" {h.ljust(w)} " for h, w in zip(headers, col_widths)) + "|"
        # build rows
        row_lines = [
            "|" + "|".join(f" {cell.ljust(w)} " for cell, w in zip(row, col_widths)) + "|"
            for row in rows
        ]
        return "\n".join([sep, header_line, sep] + row_lines + [sep])

    with open(filename, "w", encoding="utf-8") as f:
        # # ---- Groups ----
        # f.write(f"GROUPS ({len(dict_groups)})\n")
        # for g in dict_groups.keys():
        #     f.write(f"- {g}\n")
        # f.write("\n")

        # # ---- Coaches ----
        # f.write(f"COACHES ({len(dict_coaches)})\n")
        # for c in dict_coaches.keys():
        #     f.write(f"- {c}\n")
        # f.write("\n")

        # ---- Table 1: Timeslot view ----
        headers1 = ["Timeslot"] + [f"Table {i+1}" for i in range(max(len(slot) for slot in timeslots))]
        rows1 = []
        for i, slot in enumerate(timeslots, start=1):
            row = [str(i)]
            for group in slot:
                coaches = [c for c in dict_groups[group].values() if c]  # remove empty
                row.append(f"{group} ({', '.join(coaches)})")
            while len(row) < len(headers1):  # pad
                row.append("")
            rows1.append(row)

        f.write("TABLE 1: Timeslots and Groups\n")
        f.write(format_table(headers1, rows1))
        f.write("\n\n")

        # ---- Table 2: Coach view ----
        headers2 = ["Coach"] + [f"Timeslot {i+1}" for i in range(len(timeslots))]
        rows2 = []
        for coach, groups in dict_coaches.items():
            row = [coach]
            for slot in timeslots:
                entry = ""
                for group in slot:
                    if group in groups:
                        others = [c for c in dict_groups[group].values() if c and c != coach]
                        entry = f"{group} ({', '.join(others) if others else ''})"
                row.append(entry)
            rows2.append(row)

        f.write("TABLE 2: Coaches per Timeslot\n")
        f.write(format_table(headers2, rows2))
        f.write("\n")

    print(f"✅ Plain text tables written to {filename}")

    with open(filename, "r", encoding="utf-8") as f:
        return f.read()



if __name__ == "__main__":
    file_path = os.path.join(os.path.dirname(__file__), 'groups.csv')
    data = read_csv(file_path)

    dict_groups = make_dict_groups(data)
    dict_coaches = make_dict_coaches(data)

    adjacency = create_adjacency_group_graph(dict_groups, dict_coaches)

    timeslots = color_graph_all_optimal(adjacency)
    random_timeslot = random.choice(timeslots)
    print_statment = printer_functions(random_timeslot, dict_coaches, dict_groups)
    print(print_statment)

    

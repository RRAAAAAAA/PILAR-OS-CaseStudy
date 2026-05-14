# CPU Scheduling Simulator — V8
# Operating Systems Case Study
# Instructor: Jo Anne Cura

import tkinter as tk
from tkinter import ttk, messagebox

# ── Result helpers ────────────────────────────────────────────

def calculate_results(processes, timeline):
    """Compute Waiting Time (WT) and Turnaround Time (TAT) for each process."""

    # Walk the timeline and record the last end time per process
    # (a process may appear in multiple segments, e.g. Round Robin)
    finish = {}
    for name, start, end in timeline:
        if name not in finish or end > finish[name]:
            finish[name] = end  # keep the latest finish time only

    # TAT = Finish Time − Arrival Time
    # WT  = TAT − Burst Time  (time spent waiting, not executing)
    results = []
    for p in processes:
        tat = finish[p["name"]] - p["arrival"]
        wt  = tat - p["burst"]
        results.append({"name": p["name"], "tat": tat, "wt": wt})
    return results


def merge_timeline(tl):
    """Collapse adjacent segments of the same process into one block.

    Example: [P1,0,2], [P1,2,4]  ->  [P1,0,4]
    This keeps the Gantt chart clean when a process runs back-to-back.
    """
    if not tl:
        return []
    out = [list(tl[0])]  # start with the first segment as a mutable list
    for seg in tl[1:]:
        # Merge if: same process AND this segment starts where the last one ended
        if seg[0] == out[-1][0] and seg[1] == out[-1][2]:
            out[-1][2] = seg[2]  # just extend the end time
        else:
            out.append(list(seg))
    return out


# ── Scheduling Algorithms ─────────────────────────────────────

def run_fcfs(processes):
    """First-Come, First-Served — non-preemptive, ordered by arrival time."""
    # Tie-break by name so results are deterministic when arrivals are equal
    ordered = sorted(processes, key=lambda p: (p["arrival"], p["name"]))
    tl, t = [], 0
    for p in ordered:
        if t < p["arrival"]:
            t = p["arrival"]  # CPU idle — jump to when this process arrives
        tl.append([p["name"], t, t + p["burst"]])
        t += p["burst"]
    return tl, calculate_results(processes, tl)


def run_sjf(processes):
    """Shortest Job First — non-preemptive, picks shortest burst from ready queue."""
    rem = [dict(p) for p in processes]  # copy so originals stay intact
    tl, t = [], 0

    while rem:
        # Collect every process that has already arrived
        avail = [p for p in rem if p["arrival"] <= t]

        if not avail:
            # Nothing ready yet — skip CPU time to the next arrival
            t = min(p["arrival"] for p in rem)
            continue

        # Pick the process with the shortest burst; tie-break by earlier arrival
        best = avail[0]
        for p in avail[1:]:
            if p["burst"] < best["burst"]:
                best = p
            elif p["burst"] == best["burst"] and p["arrival"] < best["arrival"]:
                best = p

        tl.append([best["name"], t, t + best["burst"]])
        t += best["burst"]
        rem.remove(best)  # process is finished, remove from remaining list

    return tl, calculate_results(processes, tl)


def run_srt(processes):
    """Shortest Remaining Time — preemptive SJF, re-evaluates every tick."""
    # Build per-process lookup tables for remaining burst and arrival time
    rem = {p["name"]: p["burst"]   for p in processes}
    arr = {p["name"]: p["arrival"] for p in processes}

    tl      = []
    done    = []   # names of completed processes
    cur     = None # currently running process name
    seg_s   = 0    # start time of the current unbroken segment
    t       = 0    # current clock tick

    while len(done) < len(processes):
        # Build the ready queue: arrived and not yet finished
        avail = [p["name"] for p in processes
                 if p["name"] not in done and arr[p["name"]] <= t]

        if not avail:
            t += 1  # no process ready — advance time by one tick
            continue

        # Choose the process with the least remaining burst; tie-break by arrival
        chosen = avail[0]
        for name in avail[1:]:
            if rem[name] < rem[chosen]:
                chosen = name
            elif rem[name] == rem[chosen] and arr[name] < arr[chosen]:
                chosen = name

        # If the running process changed, save the completed segment
        if chosen != cur:
            if cur:
                tl.append([cur, seg_s, t])  # flush previous segment before switching
            cur, seg_s = chosen, t          # start a new segment for the new process

        rem[chosen] -= 1  # consume one tick of burst
        t += 1

        if rem[chosen] == 0:
            # Process finished — save its final segment and free the CPU
            tl.append([chosen, seg_s, t])
            done.append(chosen)
            cur = None

    return tl, calculate_results(processes, tl)


def run_round_robin(processes, quantum):
    """Round Robin — each process gets at most `quantum` ticks before yielding."""
    rem     = {p["name"]: p["burst"] for p in processes}  # remaining burst per process
    ordered = sorted(processes, key=lambda p: (p["arrival"], p["name"]))
    tl, queue, in_q, done, t = [], [], [], [], 0

    def enqueue_arrived():
        """Add any newly arrived processes to the ready queue (no duplicates)."""
        for p in ordered:
            if p["arrival"] <= t and p["name"] not in in_q and p["name"] not in done:
                queue.append(p["name"])
                in_q.append(p["name"])  # in_q prevents the same process being added twice

    enqueue_arrived()  # seed the queue with processes available at t=0

    while len(done) < len(processes):
        if not queue:
            # Queue empty — jump forward to the next unscheduled arrival
            next_arr = [p["arrival"] for p in ordered
                        if p["name"] not in done and p["name"] not in in_q]
            if not next_arr:
                break
            t = min(next_arr)
            enqueue_arrived()
            continue

        name = queue.pop(0)              # take the front of the FIFO queue
        run  = min(quantum, rem[name])   # run for a full quantum or until done
        tl.append([name, t, t + run])
        rem[name] -= run
        t += run
        enqueue_arrived()  # admit any processes that arrived during this slice

        if rem[name] == 0:
            done.append(name)   # process fully complete
        else:
            queue.append(name)  # still has work — re-enter at the back of the queue

    return tl, calculate_results(processes, tl)


def run_priority(processes, higher_is_better):
    """Priority Scheduling — non-preemptive; picks the best-priority ready process.

    higher_is_better=True  -> larger number wins
    higher_is_better=False -> smaller number wins (1 = Highest mode)
    """
    rem = [dict(p) for p in processes]
    tl, t = [], 0

    while rem:
        avail = [p for p in rem if p["arrival"] <= t]
        if not avail:
            t = min(p["arrival"] for p in rem)  # idle until the next process arrives
            continue

        # Select the process with the best priority value
        best = avail[0]
        for p in avail[1:]:
            if higher_is_better and p["priority"] > best["priority"]:
                best = p
            elif not higher_is_better and p["priority"] < best["priority"]:
                best = p

        tl.append([best["name"], t, t + best["burst"]])
        t += best["burst"]
        rem.remove(best)

    return tl, calculate_results(processes, tl)


def run_priority_preemptive(processes, higher_is_better):
    """Priority Scheduling — preemptive; re-evaluates priority every tick."""
    rem = {p["name"]: p["burst"]    for p in processes}
    arr = {p["name"]: p["arrival"]  for p in processes}
    pri = {p["name"]: p["priority"] for p in processes}

    tl, done, cur, seg_s, t = [], [], None, 0, 0

    while len(done) < len(processes):
        avail = [p["name"] for p in processes
                 if p["name"] not in done and arr[p["name"]] <= t]
        if not avail:
            t += 1
            continue

        chosen = avail[0]
        for name in avail[1:]:
            if higher_is_better and pri[name] > pri[chosen]:
                chosen = name
            elif not higher_is_better and pri[name] < pri[chosen]:
                chosen = name

        if chosen != cur:
            if cur:
                tl.append([cur, seg_s, t])
            cur, seg_s = chosen, t

        rem[chosen] -= 1
        t += 1

        if rem[chosen] == 0:
            tl.append([chosen, seg_s, t])
            done.append(chosen)
            cur = None

    return tl, calculate_results(processes, tl)


def run_priority_rr(processes, quantum, higher_is_better):
    """Priority + Round Robin — Round Robin but the queue is priority-ordered.

    Each round the highest-priority ready process runs for up to `quantum` ticks.
    """
    rem = {p["name"]: p["burst"]    for p in processes}
    arr = {p["name"]: p["arrival"]  for p in processes}
    pri = {p["name"]: p["priority"] for p in processes}

    ordered = sorted(processes, key=lambda p: p["arrival"])
    tl, queue, in_q, done, t = [], [], [], [], 0

    def enqueue_arrived():
        """Admit newly arrived processes into the ready queue."""
        for p in ordered:
            if arr[p["name"]] <= t and p["name"] not in in_q and p["name"] not in done:
                queue.append(p["name"])
                in_q.append(p["name"])

    enqueue_arrived()

    while len(done) < len(processes):
        if not queue:
            # Jump forward to the next unscheduled arrival
            next_arr = [arr[p["name"]] for p in ordered
                        if p["name"] not in done and p["name"] not in in_q]
            if not next_arr:
                break
            t = min(next_arr)
            enqueue_arrived()
            continue

        # From the entire ready queue, pick the single highest-priority process
        chosen = queue[0]
        for name in queue[1:]:
            if higher_is_better and pri[name] > pri[chosen]:
                chosen = name
            elif not higher_is_better and pri[name] < pri[chosen]:
                chosen = name

        queue.remove(chosen)            # temporarily remove while it runs its slice
        run = min(quantum, rem[chosen])
        tl.append([chosen, t, t + run])
        rem[chosen] -= run
        t += run
        enqueue_arrived()  # admit any processes that arrived during this slice

        if rem[chosen] == 0:
            done.append(chosen)    # finished
        else:
            queue.append(chosen)   # not done — re-enter at the back of the queue

    return tl, calculate_results(processes, tl)


# ── Colour Palette ────────────────────────────────────────────

BG_MAIN      = "#222222"   # main window background
BG_PANEL     = "#2C2C2C"   # slightly lighter panel surfaces
BG_ALT       = "#353535"   # alternating table row background
BG_ENTRY     = "#181818"   # dark entry field / canvas background
BG_HEADER    = "#111111"   # top header bar
BG_BTN       = "#3A3A3A"   # default button background
BG_BTN_RUN   = "#E64A19"   # run button — deep orange accent
FG_DARK      = "#F0F0F0"   # primary text on dark backgrounds
FG_MID       = "#999999"   # secondary / dimmed text
FG_LIGHT     = "#555555"   # subtle hint / decorative text
FG_WHITE     = "#FFFFFF"   # pure white for high-contrast labels
ACCENT       = "#FF8C00"   # primary accent — warm orange
ACCENT2      = "#FFC107"   # secondary accent — amber (Gantt axis labels)
BORDER       = "#404040"   # separator lines and borders

# Colours assigned to processes in Gantt charts; cycled when there are more than 10
GANTT_COLORS = [
    "#FF8C00","#FF5722","#FFC107","#E65100","#F57C00",
    "#FF7043","#FFB300","#D84315","#FF6D00","#FFCA28"
]

# Display names for each algorithm — order must match the runners list in _run()
ALGORITHMS = [
    "FCFS",
    "SJF  (Non-Preemptive)",
    "SRT  (Preemptive)",
    "Round Robin",
    "Priority  (Non-Preemptive)",
    "Priority  (Preemptive)",
    "Priority + Round Robin",
]

# Dropdown choices for the priority direction setting
PRIORITY_OPTIONS = ["1 = Highest", "Higher # = Higher"]


# ── Shared UI Helpers ─────────────────────────────────────────

def apply_style():
    """Configure ttk widget themes to match the dark colour palette."""
    s = ttk.Style()
    s.theme_use("clam")  # 'clam' is the only built-in theme that exposes field/arrow colours

    # Style the Combobox dropdown to blend with the dark theme
    s.configure("TCombobox",
                fieldbackground=BG_ENTRY, background=BG_BTN,
                foreground=FG_DARK, selectbackground=BG_ALT,
                selectforeground=FG_DARK, arrowcolor=ACCENT, padding=4)
    s.map("TCombobox", fieldbackground=[("readonly", BG_ENTRY)])

    # Treeview is not actively used but styled for consistency if needed later
    s.configure("Treeview",
                background=BG_PANEL, foreground=FG_DARK,
                fieldbackground=BG_PANEL, rowheight=32,
                font=("Segoe UI", 11))
    s.configure("Treeview.Heading",
                background=BG_ALT, foreground=ACCENT,
                font=("Segoe UI", 10, "bold"), relief="flat")
    s.map("Treeview", background=[("selected", "#E64A19")])


def build_header(window):
    """Render the shared top header bar (title + subtitle) for any window."""
    f = tk.Frame(window, bg=BG_HEADER, height=58)
    f.pack(fill="x")
    f.pack_propagate(False)  # lock the frame to exactly 58 px — ignore child size
    tk.Label(f, text="  CPU Scheduling Simulator",
             font=("Segoe UI", 14, "bold"), bg=BG_HEADER, fg=FG_WHITE
             ).pack(side="left", padx=20, pady=10)
    tk.Label(f, text="Operating Systems  |  Case Study",
             font=("Segoe UI", 8), bg=BG_HEADER, fg=FG_LIGHT
             ).pack(side="right", padx=20, pady=10)


# ── Input Window ──────────────────────────────────────────────

class InputWindow:
    """Main entry screen — lets the user configure processes and launch the simulation."""

    def __init__(self, window):
        self.window = window
        self.window.title("CPU Scheduling Simulator")
        self.window.configure(bg=BG_MAIN)
        self.window.resizable(True, True)

        # Open maximised to the full screen dimensions
        self.window.update_idletasks()
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        self.window.geometry(f"{sw}x{sh}+0+0")

        # Each entry: [name_var, arrival_var, burst_var, priority_var, widget_list]
        self.process_rows = []

        apply_style()
        build_header(self.window)
        self._build_controls()        # Time Quantum + Priority Direction bar
        self._build_process_table()   # editable process input table
        self._build_buttons()         # action buttons row at the bottom

    def _build_controls(self):
        """Build the settings bar: Time Quantum entry and Priority Direction dropdown."""
        panel = tk.Frame(self.window, bg=BG_PANEL)
        panel.pack(fill="x", padx=20, pady=(12, 0))
        f = tk.Frame(panel, bg=BG_PANEL, pady=14)
        f.pack(fill="x", padx=16)

        # Reusable helper for consistently styled column label text
        def lbl(text):
            return tk.Label(f, text=text, font=("Segoe UI", 9, "bold"),
                            bg=BG_PANEL, fg=ACCENT2)

        entry_kw = dict(font=("Segoe UI", 11), bg=BG_ENTRY, fg=FG_DARK,
                        insertbackground=ACCENT, relief="flat", bd=6)

        # Time Quantum — used by Round Robin and Priority + Round Robin
        lbl("Time Quantum").grid(row=0, column=0, padx=(0, 8), sticky="w")
        self.quantum_var = tk.StringVar(value="2")
        tk.Entry(f, textvariable=self.quantum_var, width=6,
                 **entry_kw).grid(row=0, column=1, padx=(0, 24))

        # Thin vertical divider between the two settings groups
        tk.Frame(f, bg=BORDER, width=1, height=34
                 ).grid(row=0, column=2, padx=(0, 24), sticky="ns")

        # Priority Direction — determines whether 1 = highest or highest number wins
        lbl("Priority Direction").grid(row=0, column=3, padx=(0, 8), sticky="w")
        self.priority_var = tk.StringVar(value=PRIORITY_OPTIONS[0])
        ttk.Combobox(f, textvariable=self.priority_var, values=PRIORITY_OPTIONS,
                     state="readonly", width=18, font=("Segoe UI", 10)
                     ).grid(row=0, column=4)

        # Clarifying note — shows which algorithms respect this setting
        tk.Label(f, text="  <- applied to Priority and Priority + Round Robin",
                 font=("Segoe UI", 8), bg=BG_PANEL, fg=FG_LIGHT
                 ).grid(row=0, column=5, padx=(16, 0), sticky="w")

    def _build_process_table(self):
        """Build the process input table with header + editable rows in one shared grid.

        Using a single tk.Frame for both headers and data rows ensures all columns
        share the same pixel geometry — no misalignment when the window is resized.
        """
        outer = tk.Frame(self.window, bg=BORDER, padx=1, pady=1)
        outer.pack(fill="x", padx=20, pady=(10, 0))
        inner = tk.Frame(outer, bg=BG_PANEL)
        inner.pack(fill="x")

        # One shared grid frame — headers and data rows live in the same grid,
        # so column widths are always pixel-identical at any window size.
        self._tbl_grid = tk.Frame(inner, bg=BG_PANEL)
        self._tbl_grid.pack(fill="x", padx=10, pady=(10, 6))

        COL_HEADERS = ["#", "Process Name", "Arrival Time", "Burst Time", "Priority"]
        COL_WEIGHTS = [1,    4,              3,              3,            3]

        # 'uniform' ties all columns to the same base unit, weights set relative sizes
        for ci, wt in enumerate(COL_WEIGHTS):
            self._tbl_grid.grid_columnconfigure(ci, weight=wt, uniform="tbl")

        # Row 0 — header labels (share the exact same columns as data entries below)
        for ci, txt in enumerate(COL_HEADERS):
            tk.Label(self._tbl_grid, text=txt,
                     font=("Segoe UI", 9, "bold"),
                     bg=BG_PANEL, fg=ACCENT,
                     padx=10, pady=8, anchor="w"
                     ).grid(row=0, column=ci, sticky="ew")

        # Row 1 — full-width separator between header and data rows
        tk.Frame(self._tbl_grid, bg=BORDER, height=1
                 ).grid(row=1, column=0, columnspan=5, sticky="ew", pady=(0, 2))

        self._tbl_next_row = 2      # row 0 = headers, row 1 = separator, row 2+ = data
        for i in range(4):
            self._add_row(default_index=i)  # pre-populate with 4 default processes

    def _build_buttons(self):
        """Build the action buttons row below the process table."""
        f = tk.Frame(self.window, bg=BG_MAIN, pady=16)
        f.pack()

        # Each tuple: (label, command, bg_colour, fg_colour, font_size, x_padding)
        btns = [
            ("+ Add Process",    self._add_row,       BG_BTN,     FG_DARK,  10, 16),
            ("- Remove Last",    self._remove_row,    BG_BTN,     FG_MID,   10, 16),
            ("> Run Simulation", self._run,           BG_BTN_RUN, FG_WHITE, 11, 26),
            ("o Reset",          self._reset,         BG_BTN,     FG_MID,   10, 16),
            ("x Close Program",  self._close_program, "#3A1A1A",  "#FF6B6B", 10, 16),
        ]
        for col, (txt, cmd, bg, fg, fs, px) in enumerate(btns):
            # Each button style gets its own hover (active) colour
            abg = "#BF360C" if bg == BG_BTN_RUN else "#5C2020" if bg == "#3A1A1A" else BORDER
            tk.Button(f, text=txt, command=cmd,
                      font=("Segoe UI", fs, "bold"), bg=bg, fg=fg,
                      activebackground=abg, activeforeground=FG_WHITE,
                      relief="flat", bd=0, padx=px, pady=9, cursor="hand2"
                      ).grid(row=0, column=col, padx=6)

    def _add_row(self, default_index=None):
        """Append a new editable process row directly into the shared table grid.

        default_index is used at startup to pre-fill rows; after that, the length
        of process_rows determines the correct sequential row number.
        """
        idx    = default_index if default_index is not None else len(self.process_rows)
        row_bg = BG_PANEL if idx % 2 == 0 else BG_ALT  # alternating row tint
        vars_  = [tk.StringVar(value=v) for v in (f"P{idx+1}", "0", "4", "1")]

        ri = self._tbl_next_row  # place this row at the next available grid row index
        self._tbl_next_row += 1

        # Common visual style applied to all four input entry fields
        estyle = dict(bg=BG_ENTRY, fg=FG_DARK, insertbackground=ACCENT,
                      font=("Segoe UI", 10), relief="flat", bd=6,
                      highlightthickness=1, highlightbackground="#1A1A1A",
                      highlightcolor=ACCENT)

        # Row number label in column 0 — lives in the same grid as the headers
        num_lbl = tk.Label(self._tbl_grid, text=f"{idx+1}.",
                           font=("Segoe UI", 9), bg=row_bg, fg=FG_LIGHT,
                           padx=10, pady=6, anchor="w")
        num_lbl.grid(row=ri, column=0, sticky="nsew")

        # Entry cells for columns 1-4; each wrapped in a frame to show row background
        cells = [num_lbl]  # include label so all row widgets can be destroyed together
        for col, var in enumerate(vars_, start=1):
            wrapper = tk.Frame(self._tbl_grid, bg=row_bg, padx=4, pady=3)
            wrapper.grid(row=ri, column=col, sticky="nsew")
            tk.Entry(wrapper, textvariable=var, **estyle).pack(fill="x")
            cells.append(wrapper)

        # Store: row[0-3] = StringVars for reading input, row[4] = all widgets for cleanup
        self.process_rows.append([*vars_, cells])

    def _remove_row(self):
        """Remove the last process row, enforcing a minimum of 3 processes."""
        if len(self.process_rows) <= 3:
            messagebox.showwarning("Minimum Processes",
                "A minimum of 3 processes is required.")
            return
        # Destroy every widget in the last row (label + entry wrappers)
        for w in self.process_rows.pop()[4]:
            w.destroy()
        self._tbl_next_row -= 1  # free the grid row index for future use

    def _reset(self):
        """Destroy all process rows and rebuild the default 4-row table."""
        for row in self.process_rows:
            for w in row[4]:
                w.destroy()  # remove all widgets from the grid
        self.process_rows  = []
        self._tbl_next_row = 2   # reset back to the first data row (after header + separator)
        for i in range(4):
            self._add_row(default_index=i)

    def _close_program(self):
        """Destroy the root window, ending the application."""
        self.window.destroy()

    def _get_processes(self):
        """Read and validate all process rows. Returns a list of dicts, or None on error."""
        processes = []
        seen      = []  # track names to detect duplicates

        for row in self.process_rows:
            name = row[0].get().strip()
            try:
                arrival  = int(row[1].get())
                burst    = int(row[2].get())
                priority = int(row[3].get())
            except ValueError:
                messagebox.showerror("Input Error",
                    f"All fields for '{name}' must be whole numbers.")
                return None

            if burst <= 0:
                messagebox.showerror("Input Error",
                    f"Burst time for '{name}' must be greater than 0.")
                return None
            if arrival < 0:
                messagebox.showerror("Input Error",
                    f"Arrival time for '{name}' cannot be negative.")
                return None
            if name in seen:
                messagebox.showerror("Input Error",
                    f"Duplicate process name: '{name}'.")
                return None

            seen.append(name)
            processes.append({"name": name, "arrival": arrival,
                               "burst": burst, "priority": priority})
        return processes

    def _run(self):
        """Validate input, run all six algorithms, then open the Results window."""
        procs = self._get_processes()
        if procs is None:
            return  # validation already showed an error dialog

        higher         = self.priority_var.get() == "Higher # = Higher"  # bool for algorithm calls
        priority_label = self.priority_var.get()  # human-readable string for display

        try:
            quantum = int(self.quantum_var.get())
            if quantum <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Input Error",
                "Time Quantum must be a positive whole number.")
            return

        # Pair each algorithm name with a zero-arg lambda that calls the right function
        runners = [
            (ALGORITHMS[0], lambda: run_fcfs(procs)),
            (ALGORITHMS[1], lambda: run_sjf(procs)),
            (ALGORITHMS[2], lambda: run_srt(procs)),
            (ALGORITHMS[3], lambda: run_round_robin(procs, quantum)),
            (ALGORITHMS[4], lambda: run_priority(procs, higher)),
            (ALGORITHMS[5], lambda: run_priority_preemptive(procs, higher)),
            (ALGORITHMS[6], lambda: run_priority_rr(procs, quantum, higher)),
        ]

        # Run every algorithm; merge consecutive same-process segments for cleaner charts
        all_timelines = {}
        for name, fn in runners:
            tl, res = fn()
            all_timelines[name] = (merge_timeline(tl), res)

        # Hide the input window and open the results in a new Toplevel
        self.window.withdraw()
        ResultsWindow(tk.Toplevel(), all_timelines, procs,
                      quantum, priority_label, self.window)


# ── Results Window ────────────────────────────────────────────

class ResultsWindow:
    """Displays all six Gantt charts with expandable inline results tables."""

    def __init__(self, window, all_timelines, procs,
                 quantum, priority_label, input_window):
        self.window         = window
        self.all_timelines  = all_timelines   # {algo_name: (timeline, results)}
        self.procs          = procs           # original process list (for table display)
        self.quantum        = quantum         # stored for the settings tag label
        self.priority_label = priority_label  # stored for the settings tag label
        self.input_window   = input_window    # reference used to restore it on Back
        self._gantt_slots   = []              # list of (canvas, tl, legend, border, tbl_container)

        self.window.title("CPU Scheduling Simulator - Results")
        self.window.configure(bg=BG_MAIN)
        self.window.resizable(True, True)
        # Closing the results window acts the same as pressing Back
        self.window.protocol("WM_DELETE_WINDOW", self._go_back_to_input)

        # Open maximised
        self.window.update_idletasks()
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        self.window.geometry(f"{sw}x{sh}+0+0")

        build_header(self.window)
        self._build_topbar()
        tk.Frame(self.window, bg=BORDER, height=1).pack(fill="x", padx=20)  # divider under topbar
        self._build_charts_panel()
        self._show_charts()

    def _build_topbar(self):
        """Build the navigation bar: Back button, hint label, and Close Program button."""
        bar = tk.Frame(self.window, bg=BG_MAIN, pady=10)
        bar.pack(fill="x", padx=20)

        tk.Button(bar, text="<- Back",
                  command=self._go_back_to_input,
                  font=("Segoe UI", 10, "bold"),
                  bg=BG_BTN, fg=FG_MID,
                  activebackground=BORDER, activeforeground=FG_DARK,
                  relief="flat", bd=0, padx=14, pady=7, cursor="hand2"
                  ).pack(side="left")

        tk.Button(bar, text="x  Close Program",
                  command=self._close_program,
                  font=("Segoe UI", 10, "bold"),
                  bg="#3A1A1A", fg="#FF6B6B",
                  activebackground="#5C2020", activeforeground=FG_WHITE,
                  relief="flat", bd=0, padx=14, pady=7, cursor="hand2"
                  ).pack(side="right")

        # Hint label — tells the user how to reveal the inline results table
        tk.Label(bar, text="Click any chart to expand its results table",
                 font=("Segoe UI", 9), bg=BG_MAIN, fg=FG_LIGHT
                 ).pack(side="right", padx=(0, 20))

    def _build_charts_panel(self):
        """Build the vertically scrollable panel that holds all six Gantt charts."""
        self.charts_panel = tk.Frame(self.window, bg=BG_MAIN)

        # Section heading above the chart list
        hdr = tk.Frame(self.charts_panel, bg=BG_MAIN)
        hdr.pack(fill="x", padx=20, pady=(12, 8))
        tk.Label(hdr, text="Gantt Charts",
                 font=("Segoe UI", 12, "bold"), bg=BG_MAIN, fg=ACCENT
                 ).pack(side="left")
        tk.Label(hdr, text="- All Algorithms  (click to view results table)",
                 font=("Segoe UI", 10), bg=BG_MAIN, fg=FG_MID
                 ).pack(side="left", padx=(8, 0))

        # Outer frame holds the scrollable canvas and its scrollbar side-by-side
        outer = tk.Frame(self.charts_panel, bg=BG_MAIN)
        outer.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Canvas is the scrollable viewport; _inner is the real content frame inside it
        self._sc = tk.Canvas(outer, bg=BG_MAIN, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=self._sc.yview)
        self._sc.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._sc.pack(side="left", fill="both", expand=True)

        # Placing _inner as a canvas window is the standard tkinter scrollable frame pattern
        self._inner  = tk.Frame(self._sc, bg=BG_MAIN)
        self._win_id = self._sc.create_window((0, 0), window=self._inner, anchor="nw")

        # Recalculate scroll region whenever _inner's total height changes (e.g. table expands)
        self._inner.bind("<Configure>",
            lambda e: self._sc.configure(scrollregion=self._sc.bbox("all")))
        # Lock the inner frame width to match the canvas whenever the window is resized
        self._sc.bind("<Configure>",
            lambda e: self._sc.itemconfig(self._win_id, width=e.width))

        # Enable mouse-wheel scrolling on the canvas and its content frame
        self._bind_scroll(self._sc)
        self._bind_scroll(self._inner)

        self._gantt_slots = []
        for i, (algo_name, (tl, _)) in enumerate(self.all_timelines.items()):

            # Separator line between chart blocks; skip before the very first one
            if i > 0:
                tk.Frame(self._inner, bg=BORDER, height=1
                         ).pack(fill="x", padx=4, pady=(4, 0))

            # ── Algorithm name header row ──────────────────────
            name_row = tk.Frame(self._inner, bg=BG_MAIN, cursor="hand2")
            name_row.pack(fill="x", padx=4, pady=(14, 5))

            tk.Label(name_row, text=algo_name.strip(),
                     font=("Segoe UI", 10, "bold"), bg=BG_MAIN, fg=ACCENT2,
                     cursor="hand2").pack(side="left")

            # Settings tag (e.g. "[Quantum = 2]") shown next to relevant algorithms
            sub = self._settings_tag(algo_name)
            if sub:
                tk.Label(name_row, text=f"  [{sub}]",
                         font=("Segoe UI", 9), bg=BG_MAIN, fg=FG_LIGHT,
                         cursor="hand2").pack(side="left")

            # Clickable affordance hint
            tk.Label(name_row, text="   View Table ->",
                     font=("Segoe UI", 8), bg=BG_MAIN, fg=FG_LIGHT,
                     cursor="hand2").pack(side="left", padx=(8, 0))

            # Decorative horizontal rule stretching to the right edge of the heading
            tk.Frame(name_row, bg=BORDER, height=1
                     ).pack(side="left", fill="x", expand=True,
                            padx=(10, 4), pady=(6, 0))

            # ── Gantt chart canvas ─────────────────────────────
            border = tk.Frame(self._inner, bg=BORDER, padx=1, pady=1, cursor="hand2")
            border.pack(fill="x", padx=4, pady=(0, 4))
            c = tk.Canvas(border, height=110, bg=BG_ENTRY,
                          highlightthickness=0, cursor="hand2")
            c.pack(fill="x")

            # ── Colour legend row below the chart ──────────────
            legend = tk.Frame(self._inner, bg=BG_MAIN)
            legend.pack(anchor="w", padx=4, pady=(3, 0))

            # Forward scroll events from chart widgets to the outer canvas
            for w in (name_row, border, c):
                self._bind_scroll(w)
            self._bind_scroll(legend)

            # Factory functions avoid the lambda late-binding trap in loops
            def make_click(name, cont, bd, leg):
                return lambda e: self._toggle_inline_table(name, cont, bd, leg)
            def make_enter(b, cont):
                # Only highlight when the table is closed (no double-highlight)
                return lambda e: b.config(bg=ACCENT) if not cont.winfo_ismapped() else None
            def make_leave(b, cont):
                return lambda e: b.config(bg=BORDER) if not cont.winfo_ismapped() else None

            # ── Inline table container ─────────────────────────
            # Created in the correct pack order now, then hidden until the chart is clicked
            tbl_container = tk.Frame(self._inner, bg=BG_MAIN)
            tbl_container.pack(fill="x", padx=4, pady=(0, 6))
            tbl_container.pack_forget()  # hidden by default

            click_fn = make_click(algo_name, tbl_container, border, legend)
            enter_fn = make_enter(border, tbl_container)
            leave_fn = make_leave(border, tbl_container)

            # Bind interaction events to the name row, border frame, and chart canvas
            for w in (name_row, border, c):
                w.bind("<Button-1>", click_fn)
                w.bind("<Enter>",    enter_fn)
                w.bind("<Leave>",    leave_fn)

            # Store all per-slot references for later use by draw and toggle methods
            self._gantt_slots.append((c, tl, legend, border, tbl_container))

    # ── Inline Table Constants ────────────────────────────────
    # The 1-px gap between cells (bg=TBL_BORDER peeking through) acts as grid lines.
    TBL_BORDER = "#3A3A3A"   # cell gap / grid line colour
    TBL_EVEN   = "#252D3A"   # even row — subtle blue tint
    TBL_ODD    = "#1E1E1E"   # odd row — slightly darker
    TBL_HDR    = "#111827"   # header row background
    TBL_AVG    = "#7A1F00"   # average row — dark red accent
    TBL_COLS   = ("Process", "Arrival Time", "Burst Time",
                  "Priority", "Waiting Time (WT)", "Turnaround Time (TAT)")

    def _show_charts(self):
        """Pack the charts panel and trigger the initial Gantt draw pass."""
        self.charts_panel.pack(fill="both", expand=True)
        self.window.update_idletasks()  # flush geometry so canvas widths are resolved before drawing
        self._draw_all_gantts()

    def _build_inline_table(self, container, algo_name):
        """Build the results grid directly inside container — no internal scrollbar.

        The outer scroll canvas handles all vertical scrolling.
        The TBL_BORDER background peeks through the 1-px cell gaps to form grid lines.
        """
        _, results = self.all_timelines[algo_name]

        # Outer frame's background colour shows through as the cell gap (grid lines)
        outer = tk.Frame(container, bg=self.TBL_BORDER, padx=1, pady=1)
        outer.pack(fill="x")
        grid = tk.Frame(outer, bg=self.TBL_BORDER)
        grid.pack(fill="x")

        ncols = len(self.TBL_COLS)
        # Equal-width columns; 'uniform' ensures all share the same base unit
        for ci in range(ncols):
            grid.grid_columnconfigure(ci, weight=1, uniform="icol")

        # ── Header row (grid row 0) ────────────────────────────
        for ci, col_name in enumerate(self.TBL_COLS):
            cell = tk.Frame(grid, bg=self.TBL_HDR)
            # padx=(0,1) on all but the last column creates the visible vertical gap
            cell.grid(row=0, column=ci, sticky="nsew",
                      padx=(0, 1) if ci < ncols - 1 else (0, 0), pady=(0, 1))
            tk.Label(cell, text=col_name,
                     font=("Segoe UI", 9, "bold"),
                     bg=self.TBL_HDR, fg=ACCENT,
                     padx=12, pady=10, anchor="center"
                     ).pack(fill="both", expand=True)

        # ── Data rows (grid rows 1 to n) ──────────────────────
        pmap     = {p["name"]: p for p in self.procs}  # name -> process dict for fast lookup
        total_wt = total_tat = 0

        for idx, r in enumerate(results):
            p      = pmap[r["name"]]
            values = (r["name"], p["arrival"], p["burst"],
                      p["priority"], r["wt"], r["tat"])
            bg = self.TBL_EVEN if idx % 2 == 0 else self.TBL_ODD  # alternating row colour
            ri = idx + 1  # offset by 1 to leave row 0 for the header

            for ci, val in enumerate(values):
                cell = tk.Frame(grid, bg=bg)
                cell.grid(row=ri, column=ci, sticky="nsew",
                          padx=(0, 1) if ci < ncols - 1 else (0, 0), pady=(0, 1))
                tk.Label(cell, text=str(val),
                         font=("Segoe UI", 10),
                         bg=bg, fg=FG_DARK,
                         padx=12, pady=9, anchor="center"
                         ).pack(fill="both", expand=True)

            total_wt  += r["wt"]
            total_tat += r["tat"]

        # ── Average row (last grid row) ────────────────────────
        n        = len(results)
        avg_wt   = round(total_wt  / n, 2)
        avg_tat  = round(total_tat / n, 2)
        # Blank strings for columns that are not averaged (arrival, burst, priority)
        avg_vals = ("- AVERAGE -", "", "", "", avg_wt, avg_tat)
        ri = n + 1

        for ci, val in enumerate(avg_vals):
            cell = tk.Frame(grid, bg=self.TBL_AVG)
            cell.grid(row=ri, column=ci, sticky="nsew",
                      padx=(0, 1) if ci < ncols - 1 else (0, 0), pady=(0, 1))
            tk.Label(cell, text=str(val),
                     font=("Segoe UI", 10, "bold"),
                     bg=self.TBL_AVG, fg="#FF9858",
                     padx=12, pady=9, anchor="center"
                     ).pack(fill="both", expand=True)

    def _toggle_inline_table(self, algo_name, container, border_frame, after_widget):
        """Show or hide the inline results table directly below the clicked Gantt chart.

        Accordion behaviour: opening one table auto-collapses any other open table.
        Table content is built lazily on first click, then cached in widget children.
        """
        if container.winfo_ismapped():
            # Table is currently visible — collapse it
            container.pack_forget()
            border_frame.config(bg=BORDER)  # restore normal border colour
            self._refresh_scroll()
            return

        # Collapse any other currently open table before expanding this one
        for _, _, _, bd, tc in self._gantt_slots:
            if tc is not container and tc.winfo_ismapped():
                tc.pack_forget()
                bd.config(bg=BORDER)

        # Build content only once; winfo_children() is empty on first open
        if not container.winfo_children():
            self._build_inline_table(container, algo_name)

        # pack(after=legend) places the table right below the chart regardless of pack order
        container.pack(after=after_widget, fill="x", padx=4, pady=(2, 10))
        border_frame.config(bg=ACCENT)  # highlight border to show open state
        self._refresh_scroll()

    def _refresh_scroll(self):
        """Recalculate the outer canvas scroll region after any layout change.

        Must be called whenever _inner's total height grows or shrinks,
        e.g. after showing or hiding an inline table.
        """
        self.window.update_idletasks()  # force geometry flush before measuring
        self._sc.configure(scrollregion=self._sc.bbox("all"))

    def _settings_tag(self, algo_name):
        """Return a short settings summary for algorithms that use quantum or priority.

        Returns an empty string for algorithms that need no extra context (FCFS, SJF, SRT).
        """
        parts = []
        if "Round Robin" in algo_name:
            parts.append(f"Quantum = {self.quantum}")
        if "Priority" in algo_name:
            parts.append(f"Priority: {self.priority_label}")
        return "  |  ".join(parts)

    def _draw_all_gantts(self):
        """Redraw every Gantt chart — called once after layout is fully resolved."""
        self.window.update_idletasks()  # ensure canvas widths are known before drawing
        for canvas, tl, legend, _, _tbl in self._gantt_slots:
            self._draw_single_gantt(canvas, tl, legend)

    def _draw_single_gantt(self, canvas, tl, legend):
        """Draw one Gantt chart: coloured process blocks, time axis ticks, and legend."""
        canvas.delete("all")               # clear any previous drawing
        for w in legend.winfo_children():
            w.destroy()                    # clear the previous legend items

        if not tl:
            canvas.create_text(80, 55, text="No data",
                               fill=FG_LIGHT, font=("Segoe UI", 9))
            return

        total  = tl[-1][2]                      # total duration = last segment's end time
        cw     = canvas.winfo_width() or 1000   # fallback if canvas not yet rendered
        lm, rm = 32, 32                          # left / right margin in pixels
        dw     = cw - lm - rm                    # drawable width between the margins
        bt, bb = 14, 84                          # block top / bottom Y coordinates
        mid_y  = (bt + bb) / 2                   # vertical centre of blocks (for text)
        tick_y = bb + 5                          # tick mark length below blocks
        time_y = bb + 18                         # Y position for time labels

        # Collect unique process names in order of first appearance in the timeline
        names = []
        for seg in tl:
            if seg[0] not in names:
                names.append(seg[0])

        # Assign one Gantt colour per unique process; cycle if more than 10 processes
        colors = {}
        for i, name in enumerate(names):
            colors[name] = GANTT_COLORS[i % len(GANTT_COLORS)]

        # ── Process blocks ─────────────────────────────────────
        for name, s, e in tl:
            x1 = lm + (s / total) * dw   # scale start time to a pixel x-position
            x2 = lm + (e / total) * dw   # scale end time to a pixel x-position
            canvas.create_rectangle(x1, bt, x2, bb,
                                    fill=colors[name], outline=BG_ENTRY, width=2)
            # Only draw the process label if the block is wide enough to fit text
            if x2 - x1 > 16:
                canvas.create_text((x1 + x2) / 2, mid_y, text=name,
                                   fill=FG_WHITE, font=("Segoe UI", 8, "bold"))

        # ── Time axis ──────────────────────────────────────────
        # Tick density adapts to total duration to avoid label crowding
        if total <= 20:
            step = 1
        elif total <= 50:
            step = 5
        elif total <= 100:
            step = 10
        else:
            step = 20

        ticks = list(range(0, total, step))
        if total not in ticks:
            ticks.append(total)  # always include the final end time on the axis

        for t in ticks:
            x = lm + (t / total) * dw
            canvas.create_line(x, bb, x, tick_y, fill=ACCENT2, width=1)  # tick mark
            canvas.create_text(x, time_y, text=str(t),
                               fill=ACCENT2, font=("Segoe UI", 7))

        # ── Colour legend ──────────────────────────────────────
        for name in names:
            item = tk.Frame(legend, bg=BG_MAIN)
            item.pack(side="left", padx=(0, 12))
            self._bind_scroll(item)  # keep scrolling working even when hovering the legend
            tk.Frame(item, bg=colors[name], width=10, height=10
                     ).pack(side="left", padx=(0, 4))  # small colour swatch
            tk.Label(item, text=name, font=("Segoe UI", 8),
                     bg=BG_MAIN, fg=FG_MID).pack(side="left")

    def _bind_scroll(self, widget):
        """Attach mouse-wheel scroll events to a widget, forwarding them to the outer canvas.

        Covers Windows/macOS (<MouseWheel>) and Linux scroll button events (<Button-4/5>).
        """
        widget.bind("<MouseWheel>",
            lambda e: self._sc.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        widget.bind("<Button-4>",
            lambda e: self._sc.yview_scroll(-1, "units"))   # Linux scroll up
        widget.bind("<Button-5>",
            lambda e: self._sc.yview_scroll(1, "units"))    # Linux scroll down

    def _close_program(self):
        """Close both the results and input windows, ending the application."""
        self.input_window.destroy()
        self.window.destroy()

    def _go_back_to_input(self):
        """Close the results window and restore the input window."""
        self.window.destroy()
        self.input_window.deiconify()  # un-hide (un-withdraw) the input window


# ── Entry Point ───────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    InputWindow(root)
    root.mainloop()  # start the tkinter event loop; blocks until the window is closed

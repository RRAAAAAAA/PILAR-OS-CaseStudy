CPU Scheduling Simulator
Operating Systems - Case Study
Tarlac State University | College of Computer Studies
Submitted by: Pilar, Renz Russel Angelo G. | BSCS-3A
Instructor: Jo Anne G. Cura


OVERVIEW

A Python/Tkinter desktop application that simulates six CPU scheduling algorithms. Users enter process parameters through a GUI, and the program generates Gantt charts, computes Waiting Time and Turnaround Time per process, and displays averages for each algorithm.


ALGORITHMS IMPLEMENTED

1. First-Come, First-Served (FCFS) - Non-Preemptive
2. Shortest Job First (SJF) - Non-Preemptive
3. Shortest Remaining Time (SRT) - Preemptive
4. Round Robin (RR) - Preemptive
5. Priority Scheduling - Non-Preemptive and Preemptive
6. Priority Scheduling with Round Robin - Preemptive


REQUIREMENTS

- Python 3.x
- Tkinter (included with Python by default on Windows and macOS)
- Linux users: run "sudo apt install python3-tk" if Tkinter is missing


HOW TO RUN

1. Clone or download this repository
2. Open a terminal in the project folder
3. Run: python PILAR-CPU_Scheduler_Program.py

No additional libraries or installation needed.


HOW TO USE

1. Set the Time Quantum (used by Round Robin and Priority with Round Robin)
2. Set the Priority Direction (1 = Highest, or Higher Number = Higher Priority)
3. Enter at least 3 processes with Process Name, Arrival Time, Burst Time, and Priority value
4. Click Run Simulation
5. The results window shows a Gantt chart and WT/TAT table for all algorithms
6. Click any Gantt chart to expand the detailed results table for that algorithm


REPOSITORY CONTENTS

- PILAR-CPU_Scheduler_Program.py - Main program source code
- PILAR-CPU_Scheduler_Documentation.docx - Full case study documentation
- README.md - This file


VIDEO DEMONSTRATION

https://drive.google.com/drive/folders/1i8qW_ftpUMvdmJWOaP64cso3eTTKP6gR

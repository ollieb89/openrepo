#!/usr/bin/env python3
"""
Phase 79 Plan 06: Verbose Task Dispatch Simulator (35 output lines)

Creates a realistic in_progress task in workspace-state.json and emits
events through the Unix socket event bridge, simulating the full L1->L3 pipeline.

This variant emits 35 output lines (vs 7 in the original) to overflow the
LogViewer panel height and trigger the autoScrollPaused scroll indicator (DASH-03).

35 lines x 0.3s = ~10.5s streaming time.
"""

import json
import socket
import time
import sys
import os

WORKSPACE_STATE_PATH = '/home/ob/Development/Tools/openrepo/workspace/.openclaw/pumplai/workspace-state.json'
SOCKET_PATH = '/home/ob/Development/Tools/openrepo/run/events.sock'
TASK_ID = 'task-verbose-output-test'

def read_state():
    with open(WORKSPACE_STATE_PATH, 'r') as f:
        return json.load(f)

def write_state(state):
    with open(WORKSPACE_STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2)

def send_event(event_data: dict):
    """Send a JSON event line through the Unix domain socket."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)
        line = json.dumps(event_data) + '\n'
        sock.sendall(line.encode('utf-8'))
        sock.close()
        print(f'  [socket] Sent: {event_data.get("type")} for task {event_data.get("task_id", "")}')
        return True
    except Exception as e:
        print(f'  [socket] Error sending event: {e}')
        return False

def main():
    T0 = int(time.time() * 1000)
    print(f'T0: {T0} ms')
    print(f'Task ID: {TASK_ID}')
    print()

    # Step 1: Create the task in workspace state (CREATED)
    print('Step 1: Creating task in workspace state...')
    state = read_state()
    state['tasks'][TASK_ID] = {
        'id': TASK_ID,
        'status': 'created',
        'skill_hint': 'Build a verbose output test project with numpy, pandas, and tests',
        'created_at': time.time(),
        'activity_log': [
            {
                'timestamp': time.time(),
                'status': 'created',
                'entry': 'Task created: Build a verbose output test project'
            }
        ]
    }
    write_state(state)
    print('  State written: status=created')

    # Emit task.created event
    send_event({
        'type': 'task.created',
        'task_id': TASK_ID,
        'project_id': 'pumplai',
        'skill_hint': 'Build a verbose output test project with numpy, pandas, and tests',
        'timestamp': time.time()
    })

    T_created = int(time.time() * 1000)
    elapsed_created = T_created - T0
    print(f'  task.created emitted at T+{elapsed_created}ms')
    print()

    time.sleep(0.5)

    # Step 2: Update task to in_progress (STARTED)
    print('Step 2: Starting task (in_progress)...')
    state = read_state()
    state['tasks'][TASK_ID]['status'] = 'in_progress'
    state['tasks'][TASK_ID]['started_at'] = time.time()
    state['tasks'][TASK_ID]['activity_log'].append({
        'timestamp': time.time(),
        'status': 'in_progress',
        'entry': 'L3 container starting: verbose output test project'
    })
    write_state(state)
    print('  State written: status=in_progress')

    send_event({
        'type': 'task.started',
        'task_id': TASK_ID,
        'project_id': 'pumplai',
        'timestamp': time.time()
    })

    T1 = int(time.time() * 1000)
    elapsed_started = T1 - T0
    print(f'  task.started emitted at T+{elapsed_started}ms')
    print()

    # Step 3: Emit 35 output events (simulating L3 container output — enough to overflow panel)
    print('Step 3: Emitting 35 task output events...')
    output_lines = [
        '+ Initializing Python environment...',
        '+ Checking Python version: 3.11.0',
        '+ Creating project directory: verbose_output_project/',
        '+ Writing requirements.txt: numpy, pandas, requests',
        '+ Installing dependencies via pip...',
        '  Collecting numpy...',
        '  Downloading numpy-1.26.0-cp311-cp311-linux_x86_64.whl',
        '  Installing collected packages: numpy',
        '  Successfully installed numpy-1.26.0',
        '  Collecting pandas...',
        '  Downloading pandas-2.1.0-cp311-cp311-linux_x86_64.whl',
        '  Installing collected packages: pandas',
        '  Successfully installed pandas-2.1.0',
        '  Collecting requests...',
        '  Successfully installed requests-2.31.0',
        '+ Creating verbose_output_project/__init__.py',
        '+ Creating verbose_output_project/main.py',
        '+ Writing main function: process_data()',
        '+ Writing utility function: validate_input()',
        '+ Writing test suite: test_main.py',
        '+ Running tests: python -m pytest test_main.py -v',
        '  PASSED test_main.py::test_process_data_empty_input',
        '  PASSED test_main.py::test_process_data_valid_input',
        '  PASSED test_main.py::test_validate_input_none',
        '  PASSED test_main.py::test_validate_input_valid',
        '  4 passed in 0.12s',
        '+ Running linter: flake8 verbose_output_project/',
        '  verbose_output_project/main.py - OK',
        '  verbose_output_project/__init__.py - OK',
        '+ Formatting with black: 2 files reformatted',
        '+ Building documentation: pdoc verbose_output_project/',
        '+ Documentation written to docs/index.html',
        '+ Staging changes: git add verbose_output_project/ test_main.py',
        '+ Committing: feat: add verbose output test project',
        '+ Push complete: branch l3/task-verbose-output-test',
    ]

    for line in output_lines:
        state = read_state()
        state['tasks'][TASK_ID]['activity_log'].append({
            'timestamp': time.time(),
            'status': 'in_progress',
            'entry': line
        })
        write_state(state)

        send_event({
            'type': 'task.output',
            'task_id': TASK_ID,
            'project_id': 'pumplai',
            'line': line,
            'stream': 'stdout',
            'timestamp': time.time()
        })
        print(f'  Output: {line}')
        time.sleep(0.3)  # Faster than original (35 lines x 0.3s = ~10.5s total)

    print()

    # Step 4: Complete the task
    print('Step 4: Completing task...')
    state = read_state()
    state['tasks'][TASK_ID]['status'] = 'completed'
    state['tasks'][TASK_ID]['completed_at'] = time.time()
    state['tasks'][TASK_ID]['activity_log'].append({
        'timestamp': time.time(),
        'status': 'completed',
        'entry': 'Task completed: verbose output test project created and committed'
    })
    write_state(state)
    print('  State written: status=completed')

    send_event({
        'type': 'task.completed',
        'task_id': TASK_ID,
        'project_id': 'pumplai',
        'timestamp': time.time()
    })

    T_complete = int(time.time() * 1000)
    elapsed_complete = T_complete - T0
    print(f'  task.completed emitted at T+{elapsed_complete}ms')
    print()

    print(f'=== Summary ===')
    print(f'T0: {T0}ms')
    print(f'task.created: T+{elapsed_created}ms')
    print(f'task.started: T+{elapsed_started}ms')
    print(f'output lines: {len(output_lines)}')
    print(f'task.completed: T+{elapsed_complete}ms')
    print(f'Total duration: {elapsed_complete}ms')
    print()
    print(f'Task ID: {TASK_ID}')
    print(f'Criterion 1 check: task.created appeared at T+{elapsed_created}ms (PASS if < 5000ms)')

    # Output results as JSON
    results = {
        'task_id': TASK_ID,
        'T0': T0,
        'T_created': T_created,
        'elapsed_created_ms': elapsed_created,
        'T_started': T1,
        'elapsed_started_ms': elapsed_started,
        'T_completed': T_complete,
        'elapsed_completed_ms': elapsed_complete,
        'output_lines': len(output_lines),
        'events_emitted': ['task.created', 'task.started'] + ['task.output'] * len(output_lines) + ['task.completed'],
        'criterion1_pass': elapsed_created < 5000
    }
    with open('/home/ob/Development/Tools/openrepo/.planning/phases/79-intg01-live-e2e-execution/79-criterion-screenshots/dispatch-results-verbose.json', 'w') as f:
        json.dump(results, f, indent=2)
    print('Results written to dispatch-results-verbose.json')
    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    main()

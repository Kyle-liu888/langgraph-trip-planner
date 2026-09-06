"""Gracefully stop this workspace's backend/Vite before Docker stops PID 1."""
import os
from pathlib import Path
import signal
import time
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--only', choices=('backend', 'frontend', 'all'), default='all')
options = parser.parse_args()

if not Path('/.dockerenv').exists() or not Path('/workspace/backend/run.py').is_file():
    raise SystemExit('Run this only inside the travel development container.')

targets = []
for path in Path('/proc').iterdir():
    if not path.name.isdigit() or int(path.name) == os.getpid():
        continue
    try:
        args = path.joinpath('cmdline').read_bytes().decode().split('\0')
        cwd = path.joinpath('cwd').resolve()
        executable = Path(args[0]).name
        backend = (cwd == Path('/workspace/backend') and executable.startswith('python')
                   and len(args) > 1 and Path(args[1]).name == 'run.py')
        frontend = (cwd == Path('/workspace/frontend') and executable == 'node'
                    and any(Path(arg).name in ('vite', 'vite.js') for arg in args[1:] if arg))
        if (backend and options.only in ('backend', 'all')) or (frontend and options.only in ('frontend', 'all')):
            pid = int(path.name)
            os.kill(pid, signal.SIGTERM)
            targets.append((pid, path.joinpath('stat').read_text().split()[21]))
    except (ProcessLookupError, FileNotFoundError, PermissionError, UnicodeDecodeError):
        continue

deadline = time.monotonic() + 35
while targets and time.monotonic() < deadline:
    alive = []
    for pid, started in targets:
        try:
            stat = Path(f'/proc/{pid}/stat').read_text().split()
            if stat[21] == started and stat[2] != 'Z':
                alive.append((pid, started))
        except FileNotFoundError:
            pass
    targets = alive
    if targets:
        time.sleep(0.2)
if targets:
    raise SystemExit('Services did not finish graceful shutdown; container left running for inspection.')
print(f'Selected services ({options.only}) stopped gracefully; unrelated processes were not signalled.')

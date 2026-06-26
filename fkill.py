#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional, Set


@dataclass(frozen=True)
class Process:
    pid: int
    ppid: int
    user: str
    cpu: float
    mem: float
    command: str

    @property
    def display_name(self) -> str:
        app_names = app_bundle_names(self.command)
        if app_names:
            return app_names[-1]
        return self.executable_name or f"PID {self.pid}"

    @property
    def icon_path(self) -> Optional[str]:
        app_paths = app_bundle_paths(self.command)
        return app_paths[-1] if app_paths else None

    @property
    def executable_name(self) -> str:
        if not self.command:
            return ""
        return os.path.basename(self.command.split()[0])

    @property
    def match_text(self) -> str:
        parts = [self.display_name, self.executable_name, str(self.pid)]
        parts.extend(app_bundle_names(self.command))
        return " ".join(part for part in parts if part)

    @property
    def is_app_process(self) -> bool:
        return bool(app_bundle_paths(self.command))

    @property
    def is_primary_app_process(self) -> bool:
        paths = app_bundle_paths(self.command)
        if len(paths) != 1:
            return False
        bundle_name = normalize_app_name(os.path.basename(paths[0]))
        executable_prefix = f"{paths[0]}/Contents/MacOS/"
        if not self.command.startswith(executable_prefix):
            return False
        executable_tail = self.command[len(executable_prefix) :].strip()
        if not bundle_name or not executable_tail:
            return False
        normalized_tail = normalize_app_name(executable_tail)
        if any(marker in normalized_tail for marker in (" helper", " renderer", " service")):
            return False
        if not normalized_tail.startswith(bundle_name):
            return False
        if len(normalized_tail) == len(bundle_name):
            return True
        return normalized_tail[len(bundle_name)].isspace()

    @property
    def is_user_app_process(self) -> bool:
        paths = app_bundle_paths(self.command)
        return self.is_primary_app_process and bool(paths) and paths[0].startswith("/Applications/")

    def matches_app_name(self, app_name: str, require_primary: bool = True) -> bool:
        normalized = normalize_app_name(app_name)
        if not normalized:
            return False
        if require_primary and not self.is_primary_app_process:
            return False
        names = [self.display_name, self.executable_name]
        names.extend(app_bundle_names(self.command))
        return any(normalize_app_name(name) == normalized for name in names)

    def matches_any_app_name(self, app_names: Iterable[str]) -> bool:
        return any(self.matches_app_name(app_name) for app_name in app_names)


def app_bundle_paths(command: str) -> List[str]:
    paths = []
    search_start = 0
    while True:
        app_index = command.find(".app", search_start)
        if app_index == -1:
            return paths
        paths.append(command[: app_index + len(".app")])
        search_start = app_index + len(".app")


def app_bundle_names(command: str) -> List[str]:
    names = []
    for path in app_bundle_paths(command):
        slash_index = path.rfind("/")
        names.append(path[slash_index + 1 :] if slash_index != -1 else path)
    return names


def normalize_app_name(name: str) -> str:
    name = os.path.basename(name.strip())
    if name.casefold().endswith(".app"):
        name = name[:-4]
    return name.casefold()


def resource_score(process: Process) -> float:
    return process.cpu + process.mem


def sort_processes(
    processes: List[Process],
    foreground_app: Optional[str] = None,
    visible_apps: Optional[Set[str]] = None,
) -> List[Process]:
    visible_apps = visible_apps or set()

    def sort_key(process: Process):
        if foreground_app and process.matches_app_name(foreground_app):
            group_rank = 0
        elif process.is_primary_app_process and process.matches_any_app_name(visible_apps):
            group_rank = 1
        elif process.is_user_app_process:
            group_rank = 2
        else:
            group_rank = 3
        return (group_rank, -resource_score(process), process.display_name.casefold(), process.pid)

    return sorted(processes, key=sort_key)


def foreground_app_name() -> Optional[str]:
    script = 'tell application "System Events" to get name of first application process whose frontmost is true'
    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=1,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    name = result.stdout.strip()
    return name or None


def visible_app_names() -> Set[str]:
    script = 'tell application "System Events" to get name of every application process whose background only is false'
    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=1,
        )
    except (subprocess.SubprocessError, OSError):
        return set()
    return {name.strip() for name in result.stdout.split(",") if name.strip()}


def list_processes() -> List[Process]:
    result = subprocess.run(
        ["/bin/ps", "-axo", "pid=,ppid=,user=,%cpu=,%mem=,command="],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [process for line in result.stdout.splitlines() if (process := parse_ps_line(line))]


def parse_ps_line(line: str) -> Optional[Process]:
    parts = line.strip().split(None, 5)
    if len(parts) < 6:
        return None
    pid, ppid, user, cpu, mem, command = parts
    try:
        return Process(
            pid=int(pid),
            ppid=int(ppid),
            user=user,
            cpu=float(cpu),
            mem=float(mem),
            command=command,
        )
    except ValueError:
        return None


def protected_pids(processes: List[Process], current_pid: int) -> Set[int]:
    protected = {1, current_pid}
    current_process = next((process for process in processes if process.pid == current_pid), None)
    if current_process:
        protected.add(current_process.ppid)
    return protected


def killable_processes(processes: List[Process], current_pid: Optional[int] = None) -> List[Process]:
    current_pid = current_pid if current_pid is not None else os.getpid()
    protected = protected_pids(processes, current_pid)
    return [
        process
        for process in processes
        if process.pid not in protected
    ]


def filter_processes(processes: List[Process], query: str) -> List[Process]:
    normalized_query = query.strip().casefold()
    candidates = killable_processes(processes)
    if not normalized_query:
        return candidates
    return [
        process
        for process in candidates
        if normalized_query in process.match_text.casefold()
    ]


def script_filter_json(
    processes: List[Process],
    query: str,
    current_pid: Optional[int] = None,
    foreground_app: Optional[str] = None,
    visible_apps: Optional[Set[str]] = None,
) -> str:
    query = query.strip()
    matches = sort_processes(
        filter_processes(killable_processes(processes, current_pid), query),
        foreground_app=foreground_app,
        visible_apps=visible_apps,
    )
    items = []

    if query and matches:
        items.append(
            {
                "uid": f"query:{query}",
                "title": f"Force kill all matching processes: {query}",
                "subtitle": f"Kill {len(matches)} process(es) with SIGKILL",
                "arg": f"query:{query}",
            }
        )

    for process in matches[:200]:
        item = {
            "uid": str(process.pid),
            "title": process.display_name,
            "subtitle": (
                f"PID {process.pid} · CPU {process.cpu:.1f}% · MEM {process.mem:.1f}% · "
                f"{process.command}"
            ),
            "arg": f"pid:{process.pid}",
        }
        if process.icon_path:
            item["icon"] = {"path": process.icon_path, "type": "fileicon"}
        items.append(item)

    if not items:
        items.append(
            {
                "title": "No matching processes",
                "subtitle": "Try another process name or PID",
                "valid": False,
            }
        )

    return json.dumps({"items": items}, ensure_ascii=False)


def kill_selection(selection: str, processes: Optional[List[Process]] = None) -> str:
    selection = selection.strip()
    processes = processes if processes is not None else list_processes()

    if selection.startswith("pid:"):
        pid = int(selection.removeprefix("pid:"))
        os.kill(pid, signal.SIGKILL)
        return f"Killed PID {pid}"

    if selection.startswith("query:"):
        query = selection.removeprefix("query:")
        matches = filter_processes(processes, query)
        for process in matches:
            os.kill(process.pid, signal.SIGKILL)
        return f"Killed {len(matches)} matching processes for '{query}'"

    raise ValueError(f"Unknown selection: {selection}")


def main(argv: List[str]) -> int:
    command = argv[1] if len(argv) > 1 else "filter"
    argument = argv[2] if len(argv) > 2 else ""

    try:
        if command == "filter":
            print(
                script_filter_json(
                    list_processes(),
                    argument,
                    current_pid=os.getpid(),
                    foreground_app=foreground_app_name(),
                    visible_apps=visible_app_names(),
                )
            )
            return 0
        if command == "kill":
            print(kill_selection(argument))
            return 0
    except ProcessLookupError:
        print("Process already exited")
        return 0
    except PermissionError as error:
        print(f"Permission denied: {error}")
        return 1
    except Exception as error:
        print(f"fkill error: {error}")
        return 1

    print("Usage: fkill.py filter [query] | fkill.py kill <pid:N|query:text>")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

"""Docker sandbox runner (spec Section 3).

One container per run: repo mounted read-write at /repo, no host credentials,
CPU/time limits. Tool calls from the executor route through here.

Week-1 state: interface + local fallback. The Docker path runs a command in
the `recall-sandbox` image (Dockerfile.sandbox); when Docker is unavailable
it falls back to a local subprocess AND SAYS SO — silent fallback would be a
lie about isolation.
"""

from __future__ import annotations

import shutil
import subprocess

IMAGE = "recall-sandbox:latest"


def docker_available() -> bool:
    return shutil.which("docker") is not None


def ensure_image() -> None:
    """Build the sandbox image if missing. TODO(week-1): pin by digest for eval runs."""
    proc = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True)
    if proc.returncode != 0:
        subprocess.run(
            ["docker", "build", "-f", "Dockerfile.sandbox", "-t", IMAGE, "."],
            check=True,
        )


def run_in_sandbox(repo_path: str, argv: list[str], timeout: int = 600) -> str:
    """Run argv with the repo mounted at /repo. Returns combined stdout/stderr."""
    if not docker_available():
        # Fallback: local execution, no isolation. Fine for early dev on your
        # own repos; never for the public demo.
        proc = subprocess.run(
            argv, cwd=repo_path, capture_output=True, text=True, timeout=timeout
        )
        return "[sandbox unavailable — ran locally]\n" + (proc.stdout + proc.stderr).strip()

    ensure_image()
    proc = subprocess.run(
        [
            "docker", "run", "--rm",
            "--cpus", "2", "--memory", "2g",
            "--network", "none",
            "-v", f"{repo_path}:/repo",
            "-w", "/repo",
            IMAGE, *argv,
        ],
        capture_output=True, text=True, timeout=timeout,
    )
    return (proc.stdout + proc.stderr).strip()

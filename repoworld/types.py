"""Public values and supervisor-only filesystem capabilities are distinct types."""
from dataclasses import dataclass
from pathlib import Path
from ..pcworld.snapshots import Snapshot


@dataclass(frozen=True)
class PublicTask:
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str


@dataclass(frozen=True)
class EnvironmentRef:
    rootfs_sha256: str
    policy_sha256: str
    root: Path


@dataclass(frozen=True)
class RepoBase:
    task: PublicTask
    snapshot: Snapshot
    environment: EnvironmentRef


@dataclass(frozen=True)
class PatchCandidate:
    base_id: str
    snapshot: Snapshot
    patch_sha256: str
    operation_id: str

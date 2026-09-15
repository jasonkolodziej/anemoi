"""Ingestion: pulls raw bytes for a source at a valid time, QC-gates them, and
lands them in the raw and processed data lakes.

Scope v2.1 §4.2. This is the layer the Data Pipeline wiki page diagrams
(orchestrator -> raw lake -> QC gate -> processed lake) but that did not yet
exist in code: `sources.py` describes *what* a source is, `availability.py`
answers *when* it publishes, and this module is what actually goes and gets
it.

Nothing here talks to a real network endpoint by default -- `Fetcher`
implementations below are thin adapters you point at NOMADS / ERDDAP / the
HRD FTP archive / AWS Open Data / NDBC. The orchestration, QC gate, and lake
writer are the reusable part; swap the fetcher per source without touching
the rest.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Protocol

from . import sources
from .sources import Role


# --------------------------------------------------------------------------- #
# Fetch
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class FetchResult:
    """Raw bytes for one source at one valid time, plus provider metadata."""

    source_key: str
    valid_time: datetime
    fetched_at: datetime
    raw_bytes: bytes
    fmt: str
    #: Checksum asserted by the provider (e.g. an ERDDAP/HRD manifest entry),
    #: if one was available. None means "nothing to check against" -- not a
    #: pass.
    provider_checksum: str | None = None

    @property
    def local_checksum(self) -> str:
        return hashlib.md5(self.raw_bytes).hexdigest()


class FetchError(RuntimeError):
    """The provider was reachable but the fetch failed (bad response, 404,
    malformed payload). Distinct from "not yet published" -- see
    `availability.py`, which is what should be consulted *before* calling a
    fetcher at all.
    """


class Fetcher(Protocol):
    """One implementation per source (or per provider, for sources that
    share one). Fetchers are intentionally dumb: they do not consult the
    availability oracle themselves. The orchestrator checks
    `oracle.published_at()` first and only calls a fetcher once a source is
    believed to be available -- a fetcher raising `FetchError` on top of that
    is a genuine failure, not an expected "not ready yet".
    """

    def fetch(self, source_key: str, valid_time: datetime) -> FetchResult: ...


# --------------------------------------------------------------------------- #
# QC gate
# --------------------------------------------------------------------------- #


class QCSeverity(str, Enum):
    PASS = "pass"
    WARN = "warn"
    #: Fails the gate. The file is not promoted to the processed lake.
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class QCFinding:
    check: str
    severity: QCSeverity
    detail: str = ""


@dataclass(frozen=True, slots=True)
class QCReport:
    source_key: str
    valid_time: datetime
    findings: tuple[QCFinding, ...]

    @property
    def passed(self) -> bool:
        return not any(f.severity is QCSeverity.FAIL for f in self.findings)


class QCCheck(Protocol):
    """One quality check. Great Expectations / Pandera would implement this
    interface rather than being reached for directly, so the gate's pass/fail
    contract stays independent of which validation library backs it.
    """

    name: str

    def run(self, result: FetchResult) -> QCFinding: ...


@dataclass(frozen=True, slots=True)
class ChecksumCheck:
    """Scope v2.1 §4.2: every file MD5-verified against provider metadata
    before lake storage.
    """

    name: str = "checksum"

    def run(self, result: FetchResult) -> QCFinding:
        if result.provider_checksum is None:
            return QCFinding(
                self.name, QCSeverity.WARN, "no provider checksum to verify against"
            )
        if result.local_checksum != result.provider_checksum:
            return QCFinding(
                self.name,
                QCSeverity.FAIL,
                f"checksum mismatch: local={result.local_checksum} "
                f"provider={result.provider_checksum}",
            )
        return QCFinding(self.name, QCSeverity.PASS)


@dataclass(frozen=True, slots=True)
class NonEmptyCheck:
    name: str = "non_empty"

    def run(self, result: FetchResult) -> QCFinding:
        if len(result.raw_bytes) == 0:
            return QCFinding(self.name, QCSeverity.FAIL, "zero-byte payload")
        return QCFinding(self.name, QCSeverity.PASS)


DEFAULT_CHECKS: tuple[QCCheck, ...] = (ChecksumCheck(), NonEmptyCheck())


def run_qc_gate(
    result: FetchResult, checks: tuple[QCCheck, ...] = DEFAULT_CHECKS
) -> QCReport:
    findings = tuple(check.run(result) for check in checks)
    return QCReport(result.source_key, result.valid_time, findings)


# --------------------------------------------------------------------------- #
# Lake
# --------------------------------------------------------------------------- #


class LakeTier(str, Enum):
    RAW = "raw"
    PROCESSED = "processed"


class LakeWriter(Protocol):
    """Writes bytes to a tier of the lake and returns the path/key written.

    A local-filesystem implementation is enough for the reference build; the
    wiki's Cloudflare R2 / ZFS NAS choice is a config detail behind this
    interface, not a reason to change any calling code.
    """

    def write(
        self, tier: LakeTier, source_key: str, valid_time: datetime, data: bytes
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class LocalLakeWriter:
    """Reference implementation: `<root>/<tier>/<source_key>/<iso-time>.<ext>`."""

    root: Path

    def write(
        self, tier: LakeTier, source_key: str, valid_time: datetime, data: bytes
    ) -> str:
        ext = sources.get(source_key).fmt.split("/")[0].strip().lower()
        path = (
            self.root
            / tier.value
            / source_key
            / f"{valid_time:%Y%m%dT%H%M%S}.{ext}"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


class IngestionOutcome(str, Enum):
    LANDED = "landed"  # raw written, QC passed, processed written
    QUARANTINED = "quarantined"  # raw written, QC failed, not promoted
    FETCH_FAILED = "fetch_failed"
    SKIPPED_NOT_OPERATIONAL = "skipped_not_operational"


@dataclass(frozen=True, slots=True)
class IngestionRecord:
    source_key: str
    valid_time: datetime
    outcome: IngestionOutcome
    raw_path: str | None = None
    processed_path: str | None = None
    qc: QCReport | None = None
    error: str | None = None


def ingest_one(
    source_key: str,
    valid_time: datetime,
    fetcher: Fetcher,
    lake: LakeWriter,
    checks: tuple[QCCheck, ...] = DEFAULT_CHECKS,
) -> IngestionRecord:
    """Fetch, QC-gate, and (if the gate passes) promote one source/time.

    Callers are expected to have already confirmed availability via
    `availability.AvailabilityOracle.published_at()` -- this function does
    the fetch-and-gate work, not the "is it time yet" work.
    """
    src = sources.get(source_key)
    if src.role is not Role.OPERATIONAL:
        return IngestionRecord(
            source_key, valid_time, IngestionOutcome.SKIPPED_NOT_OPERATIONAL
        )

    try:
        result = fetcher.fetch(source_key, valid_time)
    except FetchError as exc:
        return IngestionRecord(
            source_key, valid_time, IngestionOutcome.FETCH_FAILED, error=str(exc)
        )

    raw_path = lake.write(LakeTier.RAW, source_key, valid_time, result.raw_bytes)
    qc = run_qc_gate(result, checks)
    if not qc.passed:
        return IngestionRecord(
            source_key,
            valid_time,
            IngestionOutcome.QUARANTINED,
            raw_path=raw_path,
            qc=qc,
        )

    processed_path = lake.write(
        LakeTier.PROCESSED, source_key, valid_time, result.raw_bytes
    )
    return IngestionRecord(
        source_key,
        valid_time,
        IngestionOutcome.LANDED,
        raw_path=raw_path,
        processed_path=processed_path,
        qc=qc,
    )


def ingest_cycle_inputs(
    cycle_inputs,  # availability.CycleInputs -- typed loosely to avoid an import cycle
    fetchers: dict[str, Fetcher],
    lake: LakeWriter,
    checks: tuple[QCCheck, ...] = DEFAULT_CHECKS,
) -> list[IngestionRecord]:
    """Ingest every input the availability oracle reports as available for a
    resolved cycle. Sources without a registered fetcher are skipped rather
    than raising -- an incomplete fetcher roster is a deployment gap, not a
    bug in this function.
    """
    records: list[IngestionRecord] = []
    for status in cycle_inputs.statuses:
        if not status.available:
            continue
        fetcher = fetchers.get(status.source_key)
        if fetcher is None:
            continue
        records.append(
            ingest_one(status.source_key, status.valid_time, fetcher, lake, checks)
        )
    return records

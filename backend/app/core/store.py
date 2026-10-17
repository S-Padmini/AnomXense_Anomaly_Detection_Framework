from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any
import os
import time
import uuid

import pandas as pd


@dataclass
class DatasetSession:
    dataset_id: str
    filename: str
    file_size: int
    dataframe: pd.DataFrame
    summary: dict[str, Any]
    selected_columns: list[str]
    confirmed: bool = False
    preprocessed_df: pd.DataFrame | None = None
    preprocess_result: dict[str, Any] | None = None
    statistical_result: dict[str, Any] | None = None
    phase4_objective: dict[str, Any] | None = None
    phase4_recommendations: list[dict[str, Any]] | None = None
    phase4_confirmed: bool = False
    created_at: float = 0.0
    last_accessed: float = 0.0

    def touch(self) -> None:
        self.last_accessed = time.time()


class DatasetStore:
    """Thread-safe in-memory sessions for local/single-worker deployments.

    For multiple workers or production persistence, use shared storage. Large
    DataFrames remain in process memory until the session expires.
    """

    def __init__(self, ttl_seconds: int | None = None) -> None:
        self._sessions: dict[str, DatasetSession] = {}
        self._lock = RLock()
        configured_ttl = os.getenv("DATASET_SESSION_TTL_SECONDS", "3600")
        self.ttl_seconds = int(ttl_seconds if ttl_seconds is not None else configured_ttl)
        if self.ttl_seconds <= 0:
            raise ValueError("Dataset session TTL must be positive.")

    def create(
        self,
        *,
        filename: str,
        file_size: int,
        dataframe: pd.DataFrame,
        summary: dict[str, Any],
    ) -> DatasetSession:
        dataset_id = uuid.uuid4().hex
        now = time.time()
        session = DatasetSession(
            dataset_id=dataset_id,
            filename=filename,
            file_size=file_size,
            dataframe=dataframe,
            summary=summary,
            selected_columns=[str(column) for column in dataframe.columns],
            created_at=now,
            last_accessed=now,
        )
        with self._lock:
            self._cleanup_locked()
            self._sessions[dataset_id] = session
        return session

    def get(self, dataset_id: str) -> DatasetSession:
        with self._lock:
            self._cleanup_locked()
            session = self._sessions.get(dataset_id)
            if session is None:
                raise KeyError(dataset_id)
            session.touch()
            return session

    def delete(self, dataset_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(dataset_id, None) is not None

    def _cleanup_locked(self) -> None:
        cutoff = time.time() - self.ttl_seconds
        expired = [
            key for key, value in self._sessions.items()
            if value.last_accessed < cutoff
        ]
        for key in expired:
            self._sessions.pop(key, None)


store = DatasetStore()

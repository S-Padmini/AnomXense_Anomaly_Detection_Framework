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
    created_at: float = 0.0
    last_accessed: float = 0.0

    def touch(self) -> None:
        self.last_accessed = time.time()


class DatasetStore:
    """Small in-memory session store for local development.

    A production deployment with multiple workers should use shared storage
    (Redis/database/object storage) instead.
    """

    def __init__(self, ttl_seconds: int | None = None) -> None:
        self._sessions: dict[str, DatasetSession] = {}
        self._lock = RLock()
        self.ttl_seconds = ttl_seconds or int(os.getenv("DATASET_SESSION_TTL_SECONDS", "3600"))

    def create(self, *, filename: str, file_size: int, dataframe: pd.DataFrame,
               summary: dict[str, Any]) -> DatasetSession:
        dataset_id = uuid.uuid4().hex
        now = time.time()
        session = DatasetSession(
            dataset_id=dataset_id,
            filename=filename,
            file_size=file_size,
            dataframe=dataframe,
            summary=summary,
            selected_columns=[str(c) for c in dataframe.columns],
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

    def _cleanup_locked(self) -> None:
        cutoff = time.time() - self.ttl_seconds
        for key in [k for k, v in self._sessions.items() if v.last_accessed < cutoff]:
            self._sessions.pop(key, None)


store = DatasetStore()

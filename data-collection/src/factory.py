from __future__ import annotations

from typing import Optional

from psycopg2.extensions import connection

from .data_loader import DataLoader
from .data_processer import DataProcesser
from .table_init import TableInitializer


class Factory:
    _factory: Optional[Factory] = None

    def __init__(self, conn: connection) -> None:
        if Factory._factory is not None:
            raise Exception("Factory instance already exists. Use init_factory() instead.")
        self._conn = conn
        self._table_initializer: Optional[TableInitializer] = None
        self._data_loader: Optional[DataLoader] = None
        self._data_processer: Optional[DataProcesser] = None
        self._conn = conn

    @staticmethod
    def init_factory(conn: connection) -> Factory:
        if Factory._factory is None:
            Factory._factory = Factory(conn)
        return Factory._factory

    @staticmethod
    def get_factory() -> Factory:
        if Factory._factory is None:
            raise Exception("Factory instance not initialized. Use init_factory() first.")
        return Factory._factory

    def get_table_initializer(self) -> TableInitializer:
        if self._table_initializer is None:
            self._table_initializer = TableInitializer(self._conn)
        return self._table_initializer

    def get_data_loader(self) -> DataLoader:
        if self._data_loader is None:
            self._data_loader = DataLoader(self._conn)
        return self._data_loader

    def get_data_processer(self) -> DataProcesser:
        if self._data_processer is None:
            self._data_processer = DataProcesser(self._conn)
        return self._data_processer

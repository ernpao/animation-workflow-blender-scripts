import sqlite3
from typing import Optional


class DatabaseQueue:
    def __init__(
        self,
        table_name: str,
        primary_key_name: str,
        value_column_name: str,
        check_same_thread=False,
    ) -> None:
        self.con = sqlite3.connect(
            "F:\Code Repositories\Git Repositories\\animation-workflow-blender-scripts\modules\database\database.db",
            # "modules/database/database.db",
            check_same_thread=check_same_thread,
        )
        self.table_name = table_name
        self.primary_key_name = primary_key_name
        self.value_column_name = value_column_name

    def __fetchone(self, query: str):
        cur = self.con.execute(query)
        return cur.fetchone()

    def get_last_row(self) -> Optional[any]:
        query = f"SELECT {self.primary_key_name},{self.value_column_name} FROM {self.table_name} ORDER BY {self.primary_key_name} ASC LIMIT 1"
        return self.__fetchone(query)

    def is_empty(self) -> bool:
        if self.get_last_row() is None:
            return True
        else:
            return False

    def dequeue(self) -> Optional[str]:
        result = self.get_last_row()

        if result is not None:
            primary_key = result[0]
            value = result[1]

            query = f"DELETE FROM {self.table_name} WHERE {self.primary_key_name}={primary_key}"
            cur = self.con.cursor()
            cur.execute(query)
            self.con.commit()

            return value
        else:
            return None

    def enqueue(self, value: str) -> None:
        query = f"INSERT INTO {self.table_name} ({self.value_column_name}) VALUES ('{value}')"

        cur = self.con.cursor()
        cur.execute(query)
        self.con.commit()

    def clear(self):
        query = f"DELETE FROM {self.table_name}"
        cur = self.con.cursor()
        cur.execute(query)
        self.con.commit()

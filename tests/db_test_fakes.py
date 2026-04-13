"""Postgres cursor/connection fakes shared by test_db modules (not a pytest module)."""


class _FakeCursor:
    rowcount = 0

    def __init__(self, rows):
        self._rows = rows
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def close(self):
        return None


class _FakeConn:
    def __init__(self, rows):
        self.cursor_obj = _FakeCursor(rows)

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        pass

    def close(self):
        pass

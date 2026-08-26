"""Summary metrics for the dashboard's status cards."""
from __future__ import annotations

from app.db.connection import Database

_METRIC_QUERIES = {
    "Schools": "SELECT COUNT(*) FROM Schools",
    "Students": "SELECT COUNT(*) FROM Students",
    "Teams": "SELECT COUNT(*) FROM Teams",
    "Matches": "SELECT COUNT(*) FROM Matches",
    "Fantasy Users": "SELECT COUNT(*) FROM USERS",
    "Active Rounds": "SELECT COUNT(*) FROM ROUNDS WHERE status = 'Active'",
    "Squad Slots Filled": "SELECT COUNT(*) FROM USER_SQUADS",
    "Market Transactions": "SELECT COUNT(*) FROM TRANSACTIONS",
}


class DashboardService:
    @staticmethod
    def metrics() -> dict[str, int]:
        results: dict[str, int] = {}
        with Database.cursor() as cur:
            for label, sql in _METRIC_QUERIES.items():
                cur.execute(sql)
                results[label] = cur.fetchone()[0]
        return results

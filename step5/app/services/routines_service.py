"""Thin wrappers around the Stage D PL/pgSQL functions and procedures.

Every call goes through `Database.cursor_with_notices()` so RAISE NOTICE /
RAISE WARNING messages emitted by the routine (and by any trigger it fires,
e.g. trg_students_price_autocalc or trg_users_budget_audit) are captured and
handed back to the UI as real-time feedback, alongside the return value.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.db.connection import Database


@dataclass
class RoutineResult:
    value: object
    notices: list[str]


class RoutinesService:
    # -- Stage D Function 1 --------------------------------------------------
    @staticmethod
    def calculate_player_market_value(student_id: str) -> RoutineResult:
        with Database.cursor_with_notices() as (cur, notices):
            cur.execute("SELECT fn_calculate_player_market_value(%s);", [student_id])
            value = cur.fetchone()[0]
            messages = [n.strip() for n in notices]
        return RoutineResult(value, messages)

    # -- Stage D Function 2 --------------------------------------------------
    @staticmethod
    def evaluate_squad_compliance(user_id: int) -> RoutineResult:
        with Database.cursor_with_notices() as (cur, notices):
            cur.execute(
                "SELECT (fn_evaluate_squad_compliance(%s)).*;",
                [user_id],
            )
            row = cur.fetchone()
            col_names = [d[0] for d in cur.description]
            messages = [n.strip() for n in notices]
        value = dict(zip(col_names, row)) if row else None
        return RoutineResult(value, messages)

    # -- Stage D Procedure 1 --------------------------------------------------
    @staticmethod
    def process_player_transfer(user_id: int, player_id: str, action_type: str) -> RoutineResult:
        with Database.cursor_with_notices() as (cur, notices):
            cur.execute(
                "CALL sp_process_player_transfer(%s, %s, %s, %s, %s);",
                [user_id, player_id, action_type, None, None],
            )
            row = cur.fetchone()
            messages = [n.strip() for n in notices]
        success, message = (row[0], row[1]) if row else (False, "No result returned.")
        return RoutineResult({"success": success, "message": message}, messages)

    # -- Stage D Procedure 2 --------------------------------------------------
    @staticmethod
    def settle_round(round_id: int) -> RoutineResult:
        with Database.cursor_with_notices() as (cur, notices):
            cur.execute(
                "CALL sp_settle_round(%s, %s, %s);",
                [round_id, None, None],
            )
            row = cur.fetchone()
            messages = [n.strip() for n in notices]
        processed, errors = (row[0], row[1]) if row else (0, 0)
        return RoutineResult(
            {"players_processed": processed, "errors_encountered": errors}, messages
        )

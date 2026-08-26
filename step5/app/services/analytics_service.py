"""Stage B analytical queries + Stage C views, packaged as runnable reports
for the Analytics & Reports screen. Each report has exactly one interactive
numeric filter, bound with a parameterized placeholder (never string-formatted).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.db.connection import Database


@dataclass(frozen=True)
class ReportSpec:
    key: str
    label: str
    description: str
    sql: str                       # contains exactly one %s for the filter value
    filter_label: str
    filter_kind: str = "int"       # int | decimal
    filter_default: float = 1
    default_query: Optional[str] = None  # optional: compute a smarter default on load


REPORTS: list[ReportSpec] = [
    ReportSpec(
        key="goal_scorers",
        label="Top Goal Scorers & Offensive Performance",
        description=(
            "Forwards who scored at least the given number of goals, broken down "
            "by school and by the year/month the goals were scored in."
        ),
        sql="""
            SELECT
                s.first_name || ' ' || s.last_name AS player_full_name,
                sc.school_name,
                s.technical_rating,
                EXTRACT(YEAR FROM m.match_date)::INT AS match_year,
                TO_CHAR(m.match_date, 'Month') AS match_month,
                COUNT(me.event_id) AS total_goals_scored
            FROM Students s
            JOIN Schools sc ON s.school_id = sc.school_id
            JOIN Match_Events me ON s.student_id = me.student_id
            JOIN Matches m ON me.match_id = m.match_id
            WHERE s.preferred_position = 'Forward'
              AND me.event_type = 'Goal'
            GROUP BY s.student_id, s.first_name, s.last_name, sc.school_name,
                     s.technical_rating, EXTRACT(YEAR FROM m.match_date),
                     TO_CHAR(m.match_date, 'Month')
            HAVING COUNT(me.event_id) >= %s
            ORDER BY total_goals_scored DESC, s.technical_rating DESC
            LIMIT 200;
        """,
        filter_label="Minimum goals scored",
        filter_kind="int",
        filter_default=1,
    ),
    ReportSpec(
        key="field_maintenance",
        label="Facility Maintenance Budget Analysis",
        description=(
            "Artificial-turf fields whose cumulative maintenance spend exceeds the "
            "given dollar threshold (defaults to the league-wide per-field average)."
        ),
        sql="""
            SELECT
                f.field_name, f.city_address, f.surface_type,
                f.maintenance_status,
                SUM(ml.maintenance_cost) AS total_spent,
                COUNT(ml.log_date) AS inspection_count
            FROM Fields f
            JOIN Maintenance_Logs ml ON f.field_id = ml.field_id
            WHERE f.surface_type = 'Artificial Turf'
            GROUP BY f.field_id, f.field_name, f.city_address, f.surface_type,
                     f.maintenance_status
            HAVING SUM(ml.maintenance_cost) > %s
            ORDER BY total_spent DESC
            LIMIT 200;
        """,
        filter_label="Minimum total maintenance spend ($)",
        filter_kind="decimal",
        filter_default=3000,
        default_query="""
            SELECT COALESCE(AVG(total_per_field), 0)
            FROM (SELECT SUM(maintenance_cost) AS total_per_field
                  FROM Maintenance_Logs GROUP BY field_id) AS avg_table
        """,
    ),
    ReportSpec(
        key="top_market_players",
        label="Top Players by Market Value",
        description=(
            "Highest real-world goal-scoring / most valuable players, drawn from "
            "v_school_player_market_performance."
        ),
        sql="""
            SELECT full_name, school_name, team_name, preferred_position,
                   total_goals, current_price, fantasy_team_selections
            FROM v_school_player_market_performance
            ORDER BY total_goals DESC, current_price DESC
            LIMIT %s;
        """,
        filter_label="Result limit (top N)",
        filter_kind="int",
        filter_default=10,
    ),
    ReportSpec(
        key="top_fantasy_managers",
        label="Top Fantasy Managers by Net Worth",
        description=(
            "Fantasy users ranked by total club net worth (budget + squad market "
            "value), drawn from v_fantasy_user_portfolio_summary."
        ),
        sql="""
            SELECT user_name, current_budget, squad_market_value,
                   (current_budget + squad_market_value) AS total_club_net_worth,
                   distinct_schools_represented
            FROM v_fantasy_user_portfolio_summary
            WHERE total_squad_players > 0
            ORDER BY total_club_net_worth DESC
            LIMIT %s;
        """,
        filter_label="Result limit (top N)",
        filter_kind="int",
        filter_default=10,
    ),
]

REPORTS_BY_KEY = {r.key: r for r in REPORTS}


class AnalyticsService:
    @staticmethod
    def suggest_default(report: ReportSpec):
        if report.default_query is None:
            return report.filter_default
        with Database.cursor() as cur:
            cur.execute(report.default_query)
            value = cur.fetchone()[0]
        return value if value else report.filter_default

    @staticmethod
    def run(report: ReportSpec, filter_value) -> tuple[list[str], list[tuple]]:
        with Database.cursor() as cur:
            cur.execute(report.sql, [filter_value])
            col_names = [d[0] for d in cur.description]
            rows = cur.fetchall()
        return col_names, rows

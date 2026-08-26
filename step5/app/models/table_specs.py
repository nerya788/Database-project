"""Metadata-driven schema registry for the generic CRUD screen.

Every table in `school_football_db` (core school schema + the Stage C/D
"Fantasy League & Trading" partner tables) is described once here as a
`TableSpec`: its columns, their widget "kind", any enum choices, and - for
foreign keys - the lookup query used to populate a combo box with
human-readable labels while still storing the underlying id.

The generic CRUD view (app/ui/views/crud_view.py) and the generic CRUD
service (app/services/crud_service.py) both work purely off this metadata,
so adding a new table to the app means adding one TableSpec here, not a new
screen.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class FKRef:
    """A lookup query for a foreign key combo box.

    The query MUST return exactly two columns: (id_value, display_label).
    `params` binds any %s placeholders in `query` - used for cascading
    pickers scoped to a parent selection (e.g. "students in this school"),
    built fresh per selection via a factory function rather than a fixed
    module-level constant.
    """

    query: str
    params: tuple = ()


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    label: str
    kind: str = "text"  # text | int | decimal | date | time | datetime | bool | enum | fk
    choices: Optional[list[str]] = None       # for kind == "enum"
    fk: Optional[FKRef] = None                # for kind == "fk"
    pk: bool = False
    auto: bool = False        # DB-assigned (SERIAL, or a trigger) -> excluded from INSERT/UPDATE
    nullable: bool = False
    # If set on a PK column: the form hides this field entirely (no widget -
    # it carries no meaning a user should see or type) and the CRUD layer
    # silently runs this query on Create to compute its value, exactly like
    # a true SERIAL column would - just without database-level support.
    auto_generate_query: Optional[str] = None


@dataclass(frozen=True)
class TableSpec:
    key: str                    # unique registry key, used as nav id
    label: str                  # display name in the UI (nav / screen title)
    table: str                  # real table name in PostgreSQL
    columns: list[ColumnSpec]
    list_query: str             # human-readable (joined) SELECT for the grid
    readonly: bool = False      # True => list-only, no create/update/delete (e.g. audit log)
    help_text: str = ""
    # Singular, prose-friendly name for error dialogs - e.g. "This <entity_name>
    # cannot be deleted because it still has associated <other entity_name>
    # records...". Distinct from `label` (which is plural/nav-oriented, e.g.
    # "Students (Players)") so constraint-error sentences read naturally.
    entity_name: str = "record"
    # Names of list_query result columns that are fetched (needed to track
    # which row is selected) but never rendered in the grid - raw numeric
    # ids that a resolved, human-readable column already stands in for.
    grid_hidden_columns: list[str] = field(default_factory=list)

    @property
    def pk_columns(self) -> list[str]:
        return [c.name for c in self.columns if c.pk]

    @property
    def insert_columns(self) -> list[ColumnSpec]:
        return [c for c in self.columns if not c.auto]

    @property
    def editable_columns(self) -> list[ColumnSpec]:
        """Columns shown (and settable) on the Update form - everything but the PK."""
        return [c for c in self.columns if not c.pk]

    @property
    def auto_assigned_pk_column(self) -> Optional[str]:
        """The name of the PK column with an `auto_generate_query`, if any."""
        for c in self.columns:
            if c.pk and c.auto_generate_query:
                return c.name
        return None

    def suggest_pk_query(self) -> Optional[str]:
        """The `auto_generate_query` for `auto_assigned_pk_column`, if any."""
        for c in self.columns:
            if c.pk and c.auto_generate_query:
                return c.auto_generate_query
        return None


# ---------------------------------------------------------------------------
# Reusable FK lookup queries
# ---------------------------------------------------------------------------

FK_SCHOOLS = FKRef("SELECT school_id, school_name FROM Schools ORDER BY school_name")
FK_FIELDS = FKRef("SELECT field_id, field_name FROM Fields ORDER BY field_name")
FK_TEAMS = FKRef("SELECT team_id, team_name FROM Teams ORDER BY team_name")
FK_STUDENTS = FKRef(
    "SELECT student_id, first_name || ' ' || last_name "
    "FROM Students ORDER BY last_name, first_name"
)
FK_GLOBAL_EQUIPMENT = FKRef(
    "SELECT item_barcode, brand_model FROM Global_Equipment ORDER BY brand_model"
)
FK_USERS = FKRef("SELECT user_id, user_name FROM USERS ORDER BY user_name")
FK_ROUNDS = FKRef(
    "SELECT round_id, 'Round ' || round_number || '  (' || status || ')' "
    "FROM ROUNDS ORDER BY round_number"
)
FK_MATCHES = FKRef(
    "SELECT m.match_id, ht.team_name || ' vs ' || at.team_name || '  (' || m.match_date || ')' "
    "FROM Matches m "
    "JOIN Teams ht ON m.home_team_id = ht.team_id "
    "JOIN Teams at ON m.away_team_id = at.team_id "
    "ORDER BY m.match_date DESC"
)


def fk_students_by_school(school_id) -> FKRef:
    """Students scoped to one school (~50 rows) instead of all 25,000 -
    used to cascade a School picker into a Player picker so the player list
    never needs the search box to find anyone (e.g. every student sharing a
    common surname no longer floods the default, unfiltered view)."""
    return FKRef(
        "SELECT student_id, first_name || ' ' || last_name "
        "FROM Students WHERE school_id = %s ORDER BY last_name, first_name",
        params=(school_id,),
    )

# ---------------------------------------------------------------------------
# Enum choice lists (mirrors the PostgreSQL ENUM types in Setup_PostgreSQL.sql)
# ---------------------------------------------------------------------------

SURFACE_TYPES = ["Natural Grass", "Artificial Turf", "Hybrid"]
YES_NO = ["Yes", "No"]
FIELD_STATUSES = ["Operational", "Needs Renovation", "Closed"]
POSITIONS = ["Goalkeeper", "Defender", "Midfielder", "Forward"]
FEET = ["Right", "Left", "Both"]
AGE_GROUPS = ["U12", "U14", "U16", "U18"]
EQUIPMENT_STATUSES = ["Operational", "Under Repair", "Needs Inspection", "In Central Warehouse"]
GEAR_CATEGORIES = ["Balls", "Cones", "Vests", "Agility Ladders", "Goal Nets"]
SIZE_STANDARDS = ["Size 4", "Size 5", "Standard", "Junior"]
KIT_TYPES = ["First Aid Kit", "Ice Packs & Strapping", "Bandages & Tape", "Defibrillator & AED Kit"]
MATCH_STATUSES = ["Completed", "Scheduled", "Postponed", "In Progress"]
ROUND_STAGES = ["Round 1", "Round 2", "Round 3", "Quarter Final", "Semi Final", "Final"]
EVENT_TYPES = ["Goal", "Yellow Card", "Red Card", "Assist", "Substitution"]
LINEUP_STATUSES = ["Starting XI", "Bench"]
ACTION_TYPES = ["BUY", "SELL"]
ROUND_STATUSES = ["Upcoming", "Active", "Completed"]


# ---------------------------------------------------------------------------
# Table specs
# ---------------------------------------------------------------------------

SCHOOLS = TableSpec(
    key="schools",
    label="Schools",
    entity_name="School",
    table="Schools",
    help_text="Participating schools in the league.",
    columns=[
        ColumnSpec("school_id", "School ID", kind="int", pk=True, auto=True),
        ColumnSpec("school_name", "School Name"),
        ColumnSpec("city", "City"),
        ColumnSpec("full_address", "Full Address"),
        ColumnSpec("education_network", "Education Network"),
        ColumnSpec("sports_director_name", "Sports Director"),
        ColumnSpec("contact_phone", "Contact Phone"),
    ],
    list_query="""
        SELECT school_id, school_name, city, full_address,
               education_network, sports_director_name, contact_phone
        FROM Schools ORDER BY school_id
    """,
    grid_hidden_columns=["school_id"],
)

FIELDS = TableSpec(
    key="fields",
    label="Fields",
    entity_name="Field",
    table="Fields",
    help_text="Physical venues used for practices and matches.",
    columns=[
        ColumnSpec("field_id", "Field ID", kind="int", pk=True, auto=True),
        ColumnSpec("field_name", "Field Name"),
        ColumnSpec("city_address", "City / Address"),
        ColumnSpec("surface_type", "Surface Type", kind="enum", choices=SURFACE_TYPES),
        ColumnSpec("has_lighting", "Has Lighting", kind="enum", choices=YES_NO),
        ColumnSpec("maintenance_status", "Maintenance Status", kind="enum", choices=FIELD_STATUSES),
    ],
    list_query="""
        SELECT field_id, field_name, city_address, surface_type,
               has_lighting, maintenance_status
        FROM Fields ORDER BY field_id
    """,
    grid_hidden_columns=["field_id"],
)

STUDENTS = TableSpec(
    key="students",
    label="Students (Players)",
    entity_name="Student",
    table="Students",
    help_text="Player roster and profile information.",
    columns=[
        ColumnSpec(
            "student_id", "Student ID", kind="text", pk=True,
            auto_generate_query=(
                "SELECT (COALESCE(MAX(student_id::BIGINT), 100000000) + 1)::TEXT FROM Students"
            ),
        ),
        ColumnSpec("first_name", "First Name"),
        ColumnSpec("last_name", "Last Name"),
        ColumnSpec("birth_date", "Birth Date", kind="date"),
        ColumnSpec("school_id", "School", kind="fk", fk=FK_SCHOOLS),
        ColumnSpec("preferred_position", "Position", kind="enum", choices=POSITIONS),
        ColumnSpec("strong_foot", "Strong Foot", kind="enum", choices=FEET),
        ColumnSpec("join_date", "Join Date", kind="date"),
        ColumnSpec("technical_rating", "Technical Rating (1-100)", kind="int"),
        ColumnSpec("mental_rating", "Mental Rating (1-100)", kind="int"),
        ColumnSpec("current_price", "Market Price ($, auto)", kind="decimal", auto=True),
    ],
    list_query="""
        SELECT s.student_id, s.first_name, s.last_name, s.birth_date,
               sc.school_name, s.preferred_position, s.strong_foot,
               s.join_date, s.technical_rating, s.mental_rating, s.current_price
        FROM Students s JOIN Schools sc ON s.school_id = sc.school_id
        ORDER BY s.student_id
    """,
    grid_hidden_columns=["student_id"],
)

TEAMS = TableSpec(
    key="teams",
    label="Teams",
    entity_name="Team",
    table="Teams",
    columns=[
        ColumnSpec("team_id", "Team ID", kind="int", pk=True, auto=True),
        ColumnSpec("team_name", "Team Name"),
        ColumnSpec("school_id", "School", kind="fk", fk=FK_SCHOOLS),
        ColumnSpec("captain_student_id", "Captain", kind="fk", fk=FK_STUDENTS),
        ColumnSpec("age_group", "Age Group", kind="enum", choices=AGE_GROUPS),
        ColumnSpec("established_year", "Established Year", kind="int"),
    ],
    list_query="""
        SELECT t.team_id, t.team_name, sc.school_name,
               st.first_name || ' ' || st.last_name AS captain_name,
               t.age_group, t.established_year
        FROM Teams t
        JOIN Schools sc ON t.school_id = sc.school_id
        JOIN Students st ON t.captain_student_id = st.student_id
        ORDER BY t.team_id
    """,
    grid_hidden_columns=["team_id"],
)

GLOBAL_EQUIPMENT = TableSpec(
    key="global_equipment",
    label="Equipment (General)",
    entity_name="Equipment Item",
    table="Global_Equipment",
    columns=[
        ColumnSpec("item_barcode", "Item Barcode", kind="text", pk=True),
        ColumnSpec("brand_model", "Brand / Model"),
        ColumnSpec("purchase_date", "Purchase Date", kind="date"),
        ColumnSpec("unit_cost_usd", "Unit Cost ($)", kind="decimal"),
        ColumnSpec("current_status", "Status", kind="enum", choices=EQUIPMENT_STATUSES),
        ColumnSpec("school_id", "Assigned School", kind="fk", fk=FK_SCHOOLS, nullable=True),
        ColumnSpec("shipping_date", "Shipping Date", kind="date", nullable=True),
    ],
    list_query="""
        SELECT ge.item_barcode, ge.brand_model, ge.purchase_date, ge.unit_cost_usd,
               ge.current_status,
               COALESCE(sc.school_name, '(Unassigned - Central Warehouse)') AS assigned_school,
               ge.shipping_date
        FROM Global_Equipment ge LEFT JOIN Schools sc ON ge.school_id = sc.school_id
        ORDER BY ge.item_barcode
    """,
)

TRAINING_GEAR = TableSpec(
    key="training_gear",
    label="Training Gear",
    entity_name="Training Gear Item",
    table="Training_Gear",
    help_text="Select the equipment item this gear record belongs to.",
    columns=[
        ColumnSpec("item_barcode", "Equipment Item", kind="fk", fk=FK_GLOBAL_EQUIPMENT, pk=True),
        ColumnSpec("gear_category", "Gear Category", kind="enum", choices=GEAR_CATEGORIES),
        ColumnSpec("size_standard", "Size Standard", kind="enum", choices=SIZE_STANDARDS),
    ],
    list_query="""
        SELECT tg.item_barcode, ge.brand_model, tg.gear_category, tg.size_standard
        FROM Training_Gear tg JOIN Global_Equipment ge ON tg.item_barcode = ge.item_barcode
        ORDER BY tg.item_barcode
    """,
)

MEDICAL_KITS = TableSpec(
    key="medical_kits",
    label="Medical Kits",
    entity_name="Medical Kit",
    table="Medical_Kits",
    help_text="Select the equipment item this medical kit belongs to.",
    columns=[
        ColumnSpec("item_barcode", "Equipment Item", kind="fk", fk=FK_GLOBAL_EQUIPMENT, pk=True),
        ColumnSpec("kit_type", "Kit Type", kind="enum", choices=KIT_TYPES),
        ColumnSpec("expiry_date", "Expiry Date", kind="date"),
        ColumnSpec("is_sterile", "Is Sterile", kind="bool"),
    ],
    list_query="""
        SELECT mk.item_barcode, ge.brand_model, mk.kit_type, mk.expiry_date, mk.is_sterile
        FROM Medical_Kits mk JOIN Global_Equipment ge ON mk.item_barcode = ge.item_barcode
        ORDER BY mk.item_barcode
    """,
)

PRACTICES = TableSpec(
    key="practices",
    label="Practices",
    entity_name="Practice",
    table="Practices",
    columns=[
        ColumnSpec("practice_id", "Practice ID", kind="int", pk=True, auto=True),
        ColumnSpec("team_id", "Team", kind="fk", fk=FK_TEAMS),
        ColumnSpec("field_id", "Field", kind="fk", fk=FK_FIELDS),
        ColumnSpec("practice_date", "Practice Date", kind="date"),
        ColumnSpec("start_time", "Start Time (HH:MM)", kind="time"),
        ColumnSpec("duration_minutes", "Duration (min)", kind="int"),
        ColumnSpec("practice_topic", "Topic"),
    ],
    list_query="""
        SELECT p.practice_id, t.team_name, f.field_name, p.practice_date,
               p.start_time, p.duration_minutes, p.practice_topic
        FROM Practices p JOIN Teams t ON p.team_id = t.team_id
        JOIN Fields f ON p.field_id = f.field_id
        ORDER BY p.practice_id
    """,
    grid_hidden_columns=["practice_id"],
)

MATCHES = TableSpec(
    key="matches",
    label="Matches",
    entity_name="Match",
    table="Matches",
    columns=[
        ColumnSpec("match_id", "Match ID", kind="int", pk=True, auto=True),
        ColumnSpec("home_team_id", "Home Team", kind="fk", fk=FK_TEAMS),
        ColumnSpec("away_team_id", "Away Team", kind="fk", fk=FK_TEAMS),
        ColumnSpec("field_id", "Field", kind="fk", fk=FK_FIELDS),
        ColumnSpec("match_date", "Match Date", kind="date"),
        ColumnSpec("start_time", "Start Time (HH:MM)", kind="time"),
        ColumnSpec("home_score", "Home Score", kind="int"),
        ColumnSpec("away_score", "Away Score", kind="int"),
        ColumnSpec("match_status", "Status", kind="enum", choices=MATCH_STATUSES),
        ColumnSpec("round_stage", "Round Stage", kind="enum", choices=ROUND_STAGES),
        ColumnSpec("referee_name", "Referee"),
    ],
    list_query="""
        SELECT m.match_id, ht.team_name AS home_team, at.team_name AS away_team,
               f.field_name, m.match_date, m.start_time, m.home_score, m.away_score,
               m.match_status, m.round_stage, m.referee_name
        FROM Matches m
        JOIN Teams ht ON m.home_team_id = ht.team_id
        JOIN Teams at ON m.away_team_id = at.team_id
        JOIN Fields f ON m.field_id = f.field_id
        ORDER BY m.match_id
    """,
    grid_hidden_columns=["match_id"],
)

MAINTENANCE_LOGS = TableSpec(
    key="maintenance_logs",
    label="Maintenance Logs",
    entity_name="Maintenance Log Entry",
    table="Maintenance_Logs",
    help_text="Each entry is tied to a specific field and date, which cannot be changed later.",
    columns=[
        ColumnSpec("field_id", "Field", kind="fk", fk=FK_FIELDS, pk=True),
        ColumnSpec("log_date", "Log Date", kind="date", pk=True),
        ColumnSpec("performed_by", "Performed By"),
        ColumnSpec("maintenance_cost", "Cost ($)", kind="decimal"),
        ColumnSpec("work_summary", "Work Summary"),
        ColumnSpec("safety_passed", "Safety Passed", kind="bool"),
    ],
    list_query="""
        SELECT ml.field_id, f.field_name, ml.log_date, ml.performed_by,
               ml.maintenance_cost, ml.work_summary, ml.safety_passed
        FROM Maintenance_Logs ml JOIN Fields f ON ml.field_id = f.field_id
        ORDER BY ml.field_id, ml.log_date
    """,
    grid_hidden_columns=["field_id"],
)

MATCH_EVENTS = TableSpec(
    key="match_events",
    label="Match Events",
    entity_name="Match Event",
    table="Match_Events",
    columns=[
        ColumnSpec("event_id", "Event ID", kind="int", pk=True, auto=True),
        ColumnSpec("match_id", "Match", kind="fk", fk=FK_MATCHES),
        ColumnSpec("student_id", "Player", kind="fk", fk=FK_STUDENTS),
        ColumnSpec("minute_in_game", "Minute (1-120)", kind="int"),
        ColumnSpec("event_type", "Event Type", kind="enum", choices=EVENT_TYPES),
        ColumnSpec("description", "Description", nullable=True),
    ],
    list_query="""
        SELECT me.event_id,
               ht.team_name || ' vs ' || at.team_name || '  (' || m.match_date || ')' AS match_label,
               s.first_name || ' ' || s.last_name AS player_name,
               me.minute_in_game, me.event_type, me.description
        FROM Match_Events me
        JOIN Matches m ON me.match_id = m.match_id
        JOIN Teams ht ON m.home_team_id = ht.team_id
        JOIN Teams at ON m.away_team_id = at.team_id
        JOIN Students s ON me.student_id = s.student_id
        ORDER BY me.event_id
    """,
    grid_hidden_columns=["event_id"],
)

TEAM_PLAYERS = TableSpec(
    key="team_players",
    label="Team Rosters",
    entity_name="Roster Entry",
    table="Team_Players",
    help_text="Defines which students are on which team's roster.",
    columns=[
        ColumnSpec("team_id", "Team", kind="fk", fk=FK_TEAMS, pk=True),
        ColumnSpec("student_id", "Student", kind="fk", fk=FK_STUDENTS, pk=True),
    ],
    list_query="""
        SELECT tp.team_id, t.team_name, tp.student_id,
               s.first_name || ' ' || s.last_name AS player_name
        FROM Team_Players tp
        JOIN Teams t ON tp.team_id = t.team_id
        JOIN Students s ON tp.student_id = s.student_id
        ORDER BY tp.team_id, tp.student_id
    """,
    grid_hidden_columns=["team_id", "student_id"],
)

FANTASY_USERS = TableSpec(
    key="fantasy_users",
    label="Fantasy Users",
    entity_name="Fantasy User",
    table="USERS",
    help_text="A manager's budget can never be reduced below zero.",
    columns=[
        ColumnSpec(
            "user_id", "User ID", kind="int", pk=True,
            auto_generate_query="SELECT COALESCE(MAX(user_id), 0) + 1 FROM USERS",
        ),
        ColumnSpec("user_name", "User Name"),
        ColumnSpec("current_budget", "Current Budget ($)", kind="decimal"),
    ],
    list_query="SELECT user_id, user_name, current_budget FROM USERS ORDER BY user_id",
    grid_hidden_columns=["user_id"],
)

ROUNDS = TableSpec(
    key="rounds",
    label="Fantasy Rounds",
    entity_name="Round",
    table="ROUNDS",
    columns=[
        ColumnSpec(
            "round_id", "Round ID", kind="int", pk=True,
            auto_generate_query="SELECT COALESCE(MAX(round_id), 0) + 1 FROM ROUNDS",
        ),
        ColumnSpec("round_number", "Round Number", kind="int"),
        ColumnSpec("start_date", "Start Date", kind="date"),
        ColumnSpec("end_date", "End Date", kind="date"),
        ColumnSpec("status", "Status", kind="enum", choices=ROUND_STATUSES),
    ],
    list_query="""
        SELECT round_id, round_number, start_date, end_date, status
        FROM ROUNDS ORDER BY round_id
    """,
    grid_hidden_columns=["round_id"],
)

USER_SQUADS = TableSpec(
    key="user_squads",
    label="Fantasy Squads",
    entity_name="Squad Entry",
    table="USER_SQUADS",
    columns=[
        ColumnSpec(
            "squad_record_id", "Squad Record ID", kind="int", pk=True,
            auto_generate_query="SELECT COALESCE(MAX(squad_record_id), 0) + 1 FROM USER_SQUADS",
        ),
        ColumnSpec("lineup_status", "Lineup Status", kind="enum", choices=LINEUP_STATUSES),
        ColumnSpec("user_id", "Fantasy User", kind="fk", fk=FK_USERS),
        ColumnSpec("player_id", "Player", kind="fk", fk=FK_STUDENTS),
    ],
    list_query="""
        SELECT us.squad_record_id, u.user_name,
               s.first_name || ' ' || s.last_name AS player_name, us.lineup_status
        FROM USER_SQUADS us
        JOIN USERS u ON us.user_id = u.user_id
        JOIN Students s ON us.player_id = s.student_id
        ORDER BY us.squad_record_id
    """,
    grid_hidden_columns=["squad_record_id"],
)

TRANSACTIONS = TableSpec(
    key="transactions",
    label="Market Transactions",
    entity_name="Transaction",
    table="TRANSACTIONS",
    help_text="New purchases and sales are best made from the Actions screen, which keeps "
              "manager budgets and squads in sync automatically.",
    columns=[
        ColumnSpec(
            "transaction_id", "Transaction ID", kind="int", pk=True,
            auto_generate_query="SELECT COALESCE(MAX(transaction_id), 0) + 1 FROM TRANSACTIONS",
        ),
        ColumnSpec("transaction_time", "Transaction Time", kind="datetime"),
        ColumnSpec("action_type", "Action", kind="enum", choices=ACTION_TYPES),
        ColumnSpec("transaction_price", "Price ($)", kind="decimal"),
        ColumnSpec("user_id", "Fantasy User", kind="fk", fk=FK_USERS),
        ColumnSpec("player_id", "Player", kind="fk", fk=FK_STUDENTS),
    ],
    list_query="""
        SELECT tx.transaction_id, u.user_name,
               s.first_name || ' ' || s.last_name AS player_name,
               tx.action_type, tx.transaction_price, tx.transaction_time
        FROM TRANSACTIONS tx
        JOIN USERS u ON tx.user_id = u.user_id
        JOIN Students s ON tx.player_id = s.student_id
        ORDER BY tx.transaction_id
    """,
    grid_hidden_columns=["transaction_id"],
)

PRICE_HISTORY = TableSpec(
    key="price_history",
    label="Price History",
    entity_name="Price History Entry",
    table="PRICE_HISTORY",
    help_text="Price snapshots are normally generated automatically when a league round is settled.",
    columns=[
        ColumnSpec(
            "history_id", "History ID", kind="int", pk=True,
            auto_generate_query="SELECT COALESCE(MAX(history_id), 0) + 1 FROM PRICE_HISTORY",
        ),
        ColumnSpec("recorded_price", "Recorded Price ($)", kind="decimal"),
        ColumnSpec("player_id", "Player", kind="fk", fk=FK_STUDENTS),
        ColumnSpec("round_id", "Round", kind="fk", fk=FK_ROUNDS),
    ],
    list_query="""
        SELECT ph.history_id, s.first_name || ' ' || s.last_name AS player_name,
               ph.recorded_price, r.round_number, ph.round_id
        FROM PRICE_HISTORY ph
        JOIN Students s ON ph.player_id = s.student_id
        JOIN ROUNDS r ON ph.round_id = r.round_id
        ORDER BY ph.history_id
    """,
    grid_hidden_columns=["history_id", "round_id"],
)

BUDGET_AUDIT_LOG = TableSpec(
    key="budget_audit_log",
    label="Budget Audit Log",
    entity_name="Audit Log Entry",
    table="Budget_Audit_Log",
    readonly=True,
    help_text="A read-only history of every change to manager budgets.",
    columns=[
        ColumnSpec("audit_id", "Audit ID", kind="int", pk=True, auto=True),
        ColumnSpec("user_id", "Fantasy User", kind="fk", fk=FK_USERS),
        ColumnSpec("old_budget", "Old Budget ($)", kind="decimal"),
        ColumnSpec("new_budget", "New Budget ($)", kind="decimal"),
        ColumnSpec("change_amount", "Change ($)", kind="decimal"),
        ColumnSpec("changed_at", "Changed At", kind="datetime", auto=True),
    ],
    list_query="""
        SELECT ba.audit_id, u.user_name, ba.old_budget, ba.new_budget,
               ba.change_amount, ba.changed_at
        FROM Budget_Audit_Log ba JOIN USERS u ON ba.user_id = u.user_id
        ORDER BY ba.audit_id
    """,
    grid_hidden_columns=["audit_id"],
)


# ---------------------------------------------------------------------------
# Registry: grouped for the sidebar entity picker, in display order
# ---------------------------------------------------------------------------

TABLE_GROUPS: list[tuple[str, list[TableSpec]]] = [
    ("Core School Data", [SCHOOLS, FIELDS, STUDENTS, TEAMS]),
    ("Equipment & Facilities", [GLOBAL_EQUIPMENT, TRAINING_GEAR, MEDICAL_KITS, MAINTENANCE_LOGS]),
    ("Matches & Activities", [PRACTICES, MATCHES, MATCH_EVENTS, TEAM_PLAYERS]),
    ("Fantasy League & Trading", [FANTASY_USERS, ROUNDS, USER_SQUADS, TRANSACTIONS,
                                   PRICE_HISTORY, BUDGET_AUDIT_LOG]),
]

TABLE_SPECS: dict[str, TableSpec] = {
    spec.key: spec for _, specs in TABLE_GROUPS for spec in specs
}


def get_spec(key: str) -> TableSpec:
    return TABLE_SPECS[key]

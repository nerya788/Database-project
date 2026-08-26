# Stage E - School Football & Fantasy League Manager (Desktop GUI)

A desktop GUI for `school_football_db` (PostgreSQL 18): the core school
football schema plus the Stage C/D "Fantasy League & Trading" partner
system. Built with **CustomTkinter** (UI) and **psycopg2** (database access).

> This app targets the schema and PL/pgSQL routines that actually exist in
> this repository (`step1`-`step4`) - `Students`, `Teams`, `USERS`,
> `USER_SQUADS`, `ROUNDS`, `TRANSACTIONS`, `PRICE_HISTORY`, etc., and the
> Stage D routines `fn_calculate_player_market_value`,
> `fn_evaluate_squad_compliance`, `sp_process_player_transfer`, and
> `sp_settle_round`. Run `step1`-`step4` against your database first.

## Features

- **Dashboard** - live connection status, summary metrics (row counts,
  active rounds, etc.), quick navigation.
- **Manage Data** - one generic, metadata-driven CRUD screen covering all
  18 tables (grouped: Core School Data / Equipment & Facilities /
  Matches & Activities / Fantasy League & Trading). Every foreign key is
  shown as a searchable dropdown of human-readable labels (never a raw id);
  selecting a row in the grid auto-populates the form for editing.
- **Analytics & Reports** - two Stage B analytical queries (Goal Scorers,
  Facility Maintenance Budget) and two Stage C view-based reports (Top
  Players by Market Value, Top Fantasy Managers by Net Worth), each with
  one interactive numeric filter and a background-threaded, non-blocking run.
- **Stage D Routines** - interactive execution of both PL/pgSQL functions
  and both procedures, with live `RAISE NOTICE` feedback and result panels.
- Dark / light / system theme, graceful error dialogs for constraint
  violations, and background threads with loading indicators for any
  query or routine call.

## Project layout

```
step5/
  main.py                       entry point
  requirements.txt
  .env.example                  copy to .env and fill in real credentials
  app/
    config.py                   env-based configuration
    db/connection.py            pooled psycopg2 connection manager
    models/
      table_specs.py            schema metadata for every CRUD table
      parsing.py                form value <-> Python/SQL value coercion
    services/
      crud_service.py           generic list/get/insert/update/delete
      analytics_service.py      Stage B/C report definitions + execution
      routines_service.py       Stage D function/procedure wrappers
      dashboard_service.py      summary metric queries
    ui/
      app_window.py              main window + sidebar navigation
      theme.py, dialogs.py, async_utils.py
      widgets/data_table.py       searchable results grid
      views/
        dashboard_view.py, crud_view.py, analytics_view.py, routines_view.py
```

## Setup

1. **Create a virtual environment** (from inside `step5/`):

   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # macOS/Linux
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the database connection:**

   Copy `.env.example` to `.env` and fill in your real PostgreSQL
   credentials:

   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=school_football_db
   DB_USER=postgres
   DB_PASSWORD=your_password_here
   ```

   `.env` is git-ignored - never commit real credentials in
   `.env.example`.

4. **Run the app:**

   ```bash
   python main.py
   ```

## Notes

- `Students.current_price` and `Budget_Audit_Log` are populated
  automatically by the `trg_students_price_autocalc` and
  `trg_users_budget_audit` triggers (step4) - the UI shows them as
  read-only.
- For BUY/SELL transactions, prefer the **Stage D Routines -> Process
  Player Transfer** action over manually inserting a `TRANSACTIONS` row -
  it keeps budgets, squads and the transaction log consistent via
  `sp_process_player_transfer`.
- The "Manage Data" screen adds one table (`TableSpec`) per entity in
  `app/models/table_specs.py`; adding a new table to the app means adding
  one spec there, not a new screen.

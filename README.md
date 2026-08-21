# Database Systems Project – Stage A
## School Football Management System (`school_football_db`)

**Student Name:** Nerya Cohen | **Student ID:** 316482801
**Submission Date:** 20/08/2026  
**Environment:** MySQL 8.x / 9.x, VS Code, SQL, python3.13, ERDPlus  

---

## 1. System Overview & Architecture

This database system manages an extensive national school football league, integrating athletic, administrative, and logistical operations:
- **Institutions & Teams:** Tracks participating schools, age-bracketed teams, and team captains.
- **Athletes & Performance:** Maintains detailed profiles for students, playing positions, strong-foot attributes, and technical/mental ability ratings.
- **Scheduling & Fixtures:** Manages official match schedules, live scores, round stages, referee assignments, and training sessions across designated sports facilities.
- **Inventory & Logistics:** Tracks global equipment acquisitions, purchase and shipping timelines, unit costs, and school-level asset allocations.

The database is normalized to **Third Normal Form (3NF)** to eliminate data redundancy and preserve strict referential integrity.

---

## 2. System Diagrams

### 2.1 Entity Relationship Diagram (ERD)
Conceptual model displaying 7 entities, attributes, primary keys, and relationship cardinalities using Chen's notation.

![ERD Diagram](images/ERD.png)

---

### 2.2 Relational Schema Diagram (DSD)
Logical model depicting physical relational tables, column data types, Primary Keys (PK), Foreign Keys (FK), and relational constraints.

![DSD Diagram](images/DSD.png)

---

## 3. Data Dictionary

The database consists of 7 relational tables populating a total of **52,500 records**.

### Table 1: `Schools`
Represents participating educational institutions (500 rows).
| Column Name | Data Type | Constraints / Defaults | Description |
| :--- | :--- | :--- | :--- |
| `school_id` | `INT` | `PRIMARY KEY`, `AUTO_INCREMENT` | Unique identifier for each school |
| `school_name` | `VARCHAR(100)` | `NOT NULL` | Name of the educational institution |
| `city` | `VARCHAR(50)` | `NOT NULL` | City where the school is located |
| `education_network` | `VARCHAR(50)` | `NOT NULL` | Associated educational network |
| `contact_phone` | `VARCHAR(20)` | `NOT NULL` | Administrative contact phone number |
| `sports_director_name` | `VARCHAR(100)` | `NOT NULL` | Name of the sports department director |
| `full_address` | `VARCHAR(255)` | `NOT NULL` | Complete street address |

---

### Table 2: `Fields`
Represents sports venues and match fields (500 rows).
| Column Name | Data Type | Constraints / Defaults | Description |
| :--- | :--- | :--- | :--- |
| `field_id` | `INT` | `PRIMARY KEY`, `AUTO_INCREMENT` | Unique field identifier |
| `field_name` | `VARCHAR(100)` | `NOT NULL` | Facility/field name |
| `city_address` | `VARCHAR(100)` | `NOT NULL` | Physical location and city |
| `surface_type` | `VARCHAR(30)` | `NOT NULL`, `CHECK` | Surface type (e.g., Natural Grass, Artificial Turf) |
| `has_lighting` | `BOOLEAN` | `NOT NULL` | Night lighting availability flag |
| `capacity` | `INT` | `NOT NULL`, `CHECK (capacity >= 0)` | Spectator seating capacity |
| `maintenance_status` | `VARCHAR(30)` | `NOT NULL` | Current field maintenance status |

---

### Table 3: `Students` (Large Table #1)
Represents enrolled student-athletes (25,000 rows).
| Column Name | Data Type | Constraints / Defaults | Description |
| :--- | :--- | :--- | :--- |
| `student_id` | `INT` | `PRIMARY KEY`, `AUTO_INCREMENT` | Unique student identification number |
| `school_id` | `INT` | `NOT NULL`, `FK` $\rightarrow$ `Schools(school_id)` | Enrolled school reference |
| `first_name` | `VARCHAR(50)` | `NOT NULL` | Student first name |
| `last_name` | `VARCHAR(50)` | `NOT NULL` | Student last name |
| `birth_date` | `DATE` | `NOT NULL` | Date of birth |
| `join_date` | `DATE` | `NOT NULL` | System registration date |
| `preferred_position` | `VARCHAR(30)` | `NOT NULL`, `CHECK` | Tactical playing position |
| `strong_foot` | `VARCHAR(10)` | `NOT NULL`, `CHECK` (Right, Left, Both) | Dominant playing foot |
| `technical_rating` | `INT` | `CHECK (1 TO 100)` | Assessed technical skill rating |
| `mental_rating` | `INT` | `CHECK (1 TO 100)` | Assessed mental/tactical rating |

---

### Table 4: `Teams`
Represents school football squads across age tiers (500 rows).
| Column Name | Data Type | Constraints / Defaults | Description |
| :--- | :--- | :--- | :--- |
| `team_id` | `INT` | `PRIMARY KEY`, `AUTO_INCREMENT` | Unique team identifier |
| `school_id` | `INT` | `NOT NULL`, `FK` $\rightarrow$ `Schools(school_id)` | Represented school |
| `captain_student_id` | `INT` | `NOT NULL`, `UNIQUE`, `FK` $\rightarrow$ `Students` | Assigned team captain (1:1 relation) |
| `team_name` | `VARCHAR(100)` | `NOT NULL` | Official team name |
| `age_group` | `VARCHAR(20)` | `NOT NULL` | Age bracket (U14, U16, U18) |
| `established_year` | `INT` | `NOT NULL`, `CHECK (1900 TO 2026)` | Founding year |

---

### Table 5: `Global_Equipment` (Large Table #2)
Represents the league's global equipment inventory (25,000 rows).
| Column Name | Data Type | Constraints / Defaults | Description |
| :--- | :--- | :--- | :--- |
| `item_barcode` | `VARCHAR(64)` | `PRIMARY KEY` | Unique scannable barcode string |
| `school_id` | `INT` | `NULL`, `FK` $\rightarrow$ `Schools(school_id)` | School allocation (`NULL` = Central Warehouse) |
| `item_type` | `VARCHAR(50)` | `NOT NULL` | Gear category (Balls, Cones, Vests, etc.) |
| `brand_model` | `VARCHAR(100)` | `NOT NULL` | Manufacturer and model identifier |
| `purchase_date` | `DATE` | `NOT NULL` | Procurement date |
| `shipping_date` | `DATE` | `NULL`, `CHECK (shipping_date >= purchase_date)` | Delivery date |
| `unit_cost_usd` | `DECIMAL(8,2)` | `NOT NULL`, `CHECK (unit_cost_usd > 0)` | Unit purchase cost in USD |
| `current_status` | `VARCHAR(30)` | `NOT NULL` | Operational condition and status |

---

### Table 6: `Practices`
Represents scheduled team training sessions (500 rows).
| Column Name | Data Type | Constraints / Defaults | Description |
| :--- | :--- | :--- | :--- |
| `practice_id` | `INT` | `PRIMARY KEY`, `AUTO_INCREMENT` | Unique practice session ID |
| `team_id` | `INT` | `NOT NULL`, `FK` $\rightarrow$ `Teams(team_id)` | Participating team |
| `field_id` | `INT` | `NOT NULL`, `FK` $\rightarrow$ `Fields(field_id)` | Training venue |
| `start_timestamp` | `DATETIME` | `NOT NULL` | Session start timestamp |
| `duration_minutes` | `INT` | `NOT NULL`, `CHECK (duration_minutes > 0)` | Total duration in minutes |
| `practice_topic` | `VARCHAR(100)` | `NOT NULL` | Main tactical/physical focus |

---

### Table 7: `Matches`
Represents official competitive fixtures (500 rows).
| Column Name | Data Type | Constraints / Defaults | Description |
| :--- | :--- | :--- | :--- |
| `match_id` | `INT` | `PRIMARY KEY`, `AUTO_INCREMENT` | Unique match identifier |
| `home_team_id` | `INT` | `NOT NULL`, `FK` $\rightarrow$ `Teams(team_id)` | Designated home team |
| `away_team_id` | `INT` | `NOT NULL`, `FK` $\rightarrow$ `Teams(team_id)` | Designated away team |
| `field_id` | `INT` | `NOT NULL`, `FK` $\rightarrow$ `Fields(field_id)` | Match venue |
| `match_date` | `DATE` | `NOT NULL` | Scheduled match date |
| `start_time` | `TIME` | `NOT NULL` | Kickoff time |
| `home_score` | `INT` | `NOT NULL`, `CHECK (home_score >= 0)` | Goals scored by home team |
| `away_score` | `INT` | `NOT NULL`, `CHECK (away_score >= 0)` | Goals scored by away team |
| `match_status` | `VARCHAR(30)` | `NOT NULL` | Fixture status (e.g., Completed, Rescheduled) |
| `referee_name` | `VARCHAR(100)` | `NOT NULL` | Appointed match official |
| `round_stage` | `VARCHAR(50)` | `NOT NULL` | Tournament stage or league round |

---

## 4. Data Generation & Ingestion Methodology

The dataset was synthesized and ingested using three complementary methodologies:

1. **External Mock Generators (Mockaroo / Import Files):**  
   Initial data structures and realistic naming conventions for categorical reference sets.
2. **Programmatic Data Generation (Python):**  
   Custom Python scripts using data synthesis logic to populate the two high-volume tables (`Students` and `Global_Equipment`, 25,000 rows each). This ensured realistic statistical distributions, relational coherence, and constraint adherence.
3. **Direct SQL Data Manipulation (`insertTables.sql`):**  
   Consolidated DML batch operations structured to respect foreign key dependency hierarchies.

### 4.1 Programmatic Data Generation Pipeline (`generate_data.py`)

The dataset was generated using a custom Python pipeline that ensures relational consistency, valid foreign key references, and logical domain constraints across all 52,500 records:

```python
import random

with open("../insertTables.sql", "w", encoding="utf-8") as f:
    f.write("-- School Football League Database Mass Insert Script\n\n")

    # 1. Schools (500)
    for s_id in range(1, 501):
        city = random.choice(cities)
        f.write(
            f"INSERT INTO Schools VALUES ({s_id}, '{city} School #{s_id}', "
            f"'{city}', '{random.randint(1,100)} Main St', "
            f"'{random.choice(networks)}', "
            f"'{random.choice(first_names)} {random.choice(last_names)}', "
            f"'050-{random.randint(1000000,9999999)}');\n"
        )
        
    # 2. Fields (500)
    for f_id in range(1, 501):
        city = random.choice(cities)
        f.write(
            f"INSERT INTO Fields VALUES ({f_id}, '{city} Arena #{f_id}', "
            f"'{random.randint(1,100)} Sports Ave', "
            f"'{random.choice(surfaces)}', "
            f"'{random.choice(['Yes', 'No'])}', "
            f"'{random.choice(['Operational', 'Needs Renovation', 'Closed'])}');\n"
        )

    # 3. Students (25,000)
    student_ids = [f"{i:09d}" for i in range(100000001, 100025001)]
    for st_id in student_ids:
        f.write(
            f"INSERT INTO Students VALUES ('{st_id}', "
            f"'{random.choice(first_names)}', '{random.choice(last_names)}', "
            f"'{random_date(2008, 2014)}', {random.randint(1, 500)}, "
            f"'{random.choice(positions)}', '{random.choice(feet)}', "
            f"'{random_date(2024, 2026)}', {random.randint(30, 99)}, "
            f"{random.randint(30, 99)});\n"
        )

    # 4. Teams (500)
    for t_id in range(1, 501):
        f.write(
            f"INSERT INTO Teams VALUES ({t_id}, 'Team #{t_id}', {t_id}, "
            f"'{student_ids[t_id - 1]}', "
            f"'{random.choice(['U12', 'U14', 'U16', 'U18'])}', "
            f"{random.randint(2015, 2024)});\n"
        )

    # 5. Global_Equipment (25,000)
    for eq_id in range(1, 25001):
        st = random.choice(equip_statuses)
        sc = "NULL" if st == 'In Central Warehouse' else str(random.randint(1, 500))
        sh_d = "NULL" if sc == "NULL" else f"'{random_date(2025, 2026)}'"
        f.write(
            f"INSERT INTO Global_Equipment VALUES ('EQP-{eq_id:06d}', "
            f"'{random.choice(equip_types)}', '{random.choice(equip_brands)}', "
            f"'{random_date(2022, 2024)}', {round(random.uniform(15, 120), 2)}, "
            f"'{st}', {sc}, {sh_d});\n"
        )

    # 6. Practices (500)
    for pr_id in range(1, 501):
        f.write(
            f"INSERT INTO Practices VALUES ({pr_id}, {random.randint(1, 500)}, "
            f"{random.randint(1, 500)}, '{random_date(2025, 2026)}', "
            f"'{random.randint(15, 20):02d}:00', {random.choice([60, 90, 120])}, "
            f"'{random.choice(practice_topics)}');\n"
        )

    # 7. Matches (500)
    for m_id in range(1, 501):
        h_team = random.randint(1, 250)
        a_team = random.randint(251, 500)
        f.write(
            f"INSERT INTO Matches VALUES ({m_id}, {h_team}, {a_team}, "
            f"{random.randint(1, 500)}, '{random_date(2025, 2026)}', '18:00', "
            f"{random.randint(0, 5)}, {random.randint(0, 5)}, "
            f"'{random.choice(match_statuses)}', '{random.choice(rounds)}', "
            f"'{random.choice(referees)}');\n"
        )

    f.write("COMMIT;\n")
```

---

## 5. Dataset Validation & Row Count Verification

Row counts and integrity checks were validated using `selectAll.sql`:

| Table Name | Actual Row Count | Minimum Academic Requirement | Status |
| :--- | :--- | :--- | :--- |
| `Schools` | **500** | $\ge 500$ | Passed |
| `Fields` | **500** | $\ge 500$ | Passed |
| `Students` | **25,000** | $\ge 10,000$ (Large Table 1) | Passed |
| `Teams` | **500** | $\ge 500$ | Passed |
| `Global_Equipment` | **25,000** | $\ge 10,000$ (Large Table 2) | Passed |
| `Practices` | **500** | $\ge 500$ | Passed |
| `Matches` | **500** | $\ge 500$ | Passed |
| **Total Records** | **52,500** | **Comprehensive Target Met** | **Passed** |

### 5.1 Verification Query Execution Result
Below is the execution output confirming the populated rows across all entities:

![Database Record Count Verification](images/verification_results.png)

---

## 6. Backup & Recovery Procedures

Database schemas and data were backed up using two independent methodologies:

### 6.1 Command Line Interface Backup (CLI - `mysqldump`)
Executed via command line terminal to `step1/backup_2026_08_20.sql`:
```bash
mysqldump -u root -p --single-transaction --set-gtid-purged=OFF school_football_db > step1/backup_2026_08_20.sql
```

![CLI Backup Execution](images/backup_cli.png)

---

### 6.2 Graphical User Interface Backup (UI Tool)
Executed via the database client management GUI export interface to `step1/backup_2026_08_20_ui.sql`:

![UI Backup Execution](images/backup_ui.png)

---

## 7. Project Directory Structure

```plaintext
DBProject_316482801/
│
├── images/
│   ├── DSD.png                     # Relational schema diagram
│   ├── ERD.png                     # Conceptual entity-relationship diagram
│   ├── backup_cli.png              # Screenshot of CLI backup execution
│   ├── backup_ui.png               # Screenshot of GUI backup execution
│   └── verification_results.png    # Screenshot of row count verification query
│
├── step1/
│   ├── auditDistribution.sql       # Distribution analysis queries
│   ├── backup_2026_08_20.sql       # Full physical dump via mysqldump CLI
│   ├── backup_2026_08_20_ui.sql    # Full physical dump via GUI export tool
│   ├── createTables.sql            # DDL script creating 7 relational tables
│   ├── dropTables.sql              # DDL cleanup script in dependency order
│   ├── insertTables.sql            # Consolidated DML script (52,500 rows)
│   └── selectAll.sql               # Verification and row count query script
│
├── .gitignore                      # Git exclusion rules
└── README.md                       # Comprehensive project documentation
```

---
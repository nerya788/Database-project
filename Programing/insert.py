import random
from datetime import datetime, timedelta

# Helper data arrays
cities = ["Jerusalem", "Tel Aviv", "Haifa", "Beer Sheva", "Netanya", "Petah Tikva", "Ashdod", "Rishon LeZion", "Holon", "Bat Yam", "Rehovot", "Kfar Saba", "Herzliya", "Ranana", "Modihin", "Eilat", "Nazareth", "Afula", "Tiberias", "Safed"]
networks = ["AMAL", "ORT", "AMIT", "Independent", "Municipal", "Bnei Akiva", "Tzafon", "Hazorim", "Tzvia", "Noam"]
first_names = ["Noam", "Uri", "David", "Ariel", "Eitan", "Daniel", "Yosef", "Omer", "Itamar", "Lior", "Maya", "Tamar", "Noa", "Shira", "Yael", "Sara", "Roni", "Talia", "Hadas", "Michal", "Aviv", "Eden", "Gal", "Noga", "Rivka","Moshe", "Yonatan", "Shlomo", "Yitzhak", "Maor", "Erez", "Alon", "Yair", "Nadav", "Itai", "Tal", "Oren","Nerya"]
last_names = ["Cohen", "Levi", "Mizrahi", "Peretz", "Biton", "Dahan", "Avraham", "Friedman", "Malka", "Azulay", "Katz", "Gabai","Shitrit", "Ben David","Avramovich", "Man","Averman", "Bachar","Burstein", "Cohen-Avrahami", "Dayan", "Farkash", "Hazan", "Israeli", "Kahana", "Lifshitz", "Maimon", "Paz", "Rabinovich", "Saban"]
surfaces = ["Natural Grass", "Artificial Turf", "Hybrid"]
positions = ["Goalkeeper", "Defender", "Midfielder", "Forward"]
feet = ["Right", "Left", "Both"]
equip_brands = ["Nike", "Adidas", "Puma", "Select", "Uhlsport", "Molten"]
equip_statuses = ["Operational", "Under Repair", "Needs Inspection", "In Central Warehouse"]
practice_topics = ["Tactical Positioning", "High Pressing", "Set Pieces", "Endurance & Speed", "Ball Control", "Defensive Line Transitions", "Attacking Patterns", "Team Cohesion Drills", "Goalkeeper Training", "Fitness & Agility"]
match_statuses = ["Completed", "Scheduled", "Postponed", "In Progress"]
rounds = ["Round 1", "Round 2", "Round 3", "Quarter Final", "Semi Final", "Final"]
referees = ["Alon Yefet", "Liran Liany", "Roi Reinshreiber", "Eitan Shmuelevitz", "Orel Grinfeld", "Gal Leibovich"]

# Specialized categories
gear_categories = ["Balls", "Cones", "Vests", "Agility Ladders", "Goal Nets"]
gear_sizes = ["Size 4", "Size 5", "Standard", "Junior"]
kit_types = ["First Aid Kit", "Ice Packs & Strapping", "Bandages & Tape", "Defibrillator & AED Kit"]
maintenance_companies = ["GreenField Turf Ltd", "ProGrass Solutions", "Metro Stadium Services", "SafePlay Maintenance"]
event_types = ["Goal", "Yellow Card", "Red Card", "Assist", "Substitution"]

def random_date(start_year, end_year):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return (start + timedelta(days=random.randint(0, (end - start).days))).strftime("%Y-%m-%d")

with open("../step1/insertTables.sql", "w", encoding="utf-8") as f:
    f.write("-- School Football League Database Complete Mass Insert Script (11 Tables)\n\n")

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

    # 5. Global_Equipment (25,000) - Superclass
    for eq_id in range(1, 25001):
        st = random.choice(equip_statuses)
        sc = "NULL" if st == 'In Central Warehouse' else str(random.randint(1, 500))
        sh_d = "NULL" if sc == "NULL" else f"'{random_date(2025, 2026)}'"
        f.write(
            f"INSERT INTO Global_Equipment VALUES ('EQP-{eq_id:06d}', "
            f"'{random.choice(equip_brands)}', '{random_date(2022, 2024)}', "
            f"{round(random.uniform(15, 120), 2)}, '{st}', {sc}, {sh_d});\n"
        )

    # 5.1 Training_Gear (Subclass 1 - 20,000 items: EQP-000001 to EQP-020000)
    for eq_id in range(1, 20001):
        f.write(
            f"INSERT INTO Training_Gear VALUES ('EQP-{eq_id:06d}', "
            f"'{random.choice(gear_categories)}', '{random.choice(gear_sizes)}');\n"
        )

    # 5.2 Medical_Kits (Subclass 2 - 5,000 items: EQP-020001 to EQP-025000)
    for eq_id in range(20001, 25001):
        is_ster = "TRUE" if random.random() > 0.1 else "FALSE"
        f.write(
            f"INSERT INTO Medical_Kits VALUES ('EQP-{eq_id:06d}', "
            f"'{random.choice(kit_types)}', '{random_date(2026, 2028)}', {is_ster});\n"
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

    # 8. Maintenance_Logs (1,000 rows - Identifying Weak Entity for Fields)
    for f_id in range(1, 501):
        # 2 logs per field with different dates
        for log_month in [3, 8]:
            log_date = f"2025-{log_month:02d}-{random.randint(1, 28):02d}"
            cost = round(random.uniform(250.0, 3500.0), 2)
            passed = "TRUE" if random.random() > 0.05 else "FALSE"
            f.write(
                f"INSERT INTO Maintenance_Logs VALUES ({f_id}, '{log_date}', "
                f"'{random.choice(maintenance_companies)}', {cost}, "
                f"'Routine field and turf safety inspection', {passed});\n"
            )

    # 9. Match_Events (1,500 rows - Associative Entity for M:N between Students & Matches)
    event_id = 1
    for m_id in range(1, 501):
        num_events = random.randint(1, 4)
        for _ in range(num_events):
            student_idx = random.randint(0, len(student_ids) - 1)
            f.write(
                f"INSERT INTO Match_Events VALUES ({event_id}, {m_id}, "
                f"'{student_ids[student_idx]}', {random.randint(1, 90)}, "
                f"'{random.choice(event_types)}', 'Official recorded match event');\n"
            )
            event_id += 1

    f.write("COMMIT;\n")

print("Enhanced insertTables.sql generation completed successfully.")
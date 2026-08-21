import random
from datetime import datetime, timedelta

random.seed(42)

# Data Base Generation Parameters
cities = ["Jerusalem", "Tel Aviv", "Haifa", "Rishon LeZion", "Petah Tikva", "Ashdod", "Netanya", "Beer Sheva", "Holon", "Lod"]
first_names = ["Noam", "Uri", "David", "Ariel", "Eitan", "Itamar", "Daniel", "Yosef", "Omer", "Lavie", "Yonatan", "Matan", "Ido", "Roi"]
last_names = ["Cohen", "Levi", "Mizrahi", "Peretz", "Biton", "Dahan", "Avraham", "Friedman", "Katz", "David", "Navon", "Erez"]
networks = ["AMIT", "ORT", "AMAL", "Bnei Akiva", "Darca"]
positions = ["Goalkeeper", "Defender", "Midfielder", "Forward"]
feet = ["Right", "Left", "Both"]
surfaces = ["Asphalt", "Synthetic Grass", "Natural Grass", "Parquet Hall"]
equip_types = ["Match Ball", "Training Ball", "Cones Set", "Goal Net", "Match Jersey", "Training Bibs"]
equip_brands = ["Adidas Al Rihla", "Nike Academy Pro", "Puma TeamFinal", "Select Numero 10"]
equip_statuses = ["In Central Warehouse", "In Use", "Lost", "Damaged/Scrapped"]
practice_topics = ["Fitness", "Tactics", "Internal Scrimmage", "Passing Drills", "Set Pieces"]
match_statuses = ["Scheduled", "Ongoing", "Finished", "Postponed", "Cancelled"]
rounds = ["Round 1", "Round 2", "Quarter-Finals", "Semi-Finals", "Final"]
referees = ["Alon Yefet", "Orel Grinfeeld", "Roi Reinshreiber", "Liran Liani", "Erez Papir"]

def random_date(start_year, end_year):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return (start + timedelta(days=random.randint(0, (end - start).days))).strftime("%Y-%m-%d")

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
print("Complete insertTables.sql generation finished.")
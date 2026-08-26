"""Database Address Enrichment Script.

The mock data loaded into `school_football_db` gives every school and field
a near-identical, generic address ("32 Main St", "68 Sports Ave" - only
~100 distinct values shared across 500 rows each). This one-off migration
replaces them with realistic, geographically-plausible Israeli addresses:
a real, well-known street name for the row's city (falling back to a
common nationwide Israeli street name when no city-specific list is
curated) plus a Faker-generated house number.

Tables updated (the only two address-bearing columns in the schema):
  - Schools.full_address   ("<Street> <Suffix> <Number>")
  - Fields.city_address     ("<Street> <Suffix> <Number>, <City>" - the
                              city is parsed from field_name, e.g.
                              "Eilat Arena #12", since Fields has no
                              separate city column of its own)

Usage (from the repository root, with the step5 venv active):

    python step5/scripts/update_realistic_addresses.py            # asks to
                                                                    # confirm,
                                                                    # then commits
    python step5/scripts/update_realistic_addresses.py --dry-run   # preview only,
                                                                     # nothing written
    python step5/scripts/update_realistic_addresses.py --yes       # skip the
                                                                     # confirmation
                                                                     # prompt

Connects using the same step5/.env configuration as the GUI app
(app.config.DB_CONFIG) - no separate credentials to maintain.
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from pathlib import Path

# Allow running this script directly (python step5/scripts/update_realistic_addresses.py)
# without step5/ already being on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2
from faker import Faker

from app.config import DB_CONFIG

SEED = 20260826  # fixed seed: re-running the script reproduces the same addresses

STREET_SUFFIXES = ["St", "Rd", "Ave", "Blvd"]

# Nationwide street names common to virtually every Israeli city/town - the
# fallback pool, and also blended into every city-specific list for variety.
GENERIC_STREETS = [
    "Herzl", "Ben Gurion", "Weizmann", "Jabotinsky", "Rothschild", "Sokolov",
    "Bialik", "Trumpeldor", "HaGalil", "HaShalom", "HaAtzmaut", "Golda Meir",
    "Menachem Begin", "Moshe Dayan", "Yitzhak Rabin", "Ahad Ha'am", "HaBanim",
    "Keren Kayemet", "Ha'Arazim", "Nordau", "Balfour", "Arlozorov", "Gordon",
    "Pinsker", "HaRav Kook", "Smolenskin", "Bar Kokhva", "Yehuda HaLevi",
]

# A handful of real, well-known local streets per city - used alongside the
# generic pool so addresses feel geographically grounded ("mapped logically
# to the city") without inventing unfamiliar names for cities we're less
# confident about (those simply draw from GENERIC_STREETS only).
CITY_STREETS: dict[str, list[str]] = {
    "Tel Aviv": ["Dizengoff", "Ibn Gabirol", "Allenby", "Frishman", "HaYarkon", "Sheinkin"],
    "Jerusalem": ["Jaffa Rd", "King George", "Emek Refaim", "Agron", "HaPalmach", "Bezalel"],
    "Haifa": ["HaNassi", "Yefe Nof", "Moriah", "Horev"],
    "Beer Sheva": ["Rager", "Yerushalayim", "Tuviyahu"],
    "Netanya": ["Shderot Ben Gurion", "Smilansky", "HaMeyasdim"],
    "Herzliya": ["Maskit", "Achuza", "HaBanim"],
    "Petah Tikva": ["HaBaron", "HaChashmonaim", "HaEm HaChorevet"],
    "Rishon LeZion": ["HaChovevim", "Shderot Moshe Dayan"],
    "Ashdod": ["HaGefen", "HaTmarim"],
    "Bat Yam": ["Balfour", "HaAtzmaut"],
    "Holon": ["Sokolov", "Golda Meir"],
    "Rehovot": ["HaMeyasdim", "Bilu"],
    "Kfar Saba": ["HaShahar", "Weizmann"],
    "Ranana": ["Ahuza", "HaPardes"],
}

FIELD_CITY_PATTERN = re.compile(r"^(.*?)\s+Arena #\d+$")


def streets_for_city(city: str) -> list[str]:
    return CITY_STREETS.get(city, []) + GENERIC_STREETS


def make_address_builder(fake: Faker, rng: random.Random):
    """Returns a function generating a unique "<Street> <Suffix> <Number>"
    address per call, tracking what has already been issued so no two rows
    collide.
    """
    used: set[str] = set()

    def build(city: str, suffix_city: str | None = None) -> str:
        candidates = streets_for_city(city)
        for _ in range(50):
            street = rng.choice(candidates)
            suffix = rng.choice(STREET_SUFFIXES)
            number = int(fake.building_number())
            if number <= 0:
                number = rng.randint(1, 199)
            address = f"{street} {suffix} {number}"
            if suffix_city:
                address = f"{address}, {suffix_city}"
            if address not in used:
                used.add(address)
                return address
        # Astronomically unlikely with ~30 streets x 4 suffixes x 200 numbers
        # per city, but guarantee distinctness regardless.
        address = f"{street} {suffix} {number}-{len(used)}"
        used.add(address)
        return address

    return build


def update_schools(conn, fake: Faker, rng: random.Random, dry_run: bool) -> tuple[int, list[tuple]]:
    build_address = make_address_builder(fake, rng)
    samples = []
    with conn.cursor() as cur:
        cur.execute("SELECT school_id, city, full_address FROM Schools ORDER BY school_id")
        rows = cur.fetchall()
        for school_id, city, old_address in rows:
            new_address = build_address(city)
            if len(samples) < 5:
                samples.append((school_id, city, old_address, new_address))
            if not dry_run:
                cur.execute(
                    "UPDATE Schools SET full_address = %s WHERE school_id = %s",
                    (new_address, school_id),
                )
    return len(rows), samples


def update_fields(conn, fake: Faker, rng: random.Random, dry_run: bool) -> tuple[int, list[tuple]]:
    build_address = make_address_builder(fake, rng)
    samples = []
    with conn.cursor() as cur:
        cur.execute("SELECT field_id, field_name, city_address FROM Fields ORDER BY field_id")
        rows = cur.fetchall()
        for field_id, field_name, old_address in rows:
            match = FIELD_CITY_PATTERN.match(field_name or "")
            city = match.group(1) if match else "Tel Aviv"
            new_address = build_address(city, suffix_city=city)
            if len(samples) < 5:
                samples.append((field_id, field_name, old_address, new_address))
            if not dry_run:
                cur.execute(
                    "UPDATE Fields SET city_address = %s WHERE field_id = %s",
                    (new_address, field_id),
                )
    return len(rows), samples


def print_samples(title: str, samples: list[tuple]) -> None:
    print(f"\n  Sample {title}:")
    for row in samples:
        label, old_value, new_value = row[1], row[2], row[3]
        print(f"    #{row[0]:<6} {label!s:<28} {old_value!r:<20} -> {new_value!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                         help="Generate and print addresses without writing to the database.")
    parser.add_argument("--yes", action="store_true",
                         help="Skip the confirmation prompt before committing.")
    args = parser.parse_args()

    fake = Faker("he_IL")
    fake.seed_instance(SEED)
    rng = random.Random(SEED)

    print(f"Connecting to {DB_CONFIG.dbname} @ {DB_CONFIG.host}:{DB_CONFIG.port} as {DB_CONFIG.user} ...")
    conn = psycopg2.connect(DB_CONFIG.dsn)
    conn.autocommit = False

    try:
        if not args.dry_run and not args.yes:
            answer = input(
                "\nThis will overwrite Schools.full_address and Fields.city_address "
                "for every row. Continue? [y/N] "
            ).strip().lower()
            if answer != "y":
                print("Aborted - no changes made.")
                conn.rollback()
                return 1

        schools_count, schools_samples = update_schools(conn, fake, rng, args.dry_run)
        fields_count, fields_samples = update_fields(conn, fake, rng, args.dry_run)

        if args.dry_run:
            conn.rollback()
            print("\n[DRY RUN] No changes were written (transaction rolled back).")
        else:
            conn.commit()
            print("\nChanges committed.")

        print("\n=== Summary ===")
        print(f"  Schools.full_address updated : {schools_count} row(s)")
        print(f"  Fields.city_address updated   : {fields_count} row(s)")
        print_samples("Schools", schools_samples)
        print_samples("Fields", fields_samples)
        return 0

    except Exception as exc:  # noqa: BLE001 - top-level script safety net
        conn.rollback()
        print(f"\nERROR: {exc}", file=sys.stderr)
        print("Transaction rolled back - no changes were made.", file=sys.stderr)
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

# companies/services/csv_parser_service.py

import csv
from io import TextIOWrapper


class CSVInviteParser:

    @staticmethod
    def parse(file):
        decoded_file = TextIOWrapper(file, encoding="utf-8")
        reader = csv.DictReader(decoded_file)

        invites = []

        for row in reader:
            invites.append(
                {
                    "email": row.get("email", "").strip(),
                    "role_name": row.get("role", "").strip(),
                    "department_name": row.get("department", "").strip(),
                }
            )

        return invites

import csv
import os
from django.core.management.base import BaseCommand, CommandError
from portal.models import Clinic


class Command(BaseCommand):
    help = "Import clinics from a CSV file into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            default="bangalore_clinics.csv",
            help="Path to the CSV file (default: bangalore_clinics.csv)",
        )

    def handle(self, *args, **options):
        csv_path = options["csv"]

        if not os.path.exists(csv_path):
            raise CommandError(f"CSV file not found at: {csv_path}")

        created_count = 0
        updated_count = 0

        def safe_float(val):
            try:
                return float(val.strip()) if val and val.strip() else None
            except (ValueError, AttributeError):
                return None

        with open(csv_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("name", "").strip()
                area = row.get("area", "").strip()

                if not name:
                    continue

                open_now_val = row.get("open_now", "").strip().lower()
                open_now = open_now_val in ("true", "1", "yes", "t")

                is_verified_raw = row.get("is_verified", "").strip().lower()
                is_verified = is_verified_raw in ("true", "1", "yes", "t") if is_verified_raw else True

                defaults = {
                    "city": row.get("city", "Bengaluru").strip() or "Bengaluru",
                    "category": row.get("category", "").strip(),
                    "type": row.get("type", "").strip(),
                    "open_now": open_now,
                    "hours": row.get("hours", "").strip(),
                    "address": row.get("address", "").strip(),
                    "latitude": safe_float(row.get("latitude")),
                    "longitude": safe_float(row.get("longitude")),
                    "google_maps_url": row.get("google_maps_url", "").strip(),
                    "is_verified": is_verified,
                }

                clinic, created = Clinic.objects.update_or_create(
                    name=name,
                    area=area,
                    defaults=defaults,
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed clinics CSV: {created_count} created, {updated_count} updated."
            )
        )


import csv
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from trip_planner.models import TruckStop

US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY","DC",
}


class Command(BaseCommand):
    help = "Loads fuel price CSV and joins each station to real lat/lon via a city/state reference table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fuel-csv",
            default=str(Path(settings.BASE_DIR) / "fuel-prices-for-be-assessment.csv"),
        )
        parser.add_argument(
            "--cities-csv",
            default=str(Path(settings.BASE_DIR) / "us_cities_ref.csv"),
        )

    def handle(self, *_args, **options):
        fuel_csv = Path(options["fuel_csv"])
        cities_csv = Path(options["cities_csv"])

        if not fuel_csv.exists():
            self.stdout.write(self.style.ERROR(f"CSV file not found at {fuel_csv}"))
            return
        if not cities_csv.exists():
            self.stdout.write(self.style.ERROR(
                f"City reference CSV not found at {cities_csv}. "
                "Without it, stations can't be geocoded and fuel search can't be geographic."
            ))
            return

        city_coords = self._load_city_coords(cities_csv)
        self.stdout.write(f"Loaded {len(city_coords)} city/state coordinate pairs.")

        self.stdout.write("Clearing existing truck stops records...")
        TruckStop.objects.all().delete()

        stops_to_create, skipped_non_us, skipped_no_match = self._build_truck_stops(
            fuel_csv, city_coords
        )

        with transaction.atomic():
            TruckStop.objects.bulk_create(stops_to_create, batch_size=1000)

        geocoded = sum(1 for s in stops_to_create if s.latitude is not None)
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(stops_to_create)} stations ({geocoded} geocoded). "
            f"Skipped {skipped_non_us} non-US rows, {skipped_no_match} rows with no city/state coordinate match."
        ))

    def _load_city_coords(self, cities_csv):
        city_coords = {}
        with open(cities_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = (row["CITY"].strip().lower(), row["STATE_CODE"].strip().upper())
                if key not in city_coords:
                    city_coords[key] = (
                        float(row["LATITUDE"]),
                        float(row["LONGITUDE"]),
                    )
        return city_coords

    def _build_truck_stops(self, fuel_csv, city_coords):
        stops_to_create = []
        skipped_non_us = 0
        skipped_no_match = 0

        with open(fuel_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                state = row["State"].strip().upper()
                if state not in US_STATES:
                    skipped_non_us += 1
                    continue

                city = row["City"].strip()
                coords = city_coords.get((city.lower(), state))
                if coords is None:
                    skipped_no_match += 1
                    lat, lon = None, None
                else:
                    lat, lon = coords

                stops_to_create.append(TruckStop(
                    opis_id=int(row["OPIS Truckstop ID"]),
                    name=row["Truckstop Name"].strip(),
                    address=row["Address"].strip(),
                    city=city,
                    state=state,
                    rack_id=int(row["Rack ID"]) if row["Rack ID"] else 0,
                    retail_price=float(row["Retail Price"]),
                    latitude=lat,
                    longitude=lon,
                ))

        return stops_to_create, skipped_non_us, skipped_no_match

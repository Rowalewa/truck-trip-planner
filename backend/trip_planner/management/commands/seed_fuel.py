import csv
import os
from django.core.management.base import BaseCommand
from trip_planner.models import TruckStop

class Command(BaseCommand):
    help = 'Ingests truck stop fuel data from a CSV file into the database.'

    def handle(self, *args, **options):
        csv_file_path = 'fuel-prices-for-be-assessment.csv'

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found at {csv_file_path}"))
            return

        self.stdout.write("Clearing existing truck stops records...")
        TruckStop.objects.all().delete()

        self.stdout.write("Reading CSV and parsing records...")
        truck_stops_to_create = []

        with open(csv_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Map CSV column headers to your Django Model fields
                stop = TruckStop(
                    opis_id=int(row['OPIS Truckstop ID']),
                    name=row['Truckstop Name'],
                    address=row['Address'],
                    city=row['City'],
                    state=row['State'],
                    rack_id=int(row['Rack ID']),
                    retail_price=float(row['Retail Price'])
                )
                truck_stops_to_create.append(stop)

        self.stdout.write(f"Bulk-inserting {len(truck_stops_to_create)} records into database...")
        # bulk_create fires a single massive database query instead of 8,000 separate ones
        TruckStop.objects.bulk_create(truck_stops_to_create)

        self.stdout.write(self.style.SUCCESS("Successfully seeded fuel data!"))
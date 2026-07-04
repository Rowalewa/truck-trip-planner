from django.db import models

# Create your models here.
# defining a clean database table structure that mirrors the CSV data exactly
class TruckStop(models.Model):
    # Remove unique=True in opis_id because the source data contains duplicates
    opis_id = models.IntegerField()
    name = models.CharField(max_length=255) 
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=10)
    rack_id = models.IntegerField()
    retail_price = models.DecimalField(max_digits=6, decimal_places=3)

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state} (${self.retail_price})"
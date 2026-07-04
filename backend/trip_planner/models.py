from django.db import models

class TruckStop(models.Model):
    opis_id = models.IntegerField()
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=10)
    rack_id = models.IntegerField()
    retail_price = models.DecimalField(max_digits=6, decimal_places=3)
    latitude = models.FloatField(null=True, db_index=True)
    longitude = models.FloatField(null=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["retail_price"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state} (${self.retail_price})"

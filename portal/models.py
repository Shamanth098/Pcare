from django.db import models


class Clinic(models.Model):
    name = models.CharField(max_length=255)
    area = models.CharField(max_length=255)
    city = models.CharField(max_length=100, default="Bengaluru")
    category = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    open_now = models.BooleanField(default=False)
    hours = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    google_maps_url = models.URLField(max_length=500, blank=True)
    is_verified = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.area})"

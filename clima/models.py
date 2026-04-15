from django.db import models

class ConsultaClima(models.Model):
    ciudad = models.CharField(max_length=100)
    pais = models.CharField(max_length=10)
    temperatura = models.FloatField()
    descripcion = models.CharField(max_length=200)
    humedad = models.IntegerField(default=0)
    latitud = models.FloatField(default=0)
    longitud = models.FloatField(default=0)
    icono = models.CharField(max_length=10, blank=True, null=True)
    favorita = models.BooleanField(default=False)
    fecha_consulta = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ciudad} - {self.temperatura}°C"
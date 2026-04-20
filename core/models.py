from django.db import models
from django.contrib.auth.models import User
import json

class Team(models.Model):
    id_equipo = models.IntegerField(unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=100, unique=True)
    pais = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"


class Player(models.Model):
    id_jugador = models.IntegerField(unique=True)
    nombre = models.CharField(max_length=200)
    posicion = models.CharField(max_length=50)
    valoracion = models.IntegerField()
    estilo_juego = models.CharField(max_length=100, blank=True)
    pais = models.CharField(max_length=100, blank=True)
    equipo_original = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name="jugadores_originales")
    
    # NUEVO CAMPO: Backup del equipo original (para que no se pierda al liberar)
    equipo_original_backup = models.ForeignKey(
        Team, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="jugadores_backup"
    )

    edad = models.IntegerField()
    altura = models.IntegerField()
    peso = models.IntegerField()
    pie = models.CharField(max_length=20)

    # Guardamos todas las stats extras en JSON
    stats_extra = models.JSONField(default=dict)

    # NUEVOS CAMPOS para mercado y cálculos
    en_mercado = models.BooleanField(default=False)  # Saber si está disponible en mercado
    precio_calculado = models.BigIntegerField(default=0)  # Precio dinámico
    salario_anual = models.BigIntegerField(default=0)     # Salario dinámico

    def __str__(self):
        return f"{self.nombre} ({self.valoracion}) - {self.posicion}"

    class Meta:
        verbose_name = "Jugador"
        verbose_name_plural = "Jugadores"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    equipo_asignado = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    
    presupuesto_traspaso = models.BigIntegerField(default=3500000000)   # 3.500 millones
    presupuesto_salarial = models.BigIntegerField(default=3500000000)   # 3.500 millones

    # Para la elección inicial de 2 equipos
    opcion1 = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="opcion1")
    opcion2 = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="opcion2")
    primer_login_completado = models.BooleanField(default=False)

    estado_eleccion = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente de revisión'),
            ('aprobado', 'Aprobado'),
            ('negado', 'Negado - Puede volver a elegir'),
        ],
        default='pendiente'
    )

    def __str__(self):
        return self.user.username


# ==================== NUEVO MODELO PARA OFERTAS DE TRASPASO ====================
class TransferOffer(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('accepted', 'Aceptada'),
        ('rejected', 'Rechazada'),
        ('counter', 'Contraoferta'),
    ]

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offers_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offers_received')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='offers')
    
    amount = models.BigIntegerField(help_text="Cantidad ofrecida en dólares")
    message = models.TextField(blank=True, null=True, help_text="Mensaje opcional para el dueño")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Oferta de Traspaso"
        verbose_name_plural = "Ofertas de Traspaso"

    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username} | {self.player.nombre} (${self.amount:,})"

    @property
    def status_display(self):
        return self.get_status_display()
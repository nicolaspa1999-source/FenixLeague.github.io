from django.core.management.base import BaseCommand
from core.models import Team, Player
import csv
import os

class Command(BaseCommand):
    help = 'Carga equipos y jugadores desde jugadores_pes2017.csv'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🚀 Cargando equipos y jugadores desde CSV...'))

        csv_path = os.path.join(os.getcwd(), 'jugadores_pes2017.csv')
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR('✗ No se encontró jugadores_pes2017.csv'))
            return

        teams_created = 0
        players_loaded = 0
        team_cache = {}

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')

            for row in reader:
                try:
                    equipo_nombre = row.get('Equipo', '').strip()
                    if not equipo_nombre:
                        continue

                    # Crear equipo si no existe
                    if equipo_nombre not in team_cache:
                        team, created = Team.objects.get_or_create(nombre=equipo_nombre)
                        team_cache[equipo_nombre] = team
                        if created:
                            teams_created += 1

                    # Crear jugador
                    player_id = int(row['ID Jugador'])
                    player, created = Player.objects.update_or_create(
                        id_jugador=player_id,
                        defaults={
                            'nombre': row.get('Nombre del jugador', '').strip(),
                            'posicion': row.get('Posicion', ''),
                            'valoracion': int(row.get('Valoracion', 70)),
                            'estilo_juego': row.get('Estilo de juego', ''),
                            'pais': row.get('Pais', ''),
                            'edad': int(row.get('Edad', 25)),
                            'altura': int(row.get('Altura', 180)),
                            'peso': int(row.get('Peso', 75)),
                            'pie': row.get('Pie', 'Derecho'),
                            'equipo_original': team_cache[equipo_nombre],
                        }
                    )
                    players_loaded += 1

                except Exception as e:
                    continue

        self.stdout.write(self.style.SUCCESS(f'   → {teams_created} equipos creados'))
        self.stdout.write(self.style.SUCCESS(f'   → {players_loaded} jugadores cargados'))
        self.stdout.write(self.style.SUCCESS('\n✅ CARGA COMPLETA FINALIZADA'))
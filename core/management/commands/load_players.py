from django.core.management.base import BaseCommand
from core.models import Player, Team
import csv
import os

class Command(BaseCommand):
    help = 'Carga completa de jugadores con TODAS las stats y habilidades'

    def handle(self, *args, **options):
        csv_path = os.path.join(os.getcwd(), 'jugadores_pes2017.csv')

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'✗ No se encontró el archivo: {csv_path}'))
            return

        self.stdout.write(self.style.WARNING('🚀 Iniciando carga COMPLETA de jugadores...'))
        self.stdout.write(self.style.SUCCESS('Procesando... (mostraré progreso cada 1000 jugadores)'))

        count = 0
        skipped = 0

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')

            for row in reader:
                try:
                    player_id = int(row.get('ID Jugador', 0))
                    if player_id == 0:
                        skipped += 1
                        continue

                    nombre = row.get('Nombre del jugador', '').strip()

                    # Cargar TODAS las columnas como stats_extra
                    stats_extra = {}
                    for key, value in row.items():
                        if key not in ['ID Jugador', 'Nombre del jugador', 'Equipo', 'ID Equipo']:
                            try:
                                stats_extra[key] = int(value) if value and value.strip() else 0
                            except (ValueError, TypeError):
                                stats_extra[key] = str(value).strip() if value else ""

                    player, created = Player.objects.update_or_create(
                        id_jugador=player_id,
                        defaults={
                            'nombre': nombre,
                            'posicion': row.get('Posicion', ''),
                            'valoracion': int(row.get('Valoracion', 70)),
                            'estilo_juego': row.get('Estilo de juego', ''),
                            'pais': row.get('Pais', ''),
                            'edad': int(row.get('Edad', 25)),
                            'altura': int(row.get('Altura', 180)),
                            'peso': int(row.get('Peso', 75)),
                            'pie': row.get('Pie', 'Derecho'),
                            'stats_extra': stats_extra,
                        }
                    )

                    # Asignar equipo
                    equipo_nombre = row.get('Equipo', '').strip()
                    if equipo_nombre:
                        team = Team.objects.filter(nombre__icontains=equipo_nombre).first()
                        if team:
                            player.equipo_original = team
                            player.save()

                    count += 1

                    # Mostrar progreso cada 1000 jugadores
                    if count % 1000 == 0:
                        self.stdout.write(self.style.SUCCESS(f'   → {count} jugadores procesados...'))

                except Exception:
                    skipped += 1
                    continue

        # Mensaje final
        self.stdout.write(self.style.SUCCESS(f'\n✅ CARGA FINALIZADA'))
        self.stdout.write(self.style.SUCCESS(f'   → {count} jugadores procesados correctamente'))
        self.stdout.write(self.style.SUCCESS(f'   → {skipped} filas omitidas'))
        self.stdout.write(self.style.SUCCESS('Todas las habilidades y stats han sido cargadas correctamente en stats_extra.'))
import csv
from django.core.management.base import BaseCommand
from core.models import Team, Player

class Command(BaseCommand):
    help = 'Importa jugadores desde CSV de PES 2017 (separado por ;)'

    def handle(self, *args, **kwargs):
        csv_path = 'jugadores_pes2017.csv'

        try:
            with open(csv_path, encoding='utf-8-sig') as f:   # utf-8-sig elimina el BOM \ufeff
                # Leemos manualmente porque está separado por ;
                lines = f.readlines()

            # Primera línea = cabeceras
            headers = [h.strip() for h in lines[0].strip().split(';')]

            self.stdout.write(self.style.SUCCESS(f"Columnas detectadas: {len(headers)}"))
            self.stdout.write(str(headers[:20]))  # Muestra primeras 20 columnas

            teams_created = 0
            players_created = 0

            for i, line in enumerate(lines[1:], start=2):   # saltamos la cabecera
                try:
                    values = [v.strip() for v in line.strip().split(';')]
                    if len(values) != len(headers):
                        continue

                    row = dict(zip(headers, values))

                    id_jugador = row.get('ID Jugador')
                    nombre = row.get('Nombre del jugador')
                    posicion = row.get('Posicion')
                    valoracion = row.get('Valoracion')
                    equipo_nombre = row.get('Equipo')
                    id_equipo = row.get('ID Equipo')
                    pais = row.get('Pais', '')
                    edad = row.get('Edad')
                    altura = row.get('Altura')
                    peso = row.get('Peso')
                    pie = row.get('Pie', 'Derecho')

                    if not all([id_jugador, nombre, posicion, valoracion, equipo_nombre]):
                        continue

                    # Crear equipo
                    team, created = Team.objects.get_or_create(
                        id_equipo=id_equipo if id_equipo else None,
                        defaults={'nombre': equipo_nombre, 'pais': pais}
                    )
                    if created:
                        teams_created += 1

                    # Stats extras
                    stats = {k: v for k, v in row.items() if k not in [
                        'ID Jugador', 'Nombre del jugador', 'Posicion', 'Valoracion',
                        'Estilo de juego', 'Pais', 'Equipo', 'ID Equipo', 'Edad',
                        'Altura', 'Peso', 'Pie'
                    ]}

                    Player.objects.create(
                        id_jugador=int(id_jugador),
                        nombre=nombre,
                        posicion=posicion,
                        valoracion=int(valoracion),
                        estilo_juego=row.get('Estilo de juego', ''),
                        pais=pais,
                        equipo_original=team,
                        edad=int(edad) if edad else 25,
                        altura=int(altura) if altura else 180,
                        peso=int(peso) if peso else 75,
                        pie=pie,
                        stats_extra=stats
                    )
                    players_created += 1

                    if players_created % 5000 == 0:
                        self.stdout.write(f'→ Importados {players_created} jugadores...')

                except Exception as e:
                    if i % 5000 == 0:
                        self.stdout.write(self.style.WARNING(f'Error en fila {i}: {str(e)}'))
                    continue

            self.stdout.write(self.style.SUCCESS(
                f'✅ ¡Importación completada con éxito!'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   Equipos creados: {teams_created}'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   Jugadores importados: {players_created}'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error general: {str(e)}'))
from django.core.management.base import BaseCommand
from core.models import Player, UserProfile, Team
import csv
import os

class Command(BaseCommand):
    help = 'Reset TOTAL RÁPIDO y SEGURO - Restaura todos los jugadores desde CSV'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🚀 Iniciando RESET TOTAL RÁPIDO...'))

        # 1. Resetear usuarios
        updated = UserProfile.objects.all().update(
            equipo_asignado=None,
            opcion1=None,
            opcion2=None,
            primer_login_completado=False,
            estado_eleccion='pendiente',
            presupuesto_traspaso=220_000_000,
            presupuesto_salarial=62_000_000
        )
        self.stdout.write(self.style.SUCCESS(f'   → {updated} usuarios reseteados con presupuestos correctos'))

        # 2. Restaurar jugadores desde CSV
        csv_path = os.path.join(os.getcwd(), 'jugadores_pes2017.csv')
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'✗ No se encontró el archivo jugadores_pes2017.csv'))
            return

        self.stdout.write(self.style.WARNING('   Restaurando jugadores desde CSV...'))

        # Crear diccionario rápido: player_id → equipo_nombre
        player_to_team = {}
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                try:
                    pid = int(row['ID Jugador'])
                    equipo = row.get('Equipo', '').strip()
                    if equipo:
                        player_to_team[pid] = equipo
                except:
                    continue

        # Actualizar jugadores
        players = Player.objects.all()
        restored = 0
        not_found = 0

        for player in players:
            if player.id_jugador in player_to_team:
                equipo_nombre = player_to_team[player.id_jugador]
                
                # Buscar equipo
                team = Team.objects.filter(nombre__iexact=equipo_nombre).first()
                if not team:
                    team = Team.objects.filter(nombre__icontains=equipo_nombre).first()

                if team:
                    if player.equipo_original != team:
                        player.equipo_original = team
                        player.save()
                    restored += 1
                else:
                    not_found += 1
                    if not_found <= 20:
                        self.stdout.write(self.style.WARNING(f'   ⚠️ No se encontró equipo para: {player.nombre} ({equipo_nombre})'))

        self.stdout.write(self.style.SUCCESS(f'   → {restored} jugadores restaurados correctamente'))
        if not_found > 0:
            self.stdout.write(self.style.WARNING(f'   ⚠️ {not_found} jugadores no pudieron ser asignados a un equipo'))

        self.stdout.write(self.style.SUCCESS('\n✅ RESET TOTAL FINALIZADO CON ÉXITO'))
        self.stdout.write(self.style.WARNING('La liga está completamente limpia y lista para probar.'))
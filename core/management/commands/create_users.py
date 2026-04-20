from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile

class Command(BaseCommand):
    help = 'Crea los 12 usuarios para Fenix League con posibilidad de contraseña personalizada'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Creando usuarios para Fenix League...'))

        # Aquí puedes cambiar las contraseñas individuales fácilmente
        players_data = [
            {"username": "StefanoP",    "password": "123456"},
            {"username": "MatiasP",     "password": "123456"},
            {"username": "JoshuaC",     "password": "123456"},
            {"username": "EdysonH",     "password": "123456"},
            {"username": "JulianA",     "password": "123456"},
            {"username": "NicoA",       "password": "123456"},
            {"username": "DavidF",      "password": "123456"},
            {"username": "EduF",        "password": "123456"},
            {"username": "MiguelF",     "password": "123456"},
            {"username": "RaulF",       "password": "123456"},
            {"username": "SantiagoF",   "password": "123456"},
            {"username": "YersiC",      "password": "123456"},
        ]

        created = 0
        for data in players_data:
            username = data["username"]
            password = data["password"]

            user, user_created = User.objects.get_or_create(username=username)

            if user_created:
                user.set_password(password)
                user.save()
                created += 1
                self.stdout.write(self.style.SUCCESS(f'   ✓ Creado: {username} | Contraseña: {password}'))
            else:
                # Si ya existe, actualizamos la contraseña
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.WARNING(f'   → Actualizada contraseña de: {username}'))

            # Crear o actualizar perfil
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.presupuesto_traspaso = 3500000000
            profile.presupuesto_salarial = 3500000000
            profile.estado_eleccion = 'pendiente'
            profile.primer_login_completado = False
            profile.save()

        self.stdout.write(self.style.SUCCESS(f'\n✅ Se procesaron {created} usuarios'))
        self.stdout.write(self.style.SUCCESS('Puedes cambiar cualquier contraseña editando el código y volviendo a ejecutar el comando.'))
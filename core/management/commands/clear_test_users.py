from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile

class Command(BaseCommand):
    help = 'Elimina todos los usuarios de prueba (excepto el admin)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Eliminando usuarios de prueba...'))

        # Eliminar todos los usuarios excepto el admin y superusuarios
        deleted = User.objects.filter(is_superuser=False).delete()

        self.stdout.write(self.style.SUCCESS(f'   → Se eliminaron {deleted[0]} usuarios'))

        # También limpiamos los perfiles
        UserProfile.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('✅ Todos los usuarios de prueba han sido eliminados.'))
        self.stdout.write(self.style.WARNING('Ahora puedes volver a crear solo los usuarios que deseas.'))
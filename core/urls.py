from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('elegir-equipos/', views.elegir_equipos, name='elegir_equipos'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('mi-equipo/', views.mi_equipo, name='mi_equipo'),
    path('jugador/<int:id>/', views.detalle_jugador, name='detalle_jugador'),
    path('liberar-jugador/', views.liberar_jugador, name='liberar_jugador'),
    path('fichar-jugador/', views.fichar_jugador, name='fichar_jugador'),
]
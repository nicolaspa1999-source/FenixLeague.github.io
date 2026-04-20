from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import UserProfile, Team, Player, TransferOffer
import json
from django.http import JsonResponse

# ====================== HOME ======================
def home(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_panel')

        profile = UserProfile.objects.get_or_create(user=request.user)[0]

        # Caso 1: Aún no ha elegido equipos → ir a elegir
        if not profile.primer_login_completado:
            return redirect('elegir_equipos')

        # Caso 2: Ya eligió pero está esperando aprobación del admin
        if profile.primer_login_completado and profile.estado_eleccion == 'pendiente':
            return render(request, 'home.html', {
                'profile': profile,
                'esperando_aprobacion': True
            })

        # Caso 3: Ya tiene equipo asignado → ir a Mi Equipo
        if profile.estado_eleccion == 'aprobado' and profile.equipo_asignado:
            return redirect('mi_equipo')

        # Caso por defecto
        return render(request, 'home.html', {'profile': profile})

    return render(request, 'home.html')

# ====================== LOGIN / LOGOUT ======================
def login_view(request):
    storage = messages.get_messages(request)
    for message in storage:
        pass
    storage.used = True

    if 'messages' in request.session:
        del request.session['messages']

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.is_superuser:
                return redirect('admin_panel')
            else:
                return redirect('home')
    else:
        form = AuthenticationForm()
    
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')   # ← Cambiado a 'login'

# ====================== ELEGIR EQUIPOS ======================
@login_required
def elegir_equipos(request):
    profile = UserProfile.objects.get(user=request.user)

    # Si ya completó la elección, no debe volver aquí
    if profile.primer_login_completado:
        if profile.estado_eleccion == 'aprobado' and profile.equipo_asignado:
            return redirect('mi_equipo')
        else:
            return redirect('home')   # Va a home para mostrar "esperando aprobación"

    if request.method == 'POST':
        opcion1_id = request.POST.get('opcion1')
        opcion2_id = request.POST.get('opcion2')

        if not opcion1_id or not opcion2_id or opcion1_id == opcion2_id:
            messages.error(request, "Debes elegir 2 equipos diferentes")
        else:
            try:
                opcion1 = Team.objects.get(id=opcion1_id)
                opcion2 = Team.objects.get(id=opcion2_id)

                profile.opcion1 = opcion1
                profile.opcion2 = opcion2
                profile.primer_login_completado = True
                profile.estado_eleccion = 'pendiente'   # Muy importante
                profile.save()

                messages.success(request, "¡Tus 2 opciones de equipo han sido guardadas correctamente!")

                # Mensajes de advertencia si alguien más eligió el mismo equipo
                if UserProfile.objects.filter(opcion1=opcion1).exclude(user=request.user).exists():
                    usuario = UserProfile.objects.filter(opcion1=opcion1).exclude(user=request.user).first().user.username
                    messages.warning(request, f"El participante <strong>{usuario}</strong> ya eligió el equipo <strong>{opcion1.nombre}</strong>")

                if UserProfile.objects.filter(opcion2=opcion2).exclude(user=request.user).exists():
                    usuario = UserProfile.objects.filter(opcion2=opcion2).exclude(user=request.user).first().user.username
                    messages.warning(request, f"El participante <strong>{usuario}</strong> ya eligió el equipo <strong>{opcion2.nombre}</strong>")

                return redirect('home')   # ← Aquí va a home para mostrar el mensaje de espera

            except Team.DoesNotExist:
                messages.error(request, "Error al seleccionar los equipos. Inténtalo de nuevo.")

    equipos = Team.objects.all().order_by('nombre')
    return render(request, 'elegir_equipos.html', {
        'equipos': equipos,
        'profile': profile
    })


# ====================== ADMIN PANEL ======================
@login_required
def admin_panel(request):
    if not request.user.is_superuser:
        messages.error(request, "Solo el administrador puede acceder.")
        return redirect('home')

    profiles = UserProfile.objects.select_related('user', 'opcion1', 'opcion2', 'equipo_asignado').all()
    all_teams = Team.objects.all().order_by('nombre')

    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')
        action = request.POST.get('action')
        equipo_id = request.POST.get('equipo_id')

        if profile_id:
            try:
                profile = UserProfile.objects.get(id=profile_id)
                
                if action == 'aceptar_op1' and profile.opcion1:
                    profile.equipo_asignado = profile.opcion1
                    profile.estado_eleccion = 'aprobado'
                    messages.success(request, f"✅ Aceptado {profile.opcion1.nombre} para {profile.user.username}")

                elif action == 'aceptar_op2' and profile.opcion2:
                    profile.equipo_asignado = profile.opcion2
                    profile.estado_eleccion = 'aprobado'
                    messages.success(request, f"✅ Aceptado {profile.opcion2.nombre} para {profile.user.username}")

                elif action == 'sorteo' and equipo_id:
                    equipo = Team.objects.get(id=equipo_id)
                    profile.equipo_asignado = equipo
                    profile.estado_eleccion = 'aprobado'
                    messages.success(request, f"✅ Asignado por sorteo: {equipo.nombre} a {profile.user.username}")

                profile.save()
            except Exception as e:
                messages.error(request, f"Error al procesar: {e}")

    return render(request, 'admin_panel.html', {
        'profiles': profiles,
        'all_teams': all_teams
    })


# ====================== MI EQUIPO ======================
@login_required
def mi_equipo(request):
    profile = UserProfile.objects.get_or_create(user=request.user)[0]

    active_tab = request.GET.get('tab', 'mi_equipo')

    mis_jugadores = Player.objects.filter(equipo_original=profile.equipo_asignado).order_by('posicion', '-valoracion') if profile.equipo_asignado else []

    # Excluir jugadores de FC Ultimate Team (ID 14600) para evitar duplicados en el Mercado
    all_players = Player.objects.exclude(
        equipo_original__id=14600
    ).order_by('-valoracion')

    taken_teams = set()
    for p in UserProfile.objects.filter(equipo_asignado__isnull=False).exclude(user=request.user):
        if p.equipo_asignado and p.equipo_asignado.nombre:
            taken_teams.add(p.equipo_asignado.nombre)

    presupuesto_traspaso = profile.presupuesto_traspaso
    presupuesto_salarial = profile.presupuesto_salarial
    cantidad_jugadores = len(mis_jugadores)

    def calcular_precio_y_salario(valoracion, es_leyenda):
        # ==================== JUGADORES ACTIVOS ====================
        if not es_leyenda:
            if 95 <= valoracion <= 97:
                precio = {95: 240_000_000, 96: 300_000_000, 97: 380_000_000}.get(valoracion, 240_000_000)
            elif 90 <= valoracion <= 94:
                precio = {90: 110_000_000, 91: 125_000_000, 92: 140_000_000,
                         93: 155_000_000, 94: 175_000_000}.get(valoracion, 110_000_000)
            elif 85 <= valoracion <= 89:
                precio = {85: 45_000_000, 86: 55_000_000, 87: 65_000_000,
                         88: 75_000_000, 89: 85_000_000}.get(valoracion, 45_000_000)
            else:  # 75-84
                precio = {75: 12_000_000, 76: 15_000_000, 77: 18_000_000, 78: 22_000_000,
                         79: 26_000_000, 80: 30_000_000, 81: 32_000_000, 82: 33_000_000,
                         83: 34_000_000, 84: 35_000_000}.get(valoracion, 12_000_000)
        
        # ==================== LEYENDAS ====================
        else:
            if 95 <= valoracion <= 98:
                precio = {96: 850_000_000, 97: 1_100_000_000, 98: 1_450_000_000}.get(valoracion, 850_000_000)
            elif 90 <= valoracion <= 94:
                precio = {90: 380_000_000, 91: 420_000_000, 92: 480_000_000,
                         93: 540_000_000, 94: 620_000_000}.get(valoracion, 380_000_000)
            elif 85 <= valoracion <= 89:
                precio = {85: 140_000_000, 86: 160_000_000, 87: 190_000_000,
                         88: 210_000_000, 89: 240_000_000}.get(valoracion, 140_000_000)
            else:
                precio = 140_000_000

        # Salario anual ≈ 8% del precio de fichaje (escala equilibrada)
        salario = int(precio * 0.08)

        return precio, salario

    # Aplicar precios y detección de leyenda
    for jugador in list(all_players) + list(mis_jugadores):
        equipo_name = getattr(jugador.equipo_original, 'nombre', '')
        
        # Detección de leyendas (por nombre + IDs que mencionaste antes)
        es_leyenda = any(x in equipo_name.lower() for x in [
            "ea sports legacy", "ea sports icons", "ea sports legends",
            "ea sports classica", "ea sports warriors", "ea sports titans", "ea sports kings"
        ])
        
        # También por ID de equipo (por si el nombre no coincide exactamente)
        equipo_id = getattr(getattr(jugador.equipo_original, 'id_equipo', None), 'id_equipo', None) if jugador.equipo_original else None
        if equipo_id in [90150, 27030, 27040, 14580, 14590, 14620, 14630]:
            es_leyenda = True

        jugador.es_leyenda = es_leyenda
        jugador.precio_calculado, jugador.salario_anual = calcular_precio_y_salario(jugador.valoracion, es_leyenda)

    paginator = Paginator(all_players, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

                # === CREAR MAPA DE JUGADORES TOMADOS POR USUARIOS ===
    taken_players = {}  # id_jugador → username del dueño
    for p in UserProfile.objects.filter(equipo_asignado__isnull=False):
        if p.equipo_asignado:
            jugadores_del_usuario = Player.objects.filter(equipo_original=p.equipo_asignado)
            for jug in jugadores_del_usuario:
                taken_players[jug.id] = p.user.username

    # === LISTA OFICIAL DE EQUIPOS LEYENDA (por ID y nombre) ===
    equipos_leyenda_ids = [90150, 27030, 27040, 14580, 14590, 14620, 14630]

    equipos_leyenda_nombres = [
        "ea sports legacy", "ea sports icons", "ea sports legends",
        "ea sports classica", "ea sports warriors", "ea sports titans",
        "ea sports kings", "ea sport legends", "ea sport icons",
        "ea sports classics"
    ]

    # Calcular leyenda y precios para todos los jugadores
    for jugador in list(all_players) + list(mis_jugadores):
        equipo = getattr(jugador, 'equipo_original', None)
        equipo_name = getattr(equipo, 'nombre', '').lower().strip()
        equipo_id = getattr(equipo, 'id', None)

        # Es leyenda si coincide por ID o por nombre
        es_leyenda = (equipo_id in equipos_leyenda_ids) or \
                     any(keyword in equipo_name for keyword in equipos_leyenda_nombres)

        jugador.es_leyenda = es_leyenda
        jugador.precio_calculado, jugador.salario_anual = calcular_precio_y_salario(jugador.valoracion, es_leyenda)

    # === GENERAR JSON PARA EL FRONTEND ===
    all_players_json = json.dumps([
        {
            'id': jugador.id,
            'nombre': jugador.nombre,
            'posicion': jugador.posicion or '',
            'pais': jugador.pais or '',
            'estilo_juego': getattr(jugador, 'estilo_juego', '') or '',
            'valoracion': jugador.valoracion,
            'edad': jugador.edad,
            'altura': jugador.altura,
            'precio_calculado': getattr(jugador, 'precio_calculado', 0),
            'salario_anual': getattr(jugador, 'salario_anual', 0),
            'es_leyenda': getattr(jugador, 'es_leyenda', False),
            'equipo_original': getattr(getattr(jugador, 'equipo_original', None), 'nombre', 'Sin Equipo'),
            'dueño_actual': taken_players.get(jugador.id, None)   # None = libre
        }
        for jugador in all_players
    ], ensure_ascii=False)

    return render(request, 'mi_equipo.html', {
        'profile': profile,
        'mis_jugadores': mis_jugadores,
        'page_obj': page_obj,
        'all_players': all_players,
        'taken_teams': taken_teams,
        'cantidad_jugadores': cantidad_jugadores,
        'presupuesto_traspaso': presupuesto_traspaso,
        'presupuesto_salarial': presupuesto_salarial,
        'active_tab': active_tab,
        'all_players_json': all_players_json,
    })


# ====================== DETALLE JUGADOR ======================
@login_required
def detalle_jugador(request, id):
    try:
        jugador = Player.objects.get(id=id)
    except Player.DoesNotExist:
        messages.error(request, "Jugador no encontrado.")
        return redirect('mi_equipo')

    stats = jugador.stats_extra or {}

    categorias = {
        "AGRESOR": ["Ataque", "Control de balon", "Regate", "Pase raso", "Pace bombeado", "Finalizacion", "Balon parado", "Cabeza"],
        "DEFENSA": ["Defensa", "Recuperacion de balon", "Potencia de tiro", "Marcaje"],
        "ATLETISMO": ["Velocidad", "Fuerza explosiva", "Salto", "Resistencia", "Contacto fisico"],
        "PORTERO": ["Capacidad de portero", "Atajar", "Despejar", "Reflejos", "Cobertura"],
        "PIE MALO": ["Uso de pie malo", "Presicion de pie malo"],
        "MENTAL": ["Regularidad", "Resistencia a lesiones"]
    }

    stats_ordenadas = {}
    usados = set()

    for categoria, lista in categorias.items():
        stats_ordenadas[categoria] = {}
        for stat in lista:
            if stat in stats:
                try:
                    valor = int(stats[stat])
                except (ValueError, TypeError):
                    valor = 0

                if stat in ["Uso de pie malo", "Presicion de pie malo"]:
                    color_class = "stat-80" if valor >= 4 else "stat-70" if valor >= 2 else "stat-bajo"
                elif stat == "Regularidad":
                    color_class = "stat-80" if valor >= 7 else "stat-70" if valor >= 4 else "stat-bajo"
                elif stat == "Resistencia a lesiones":
                    color_class = "stat-80" if valor >= 3 else "stat-70" if valor >= 2 else "stat-bajo"
                else:
                    color_class = "stat-95" if valor >= 95 else \
                                  "stat-90" if valor >= 90 else \
                                  "stat-80" if valor >= 80 else \
                                  "stat-70" if valor >= 70 else "stat-bajo"

                stats_ordenadas[categoria][stat] = {"value": valor, "color": color_class}
                usados.add(stat)

    otras_stats = {}
    for k, v in stats.items():
        if k not in usados and not isinstance(v, str):
            try:
                valor = int(v)
            except (ValueError, TypeError):
                valor = 0
            color_class = "stat-95" if valor >= 95 else "stat-90" if valor >= 90 else "stat-80" if valor >= 80 else "stat-70" if valor >= 70 else "stat-bajo"
            otras_stats[k] = {"value": valor, "color": color_class}

    habilidades = {k: v for k, v in stats.items() if v in ["Si", "No"]}

    posiciones = {}
    for k, v in stats.items():
        if k in ["PO","DFC","LI","LD","MCD","MC","MMI","MMD","MO","EXI","EXD","SD","CD"]:
            try:
                valor = int(v)
            except (ValueError, TypeError):
                valor = 0
            color_class = "stat-80" if valor >= 2 else "stat-70" if valor == 1 else "stat-bajo"
            posiciones[k] = {"value": valor, "color": color_class}

    return render(request, "jugador_stats.html", {
        "jugador": jugador,
        "stats_ordenadas": stats_ordenadas,
        "otras_stats": otras_stats,
        "habilidades": habilidades,
        "posiciones": posiciones,
    })


# ====================== LIBERAR JUGADOR ======================
PORCENTAJE_TRASPASO = 0.30
PORCENTAJE_SALARIAL = 0.15

@login_required
def liberar_jugador(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            player_id = data.get("player_id")

            jugador = get_object_or_404(Player, id=player_id)
            profile = UserProfile.objects.get(user=request.user)

            if jugador.equipo_original != profile.equipo_asignado:
                return JsonResponse({"success": False, "error": "Este jugador no pertenece a tu equipo"})

            # === CÁLCULO EXACTO DEL PRECIO (misma tabla que en mi_equipo) ===
            equipo_name = getattr(jugador.equipo_original, 'nombre', '').lower()
            es_leyenda = any(x in equipo_name for x in [
                "ea sports legacy", "ea sports icons", "ea sports legends",
                "ea sports classica", "ea sports warriors", "ea sports titans", "ea sports kings"
            ])

            if not es_leyenda:
                if 95 <= jugador.valoracion <= 97:
                    precio = {95: 240_000_000, 96: 300_000_000, 97: 380_000_000}.get(jugador.valoracion, 240_000_000)
                elif 90 <= jugador.valoracion <= 94:
                    precio = {90: 110_000_000, 91: 125_000_000, 92: 140_000_000,
                             93: 155_000_000, 94: 175_000_000}.get(jugador.valoracion, 110_000_000)
                elif 85 <= jugador.valoracion <= 89:
                    precio = {85: 45_000_000, 86: 55_000_000, 87: 65_000_000,
                             88: 75_000_000, 89: 85_000_000}.get(jugador.valoracion, 45_000_000)
                else:  # 75-84
                    precio = {75: 12_000_000, 76: 15_000_000, 77: 18_000_000, 78: 22_000_000,
                             79: 26_000_000, 80: 30_000_000, 81: 32_000_000, 82: 33_000_000,
                             83: 34_000_000, 84: 35_000_000}.get(jugador.valoracion, 12_000_000)
            else:
                if 95 <= jugador.valoracion <= 98:
                    precio = {96: 850_000_000, 97: 1_100_000_000, 98: 1_450_000_000}.get(jugador.valoracion, 850_000_000)
                elif 90 <= jugador.valoracion <= 94:
                    precio = {90: 380_000_000, 91: 420_000_000, 92: 480_000_000,
                             93: 540_000_000, 94: 620_000_000}.get(jugador.valoracion, 380_000_000)
                elif 85 <= jugador.valoracion <= 89:
                    precio = {85: 140_000_000, 86: 160_000_000, 87: 190_000_000,
                             88: 210_000_000, 89: 240_000_000}.get(jugador.valoracion, 140_000_000)
                else:
                    precio = 140_000_000

            # Calcular recuperación
            traspaso_recuperado = round(precio * PORCENTAJE_TRASPASO)
            salarial_recuperado = round(precio * PORCENTAJE_SALARIAL)

            # Actualizar presupuestos
            profile.presupuesto_traspaso += traspaso_recuperado
            profile.presupuesto_salarial += salarial_recuperado
            profile.save()

            # Liberar jugador
            jugador.equipo_original = None
            jugador.save()

            return JsonResponse({
                "success": True,
                "message": f"Se liberó {jugador.nombre}.\n"
                           f"+${traspaso_recuperado:,} a Traspasos\n"
                           f"+${salarial_recuperado:,} a Salarial"
            })

        except Exception as e:
            print("Error al liberar jugador:", str(e))
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido"})

# ====================== FICHAR JUGADOR ======================
@login_required
def fichar_jugador(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            player_id = data.get('player_id')

            if not player_id:
                return JsonResponse({"success": False, "error": "ID de jugador no proporcionado"})

            profile = UserProfile.objects.get(user=request.user)
            jugador = get_object_or_404(Player, id=player_id)

            if jugador.equipo_original == profile.equipo_asignado:
                return JsonResponse({"success": False, "error": "Este jugador ya está en tu equipo"})

            # Límite de plantilla
            mis_jugadores_count = Player.objects.filter(equipo_original=profile.equipo_asignado).count()
            if mis_jugadores_count >= 32:
                return JsonResponse({"success": False, "error": "Plantilla Completa (máximo 32 jugadores)"})

            # === CÁLCULO DIRECTO DEL PRECIO (igual que en mi_equipo) ===
            equipo_name = getattr(jugador.equipo_original, 'nombre', '') if jugador.equipo_original else ''
            es_leyenda = any(x in equipo_name.lower() for x in [
                "ea sports legacy", "ea sports icons", "ea sports legends",
                "ea sports classica", "ea sports warriors", "ea sports titans", "ea sports kings"
            ])

            # Tabla de precios (copiada exactamente de tu función)
            if not es_leyenda:
                if 95 <= jugador.valoracion <= 97:
                    precio = {95: 240_000_000, 96: 300_000_000, 97: 380_000_000}.get(jugador.valoracion, 240_000_000)
                elif 90 <= jugador.valoracion <= 94:
                    precio = {90: 110_000_000, 91: 125_000_000, 92: 140_000_000,
                             93: 155_000_000, 94: 175_000_000}.get(jugador.valoracion, 110_000_000)
                elif 85 <= jugador.valoracion <= 89:
                    precio = {85: 45_000_000, 86: 55_000_000, 87: 65_000_000,
                             88: 75_000_000, 89: 85_000_000}.get(jugador.valoracion, 45_000_000)
                else:  # 75-84
                    precio = {75: 12_000_000, 76: 15_000_000, 77: 18_000_000, 78: 22_000_000,
                             79: 26_000_000, 80: 30_000_000, 81: 32_000_000, 82: 33_000_000,
                             83: 34_000_000, 84: 35_000_000}.get(jugador.valoracion, 12_000_000)
            else:
                if 95 <= jugador.valoracion <= 98:
                    precio = {96: 850_000_000, 97: 1_100_000_000, 98: 1_450_000_000}.get(jugador.valoracion, 850_000_000)
                elif 90 <= jugador.valoracion <= 94:
                    precio = {90: 380_000_000, 91: 420_000_000, 92: 480_000_000,
                             93: 540_000_000, 94: 620_000_000}.get(jugador.valoracion, 380_000_000)
                elif 85 <= jugador.valoracion <= 89:
                    precio = {85: 140_000_000, 86: 160_000_000, 87: 190_000_000,
                             88: 210_000_000, 89: 240_000_000}.get(jugador.valoracion, 140_000_000)
                else:
                    precio = 140_000_000

            salario = int(precio * 0.08)

            # Validaciones
            if precio > profile.presupuesto_traspaso:
                return JsonResponse({"success": False, "error": f"Presupuesto de Traspasos insuficiente. Necesitas ${precio:,} y tienes ${profile.presupuesto_traspaso:,}"})

            if salario > profile.presupuesto_salarial:
                return JsonResponse({"success": False, "error": "Presupuesto Salarial insuficiente"})

            # Realizar fichaje
            jugador.equipo_original = profile.equipo_asignado
            jugador.precio_calculado = precio
            jugador.salario_anual = salario
            jugador.save()

            profile.presupuesto_traspaso -= precio
            profile.presupuesto_salarial -= salario
            profile.save()

            return JsonResponse({
                "success": True,
                "message": f"¡{jugador.nombre} fichado correctamente!\n"
                           f"-${precio:,} Traspasos\n"
                           f"-${salario:,} Salarial"
            })

        except Exception as e:
            print("Error al fichar jugador:", str(e))
            return JsonResponse({"success": False, "error": f"Error interno: {str(e)}"})

    return JsonResponse({"success": False, "error": "Método no permitido"})
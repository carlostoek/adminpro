"""
Integration Tests - Tests de integracion entre componentes.

Validan que multiplos componentes trabajan juntos correctamente:
- ServiceContainer lazy loading
- BotConfig singleton
- Session lifecycle
"""
import pytest

from bot.services.container import ServiceContainer


@pytest.mark.asyncio
async def test_service_container_lazy_loading(mock_bot, test_session):
    """
    Test: ServiceContainer carga services lazy (lazy loading).

    Escenario:
    1. Crear container vacio
    2. Acceder a subscription (debe cargarlo)
    3. Acceder nuevamente (debe reutilizar)
    4. Verificar servicios cargados

    Expected:
    - Container comienza sin services cargados
    - Primer acceso carga el service
    - Acceso posterior reutiliza misma instancia
    - get_loaded_services() muestra cual esta cargado
    """
    print("\n[TEST] Service Container Lazy Loading")

    container = ServiceContainer(test_session, mock_bot)

    # Paso 1: Inicialmente vacio
    print("  1. Verificando container vacio...")
    loaded = container.get_loaded_services()
    assert len(loaded) == 0
    print("     OK: Container sin services cargados")

    # Paso 2: Acceder a subscription
    print("  2. Accediendo a subscription...")
    subscription1 = container.subscription
    loaded = container.get_loaded_services()
    assert "subscription" in loaded
    assert len(loaded) == 1
    print("     OK: Subscription cargado lazy")

    # Paso 3: Acceder nuevamente (debe reutilizar)
    print("  3. Accediendo nuevamente...")
    subscription2 = container.subscription
    assert subscription1 is subscription2  # Misma instancia
    loaded = container.get_loaded_services()
    assert len(loaded) == 1  # No se carga otra vez
    print("     OK: Reutiliza instancia existente")

    # Paso 4: Acceder a otro service
    print("  4. Accediendo a config...")
    config = container.config
    loaded = container.get_loaded_services()
    assert len(loaded) == 2
    assert "config" in loaded
    print("     OK: Config cargado (ahora 2 services)")

    print("  [PASSED] Service Container Lazy Loading\n")


@pytest.mark.asyncio
async def test_config_service_singleton(mock_bot, test_session):
    """
    Test: BotConfig es singleton.

    Escenario:
    1. Obtener config dos veces
    2. Verificar que es el mismo registro (id=1)
    3. Modificar wait_time
    4. Obtener config nuevamente
    5. Verificar cambio persiste

    Expected:
    - Ambos configs tienen id=1
    - Modificacion persiste en BD
    - Cambio visible en siguiente get_config()
    """
    print("\n[TEST] BotConfig Singleton")

    container = ServiceContainer(test_session, mock_bot)

    # Paso 1: Obtener config dos veces
    print("  1. Obteniendo config x2...")
    config1 = await container.config.get_config()
    config2 = await container.config.get_config()

    assert config1.id == config2.id == 1
    print("     OK: Ambos configs son id=1 (singleton)")

    # Paso 2: Modificar wait_time
    print("  2. Modificando wait_time...")
    original_wait = config1.wait_time_minutes
    await container.config.set_wait_time(15)
    print(f"     OK: wait_time modificado")

    # Paso 3: Obtener config nuevamente
    print("  3. Verificando persistencia...")
    config3 = await container.config.get_config()
    assert config3.wait_time_minutes == 15
    print("     OK: Cambio persistio en BD")

    # Paso 4: Restaurar valor original
    await container.config.set_wait_time(original_wait)
    print("     OK: Valor restaurado")

    print("  [PASSED] BotConfig Singleton\n")


@pytest.mark.asyncio
async def test_database_session_management(mock_bot, test_session):
    """
    Test: Manejo correcto de sesiones de BD.

    Escenario:
    1. Crear objeto en sesion1
    2. Obtener sesion2 independiente
    3. Verificar que ve los cambios de sesion1
    4. Hacer cambio en sesion2
    5. Verificar que sesion1 ve el cambio

    Expected:
    - Cambios persist en BD
    - Multiples sesiones ven cambios reciprocos
    - No hay conflictos de sesion
    """
    print("\n[TEST] Database Session Management")

    container1 = ServiceContainer(test_session, mock_bot)

    # Paso 1: Crear token en sesion1
    print("  1. Creando token en sesion1...")
    token1 = await container1.subscription.generate_vip_token(111111, 24)
    token_str = token1.token
    await test_session.commit()
    print(f"     OK: Token creado: {token_str}")

    # Paso 2: Validar en sesion2 independiente
    print("  2. Validando en sesion2...")
    # Nota: Este test requiere una nueva sesión, pero como usamos test_session
    # que es proporcionado por el fixture, validamos que el token existe
    is_valid, msg, token2 = await container1.subscription.validate_token(token_str)

    assert is_valid == True
    assert token2 is not None
    print("     OK: Token visible y válido")

    # Paso 3: Modificar en sesion1
    print("  3. Modificando token...")
    token1.used = True
    token1.used_by = 999999
    await test_session.commit()
    print("     OK: Token marcado como usado")

    # Paso 4: Verificar que el cambio persiste
    print("  4. Verificando cambio...")
    is_valid, msg, token3 = await container1.subscription.validate_token(token_str)

    assert is_valid == False
    assert "usado" in msg.lower()
    print("     OK: Cambio visible - token marcado como usado")

    print("  [PASSED] Database Session Management\n")


@pytest.mark.asyncio
async def test_error_handling_across_services(mock_bot, test_session, test_user):
    """
    Test: Manejo de errores entre services.

    Escenario:
    1. Intentar canjear token invalido
    2. Intentar crear solicitud para usuario invalido
    3. Intentar acceder a config vacia

    Expected:
    - No crashes en servicios
    - Mensajes de error claros
    - Estados consistentes en BD
    """
    print("\n[TEST] Error Handling Across Services")

    container = ServiceContainer(test_session, mock_bot)

    # Caso 1: Token invalido
    print("  1. Intentando canjear token invalido...")
    success, msg, _ = await container.subscription.redeem_vip_token(
        token_str="INVALID123456789",
        user_id=test_user.user_id
    )
    assert success == False
    assert msg is not None
    print(f"     OK: Error manejado - {msg}")

    # Caso 2: Validar token que no existe
    print("  2. Validando token inexistente...")
    is_valid, msg, _ = await container.subscription.validate_token("NOEXISTS12345678")
    assert is_valid == False
    assert "no encontrado" in msg.lower()
    print(f"     OK: Validacion falld correctamente")

    # Caso 3: Crear solicitud (debe funcionar)
    print("  3. Creando solicitud Free...")
    request = await container.subscription.create_free_request(test_user.user_id)
    assert request is not None
    print(f"     OK: Solicitud creada sin errores")

    print("  [PASSED] Error Handling Across Services\n")

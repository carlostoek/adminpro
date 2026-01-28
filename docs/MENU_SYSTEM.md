# Arquitectura del Sistema de Menús

## Visión General

### Propósito y Objetivos

El sistema de menús de AdminPro proporciona una experiencia de usuario personalizada basada en roles (Admin/VIP/Free) con una voz consistente personificada por **Lucien**, el mayordomo sofisticado de Diana. Este documento explica la arquitectura completa del sistema, desde la detección de roles hasta el routing de callbacks, pasando por los message providers y el sistema de teclados.

**Objetivos principales:**

- **Personalización por rol:** Cada usuario recibe una experiencia de menú adaptada a su rol (Admin, VIP, Free)
- **Consistencia de voz:** Todos los mensajes mantienen la voz de Lucien (sofisticado, misterioso, servicial)
- **Arquitectura sin estado:** Los providers no almacenan sesión ni bot, enabling escalabilidad
- **Navegación fluida:** Sistema unificado de callbacks y teclados inline
- **Mantenibilidad:** Patrones claros y reutilizables para agregar nuevas opciones de menú

### Concepto de Menús Basados en Roles

El sistema implementa **tres experiencias de menú distintas**, cada una optimizada para el rol del usuario:

| Rol | Experiencia | Terminología Lucien | Acceso |
|-----|-------------|---------------------|--------|
| **Admin** | Panel de gestión completa | "custodio", "reino", "calibración" | Config.ADMIN_USER_IDS |
| **VIP** | Contenido exclusivo premium | "círculo exclusivo", "tesoros del sanctum" | VIPSubscriber.activo |
| **Free** | Contenido gratuito + cola | "jardín público", "visitantes", "muestras" | Todos los usuarios |

**Flujo de detección de rol:**

```
Usuario envía mensaje/comando
         ↓
UserRoleDetectionMiddleware detecta rol
         ↓
Prioridad: Admin > VIP > Free (primera coincidencia gana)
         ↓
Router apropiado maneja el evento
         ↓
MessageProvider genera respuesta con voz de Lucien
         ↓
Usuario recibe menú personalizado
```

### Integración de la Voz de Lucien

**Lucien** es la personificación del sistema: un mayordomo sofisticado y misterioso que sirve a Diana. Su voz está integrada en TODO el sistema de menús:

**Características de voz:**

- **Formal pero accesible:** Siempre usa "usted", nunca "tú"
- **Misterioso:** Emplea pausas dramáticas ("...") y sugestiones
- **Observador:** Hace comentarios perspicaces sobre las intenciones del usuario
- **Referencias a Diana:** Menciona a Diana para añadir autoridad y misterio
- **Terminología específica por rol:**
  - Admin → "custodio", "reino", "calibración"
  - VIP → "círculo exclusivo", "tesoros", "sanctum"
  - Free → "jardín público", "visitantes", "muestras"

**Referencia completa:** Ver [`docs/guia-estilo.md`](guia-estilo.md) para la guía de estilo completa de Lucien.

---

## Diagrama de Arquitectura

### Vista de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                         Usuario Telegram                        │
│  (Envía mensaje, presiona botón, interactúa con el bot)         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Aiogram Dispatcher                           │
│  (Recibe eventos de Telegram: Message, CallbackQuery)          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│              RoleDetectionMiddleware                            │
│  (Detecta rol: Admin > VIP > Free, inyecta user_role)          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┼────────────┐
                ↓            ↓            ↓
        ┌───────────┐ ┌──────────┐ ┌──────────┐
        │admin_router│ │vip_router│ │free_router│
        │           │ │          │ │          │
        │Handlers:  │ │Handlers: │ │Handlers: │
        │/admin     │ │/start    │ │/start    │
        │Callbacks: │ │vip:*     │ │free:*    │
        │admin:*    │ │          │ │          │
        └─────┬─────┘ └────┬─────┘ └────┬─────┘
              │            │            │
              └────────────┼────────────┘
                           ↓
              ┌─────────────────────────┐
              │  ServiceContainer       │
              │  (DI + Lazy Loading)    │
              └────────────┬────────────┘
                           ↓
              ┌─────────────────────────┐
              │  MessageProviders       │
              │  (Voz de Lucien)        │
              └────────────┬────────────┘
                           ↓
              ┌─────────────────────────┐
              │  KeyboardFactory        │
              │  (Teclados inline)      │
              └────────────┬────────────┘
                           ↓
              ┌─────────────────────────┐
              │  Respuesta al Usuario   │
              │  (Mensaje + teclado)    │
              └─────────────────────────┘
```

### Flujo de Request-Response

```
1. USUARIO → Mensaje/Callback
   ↓
2. RoleDetectionMiddleware
   - Extrae user_id del evento
   - Consulta RoleDetectionService
   - Determina rol (Admin/VIP/Free)
   - Inyecta data["user_role"]
   ↓
3. Router Selection (basado en callback data o comando)
   - admin:... → admin_router
   - vip:... → vip_router
   - free:... → free_router
   ↓
4. Handler Execution
   - Recibe user_role inyectado
   - Ejecuta lógica de negocio
   - Llama a MessageProvider apropiado
   ↓
5. MessageProvider Generation
   - Genera texto con voz de Lucien
   - Crea teclado inline con buttons
   - Retorna (text, keyboard)
   ↓
6. Response to User
   - message.answer() o callback.message.edit()
   - Usuario ve menú personalizado
```

### Interacción de Servicios

```
┌────────────────────────────────────────────────────────────┐
│                     main.py                                 │
│  (Registra routers, middlewares, inicia bot)               │
└──────────────┬─────────────────────────────────────────────┘
               │
               ├──→ RoleDetectionMiddleware (global)
               │    └──→ RoleDetectionService
               │         └──→ Database (User, VIPSubscriber)
               │
               ├──→ DatabaseMiddleware (admin_router)
               │    └──→ AsyncSession inyección
               │
               └──→ AdminAuthMiddleware (admin_router)
                    └──→ Config.is_admin() validación
```

---

## Sistema de Detección de Rol

### UserRoleDetectionMiddleware

El middleware `RoleDetectionMiddleware` es el componente central que detecta e inyecta el rol del usuario en **todos** los handlers.

**Archivo:** [`bot/middlewares/role_detection.py`](../bot/middlewares/role_detection.py)

**Cómo funciona:**

1. **Sin estado (Stateless):** Recalcula el rol en cada request, sin caché
2. **Prioridad estricta:** Admin > VIP > Free (primera coincidencia gana)
3. **Inyección en data:** `data["user_role"]` y `data["user_id"]`
4. **Graceful degradation:** Si no hay sesión, ejecuta handler sin role injection

**Prioridad de detección:**

```python
# Lógica de detección (simplificada)
async def get_user_role(user_id: int) -> UserRole:
    # 1. Verificar si es admin (mayor prioridad)
    if user_id in Config.ADMIN_USER_IDS:
        return UserRole.ADMIN

    # 2. Verificar si es VIP activo
    vip_subscriber = await session.get(VIPSubscriber, user_id)
    if vip_subscriber and vip_subscriber.is_active():
        return UserRole.VIP

    # 3. Default: Free (todos los usuarios tienen acceso)
    return UserRole.FREE
```

**Edge cases manejados:**

- **Usuario sin sesión:** Middleware no falla, ejecuta handler sin inyección
- **VIP expirado:** Se detecta como Free (no como VIP)
- **Admin que también es VIP:** Se detecta como Admin (prioridad)
- **Usuario nuevo:** Se detecta como Free (acceso por defecto)

**Registration:**

```python
# main.py
from bot.middlewares.role_detection import RoleDetectionMiddleware

# Aplicar globalmente (messages y callbacks)
dp.message.middleware(RoleDetectionMiddleware())
dp.callback_query.middleware(RoleDetectionMiddleware())
```

### Role Change Logging

Todos los cambios de rol se registran en `UserRoleChangeLog` con **RoleChangeService**:

**Tipos de cambios:**

| Reason | Descripción | changed_by |
|--------|-------------|------------|
| `RoleChangeReason.TOKEN_REDEEMED` | Usuario canjeó token VIP | user_id |
| `RoleChangeReason.VIP_EXPIRED` | Suscripción VIP expiró | 0 (SYSTEM) |
| `RoleChangeReason.MANUAL_CHANGE` | Admin cambió rol manualmente | admin_id |
| `RoleChangeReason.KICKED` | Usuario expulsado del canal | admin_id |

**Audit trail:**

```python
# Ejemplo: Cambio de rol por expiración VIP
await role_change_service.log_role_change(
    user_id=12345,
    previous_role=UserRole.VIP,
    new_role=UserRole.FREE,
    reason=RoleChangeReason.VIP_EXPIRED,
    changed_by=0,  # 0 = SYSTEM
    change_metadata="Suscripción expiró automáticamente"
)
```

**Beneficios:**

- **Auditoría completa:** Quién cambió qué rol, cuándo, y por qué
- **Debugging:** Trazabilidad de cambios de rol inesperados
- **Compliance:** Registro para análisis de comportamiento

### Router Architecture

El sistema utiliza **routers separados por rol** para organizar handlers y callbacks:

**Estructura de routers:**

```python
# bot/handlers/admin/
admin_router = Router()
admin_router.message.middleware(DatabaseMiddleware())
admin_router.callback_query.middleware(DatabaseMiddleware())

# bot/handlers/vip/
vip_router = Router()

# bot/handlers/free/
free_router = Router()
```

**Registration en main.py:**

```python
# Admin router (solo para administradores)
dp.include_router(admin_router)

# VIP router (usuarios VIP)
dp.include_router(vip_router)

# Free router (todos los usuarios)
dp.include_router(free_router)
```

**Middleware application:**

- **AdminRouter:** `DatabaseMiddleware` + `AdminAuthMiddleware`
- **VIP/Free routers:** Solo `RoleDetectionMiddleware` (global)

**Ejemplo de handler con detección de rol:**

```python
@router.message(Command("start"))
async def start_handler(
    message: Message,
    user_role: UserRole,  # Inyectado por RoleDetectionMiddleware
    user_id: int          # Inyectado por RoleDetectionMiddleware
):
    if user_role == UserRole.ADMIN:
        return await admin_menu_handler(message)
    elif user_role == UserRole.VIP:
        return await vip_menu_handler(message)
    else:
        return await free_menu_handler(message)
```

**Ventajas de routers separados:**

- **Organización clara:** Handlers agrupados por rol
- **Middleware específico:** Cada router tiene sus propios middlewares
- **Mantenibilidad:** Fácil agregar/eliminar handlers por rol
- **Escalabilidad:** Routers pueden extenderse sin afectar otros

---

## Arquitectura de Message Providers

### Patrón BaseMessageProvider

`BaseMessageProvider` es la clase base abstracta para **todos** los message providers del sistema.

**Archivo:** [`bot/services/message/base.py`](../bot/services/message/base.py)

**Características principales:**

1. **Sin estado (Stateless):**
   - No almacena `session` ni `bot` como variables de instancia
   - Todo el contexto se pasa como parámetros de método
   - Evita memory leaks y habilita escalabilidad

2. **Composición de templates:**
   - `_compose(header, body, footer)`: Construye mensajes HTML
   - Separación de estructura y contenido

3. **Selección de variantes:**
   - `_choose_variant()`: Selección aleatoria con pesos opcionales
   - Session-aware: Excluye variantes recientes para evitar repetición

**Anti-patterns a evitar:**

```python
# ❌ INCORRECTO: Almacena session en __init__
class BadProvider(BaseMessageProvider):
    def __init__(self, session: AsyncSession):
        self.session = session  # MEMORY LEAK!

# ✅ CORRECTO: Session se pasa como parámetro
class GoodProvider(BaseMessageProvider):
    def get_message(self, session: AsyncSession) -> str:
        # Usar session localmente
        pass
```

**Jerarquía de providers:**

```
BaseMessageProvider (ABC)
         │
         ├─→ CommonMessages (mensajes compartidos)
         │    ├─→ Success/Error patterns
         │    └─→ Navigation helpers
         │
         ├─→ Admin*Messages (7 providers admin)
         │    ├─→ AdminMainMessages (menú principal admin)
         │    ├─→ AdminVIPMessages (gestión VIP)
         │    ├─→ AdminFreeMessages (gestión Free)
         │    ├─→ AdminContentMessages (CRUD contenido)
         │    ├─→ AdminInterestMessages (gestión intereses)
         │    └─→ AdminUserMessages (gestión usuarios)
         │
         └─→ User*Messages (3 providers usuario)
              ├─→ UserStartMessages (mensaje /start)
              ├─→ UserMenuMessages (menús VIP/Free)
              └─→ UserFlowMessages (flows de usuario)
```

### Patrón Stateless: Beneficios

**¿Por qué stateless?**

1. **Eficiencia de memoria:**
   - No hay estado por usuario almacenado en providers
   - Mismo provider puede atender a miles de usuarios
   - ~0 bytes de overhead por usuario

2. **Thread-safe:**
   - Compatible con async/await (race conditions imposibles)
   - Mismo provider puede ejecutarse concurrentemente
   - No locks ni semáforos necesarios

3. **Testable:**
   - Comportamiento de función pura (mismo input = mismo output)
   - Fácil de mockear en tests
   - No setup complejo necesario

4. **Cacheable:**
   - Output puede cachearse por input
   - CDN-friendly para respuestas idénticas
   - Reducciónd e carga de base de datos

**Ejemplo de patrón stateless:**

```python
class UserMenuMessages(BaseMessageProvider):
    def vip_menu_greeting(
        self,
        user_name: str,  # Contexto pasado como parámetro
        vip_expires_at: Optional[datetime] = None,
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Genera saludo del menú VIP.

        Note: No self.session ni self.bot.
        Todo el contexto viene como parámetros.
        """
        safe_name = escape_html(user_name)

        # Seleccionar variación de saludo
        greeting = self._choose_variant(
            ["Variación 1", "Variación 2", "Variación 3"],
            user_id=user_id,
            method_name="vip_menu_greeting",
            session_history=session_history
        )

        # Componer mensaje
        header = f"🎩 <b>Lucien:</b>\n\n<i>{greeting}</i>"
        body = f"Bienvenido, <b>{safe_name}</b>..."
        text = self._compose(header, body)

        # Crear teclado
        keyboard = self._vip_main_menu_keyboard()

        return text, keyboard
```

### Variaciones Session-Aware

El sistema implementa **variaciones session-aware** para evitar repetición robótica:

**SessionMessageHistory:**

- Rastrea últimas 2 variantes mostradas por mensaje/usuario
- Exclusion window de 2 variantes (no repite inmediatamente)
- ~80 bytes de overhead por usuario (acceptable)

**Funcionamiento:**

```python
# Sin session history (random simple)
greeting = random.choice(["Hola", "Bienvenido", "Saludos"])
# Puede repetir la misma variación en seguida

# Con session history (evita repetición)
greeting = provider._choose_variant(
    ["Hola", "Bienvenido", "Saludos"],
    user_id=12345,
    method_name="greeting",
    session_history=session_history
)
# Si user vio "Hola" las últimas 2 veces, excluirá "Hola"
```

**Weighted random selection:**

```python
# 60% común, 30% alternativo, 10% poético
greetings = [
    ("Bienvenido al círculo exclusivo...", 0.6),
    ("El sanctum le recibe...", 0.3),
    ("Los portales se abren...", 0.1),
]

greeting = provider._choose_variant(
    [g[0] for g in greetings],
    weights=[g[1] for g in greetings],
    user_id=user_id,
    method_name="vip_menu_greeting",
    session_history=session_history
)
```

**Beneficios:**

- **Naturalidad:** Evita repetición robótica
- **Personalidad:** Permite variaciones "raras" (10%) para sorpresa
- **Consistencia:** Mismo usuario no ve misma variación en corto tiempo

---

## Sistema de Keyboard Factory

### InlineKeyboardBuilder Usage

El sistema utiliza **funciones factory** para crear teclados inline de manera consistente:

**Archivo:** [`bot/utils/keyboards.py`](../bot/utils/keyboards.py)

**Funciones principales:**

1. **`create_inline_keyboard(buttons)`:** Crea teclado desde estructura de datos
2. **`create_menu_navigation()`:** Crea filas de navegación (Volver/Salir)
3. **`create_content_with_navigation()`:** Combina contenido + navegación

**Estructura de botones:**

```python
buttons = [
    # Fila 1: 1 botón
    [{"text": "Opción 1", "callback_data": "opt1"}],

    # Fila 2: 2 botones
    [
        {"text": "Sí", "callback_data": "yes"},
        {"text": "No", "callback_data": "no"}
    ],

    # Fila 3: botón con URL
    [{"text": "Visitar", "url": "https://example.com"}]
]

keyboard = create_inline_keyboard(buttons)
```

### Callback Data Patterns

**Formato jerárquico:**

```
{scope}:{entity}:{action}:{id}
```

**Componentes:**

- **scope:** `admin`, `vip`, `free`, `user`
- **entity:** `content`, `user`, `package`, `interest`
- **action:** `list`, `view`, `create`, `edit`, `delete`
- **id:** (opcional) ID de entidad

**Ejemplos de callbacks:**

| Callback Data | Acción |
|---------------|--------|
| `admin:content:list` | Listar paquetes de contenido |
| `admin:content:create` | Crear nuevo paquete |
| `admin:content:view:5` | Ver detalles del paquete 5 |
| `admin:content:edit:5:description` | Editar descripción del paquete 5 |
| `user:packages` | Ver lista de paquetes (VIP/Free) |
| `user:package:interest:5` | Registrar interés en paquete 5 |
| `menu:back` | Volver al menú anterior |
| `menu:exit` | Salir del menú actual |

**Ventajas del formato jerárquico:**

- **Legible:** Fácil entender qué hace el callback
- **Ruteable:** Fáchil match con `F.data.startswith("admin:content:")`
- **Escalable:** Fácil agregar nuevas acciones/entities
- **Debuggable:** Logs claros de qué callback se ejecutó

### Navigation Helpers

**`create_menu_navigation()`:**

```python
def create_menu_navigation(
    include_back: bool = True,
    include_exit: bool = False,
    back_text: str = "⬅️ Volver",
    exit_text: str = "🚪 Salir",
    back_callback: str = "menu:back",
    exit_callback: str = "menu:exit"
) -> List[List[dict]]:
    """
    Crea filas de navegación estándar.
    """
    # Retorna filas de botones para compose_keyboard
```

**Patrones de navegación:**

1. **Main menu (solo exit):**
   ```python
   create_menu_navigation(include_back=False, include_exit=False)
   # Resultado: [] (sin botones de navegación)
   ```

2. **Submenu (back + exit):**
   ```python
   create_menu_navigation(include_back=True, include_exit=True)
   # Resultado: [[Volver, Salir]]
   ```

3. **Detail view (solo back):**
   ```python
   create_menu_navigation(include_back=True, include_exit=False)
   # Resultado: [[Volver]]
   ```

**`create_content_with_navigation()`:**

```python
# Convenience wrapper
content_buttons = [
    [{"text": "Paquete 1", "callback_data": "pkg:1"}],
    [{"text": "Paquete 2", "callback_data": "pkg:2"}]
]

keyboard = create_content_with_navigation(
    content_buttons,
    include_back=True,
    include_exit=False,
    back_text="⬅️ Volver",
    back_callback="menu:back"
)
```

**Beneficios:**

- **Consistencia visual:** Mismo estilo de navegación en todos los menús
- **Mantenibilidad:** Cambio centralizado de textos/callbacks
- **Reutilización:** No repetir lógica de navegación

---

## Callback Routing

### Router Separation por Rol

El sistema implementa **routers separados** para manejar callbacks de cada rol:

**Estructura de callback handlers:**

```
bot/handlers/
├── admin/
│   ├── menu.py              # /admin command
│   ├── menu_callbacks.py    # admin:* callbacks
│   ├── content/             # admin:content:* callbacks
│   ├── users/               # admin:user:* callbacks
│   └── interests/           # admin:interests:* callbacks
├── vip/
│   ├── menu.py              # VIP menu handlers
│   └── menu_callbacks.py    # vip:* callbacks
└── free/
    ├── menu.py              # Free menu handlers
    └── menu_callbacks.py    # free:* callbacks
```

**Registration en main.py:**

```python
# Admin callbacks
dp.include_router(admin_router)

# VIP callbacks
dp.include_router(vip_router)

# Free callbacks
dp.include_router(free_router)
```

### Callback Pattern Matching

**Patrón de handler:**

```python
from aiogram import F
from aiogram.types import CallbackQuery

@router.callback_query(F.data.startswith("admin:content:"))
async def content_callback_handler(callback: CallbackQuery):
    """
    Maneja todos los callbacks admin:content:*
    """
    parts = callback.data.split(":")
    # parts = ["admin", "content", "action", "id"]

    action = parts[2]  # "list", "view", "create", "edit"
    entity_id = int(parts[3]) if len(parts) > 3 else None

    await callback.answer()  # Siempre responder al callback

    if action == "list":
        return await show_content_list(callback)
    elif action == "view":
        return await show_content_detail(callback, entity_id)
    elif action == "create":
        return await start_content_creation(callback)
    elif action == "edit":
        return await start_content_edit(callback, entity_id)
```

**Best practices:**

1. **Siempre hacer `await callback.answer()`:**
   - Evita que el callback quede "cargando" infinito
   - Opcional: mostrar toast con `callback.answer("Acción completada")`

2. **Usar `F.data.startswith()` para match:**
   - Más eficiente que regex
   - Maneja callbacks dinámicos (con IDs)

3. **Validar datos antes de procesar:**
   - Check si entity_id existe en BD
   - Verificar permisos del usuario

4. **Manejar errores gracefully:**
   - Try-except en handlers
   - Enviar mensaje de error en voz de Lucien

### Handler Execution Flow

```
Usuario presiona botón
         ↓
CallbackQuery enviado al bot
         ↓
Dispatcher routea al router apropiado
         ↓
Callback handler ejecuta:
    1. Parse callback.data
    2. await callback.answer()
    3. Ejecuta lógica de negocio
    4. Genera nueva vista (message o edit)
         ↓
Usuario ve nueva vista
```

**Ejemplo completo:**

```python
@router.callback_query(F.data.startswith("admin:content:view:"))
async def content_view_handler(callback: CallbackQuery, session: AsyncSession):
    # 1. Parse callback data
    parts = callback.data.split(":")
    package_id = int(parts[3])

    # 2. Answer callback (siempre)
    await callback.answer()

    # 3. Ejecutar lógica de negocio
    try:
        package = await session.get(ContentPackage, package_id)
        if not package:
            await callback.message.edit("⚠️ Paquete no encontrado")
            return

        # 4. Generar nueva vista
        provider = AdminContentMessages()
        text, keyboard = provider.package_detail_view(package)
        await callback.message.edit(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error viewing package {package_id}: {e}")
        await callback.message.edit("⚠️ Error al cargar paquete")
```

---

## Integración de la Voz de Lucien

### Voice Style Guide

La voz de Lucien está documentada en [`docs/guia-estilo.md`](guia-estilo.md).

**Características principales:**

| Aspecto | Implementación |
|---------|----------------|
| **Formalidad** | Siempre "usted", nunca "tú" |
| **Emoji** | 🎩 para Lucien, 🌸 para Diana |
| **Pausas** | Uso de "..." para dramatic effect |
| **Misterio** | Insinuaciones, no directas |
| **Referencias** | Menciones a Diana para autoridad |

**Terminología por rol:**

| Contexto | Término Lucien |
|----------|----------------|
| Admin | "custodio", "reino", "calibración" |
| VIP | "círculo exclusivo", "tesoros", "sanctum" |
| Free | "jardín público", "visitantes", "muestras" |
| Suscripción VIP | "membresía del círculo" |
| Contenido Free | "muestras del jardín" |
| Error | "inconveniente", "imprevisto" |
| Éxito | "Diana aprueba", "excelente elección" |

### Variaciones Role-Specific

**VIP users (elegante, exclusivo):**

```python
greetings = [
    ("Ah, un miembro del círculo exclusivo...", 0.6),
    ("Bienvenido de nuevo al sanctum...", 0.3),
    ("Los portales del reino se abren para usted...", 0.1),
]
```

**Free users (acogedor, informativo):**

```python
greetings = [
    ("Bienvenido al jardín público...", 0.7),
    ("El vestíbulo de acceso aguarda su contemplación...", 0.3),
]
```

**Admins (colaborativo, formal):**

```python
greetings = [
    ("Ah, el custodio de los dominios de Diana...", 0.6),
    ("Bienvenido al sanctum de gestión...", 0.3),
    ("Loshilos del reino esperan su dirección...", 0.1),
]
```

### Sistema de Variaciones

**Weighted random selection:**

```python
def _choose_variant(
    self,
    variants: list[str],
    weights: Optional[list[float]] = None,
    user_id: Optional[int] = None,
    method_name: Optional[str] = None,
    session_history: Optional["SessionMessageHistory"] = None
) -> str:
    """
    Selecciona variación con pesos y session awareness.
    """
    # Sin session context: random simple
    if session_history is None:
        if weights is None:
            return random.choice(variants)
        return random.choices(variants, weights=weights, k=1)[0]

    # Con session context: excluir variantes recientes
    recent_indices = session_history.get_recent_variants(
        user_id, method_name, limit=2
    )

    available_indices = [
        i for i in range(len(variants))
        if i not in recent_indices
    ]

    # Seleccionar desde disponibles
    selected_idx = random.choice(available_indices)
    session_history.add_entry(user_id, method_name, selected_idx)

    return variants[selected_idx]
```

**Voice linting:**

El sistema implementa un **pre-commit hook** para validar la voz de Lucien:

```bash
# .git/hooks/pre-commit
#!/bin/bash
# Valida que los messages providers usen voz de Lucien
python -m bot.utils.voice_linter bot/services/message/
```

**Validaciones:**

- ✅ Emoji 🎩 presente en mensajes de Lucien
- ✅ Uso de "usted", no "tú"
- ✅ Referencias a Diana apropiadas
- ✅ Pausas dramáticas ("...") usadas correctamente
- ✅ Terminología de rol correcta

---

## Ejemplos de Código

### Agregar Nueva Opción de Menú

**Escenario:** Agregar botón "Ver Estadísticas" al menú VIP

**1. Agregar callback handler:**

```python
# bot/handlers/vip/menu_callbacks.py

@router.callback_query(F.data == "vip:stats")
async def vip_stats_handler(callback: CallbackQuery, session: AsyncSession):
    """Muestra estadísticas del usuario VIP."""
    await callback.answer()

    user_id = callback.from_user.id

    # Obtener estadísticas desde servicios
    stats_service = ServiceContainer(session, callback.bot).stats
    user_stats = await stats_service.get_user_stats(user_id)

    # Generar respuesta con voz de Lucien
    provider = UserMenuMessages()
    text, keyboard = provider.vip_stats_view(
        user_name=callback.from_user.first_name,
        stats=user_stats
    )

    await callback.message.edit(text, reply_markup=keyboard)
```

**2. Agregar método a provider:**

```python
# bot/services/message/user_menu.py

class UserMenuMessages(BaseMessageProvider):
    def vip_stats_view(
        self,
        user_name: str,
        stats: dict
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """Genera vista de estadísticas VIP con voz de Lucien."""
        safe_name = escape_html(user_name)

        header = f"🎩 <b>Lucien:</b>\n\n<i>Sus logros en el círculo...</i>"

        body = (
            f"<b>📊 Estadísticas de {safe_name}</b>\n\n"
            f"<b>📦 Paquetes adquiridos:</b> {stats['packages_purchased']}\n"
            f"<b>⭐ Intereses registrados:</b> {stats['interests_registered']}\n"
            f"<b>🕐 Miembro desde:</b> {stats['member_since']}\n\n"
            f"<i>Diana observa su dedicación con particular interés...</i>"
        )

        text = self._compose(header, body)

        keyboard = create_content_with_navigation(
            content_buttons=[],  # Sin botones de contenido
            include_back=True,
            back_text="⬅️ Volver al Menú VIP"
        )

        return text, keyboard
```

**3. Agregar botón al menú principal:**

```python
# bot/services/message/user_menu.py

def _vip_main_menu_keyboard(self) -> InlineKeyboardMarkup:
    """Genera teclado del menú VIP."""
    content_buttons = [
        [{"text": "💎 Tesoros del Sanctum", "callback_data": "vip:premium"}],
        [{"text": "📊 Estado de la Membresía", "callback_data": "vip:status"}],
        [{"text": "📈 Mis Estadísticas", "callback_data": "vip:stats"}],  # NUEVO
    ]
    return create_content_with_navigation(content_buttons)
```

### Crear Message Provider

**Escenario:** Crear provider para menú de configuración de usuario

**1. Crear archivo de provider:**

```python
# bot/services/message/user_config.py

from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_content_with_navigation
from bot.utils.formatters import escape_html

class UserConfigMessages(BaseMessageProvider):
    """
    Provider para mensajes de configuración de usuario.

    Voice: Lucien (sofisticado, misterioso)
    """

    def config_menu(
        self,
        user_name: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """Genera menú de configuración."""
        safe_name = escape_html(user_name)

        header = f"🎩 <b>Lucien:</b>\n\n<i>Los ajustes del reino...</i>"

        body = (
            f"<b>⚙️ Configuración Personal</b>\n\n"
            f"<b>{safe_name}</b>, puede ajustar sus preferencias aquí...\n\n"
            f"<i>Diana permite cierta... flexibilidad en su experiencia.</i>"
        )

        text = self._compose(header, body)

        content_buttons = [
            [{"text": "🔔 Notificaciones", "callback_data": "config:notifications"}],
            [{"text": "🌐 Idioma", "callback_data": "config:language"}],
            [{"text": "🎨 Tema", "callback_data": "config:theme"}],
        ]

        keyboard = create_content_with_navigation(
            content_buttons,
            include_back=True,
            back_text="⬅️ Volver al Menú"
        )

        return text, keyboard
```

**2. Registrar en ServiceContainer:**

```python
# bot/services/container.py

class ServiceContainer:
    @property
    def user_config(self) -> UserConfigMessages:
        """User configuration messages provider (lazy loading)."""
        if not hasattr(self, "_user_config"):
            from bot.services.message.user_config import UserConfigMessages
            self._user_config = UserConfigMessages()
        return self._user_config
```

**3. Usar en handler:**

```python
# bot/handlers/user/config.py

@router.callback_query(F.data == "config:view")
async def config_view_handler(callback: CallbackQuery, container: ServiceContainer):
    """Muestra menú de configuración."""
    await callback.answer()

    provider = container.user_config
    text, keyboard = provider.config_menu(callback.from_user.first_name)

    await callback.message.edit(text, reply_markup=keyboard)
```

### Manejar Callbacks Complejos

**Escenario:** Callback con múltiples parámetros y confirmación

**Callback data:** `admin:user:role:change:{user_id}:{new_role}`

**Handler:**

```python
@router.callback_query(F.data.startswith("admin:user:role:change:"))
async def role_change_handler(callback: CallbackQuery, session: AsyncSession):
    """
    Maneja cambio de rol de usuario con confirmación.

    Callback data format: admin:user:role:change:{user_id}:{new_role}
    """
    parts = callback.data.split(":")
    target_user_id = int(parts[4])
    new_role = parts[5]

    await callback.answer()

    # 1. Obtener información del usuario
    target_user = await session.get(User, target_user_id)
    if not target_user:
        await callback.message.edit("⚠️ Usuario no encontrado")
        return

    # 2. Generar mensaje de confirmación
    provider = AdminUserMessages()
    text, keyboard = provider.role_change_confirmation(
        target_user_name=target_user.first_name,
        current_role=target_user.role,
        new_role=new_role
    )

    # 3. Editar mensaje con diálogo de confirmación
    await callback.message.edit(text, reply_markup=keyboard)
```

**Confirmation callback:** `admin:user:role:confirm:{user_id}:{new_role}`

```python
@router.callback_query(F.data.startswith("admin:user:role:confirm:"))
async def role_change_confirm_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    container: ServiceContainer
):
    """Confirma y ejecuta cambio de rol."""
    parts = callback.data.split(":")
    target_user_id = int(parts[4])
    new_role_str = parts[5]
    new_role = UserRole(new_role_str)

    await callback.answer()

    try:
        # 1. Ejecutar cambio de rol
        role_service = container.role_change
        await role_service.change_user_role(
            user_id=target_user_id,
            new_role=new_role,
            changed_by=callback.from_user.id,
            reason=RoleChangeReason.MANUAL_CHANGE
        )

        # 2. Generar mensaje de éxito
        provider = AdminUserMessages()
        text = provider.role_change_success(
            target_user_name=callback.message.reply_to_message.from_user.first_name,
            new_role=new_role
        )

        # 3. Actualizar mensaje
        await callback.message.edit(text)

    except Exception as e:
        logger.error(f"Error changing role: {e}")
        await callback.message.edit("⚠️ Error al cambiar rol")
```

---

## Guía de Testing

### Testing Message Providers

**Test de provider stateless:**

```python
import pytest
from bot.services.message.user_menu import UserMenuMessages

def test_vip_menu_greeting_stateless():
    """Test que el provider no tiene estado."""
    provider = UserMenuMessages()

    # No debe tener session ni bot
    assert not hasattr(provider, "session")
    assert not hasattr(provider, "bot")

    # Mismo input = mismo output (determinista con seed)
    text1, kb1 = provider.vip_menu_greeting("Juan", vip_expires_at=None)
    text2, kb2 = provider.vip_menu_greeting("Juan", vip_expires_at=None)

    assert "🎩" in text1
    assert "Juan" in text1
    assert "círculo exclusivo" in text1.lower()

def test_vip_menu_greeting_variants():
    """Test que todas las variantes son válidas."""
    provider = UserMenuMessages()

    for _ in range(100):  # Probar 100 veces
        text, kb = provider.vip_menu_greeting("Test", vip_expires_at=None)
        assert "🎩" in text
        assert "Test" in text
        assert len(kb.inline_keyboard) > 0
```

**Test de voz de Lucien:**

```python
def test_lucien_voice_compliance():
    """Test que los mensajes cumplen con la voz de Lucien."""
    provider = UserMenuMessages()
    text, _ = provider.vip_menu_greeting("Juan", vip_expires_at=None)

    # Emoji de Lucien presente
    assert "🎩" in text

    # Usa "usted", no "tú"
    assert "usted" in text.lower() or "su" in text.lower()
    assert "tú" not in text and "tu " not in text

    # Terminología correcta
    assert "círculo exclusivo" in text.lower() or "sanctum" in text.lower()
```

### Testing Keyboard Interactions

**Test de callback data format:**

```python
def test_callback_data_format():
    """Test que los callbacks siguen el formato correcto."""
    keyboard = create_inline_keyboard([
        [{"text": "Test", "callback_data": "admin:content:view:5"}]
    ])

    button = keyboard.inline_keyboard[0][0]
    assert button.callback_data == "admin:content:view:5"

    # Parse callback data
    parts = button.callback_data.split(":")
    assert len(parts) == 4
    assert parts[0] == "admin"
    assert parts[1] == "content"
    assert parts[2] == "view"
    assert parts[3] == "5"
```

**Test de navegación:**

```python
def test_navigation_helpers():
    """Test que los helpers de navegación funcionan."""
    nav_rows = create_menu_navigation(
        include_back=True,
        include_exit=True
    )

    assert len(nav_rows) == 1
    assert len(nav_rows[0]) == 2
    assert nav_rows[0][0]["text"] == "⬅️ Volver"
    assert nav_rows[0][1]["text"] == "🚪 Salir"
```

### Mocking Services

**Mock de ServiceContainer:**

```python
from unittest.mock import AsyncMock, Mock
from bot.services.container import ServiceContainer

@pytest.fixture
def mock_container():
    """Fixture con ServiceContainer mockeado."""
    container = Mock(spec=ServiceContainer)

    # Mock services
    container.subscription = AsyncMock()
    container.role_change = AsyncMock()
    container.stats = AsyncMock()

    return container

@pytest.mark.asyncio
async def test_handler_with_mock(mock_container):
    """Test handler con services mockeados."""
    # Configurar mock
    mock_container.subscription.get_vip_subscriber.return_value = Mock(
        is_active=Mock(return_value=True)
    )

    # Ejecutar handler
    await vip_status_handler(message, container=mock_container)

    # Verificar llamada
    mock_container.subscription.get_vip_subscriber.assert_called_once_with(12345)
```

**Mock de session:**

```python
from bot.database.engine import get_session

@pytest.mark.asyncio
async def test_handler_with_session_mock():
    """Test handler con session mockeada."""
    # Crear mock session
    mock_session = AsyncMock()
    mock_session.get.return_value = Mock(id=1, name="Test")

    # Inyectar en handler
    await handler_with_session(message, session=mock_session)

    # Verificar query
    mock_session.get.assert_called_once_with(ContentPackage, 1)
```

---

## Referencias a Implementación

### Archivos de Message Providers

**Base:**
- [`bot/services/message/base.py`](../bot/services/message/base.py) - BaseMessageProvider abstracto

**Admin providers:**
- [`bot/services/message/admin/main.py`](../bot/services/message/admin/main.py) - Menú principal admin
- [`bot/services/message/admin/vip.py`](../bot/services/message/admin/vip.py) - Gestión VIP
- [`bot/services/message/admin/free.py`](../bot/services/message/admin/free.py) - Gestión Free
- [`bot/services/message/admin/content.py`](../bot/services/message/admin/content.py) - CRUD contenido
- [`bot/services/message/admin/interests.py`](../bot/services/message/admin/interests.py) - Gestión intereses
- [`bot/services/message/admin/users.py`](../bot/services/message/admin/users.py) - Gestión usuarios

**User providers:**
- [`bot/services/message/user_menu.py`](../bot/services/message/user_menu.py) - Menús VIP/Free

### Archivos de Handlers

**Admin handlers:**
- [`bot/handlers/admin/menu.py`](../bot/handlers/admin/menu.py) - Comando /admin
- [`bot/handlers/admin/menu_callbacks.py`](../bot/handlers/admin/menu_callbacks.py) - Callbacks admin:*

**VIP handlers:**
- [`bot/handlers/vip/menu.py`](../bot/handlers/vip/menu.py) - Menú VIP
- [`bot/handlers/vip/menu_callbacks.py`](../bot/handlers/vip/menu_callbacks.py) - Callbacks vip:*

**Free handlers:**
- [`bot/handlers/free/menu.py`](../bot/handlers/free/menu.py) - Menú Free
- [`bot/handlers/free/menu_callbacks.py`](../bot/handlers/free/menu_callbacks.py) - Callbacks free:*

### Archivos de Utilidades

- [`bot/utils/keyboards.py`](../bot/utils/keyboards.py) - Keyboard factory functions
- [`bot/utils/formatters.py`](../bot/utils/formatters.py) - HTML escape y formatters

### Middlewares

- [`bot/middlewares/role_detection.py`](../bot/middlewares/role_detection.py) - Role detection middleware
- [`bot/middlewares/database.py`](../bot/middlewares/database.py) - Database session injection
- [`bot/middlewares/admin_auth.py`](../bot/middlewares/admin_auth.py) - Admin authentication

---

## Conclusión

El sistema de menús de AdminPro implementa una arquitectura escalable, mantenible y consistente que:

1. **Personaliza la experiencia por rol:** Cada usuario recibe menús adaptados a su rol
2. **Mantiene voz consistente:** Lucien's voice integrada en todos los providers
3. **Usa patrones stateless:** Eficiente memoria, thread-safe, testable
4. **Proporciona navegación fluida:** Callback routing y keyboard factory consistentes
5. **Facilita extensiones:** Patrones claros para agregar nuevas opciones

**Para contribuir al sistema de menús:**

1. Seguir patrones establecidos (stateless providers, callback format)
2. Mantener voz de Lucien (ver [`docs/guia-estilo.md`](guia-estilo.md))
3. Escribir tests para nuevos providers y handlers
4. Actualizar esta documentación con cambios arquitectónicos

**Soporte:**

- Para dudas sobre voice: Ver [`docs/guia-estilo.md`](guia-estilo.md)
- Para detalles técnicos: Ver [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- Para API reference: Ver [`docs/API.md`](API.md)

---

*Documentación generada para Phase 11-02 (Documentation).*
*Última actualización: 2026-01-28*

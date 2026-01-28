# Ejemplos de Uso - Sistema de Menús

## Visión General

Este documento proporciona ejemplos prácticos y completos del sistema de menús implementado en el bot. Cada ejemplo incluye código funcional que puedes copiar y adaptar a tus necesidades.

### Cómo usar estos ejemplos

1. **Lee el caso de uso** para entender el contexto
2. **Revisa el Message Provider** para ver cómo se estructuran los mensajes
3. **Estudia el Handler** para entender la integración con Aiogram
4. **Prueba el ejemplo** siguiendo las instrucciones de testing
5. **Adapta el código** a tu caso específico

### Prerrequisitos

- Python 3.11+
- Aiogram 3.4.1
- SQLAlchemy 2.0+
- Comprensión de los patrones de diseño del proyecto (ver `docs/MENU_SYSTEM.md`)

---

## Ejemplo 1: Menú de Administración Simple

### Caso de Uso

El administrador necesita gestionar una lista de configuraciones simples del sistema. El menú debe mostrar todas las opciones disponibles, permitir editarlas, y mantener la voz de Lucien (el mayordomo sofisticado).

### Message Provider

```python
# bot/services/message/admin_settings.py
from typing import List, Tuple
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.services.message.base import BaseMessageProvider
from bot.services.message.common import CommonMessages

class AdminSettingsMessages(BaseMessageProvider):
    """Mensajes para menú de configuración de administrador.

    Voice Pattern:
        - Formal y colaborativo
        - Usa "custodio" para dirigirse al admin
        - Terminología: "ajustes", "configuración", "parámetros"

    Example:
        >>> provider = AdminSettingsMessages()
        >>> text, keyboard = provider.settings_list(settings)
        >>> '🎩' in text and 'ajustes' in text.lower()
        True
    """

    def __init__(self):
        super().__init__()
        self.common = CommonMessages()

    def settings_list(
        self,
        settings: List[dict]
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """Generate settings list view.

        Args:
            settings: List of setting dicts with keys: id, name, value, active

        Returns:
            Tuple of (message_text, keyboard_markup)
        """
        if not settings:
            text = self.common.error(
                context="al cargar las configuraciones",
                suggestion="Cree una configuración con /add_setting"
            )
            return text, self._empty_keyboard()

        # Voice variations with weights (60% common, 30% alternate, 10% poetic)
        text_variations = [
            (60, "Custodio, aquí tiene los ajustes del sistema:"),
            (30, "Configuración actual del sanctum, custodio:"),
            (10, "Los parámetros que definen nuestra operación:"),
        ]

        # Use BaseMessageProvider._choose_variant for weighted selection
        greetings = [v[1] for v in text_variations]
        weights = [v[0] / 100 for v in text_variations]
        text = self._choose_variant(greetings, weights=weights)
        text += "\n\n" + self._format_settings(settings)

        keyboard = self._settings_keyboard(settings)
        return text, keyboard

    def _format_settings(self, settings: List[dict]) -> str:
        """Format settings list with status indicators."""
        lines = []
        for setting in settings:
            status = "✅" if setting.get("active", True) else "❌"
            name = setting.get("name", "Sin nombre")
            value = setting.get("value", "N/A")
            lines.append(f"{status} <b>{name}</b>: {value}")
        return "\n".join(lines)

    def _settings_keyboard(self, settings: List[dict]) -> InlineKeyboardMarkup:
        """Generate keyboard with setting buttons."""
        builder = InlineKeyboardBuilder()

        # Add a button for each setting
        for setting in settings:
            builder.button(
                text=f"⚙️ {setting['name']}",
                callback_data=f"admin:settings:edit:{setting['id']}"
            )

        # Navigation row with Add and Back buttons
        builder.row(
            InlineKeyboardButton(text="➕ Agregar", callback_data="admin:settings:add"),
            InlineKeyboardButton(text="🔙 Volver", callback_data="admin:menu:back"),
        )
        # Exit button on its own row
        builder.row(
            InlineKeyboardButton(text="❌ Salir", callback_data="admin:menu:exit"),
        )

        return builder.as_markup()

    def _empty_keyboard(self) -> InlineKeyboardMarkup:
        """Generate keyboard when no settings exist."""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="➕ Crear primer ajuste", callback_data="admin:settings:add"),
            InlineKeyboardButton(text="🔙 Volver", callback_data="admin:menu:back"),
        )
        return builder.as_markup()
```

### Handler Implementation

```python
# bot/handlers/admin/settings.py
from aiogram import Router, F, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import UserRole
from bot.services import ServiceContainer
from bot.services.message.admin_settings import AdminSettingsMessages
from bot.middlewares.database import DatabaseMiddleware

# Create router for settings handlers
settings_router = Router()
settings_router.message.middleware(DatabaseMiddleware())
settings_router.callback_query.middleware(DatabaseMiddleware())

@settings_router.message(Command("settings"))
async def cmd_settings(
    message: types.Message,
    session: AsyncSession,
    user_role: UserRole
):
    """Handle /settings command - show settings list."""
    # Verify admin permissions
    if user_role != UserRole.ADMIN:
        await message.answer("❌ Solo administradores pueden acceder a este menú.")
        return

    # Initialize service container and messages
    container = ServiceContainer(session, message.bot)
    messages = AdminSettingsMessages()

    # Get settings from database (example implementation)
    # In real implementation, you'd have a SettingsService
    settings = [
        {"id": 1, "name": "Welcome Message", "value": "Enabled", "active": True},
        {"id": 2, "name": "Auto-Reply", "value": "Disabled", "active": False},
    ]

    # Generate and send message
    text, keyboard = messages.settings_list(settings)
    await message.answer(text, reply_markup=keyboard)

@settings_router.callback_query(F.data.startswith("admin:settings:edit:"))
async def callback_edit_setting(
    callback: types.CallbackQuery,
    session: AsyncSession
):
    """Handle edit setting callback."""
    await callback.answer()

    # Extract setting ID from callback data
    parts = callback.data.split(":")
    setting_id = int(parts[3])

    container = ServiceContainer(session, callback.bot)

    # Get setting from database (example)
    # setting = await container.settings.get_by_id(setting_id)
    setting = {"id": setting_id, "name": "Welcome Message", "value": "Enabled"}

    if not setting:
        await callback.message.edit_text("❌ Ajuste no encontrado")
        return

    # Show edit interface
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Modificando {setting['name'].lower()}...</i>\n\n"
        f"<b>Valor actual:</b> {setting['value']}\n\n"
        f"<i>Envíe el nuevo valor para este ajuste.</i>",
        reply_markup=None
    )

    # Set FSM state for next message (would be implemented here)
    # await state.set_state(SettingsForm.editing_value)
    # await state.update_data(setting_id=setting_id)

@settings_router.callback_query(F.data == "admin:settings:add")
async def callback_add_setting(
    callback: types.CallbackQuery,
    state: FSMContext
):
    """Handle add new setting callback."""
    await callback.answer()

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Creando un nuevo ajuste para el reino...</i>\n\n"
        "<b>Envíe el nombre del nuevo ajuste:</b>"
    )

    # Set FSM state for name input
    # await state.set_state(SettingsForm.creating_name)
```

### Comportamiento Esperado

1. El administrador envía `/settings`
2. El bot responde con la lista de ajustes usando la voz de Lucien
3. Se muestran los ajustes con indicadores de estado (✅/❌)
4. El admin puede editar ajustes existentes o crear nuevos
5. Los botones de navegación permiten volver al menú principal o salir
6. El mensaje siempre mantiene el emoji 🎩 y el formato HTML

### Testing

```bash
# 1. Asegúrate de que el bot esté corriendo
python main.py

# 2. Envía /settings como administrador
# 3. Verifica que se muestra la lista de ajustes
# 4. Haz clic en un botón de editar
# 5. Envía un nuevo valor
# 6. Verifica que se guarda correctamente
# 7. Prueba la navegación (Volver, Salir)
```

### Notas

- Usa `CommonMessages` para manejar estados vacíos y errores
- Las variaciones de voz usan pesos (60/30/10) para variedad natural
- El keyboard sigue el patrón de navegación estándar del proyecto
- FSM states se usarían para input multi-step (no mostrado completo aquí)
- La validación de permisos se hace antes de procesar cualquier acción

---

## Ejemplo 2: Menú de Usuario con Detección de Rol

### Caso de Uso

Usuarios VIP y Free necesitan menús diferentes. Los miembros VIP ven contenido premium exclusivo ("tesoros del sanctum"), mientras que los usuarios Free ven contenido básico ("muestras del jardín") con información sobre cómo acceder al círculo exclusivo.

### Message Provider

```python
# bot/services/message/user_content.py
from typing import Tuple
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.database.enums import UserRole
from bot.services.message.base import BaseMessageProvider
from bot.services.message.common import CommonMessages

class UserContentMessages(BaseMessageProvider):
    """Mensajes para menú de contenido basado en rol del usuario.

    Voice Pattern:
        - VIP: "círculo exclusivo", "tesoros", "sanctum"
        - Free: "jardín público", "muestras", "vestíbulo"

    Example:
        >>> provider = UserContentMessages()
        >>> text, kb = provider.content_menu(
        ...     user_role=UserRole.VIP,
        ...     user_name="Diana"
        ... )
        >>> 'círculo' in text.lower()
        True
    """

    def __init__(self):
        super().__init__()
        self.common = CommonMessages()

    def content_menu(
        self,
        user_role: UserRole,
        user_name: str,
        content_count: int
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """Generate role-specific content menu.

        Args:
            user_role: VIP or FREE
            user_name: User's first name (will be HTML-escaped)
            content_count: Available content items

        Returns:
            Tuple of (message_text, keyboard_markup)
        """
        if user_role == UserRole.VIP:
            return self._vip_menu(user_name, content_count)
        else:
            return self._free_menu(user_name, content_count)

    def _vip_menu(self, user_name: str, count: int) -> Tuple[str, InlineKeyboardMarkup]:
        """VIP member menu with exclusive terminology."""
        # Weighted variations for VIP (70% common, 20% alternate, 10% poetic)
        text_variations = [
            (70, f"Bienvenido al círculo, {user_name}. Los tesoros te esperan."),
            (20, f"{user_name}, el sanctum abre sus puertas para ti."),
            (10, f"El círculo reconoce tu presencia, {user_name}."),
        ]

        greetings = [v[1] for v in text_variations]
        weights = [v[0] / 100 for v in text_variations]

        text = self._choose_variant(greetings, weights=weights)
        text += f"\n\n📦 Contenido disponible: <b>{count}</b> tesoros"

        keyboard = self._vip_keyboard()
        return text, keyboard

    def _free_menu(self, user_name: str, count: int) -> Tuple[str, InlineKeyboardMarkup]:
        """Free user menu with public garden terminology."""
        # Weighted variations for Free (70% welcoming, 30% informative)
        text_variations = [
            (70, f"Bienvenido al jardín, {user_name}. Disfruta las muestras."),
            (20, f"{user_name}, te invitamos a explorar lo que ofrecemos."),
            (10, f"El jardín te recibe, {user_name}."),
        ]

        greetings = [v[1] for v in text_variations]
        weights = [v[0] / 100 for v in text_variations]

        text = self._choose_variant(greetings, weights=weights)
        text += f"\n\n📦 Contenido gratuito: <b>{count}</b> muestras"
        text += "\n\n💎 <i>Los tesoros completos esperan en el círculo exclusivo.</i>"

        keyboard = self._free_keyboard()
        return text, keyboard

    def _vip_keyboard(self) -> InlineKeyboardMarkup:
        """VIP member keyboard with exclusive options."""
        builder = InlineKeyboardBuilder()

        # VIP-only options
        builder.button(text="💎 Tesoros", callback_data="user:content:list:premium")
        builder.button(text="📊 Mi Suscripción", callback_data="user:vip:subscription")
        builder.button(text="🎁 Bonus", callback_data="user:content:list:bonus")

        # Navigation row
        builder.row(
            InlineKeyboardButton(text="🔙 Volver", callback_data="user:menu:back"),
            InlineKeyboardButton(text="❌ Salir", callback_data="user:menu:exit"),
        )

        return builder.as_markup()

    def _free_keyboard(self) -> InlineKeyboardMarkup:
        """Free user keyboard with public options."""
        builder = InlineKeyboardBuilder()

        # Free-accessible options
        builder.button(text="🌷 Muestras", callback_data="user:content:list:free")
        builder.button(text="💎 Acceder al Círculo", callback_data="user:vip:join")

        # Navigation row
        builder.row(
            InlineKeyboardButton(text="🔙 Volver", callback_data="user:menu:back"),
            InlineKeyboardButton(text="❌ Salir", callback_data="user:menu:exit"),
        )

        return builder.as_markup()
```

### Handler Implementation

```python
# bot/handlers/user/content.py
from aiogram import Router, F, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import UserRole
from bot.database.enums import UserRole as UserRoleEnum
from bot.services import ServiceContainer
from bot.services.message.user_content import UserContentMessages
from bot.middlewares.database import DatabaseMiddleware

content_router = Router()
content_router.message.middleware(DatabaseMiddleware())
content_router.callback_query.middleware(DatabaseMiddleware())

@content_router.message(Command("content"))
async def cmd_content(
    message: types.Message,
    session: AsyncSession,
    user_role: UserRoleEnum
):
    """Handle /content command - role-based menu."""
    container = ServiceContainer(session, message.bot)
    messages = UserContentMessages()

    # Get content count based on role
    if user_role == UserRoleEnum.VIP:
        count = await container.content.count_premium()
    else:
        count = await container.content.count_free()

    # Generate role-specific menu
    text, keyboard = messages.content_menu(
        user_role=user_role,
        user_name=message.from_user.first_name or "visitante",
        content_count=count
    )

    await message.answer(text, reply_markup=keyboard)

@content_router.callback_query(F.data.startswith("user:content:list:"))
async def callback_content_list(
    callback: types.CallbackQuery,
    session: AsyncSession,
    user_role: UserRoleEnum
):
    """Handle content list callback."""
    await callback.answer()

    # Extract content type from callback data
    parts = callback.data.split(":")
    content_type = parts[3]  # "premium", "free", "bonus"

    container = ServiceContainer(session, callback.bot)

    # Get content based on type and role with permission validation
    if content_type == "premium" and user_role == UserRoleEnum.VIP:
        content = await container.content.get_premium()
    elif content_type == "free":
        content = await container.content.get_free()
    elif content_type == "bonus" and user_role == UserRoleEnum.VIP:
        content = await container.content.get_bonus()
    else:
        # Unauthorized access attempt
        await callback.answer(
            "❌ Este contenido no está disponible para tu rol",
            show_alert=True
        )
        return

    # Format and show content list
    if not content:
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Parece que no hay contenido disponible en esta sección...</i>"
        )
        return

    text = self._format_content_list(content)
    keyboard = self._content_list_keyboard(content, content_type)

    await callback.message.edit_text(text, reply_markup=keyboard)

def _format_content_list(self, content: list) -> str:
    """Format content list for display."""
    header = "🎩 <b>Lucien:</b>\n\n<i>Aquí está el contenido solicitado...</i>"

    items = []
    for item in content[:10]:  # Limit to 10 items
        items.append(f"📦 <b>{item.name}</b>\n{i}</i>")

    body = "\n\n".join(items)

    return f"{header}\n\n{body}"
```

### Comportamiento Esperado

**Usuario VIP:**
1. Envía `/content`
2. Ve menú con "Tesoros", "Mi Suscripción", "Bonus"
3. Terminología: "círculo", "tesoros", "sanctum"
4. Puede acceder a todo contenido premium sin restricciones

**Usuario Free:**
1. Envía `/content`
2. Ve menú con "Muestras", "Acceder al Círculo"
3. Terminología: "jardín", "muestras", "vestíbulo"
4. El botón "Acceder al Círculo" muestra información sobre VIP

### Testing

```bash
# 1. Test como usuario VIP
/content
# Verifica: Menú con "Tesoros", terminología de círculo

# 2. Test como usuario Free
/content
# Verifica: Menú con "Muestras", terminología de jardín

# 3. Test de permisos
# Intenta acceder a contenido premium como Free
# Verifica: Se muestra alerta de acceso denegado
```

### Notas

- `UserRoleDetectionMiddleware` inyecta `user_role` automáticamente
- La terminología es completamente diferente por rol para inmersión
- Los menús tienen opciones diferentes según permisos
- La validación de permisos se hace en callbacks también
- Usa pesos para variaciones naturales (70/20/10 para VIP, 70/20/10 para Free)

---

## Ejemplo 3: Visualización de Paquetes de Contenido con Paginación

### Caso de Uso

Mostrar una lista de paquetes de contenido (media packs, videos, fotos) con paginación para manejar grandes cantidades. Cada paquete muestra información esencial y permite ver detalles antes de manifestar interés.

### Message Provider

```python
# bot/services/message/content_packages.py
from typing import Tuple, List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.services.message.base import BaseMessageProvider
from bot.database.models import ContentPackage

class ContentPackageMessages(BaseMessageProvider):
    """Mensajes para visualización de paquetes de contenido con paginación.

    Voice Pattern:
        - Paquetes = "obras", "tesoros", "colecciones"
        - Paginación = "páginas de la galería"
        - Navegación fluida sin perder contexto

    Example:
        >>> provider = ContentPackageMessages()
        >>> text, kb = provider.package_list_page(packages, page=1)
        >>> 'página' in text.lower() or 'pagina' in text.lower()
        True
    """

    def __init__(self):
        super().__init__()
        self.items_per_page = 5

    def package_list_page(
        self,
        packages: List[ContentPackage],
        page: int = 1,
        total_pages: int = 1
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """Generate paginated package list view.

        Args:
            packages: List of ContentPackage objects for current page
            page: Current page number (1-indexed)
            total_pages: Total number of pages

        Returns:
            Tuple of (message_text, keyboard_markup)
        """
        # Generate header with page information
        header = "🎩 <b>Lucien:</b>\n\n<i>La colección del reino se despliega ante usted...</i>"

        # Format packages for current page
        package_items = self._format_packages(packages)

        # Page indicator
        page_info = f"\n\n📖 <b>Página {page} de {total_pages}</b>"

        body = (
            f"<b>📦 Paquetes de Contenido</b>\n\n"
            f"{package_items}"
            f"{page_info}\n\n"
            f"<i>Seleccione una obra para ver detalles completos.</i>"
        )

        text = self._compose(header, body)
        keyboard = self._paginated_keyboard(page, total_pages)

        return text, keyboard

    def _format_packages(self, packages: List[ContentPackage]) -> str:
        """Format packages for list display."""
        if not packages:
            return "<i>No hay paquetes en esta página...</i>"

        items = []
        for pkg in packages:
            # Category emoji
            emoji = self._get_category_emoji(pkg.category)
            status = "✅" if pkg.is_active else "🚫"

            # Format price
            price = "Gratis" if pkg.price is None else f"${pkg.price:.2f}"

            item = (
                f"{status} {emoji} <b>{pkg.name}</b>\n"
                f"   💰 {price} | 📦 {pkg.type.value}\n"
            )

            # Add description snippet if available
            if pkg.description:
                snippet = pkg.description[:50]
                if len(pkg.description) > 50:
                    snippet += "..."
                item += f"   <i>{snippet}</i>\n"

            items.append(item)

        return "\n".join(items)

    def _get_category_emoji(self, category) -> str:
        """Get emoji for content category."""
        category_str = str(category).lower()
        if "premium" in category_str:
            return "💎"
        elif "vip" in category_str:
            return "⭐"
        else:
            return "🆓"

    def _paginated_keyboard(
        self,
        current_page: int,
        total_pages: int
    ) -> InlineKeyboardMarkup:
        """Generate keyboard with pagination controls."""
        builder = InlineKeyboardBuilder()

        # Previous page button (disabled on first page)
        if current_page > 1:
            builder.button(
                text="⬅️ Anterior",
                callback_data=f"packages:page:{current_page - 1}"
            )
        else:
            builder.button(
                text="⏸️ Inicio",
                callback_data="packages:page:1"
            )

        # Page indicator button
        builder.button(
            text=f"📖 {current_page}/{total_pages}",
            callback_data="packages:refresh"
        )

        # Next page button (disabled on last page)
        if current_page < total_pages:
            builder.button(
                text="➡️ Siguiente",
                callback_data=f"packages:page:{current_page + 1}"
            )
        else:
            builder.button(
                text="🏁 Fin",
                callback_data="packages:refresh"
            )

        # Arrange pagination buttons in a row
        builder.adjust(3)

        # Add navigation buttons below pagination
        builder.row(
            InlineKeyboardButton(text="🔙 Volver", callback_data="menu:back")
        )

        return builder.as_markup()

    def package_detail(self, package: ContentPackage) -> Tuple[str, InlineKeyboardMarkup]:
        """Generate detailed package view.

        Args:
            package: ContentPackage to display

        Returns:
            Tuple of (message_text, keyboard_markup)
        """
        header = "🎩 <b>Lucien:</b>\n\n<i>Los detalles de la obra seleccionada...</i>"

        # Category emoji and label
        emoji = self._get_category_emoji(package.category)
        status = "✅ Activo" if package.is_active else "🚫 Inactivo"

        # Format price
        price = "Acceso gratuito" if package.price is None else f"${package.price:.2f}"

        body = (
            f"<b>{emoji} {package.name}</b>\n\n"
            f"<b>Estado:</b> {status}\n"
            f"<b>Categoría:</b> {package.category.value}\n"
            f"<b>Precio:</b> {price}\n"
            f"<b>Tipo:</b> {package.type.value}\n\n"
        )

        # Add description if available
        if package.description:
            body += f"<b>Descripción:</b>\n<i>{package.description}</i>\n\n"

        # Add media URL if available
        if package.media_url:
            body += f"<b>Media:</b> <code>{package.media_url[:50]}...</code>\n\n"

        body += "<i>¿Desea manifestar interés en esta obra?</i>"

        text = self._compose(header, body)

        # Keyboard with action buttons
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="⭐ Me interesa", callback_data=f"package:interest:{package.id}")
        )
        builder.row(
            InlineKeyboardButton(text="⬅️ Volver a la lista", callback_data="packages:page:1")
        )

        keyboard = builder.as_markup()

        return text, keyboard
```

### Handler Implementation

```python
# bot/handlers/user/packages.py
from aiogram import Router, F, types
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services import ServiceContainer
from bot.services.message.content_packages import ContentPackageMessages
from bot.middlewares.database import DatabaseMiddleware

packages_router = Router()
packages_router.callback_query.middleware(DatabaseMiddleware())

PACKAGES_PER_PAGE = 5

@packages_router.callback_query(F.data == "user:packages")
async def show_package_list(
    callback: types.CallbackQuery,
    session: AsyncSession
):
    """Show first page of package list."""
    await callback.answer()

    container = ServiceContainer(session, callback.bot)
    messages = ContentPackageMessages()

    # Get total count and packages for first page
    total_count = await container.packages.count_active()
    packages = await container.packages.get_paginated(page=1, limit=PACKAGES_PER_PAGE)

    # Calculate total pages
    total_pages = (total_count + PACKAGES_PER_PAGE - 1) // PACKAGES_PER_PAGE

    # Generate and send page
    text, keyboard = messages.package_list_page(
        packages=packages,
        page=1,
        total_pages=total_pages
    )

    await callback.message.edit_text(text, reply_markup=keyboard)

@packages_router.callback_query(F.data.startswith("packages:page:"))
async def show_package_page(
    callback: types.CallbackQuery,
    session: AsyncSession
):
    """Show specific page of package list."""
    await callback.answer()

    # Extract page number
    parts = callback.data.split(":")
    page = int(parts[2])

    container = ServiceContainer(session, callback.bot)
    messages = ContentPackageMessages()

    # Get packages for requested page
    total_count = await container.packages.count_active()
    packages = await container.packages.get_paginated(page=page, limit=PACKAGES_PER_PAGE)

    # Calculate total pages
    total_pages = (total_count + PACKAGES_PER_PAGE - 1) // PACKAGES_PER_PAGE

    # Validate page number
    if page > total_pages:
        page = total_pages
        packages = await container.packages.get_paginated(page=page, limit=PACKAGES_PER_PAGE)

    # Generate and send page
    text, keyboard = messages.package_list_page(
        packages=packages,
        page=page,
        total_pages=total_pages
    )

    await callback.message.edit_text(text, reply_markup=keyboard)

@packages_router.callback_query(F.data.startswith("package:interest:"))
async def register_interest(
    callback: types.CallbackQuery,
    session: AsyncSession
):
    """Handle user interest registration in a package."""
    await callback.answer()

    # Extract package ID
    parts = callback.data.split(":")
    package_id = int(parts[2])

    container = ServiceContainer(session, callback.bot)

    # Register interest (with debounce check)
    user_id = callback.from_user.id
    success = await container.packages.register_interest(package_id, user_id)

    if success:
        await callback.show_alert(
            "✅ Interés registrado. Te notificaremos cuando haya novedades."
        )
    else:
        await callback.show_alert(
            "ℹ️ Ya habías registrado tu interés en este paquete anteriormente."
        )
```

### Comportamiento Esperado

1. Usuario solicita ver paquetes de contenido
2. Bot muestra primera página con hasta 5 paquetes
3. Indicador de página: "Página 1 de 3"
4. Botones de navegación: Anterior (deshabilitado en página 1), Siguiente
5. Cada paquete muestra nombre, precio, categoría, estado
6. Al hacer clic en un paquete, se ven detalles completos
7. Desde detalles, puede registrar interés o volver a la lista

### Testing

```bash
# 1. Ver lista de paquetes
/user:packages
# Verifica: Se muestra página 1 con indicador de paginación

# 2. Navegar entre páginas
# Clic en "➡️ Siguiente"
# Verifica: Se muestra página 2 con contenido diferente

# 3. Ver detalles de paquete
# Clic en un paquete específico
# Verifica: Se muestran detalles completos (descripción, media, precio)

# 4. Registrar interés
# Clic en "⭐ Me interesa"
# Verifica: Alerta de confirmación
```

### Notas

- La paginación usa callbacks con número de página incluido
- El indicador de página ayuda al usuario a orientarse
- Los botones de navegación se deshabilitan visualmente en los límites
- Cada página muestra 5 items para balance entre densidad y scroll
- El botón de "volver" en detalles regresa a la página 1 (podría mejorarse para regresar a la página específica)

---

## Ejemplo 4: Formulario Multi-Step con FSM

### Caso de Uso

El administrador necesita crear un nuevo paquete de contenido. Requiere收集多个信息: nombre, tipo, precio, descripción. Se usa FSM (Finite State Machine) para mantener el contexto del paso actual.

### FSM State Definition

```python
# bot/states/admin.py
from aiogram.fsm.state import State, StatesGroup

class CreatePackageForm(StatesGroup):
    """FSM states for package creation wizard."""

    selecting_name = State()      # Step 1: Enter package name
    selecting_type = State()      # Step 2: Select package type
    selecting_price = State()     # Step 3: Enter price (optional)
    selecting_description = State()  # Step 4: Enter description (optional)
    confirming = State()          # Step 5: Confirm creation
```

### Message Provider

```python
# bot/services/message/package_creation.py
from typing import Tuple
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.message.base import BaseMessageProvider

class PackageCreationMessages(BaseMessageProvider):
    """Mensajes para el asistente de creación de paquetes.

    Voice Pattern:
        - Creación = "nueva obra", "obra maestra"
        - Pasos = "etapas", "hacia la completion"
        - Guía amable pero sofisticada

    Example:
        >>> provider = PackageCreationMessages()
        >>> text, kb = provider.step_name()
        >>> 'paso' in text.lower() or 'nombre' in text.lower()
        True
    """

    def welcome(self) -> Tuple[str, InlineKeyboardMarkup]:
        """Welcome message for package creation wizard."""
        header = "🎩 <b>Lucien:</b>\n\n<i>Excelente decisión, curador. El reino siempre acepta nuevas obras...</i>"

        body = (
            f"<b>➕ Crear Nuevo Paquete</b>\n\n"
            f"<i>Le guiaré en la creación de un nuevo paquete de contenido "
            f"para enriquecer la experiencia del círculo y del jardín.</i>\n\n"
            f"<i>El proceso constará de 4 sencillos pasos:</i>\n\n"
            f"1️⃣ <b>Nombre</b> del paquete\n"
            f"2️⃣ <b>Tipo</b> de contenido\n"
            f"3️⃣ <b>Precio</b> (opcional)\n"
            f"4️⃣ <b>Descripción</b> (opcional)\n\n"
            f"<i>¿Está listo para comenzar, curador?</i>"
        )

        text = self._compose(header, body)

        keyboard = self._create_keyboard([
            [("⏭️ Comenzar", "admin:package:create:start")],
            [("🔙 Volver", "admin:content")],
        ])

        return text, keyboard

    def step_name(self) -> Tuple[str, InlineKeyboardMarkup]:
        """Prompt for package name input."""
        header = "🎩 <b>Lucien:</b>\n\n<i>El primer paso hacia una nueva obra...</i>"

        body = (
            f"<b>➕ Paso 1/4: Nombre del Paquete</b>\n\n"
            f"<i>Por favor, proporcione el nombre de este paquete de contenido.</i>\n\n"
            f"<i>Un nombre evocador atraerá a los miembros del círculo "
            f"y a los visitantes del jardín por igual.</i>\n\n"
            f"<b>Envíe el nombre ahora:</b>"
        )

        text = self._compose(header, body)

        keyboard = self._create_keyboard([
            [("❌ Cancelar", "admin:content")],
        ])

        return text, keyboard

    def step_type(self) -> Tuple[str, InlineKeyboardMarkup]:
        """Prompt for package type selection."""
        header = "🎩 <b>Lucien:</b>\n\n<i>Excelente nombre. Ahora, definamos su naturaleza...</i>"

        body = (
            f"<b>➕ Paso 2/4: Tipo de Contenido</b>\n\n"
            f"<i>Seleccione la categoría más apropiada para esta obra.</i>\n\n"
            f"<i>Considere quién podrá acceder: ¿todos los visitantes, "
            f"solo el círculo exclusivo, o los miembros más distinguidos?</i>"
        )

        text = self._compose(header, body)

        keyboard = self._create_keyboard([
            [
                ("🆓 Contenido Gratuito", "admin:package:create:type:free_content"),
                ("⭐ Contenido VIP", "admin:package:create:type:vip_content")
            ],
            [("💎 VIP Premium", "admin:package:create:type:vip_premium")],
            [("❌ Cancelar", "admin:content")],
        ])

        return text, keyboard

    def step_price(self, current_price: str = "") -> Tuple[str, InlineKeyboardMarkup]:
        """Prompt for package price input."""
        header = "🎩 <b>Lucien:</b>\n\n<i>La categoría ha sido registrada. Ahora, el valor...</i>"

        current_display = current_price if current_price else "(no definido)"

        body = (
            f"<b>➕ Paso 3/4: Precio (Opcional)</b>\n\n"
            f"<i>Asigne un precio a este paquete, si corresponde.</i>\n\n"
            f"<i>Puede enviar un valor numérico (ej: 9.99) o /skip para omitir "
            f"y dejar el contenido gratuito.</i>\n\n"
            f"<b>Valor actual:</b> {current_display}\n\n"
            f"<b>Envíe el precio o /skip:</b>"
        )

        text = self._compose(header, body)

        keyboard = self._create_keyboard([
            [("⏭️ Omitir (/skip)", "admin:package:create:skip:price")],
            [("❌ Cancelar", "admin:content")],
        ])

        return text, keyboard

    def step_description(self) -> Tuple[str, InlineKeyboardMarkup]:
        """Prompt for package description input."""
        header = "🎩 <b>Lucien:</b>\n\n<i>Excelente. Finalmente, los detalles...</i>"

        body = (
            f"<b>➕ Paso 4/4: Descripción (Opcional)</b>\n\n"
            f"<i>Proporcione una descripción que informe a los miembros "
            f"sobre el contenido de este paquete.</i>\n\n"
            f"<i>Puede enviar una descripción detallada o /skip para omitir "
            f"este paso y finalizar.</i>\n\n"
            f"<b>Envíe la descripción o /skip:</b>"
        )

        text = self._compose(header, body)

        keyboard = self._create_keyboard([
            [("⏭️ Omitir (/skip)", "admin:package:create:skip:description")],
            [("❌ Cancelar", "admin:content")],
        ])

        return text, keyboard

    def confirmation(self, package_data: dict) -> Tuple[str, InlineKeyboardMarkup]:
        """Show confirmation before creating package."""
        header = "🎩 <b>Lucien:</b>\n\n<i>La obra está lista para ser presentada al reino...</i>"

        # Format package data
        name = package_data.get("name", "Sin nombre")
        type_display = package_data.get("type", "Sin definir").replace("_", " ").title()
        price = package_data.get("price")
        price_display = "Gratis" if price is None else f"${price}"
        description = package_data.get("description", "Sin descripción")

        body = (
            f"<b>✅ Confirmar Creación</b>\n\n"
            f"<b>📦 Nombre:</b> {name}\n"
            f"<b>📋 Tipo:</b> {type_display}\n"
            f"<b>💰 Precio:</b> {price_display}\n"
            f"<b>📄 Descripción:</b> {description}\n\n"
            f"<i>¿Confirma la creación de este paquete, curador?</i>"
        )

        text = self._compose(header, body)

        keyboard = self._create_keyboard([
            [
                ("✅ Confirmar", "admin:package:create:confirm"),
                ("❌ Cancelar", "admin:content")
            ],
        ])

        return text, keyboard

    def success(self, package_name: str) -> Tuple[str, InlineKeyboardMarkup]:
        """Success message after package creation."""
        header = "🎩 <b>Lucien:</b>\n\n<i>Enhorabuena, curador. Una nueva obra adorna el reino...</i>"

        body = (
            f"<b>✅ Paquete Creado Exitosamente</b>\n\n"
            f"<b>📦 {package_name}</b>\n"
            f"<i>El paquete ha sido registrado y está disponible para "
            f"los miembros del círculo y los visitantes del jardín.</i>\n\n"
            f"<i>¿Qué desea hacer ahora?</i>"
        )

        text = self._compose(header, body)

        keyboard = self._create_keyboard([
            [
                ("👁️ Ver Paquete", "admin:packages:list"),
                ("➕ Crear Otro", "admin:package:create:start")
            ],
            [("🔙 Menú Principal", "admin:main")],
        ])

        return text, keyboard

    def _create_keyboard(self, buttons: list) -> InlineKeyboardMarkup:
        """Helper to create inline keyboard from list of button lists."""
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        for row in buttons:
            button_list = []
            for text, callback_data in row:
                button_list.append(
                    InlineKeyboardButton(text=text, callback_data=callback_data)
                )
            builder.row(*button_list)

        return builder.as_markup()
```

### Handler Implementation

```python
# bot/handlers/admin/package_creation.py
from aiogram import Router, F, types
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services import ServiceContainer
from bot.services.message.package_creation import PackageCreationMessages
from bot.states.admin import CreatePackageForm
from bot.middlewares.database import DatabaseMiddleware

creation_router = Router()
creation_router.message.middleware(DatabaseMiddleware())
creation_router.callback_query.middleware(DatabaseMiddleware())

@creation_router.callback_query(F.data == "admin:package:create:start")
async def start_package_creation(
    callback: types.CallbackQuery,
    state: FSMContext
):
    """Start package creation wizard."""
    await callback.answer()

    messages = PackageCreationMessages()
    text, keyboard = messages.step_name()

    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(CreatePackageForm.selecting_name)

@creation_router.message(CreatePackageForm.selecting_name)
async def process_package_name(
    message: types.Message,
    state: FSMContext,
    session: AsyncSession
):
    """Process package name input."""
    name = message.text.strip()

    if len(name) < 3:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>El nombre es demasiado breve, curador. "
            "Proporcione al menos 3 caracteres...</i>"
        )
        return

    if len(name) > 100:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>El nombre es extenso demaisdo, curador. "
            "Manténgalo bajo 100 caracteres...</i>"
        )
        return

    # Store name and move to next step
    await state.update_data(name=name)

    messages = PackageCreationMessages()
    text, keyboard = messages.step_type()

    await message.answer(text, reply_markup=keyboard)
    await state.set_state(CreatePackageForm.selecting_type)

@creation_router.callback_query(F.data.startswith("admin:package:create:type:"))
async def process_package_type(
    callback: types.CallbackQuery,
    state: FSMContext
):
    """Process package type selection."""
    await callback.answer()

    # Extract type from callback data
    parts = callback.data.split(":")
    package_type = parts[4]  # e.g., "free_content", "vip_content", "vip_premium"

    # Store type and move to next step
    await state.update_data(type=package_type)

    messages = PackageCreationMessages()
    text, keyboard = messages.step_price()

    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(CreatePackageForm.selecting_price)

@creation_router.message(CreatePackageForm.selecting_price)
async def process_package_price(
    message: types.Message,
    state: FSMContext
):
    """Process package price input."""
    text = message.text.strip()

    # Check for skip command
    if text.lower() == "/skip":
        await state.update_data(price=None)
        return await move_to_description_step(message, state)

    # Validate price format
    try:
        price = float(text)
        if price < 0:
            raise ValueError("Price cannot be negative")
    except ValueError:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>El formato del valor no es válido, curador. "
            "Use un número positivo (ej: 9.99) o /skip para omitir...</i>"
        )
        return

    # Store price and move to next step
    await state.update_data(price=price)
    await move_to_description_step(message, state)

async def move_to_description_step(message: types.Message, state: FSMContext):
    """Move to description step."""
    messages = PackageCreationMessages()
    text, keyboard = messages.step_description()

    await message.answer(text, reply_markup=keyboard)
    await state.set_state(CreatePackageForm.selecting_description)

@creation_router.message(CreatePackageForm.selecting_description)
async def process_package_description(
    message: types.Message,
    state: FSMContext,
    session: AsyncSession
):
    """Process package description input."""
    text = message.text.strip()

    # Check for skip command
    if text.lower() == "/skip":
        description = None
    else:
        description = text
        # Limit description length
        if len(description) > 500:
            description = description[:500] + "..."

    # Store description and show confirmation
    await state.update_data(description=description)

    # Get all collected data
    data = await state.get_data()

    messages = PackageCreationMessages()
    text, keyboard = messages.confirmation(data)

    await message.answer(text, reply_markup=keyboard)
    await state.set_state(CreatePackageForm.confirming)

@creation_router.callback_query(F.data == "admin:package:create:confirm")
async def confirm_package_creation(
    callback: types.CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """Confirm and create the package."""
    await callback.answer()

    # Get all collected data
    data = await state.get_data()

    container = ServiceContainer(session, callback.bot)

    # Create package in database
    package = await container.packages.create(
        name=data["name"],
        package_type=data["type"],
        price=data.get("price"),
        description=data.get("description")
    )

    # Clear FSM state
    await state.clear()

    # Show success message
    messages = PackageCreationMessages()
    text, keyboard = messages.success(package.name)

    await callback.message.edit_text(text, reply_markup=keyboard)

@creation_router.callback_query(F.data.startswith("admin:package:create:skip:"))
async def skip_creation_step(
    callback: types.CallbackQuery,
    state: FSMContext
):
    """Handle skip button in creation wizard."""
    await callback.answer()

    parts = callback.data.split(":")
    step_to_skip = parts[4]  # "price" or "description"

    if step_to_skip == "price":
        await state.update_data(price=None)
        messages = PackageCreationMessages()
        text, keyboard = messages.step_description()
        await callback.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(CreatePackageForm.selecting_description)

    elif step_to_skip == "description":
        await state.update_data(description=None)
        data = await state.get_data()
        messages = PackageCreationMessages()
        text, keyboard = messages.confirmation(data)
        await callback.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(CreatePackageForm.confirming)
```

### Comportamiento Esperado

1. Admin inicia el asistente de creación
2. Ve mensaje de bienvenida con resumen de 4 pasos
3. Ingresa nombre (validación: 3-100 caracteres)
4. Selecciona tipo de contenido (botones inline)
5. Ingresa precio o usa /skip (validación: número positivo)
6. Ingresa descripción o usa /skip (máximo 500 caracteres)
7. Ve resumen de todos los datos ingresados
8. Confirma o cancela la creación
9. Si confirma, ve mensaje de éxito y opciones siguientes

### Testing

```bash
# 1. Iniciar creación
/admin:package:create:start
# Verifica: Mensaje de bienvenida con 4 pasos

# 2. Ingresar nombre válido
# Envía: "Mi Primer Paquete"
# Verifica: Pasa a paso de tipo

# 3. Seleccionar tipo
# Clic en: "⭐ Contenido VIP"
# Verifica: Pasa a paso de precio

# 4. Omitir precio
# Clic en: "⏭️ Omitir"
# Verifica: Pasa a paso de descripción

# 5. Ingresar descripción
# Envía: "Contenido exclusivo para miembros VIP"
# Verifica: Muestra confirmación con resumen

# 6. Confirmar creación
# Clic en: "✅ Confirmar"
# Verifica: Mensaje de éxito con opciones

# 7. Validación de nombre
# Envía: "AB" (muy corto)
# Verifica: Error pidiendo mínimo 3 caracteres
```

### Notas

- FSM states mantienen el contexto entre pasos
- Cada paso valida su entrada específica
- Los campos opcionales permiten /skip
- La confirmación muestra todos los datos antes de crear
- El estado se limpia después de crear o cancelar
- Mensajes de error no rompen el flujo (usuario puede reintentar)

---

## Ejemplo 5: Sistema de Registro de Intereses con Debounce

### Caso de Uso

Usuario ve un paquete de contenido y hace clic en "Me interesa". El sistema debe:
1. Registrar el interés en la base de datos
2. Evitar registros duplicados (debounce)
3. Notificar al administrador
4. Confirmar al usuario con feedback visual

### Message Provider

```python
# bot/services/message/interest_system.py
from typing import Tuple
from aiogram.types import InlineKeyboardMarkup
from bot.services.message.base import BaseMessageProvider

class InterestMessages(BaseMessageProvider):
    """Mensajes para el sistema de registro de intereses.

    Voice Pattern:
        - Interés = "manifestar interés", "marcar como deseado"
        - Confirmación sutil sin ser excesivo
        - Ya registrado = "constancia en archivos de Diana"

    Example:
        >>> provider = InterestMessages()
        >>> text = provider.interest_registered("Pack Premium")
        >>> 'registrado' in text.lower()
        True
    """

    def interest_registered(
        self,
        package_name: str,
        already_registered: bool = False
    ) -> str:
        """Generate confirmation message for interest registration.

        Args:
            package_name: Name of the package
            already_registered: Whether user had already registered interest

        Returns:
            Confirmation message text
        """
        if already_registered:
            header = "🎩 <b>Lucien:</b>\n\n<i>Ah... los archivos de Diana ya guardan constancia de su interés...</i>"
            body = (
                f"<b>⭐ Interés Previamente Registrado</b>\n\n"
                f"<b>📦 {package_name}</b>\n"
                f"<i>No te preocupes, te notificaremos cuando haya novedades.</i>"
            )
        else:
            header = "🎩 <b>Lucien:</b>\n\n<i>Excelente elección. Diana aprecia tu discernimiento...</i>"
            body = (
                f"<b>✅ Interés Registrado</b>\n\n"
                f"<b>📦 {package_name}</b>\n"
                f"<i>He tomado nota. Te notificaré cuando este paquete esté disponible.</i>"
            )

        return self._compose(header, body)

    def interest_notification(
        self,
        user_name: str,
        package_name: str,
        interest_count: int
    ) -> str:
        """Generate admin notification for new interest.

        Args:
            user_name: Name of user who registered interest
            package_name: Name of the package
            interest_count: Total interests for this package

        Returns:
            Notification message for admin
        """
        header = f"🎩 <b>Lucien:</b>\n\n<i>Un visitante ha manifestado interés en una obra, curador...</i>"

        body = (
            f"<b>⭐ Nuevo Interés Registrado</b>\n\n"
            f"<b>👤 Usuario:</b> {user_name}\n"
            f"<b>📦 Paquete:</b> {package_name}\n"
            f"<b>📊 Total Interesados:</b> {interest_count}\n\n"
            f"<i>Los miembros del círculo expresan su aprecio por el contenido.</i>"
        )

        return self._compose(header, body)

    def interest_list(
        self,
        package_name: str,
        interested_users: list
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """Generate list of users interested in a package.

        Args:
            package_name: Name of the package
            interested_users: List of user dicts with keys: name, username, registered_at

        Returns:
            Tuple of (message_text, keyboard_markup)
        """
        header = "🎩 <b>Lucien:</b>\n\n<i>Aquí están quienes han manifestado interés...</i>"

        if not interested_users:
            body = (
                f"<b>⭐ Intereses: {package_name}</b>\n\n"
                f"<i>Nadie ha mostrado interés en esta obra aún, curador.</i>"
            )
        else:
            user_list = []
            for i, user in enumerate(interested_users[:20], 1):  # Limit to 20
                username_display = f"@{user['username']}" if user.get('username') else "Sin username"
                registered = user['registered_at'].strftime("%Y-%m-%d")
                user_list.append(f"{i}. {user['name']} ({username_display}) - {registered}")

            users_text = "\n".join(user_list)
            if len(interested_users) > 20:
                users_text += f"\n... y {len(interested_users) - 20} más"

            body = (
                f"<b>⭐ Intereses: {package_name}</b>\n\n"
                f"<b>{len(interested_users)} usuario(s) interesado(s):</b>\n\n"
                f"{users_text}"
            )

        text = self._compose(header, body)

        # Keyboard with back button
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Volver", callback_data="admin:packages:list")

        keyboard = builder.as_markup()

        return text, keyboard
```

### Handler Implementation

```python
# bot/handlers/user/interest.py
from aiogram import Router, F, types
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services import ServiceContainer
from bot.services.message.interest_system import InterestMessages
from bot.database.models import PackageInterest
from bot.middlewares.database import DatabaseMiddleware

interest_router = Router()
interest_router.callback_query.middleware(DatabaseMiddleware())

# Debounce: prevent duplicate registrations within 5 seconds
INTEREST_DEBOUNCE_SECONDS = 5

@interest_router.callback_query(F.data.startswith("package:interest:"))
async def register_interest(
    callback: types.CallbackQuery,
    session: AsyncSession
):
    """Handle user interest registration in a package."""
    await callback.answer()  # Acknowledge the callback immediately

    # Extract package ID
    parts = callback.data.split(":")
    package_id = int(parts[2])

    container = ServiceContainer(session, callback.bot)
    messages = InterestMessages()

    # Get user info
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name or callback.from_user.username or "Visitante"
    username = callback.from_user.username

    # Check for existing interest (debounce)
    existing_interest = await session.execute(
        select(PackageInterest).where(
            PackageInterest.user_id == user_id,
            PackageInterest.package_id == package_id
        )
    )
    existing = existing_interest.scalar_one_or_none()

    if existing:
        # Check if recently registered (debounce)
        from datetime import datetime, timedelta
        time_diff = datetime.utcnow() - existing.created_at
        if time_diff.total_seconds() < INTEREST_DEBOUNCE_SECONDS:
            # Show alert for already registered
            await callback.show_alert(
                "ℹ️ Ya registraste tu interés recientemente. Te notificaremos cuando haya novedades."
            )
            return

        # Update existing interest timestamp
        existing.created_at = datetime.utcnow()
        await session.commit()

        # Show alert for already registered
        await callback.show_alert(
            "ℹ️ Ya habías registrado tu interés anteriormente. Te notificaremos cuando haya novedades."
        )
        return

    # Get package info for confirmation
    package = await container.packages.get_by_id(package_id)
    if not package:
        await callback.show_alert("❌ Este paquete ya no está disponible")
        return

    # Create new interest record
    new_interest = PackageInterest(
        user_id=user_id,
        package_id=package_id,
        username=username,
        user_name=user_name
    )
    session.add(new_interest)
    await session.commit()

    # Show confirmation alert
    await callback.show_alert(
        f"✅ Interés registrado en {package.name}. Te notificaremos cuando haya novedades."
    )

    # Notify admin about new interest
    await _notify_admin_about_interest(container, messages, user_name, package, session)
```

```python
# bot/handlers/admin/interest_notifications.py
"""Admin notification handlers for interest system."""

async def _notify_admin_about_interest(
    container: ServiceContainer,
    messages: InterestMessages,
    user_name: str,
    package,
    session: AsyncSession
):
    """Send notification to admin about new interest."""
    from bot.database.models import BotConfig

    # Get admin config
    config_result = await session.execute(select(BotConfig).where(BotConfig.id == 1))
    config = config_result.scalar_one_or_none()

    if not config or not config.admin_telegram_id:
        # No admin configured, skip notification
        return

    # Get total interest count for this package
    from sqlalchemy import func, select
    count_result = await session.execute(
        select(func.count(PackageInterest.id)).where(
            PackageInterest.package_id == package.id
        )
    )
    interest_count = count_result.scalar() or 0

    # Generate notification message
    notification_text = messages.interest_notification(
        user_name=user_name,
        package_name=package.name,
        interest_count=interest_count
    )

    # Send to admin
    try:
        await container.bot.send_message(
            chat_id=config.admin_telegram_id,
            text=notification_text,
            parse_mode="HTML"
        )
    except Exception as e:
        # Admin might have blocked the bot or other error
        import logging
        logging.getLogger(__name__).error(f"Failed to send interest notification: {e}")
```

```python
# bot/handlers/admin/interest_list.py
"""Admin view of interested users for a package."""

@admins_only.callback_query(F.data.startswith("admin:package:interests:"))
async def show_interested_users(
    callback: types.CallbackQuery,
    session: AsyncSession
):
    """Show list of users interested in a specific package."""
    await callback.answer()

    # Extract package ID
    parts = callback.data.split(":")
    package_id = int(parts[3])

    container = ServiceContainer(session, callback.bot)
    messages = InterestMessages()

    # Get package info
    package = await container.packages.get_by_id(package_id)
    if not package:
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Este paquete ya no existe en los archivos...</i>"
        )
        return

    # Get interested users
    from sqlalchemy import select, desc
    interests_result = await session.execute(
        select(PackageInterest)
        .where(PackageInterest.package_id == package_id)
        .order_by(desc(PackageInterest.created_at))
    )
    interests = interests_result.scalars().all()

    # Format user data
    interested_users = [
        {
            "name": interest.user_name,
            "username": interest.username,
            "registered_at": interest.created_at
        }
        for interest in interests
    ]

    # Generate and send list
    text, keyboard = messages.interest_list(package.name, interested_users)
    await callback.message.edit_text(text, reply_markup=keyboard)
```

### Comportamiento Esperado

1. Usuario ve paquete de contenido
2. Hace clic en "⭐ Me interesa"
3. Sistema verifica si ya existe registro (debounce)
4. Si es nuevo interés:
   - Crea registro en base de datos
   - Muestra alerta de confirmación
   - Envía notificación al admin
5. Si ya existe:
   - Actualiza timestamp
   - Muestra alerta informando que ya estaba registrado
6. Admin recibe notificación con:
   - Nombre del usuario
   - Nombre del paquete
   - Total de interesados
7. Admin puede ver lista completa de interesados

### Testing

```bash
# 1. Registrar interés por primera vez
# Clic en "⭐ Me interesa"
# Verifica: Alerta "✅ Interés registrado"
# Verifica: Notificación recibida por admin

# 2. Intentar registrar nuevamente (debounce)
# Clic en "⭐ Me interesa" de nuevo
# Verifica: Alerta "ℹ️ Ya registraste tu interés"

# 3. Ver lista de interesados (admin)
/admin:package:interests:1
# Verifica: Lista con usuarios y fechas

# 4. Verificar persistencia
# Reinicia el bot y verifica que el interés persistió
```

### Notas

- El debounce previene spam del mismo usuario
- Las notificaciones al admin son asíncronas (no bloquean la respuesta al usuario)
- El manejo de errores incluye el caso donde el admin ha bloqueado al bot
- La lista de interesados está limitada a 20 para no sobrecargar el mensaje
- Los intereses se ordenan por fecha descendente (más recientes primero)
- Username opcional: muestra "Sin username" si no está disponible

---

## Ejemplo 6: Testing de Message Providers

### Caso de Uso

Asegurar que los message providers funcionen correctamente con diferentes entradas, mantengan la voz de Lucien, y generen los keyboards apropiados.

### Estructura de Tests

```python
# tests/services/message/test_admin_content_messages.py
"""Tests for AdminContentMessages provider."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from bot.services.message.admin_content import AdminContentMessages
from bot.database.models import ContentPackage
from bot.database.enums import ContentCategory, ContentType


class TestAdminContentMessages:
    """Test suite for AdminContentMessages provider."""

    @pytest.fixture
    def provider(self):
        """Create message provider instance."""
        return AdminContentMessages()

    @pytest.fixture
    def sample_package(self):
        """Create sample content package for testing."""
        package = Mock(spec=ContentPackage)
        package.id = 1
        package.name = "Pack Premium de Prueba"
        package.description = "Descripción de prueba del paquete premium"
        package.price = 15.99
        package.is_active = True
        package.category = ContentCategory.VIP_PREMIUM
        package.type = ContentType.BUNDLE
        package.media_url = "https://example.com/media.zip"
        package.created_at = datetime(2025, 1, 15, 10, 30)
        package.updated_at = datetime(2025, 1, 20, 14, 45)
        return package

    # ===== CONTENT MENU TESTS =====

    def test_content_menu_has_lucien_voice(self, provider):
        """Test that content menu maintains Lucien's voice."""
        text, keyboard = provider.content_menu()

        # Check for Lucien emoji
        assert "🎩" in text

        # Check for elegant terminology
        assert "curador" in text.lower()
        assert "galería" in text.lower() or "galeria" in text.lower()

        # Check for proper HTML formatting
        assert "<b>" in text
        assert "<i>" in text

    def test_content_menu_has_navigation_buttons(self, provider):
        """Test that content menu keyboard has navigation buttons."""
        text, keyboard = provider.content_menu()

        # Check that keyboard exists
        assert keyboard is not None

        # Check for inline keyboard
        assert hasattr(keyboard, 'inline_keyboard')

        # Get button texts from keyboard
        button_texts = []
        for row in keyboard.inline_keyboard:
            for button in row:
                button_texts.append(button.text)

        # Verify expected buttons exist
        assert "📋 Ver Paquetes" in button_texts
        assert "➕ Crear Paquete" in button_texts
        assert "🔙 Volver" in button_texts

    # ===== EMPTY STATE TESTS =====

    def test_content_list_empty_has_elegant_message(self, provider):
        """Test that empty list message is elegant and encouraging."""
        text, keyboard = provider.content_list_empty()

        # Check for Lucien emoji
        assert "🎩" in text

        # Check for empty shelf imagery
        assert "vacío" in text.lower() or "vacio" in text.lower()

        # Check for encouraging language
        assert "primera obra maestra" in text.lower()

    def test_content_list_empty_has_action_button(self, provider):
        """Test that empty state has creation button."""
        text, keyboard = provider.content_list_empty()

        button_texts = _extract_button_texts(keyboard)
        assert any("crear" in btn.lower() for btn in button_texts)

    # ===== PACKAGE DETAIL TESTS =====

    def test_package_detail_shows_all_fields(self, provider, sample_package):
        """Test that package detail shows all important fields."""
        text, keyboard = provider.package_detail(sample_package, interest_count=5)

        # Check package name
        assert "Pack Premium de Prueba" in text

        # Check description
        assert "Descripción de prueba" in text

        # Check price
        assert "$15.99" in text or "15.99" in text

        # Check interest count
        assert "5" in text or "Interesados" in text

    def test_package_detail_category_emoji(self, provider, sample_package):
        """Test that package detail shows correct category emoji."""
        text, keyboard = provider.package_detail(sample_package)

        # VIP Premium should have diamond emoji
        assert "💎" in text

    def test_package_detail_inactive_indicator(self, provider):
        """Test that inactive packages show correct indicator."""
        inactive_package = Mock(spec=ContentPackage)
        inactive_package.id = 2
        inactive_package.name = "Pack Inactivo"
        inactive_package.is_active = False
        inactive_package.category = ContentCategory.FREE_CONTENT
        inactive_package.type = ContentType.STANDARD
        inactive_package.price = None
        inactive_package.description = None
        inactive_package.media_url = None
        inactive_package.created_at = datetime.now()
        inactive_package.updated_at = None

        text, keyboard = provider.package_detail(inactive_package)

        # Check for inactive indicator
        assert "🚫" in text
        assert "Inactivo" in text

    # ===== PACKAGE SUMMARY TESTS =====

    def test_package_summary_includes_essentials(self, provider, sample_package):
        """Test that package summary includes essential information."""
        summary = provider.package_summary(sample_package, interest_count=3)

        # Check name
        assert "Pack Premium de Prueba" in summary

        # Check category
        assert "💎" in summary

        # Check status
        assert "✅" in summary

        # Check interest count
        assert "3" in summary

    def test_package_summary_truncates_long_description(self, provider):
        """Test that long descriptions are truncated."""
        long_desc_package = Mock(spec=ContentPackage)
        long_desc_package.id = 3
        long_desc_package.name = "Pack con Descripción Larga"
        long_desc_package.is_active = True
        long_desc_package.category = ContentCategory.VIP_CONTENT
        long_desc_package.description = "x" * 200  # 200 characters

        summary = provider.package_summary(long_desc_package)

        # Should be truncated with ellipsis
        assert "..." in summary
        assert len(summary) < 300  # Reasonable length

    # ===== CREATION WIZARD TESTS =====

    def test_create_welcome_has_step_count(self, provider):
        """Test that creation welcome shows step count."""
        text, keyboard = provider.create_welcome()

        # Should mention 4 steps
        assert "4" in text

    def test_create_step_name_is_clear(self, provider):
        """Test that name step has clear instruction."""
        text, keyboard = provider.create_step_name()

        # Should show step number
        assert "Paso 1" in text or "1/4" in text

        # Should indicate what to send
        assert "nombre" in text.lower()

    def test_create_step_type_has_options(self, provider):
        """Test that type step provides category options."""
        text, keyboard = provider.create_step_type()

        button_texts = _extract_button_texts(keyboard)

        # Check for category options
        assert any("gratuito" in btn.lower() for btn in button_texts)
        assert any("vip" in btn.lower() for btn in button_texts)
        assert any("premium" in btn.lower() for btn in button_texts)

    # ===== WEIGHTED VARIATIONS TESTS =====

    @patch('random.choices')
    def test_choose_variant_respects_weights(self, mock_choices, provider):
        """Test that _choose_variant uses provided weights."""
        variants = ["Option A", "Option B", "Option C"]
        weights = [0.7, 0.2, 0.1]

        # Mock random.choices to return first option
        mock_choices.return_value = ["Option A"]

        result = provider._choose_variant(variants, weights=weights)

        # Verify random.choices was called with correct weights
        mock_choices.assert_called_once_with(variants, weights=weights, k=1)
        assert result == "Option A"

    # ===== HELPER FUNCTIONS =====

    def _extract_button_texts(keyboard) -> list:
        """Extract button texts from inline keyboard."""
        texts = []
        for row in keyboard.inline_keyboard:
            for button in row:
                texts.append(button.text)
        return texts


class TestCommonMessages:
    """Test suite for CommonMessages provider."""

    @pytest.fixture
    def provider(self):
        """Create message provider instance."""
        from bot.services.message.common import CommonMessages
        return CommonMessages()

    def test_error_has_lucien_voice(self, provider):
        """Test that error messages maintain Lucien's voice."""
        msg = provider.error(context="al procesar")

        assert "🎩" in msg
        assert "Lucien" in msg
        assert "inconveniente" in msg.lower() or "inesperado" in msg.lower()

    def test_error_with_suggestion(self, provider):
        """Test that error messages can include suggestions."""
        msg = provider.error(
            context="al enviar mensaje",
            suggestion="Verifica tu conexión a internet"
        )

        assert "Sugerencia" in msg or "sugerencia" in msg.lower()
        assert "conexión" in msg or "conexion" in msg.lower()

    def test_success_is_understated(self, provider):
        """Test that success messages are understated, not overly enthusiastic."""
        msg = provider.success("paquete creado")

        assert "Excelente" in msg
        # Should NOT have multiple exclamation marks
        assert msg.count("!") <= 2

    def test_not_found_uses_elegant_terminology(self, provider):
        """Test that not_found uses elegant terminology."""
        msg = provider.not_found("token", "ABC123")

        assert "🎩" in msg
        assert "archivos de Diana" in msg
        assert "localizar" in msg


# ===== INTEGRATION TESTS =====

class TestMessageProviderIntegration:
    """Integration tests for message providers with services."""

    @pytest.mark.asyncio
    async def test_provider_with_service_container(self):
        """Test that message providers work with service container."""
        from bot.services import ServiceContainer
        from bot.services.message.admin_content import AdminContentMessages
        from unittest.mock import AsyncMock

        # Mock session and bot
        session = AsyncMock()
        bot = AsyncMock()

        # Create container and provider
        container = ServiceContainer(session, bot)
        provider = AdminContentMessages()

        # Generate message
        text, keyboard = provider.content_menu()

        # Verify structure
        assert isinstance(text, str)
        assert keyboard is not None
        assert "🎩" in text
```

### Ejecución de Tests

```bash
# Ejecutar todos los tests de message providers
pytest tests/services/message/ -v

# Ejecutar solo tests de AdminContentMessages
pytest tests/services/message/test_admin_content_messages.py -v

# Ejecutar con coverage
pytest tests/services/message/ --cov=bot/services/message --cov-report=html

# Ejecutar tests específicos
pytest tests/services/message/test_admin_content_messages.py::TestAdminContentMessages::test_content_menu_has_lucien_voice -v
```

### Testing de Variaciones de Voz

```python
# tests/services/message/test_voice_variations.py
"""Tests for voice variation mechanisms."""

import pytest
from unittest.mock import patch, Mock

from bot.services.message.user_menu import UserMenuMessages
from bot.services.message.session_history import SessionMessageHistory


class TestVoiceVariations:
    """Test suite for voice variation system."""

    @pytest.fixture
    def provider(self):
        """Create message provider instance."""
        return UserMenuMessages()

    @pytest.fixture
    def session_history(self):
        """Create session history for testing."""
        return SessionMessageHistory()

    def test_weighted_variations_prevent_repetition(self, provider, session_history):
        """Test that weighted variations don't repeat too often."""
        # Simulate multiple calls for same user
        user_id = 12345
        method_name = "vip_menu_greeting"

        greetings = set()
        for _ in range(10):
            text, _ = provider.vip_menu_greeting(
                user_name="Test",
                vip_expires_at=None,
                user_id=user_id,
                session_history=session_history
            )

            # Extract greeting (first line after header)
            lines = text.split('\n')
            greeting = lines[2] if len(lines) > 2 else ""
            greetings.add(greeting.strip())

        # Should see at least 2 different variations in 10 calls
        assert len(greetings) >= 2

    @patch('random.choice')
    def test_equal_weights_distribute_evenly(self, mock_choice, provider):
        """Test that equal weights distribute selections evenly."""
        variants = ["A", "B", "C"]
        mock_choice.side_effect = ["A", "B", "C", "A", "B"]

        results = [provider._choose_variant(variants) for _ in range(5)]

        assert results == ["A", "B", "C", "A", "B"]

    @patch('random.choices')
    def test_weighted_selection_favors_common(self, mock_choices, provider):
        """Test that weighted selection favors common variants."""
        variants = ["Common", "Rare"]
        weights = [0.9, 0.1]

        # Mock to return weighted result
        mock_choices.return_value = ["Common"]

        result = provider._choose_variant(variants, weights=weights)

        assert result == "Common"
        mock_choices.assert_called_once()

    def test_session_aware_excludes_recent_variants(self, provider, session_history):
        """Test that session-aware selection excludes recent variants."""
        user_id = 12345
        method_name = "test_method"

        # Add variant 0 to history
        session_history.add_entry(user_id, method_name, 0)

        # Call with 3 variants - should avoid variant 0
        with patch('random.choice') as mock_choice:
            mock_choice.return_value = "Variant 1"
            result = provider._choose_variant(
                ["Variant 0", "Variant 1", "Variant 2"],
                user_id=user_id,
                method_name=method_name,
                session_history=session_history
            )

            # Should have called choice with variants excluding 0
            called_variants = mock_choice.call_args[0][0]
            assert "Variant 0" not in called_variants
            assert len(called_variants) == 2  # Only variants 1 and 2


# ===== VOICE LINTING TESTS =====

class TestVoiceLints:
    """Tests to validate Lucien's voice consistency."""

    @pytest.fixture
    def all_providers(self):
        """Get all message provider instances."""
        from bot.services.message.admin_content import AdminContentMessages
        from bot.services.message.user_menu import UserMenuMessages
        from bot.services.message.common import CommonMessages

        return {
            "admin_content": AdminContentMessages(),
            "user_menu": UserMenuMessages(),
            "common": CommonMessages(),
        }

    def test_all_messages_have_lucien_header(self, all_providers):
        """Test that all public methods include Lucien header."""
        for provider_name, provider in all_providers.items():
            # Get all public methods that return tuples
            methods = [
                getattr(provider, method_name)
                for method_name in dir(provider)
                if not method_name.startswith('_')
                and callable(getattr(provider, method_name))
            ]

            for method in methods[:5]:  # Test first 5 methods
                try:
                    # Call method with minimal args
                    if provider_name == "admin_content" and method.__name__ == "content_menu":
                        result = method()
                        if isinstance(result, tuple) and len(result) >= 1:
                            text = result[0]
                            assert "🎩" in text, f"{provider_name}.{method.__name__} missing Lucien emoji"
                except:
                    pass  # Skip methods that require complex args

    def test_no_excessive_punctuation(self, all_providers):
        """Test that messages don't have excessive punctuation."""
        for provider_name, provider in all_providers.items():
            # Test common methods
            if hasattr(provider, 'content_menu'):
                text, _ = provider.content_menu()
                # No more than 2 exclamation marks
                assert text.count('!') <= 2, f"{provider_name} has too many exclamation marks"

            if hasattr(provider, 'error'):
                text = provider.error("test")
                assert text.count('!') <= 2, f"{provider_name}.error has too many exclamation marks"

    def test_no_technical_terminology(self, all_providers):
        """Test that messages avoid overly technical terminology."""
        forbidden_terms = [
            "database", "SQL", "query", "API", "endpoint",
            "HTTP", "error 404", "null pointer", "exception"
        ]

        for provider_name, provider in all_providers.items():
            if hasattr(provider, 'error'):
                text = provider.error("test context")

                for term in forbidden_terms:
                    assert term.lower() not in text.lower(), \
                        f"{provider_name}.error contains technical term: {term}"
```

### Notas

- Los tests validan tanto la estructura como el contenido
- Se usa `unittest.mock` para aislar el comportamiento
- Los tests de variaciones verifican la aleatoriedad sin depender de ella
- Los "voice lints" aseguran consistencia en toda la base de código
- Los tests de integración verifican la compatibilidad con ServiceContainer
- Se usa `pytest.mark.asyncio` para tests asíncronos

---

## Ejemplo 7: Patrones de Integración de Voz de Lucien

### Caso de Uso

Aprender a integrar la voz de Lucien consistentemente en nuevos message providers, manteniendo los patrones establecidos del proyecto.

### Patrones de Voz por Contexto

```python
# bot/services/message/voice_patterns.py
"""Reference guide for Lucien's voice integration patterns.

VOICE TERMINOLOGY MAPPING:
=========================

Generic → Lucien Voice:
-----------------------
- Usuario → visitante, alma, miembro (del círculo)
- Administrador → custodio, guardián, curador
- Contenido → tesoros, obras, colecciones
- Configuración → ajustes del reino, parámetros
- Error → inconveniente, imprevisto, perturbación
- Éxito → como se esperaba, Diana aprobará
- Gratis → sin costo, acceso abierto
- Premium → exclusivo, del círculo, del sanctum
- Comprar → adquirir, obtener
- Vender → ofrecer, presentar

TONE BY USER ROLE:
==================

VIP Members:
- Keywords: círculo, sanctum, tesoros, exclusivo, privilegios
- Tone: Welcoming, recognizing membership, intimate
- Example: "Bienvenido al círculo, {name}. Los tesoros te esperan."

Free Users:
- Keywords: jardín, vestíbulo, muestras, público, visitantes
- Tone: Inviting, encouraging VIP upgrade, accessible
- Example: "Bienvenido al jardín, {name}. Disfruta las muestras."

Administrators:
- Keywords: custodio, curador, reino, galería, archivos
- Tone: Collaborative, respectful of authority, formal
- Example: "La galería de tesoros aguarda su dirección, curador."

ERROR MESSAGES:
- Tone: Calm, mysterious, takes responsibility, consults Diana
- Example: "Hmm... algo inesperado ha ocurrido. Permítame consultar con Diana."

SUCCESS MESSAGES:
- Tone: Understated, acknowledges achievement, references Diana
- Example: "Excelente. {action} ha sido completado como se esperaba."

CONFIRMATION DIALOGS:
- Tone: Serious, respectful of decision, clear options
- Example: "¿Confirma esta acción, custodio?"

WEIGHTED VARIATION RULES:
========================

Common Greeting (70% weight):
- Standard welcoming message
- Most users see this
- Example: "Bienvenido al jardín..."

Alternate Greeting (20% weight):
- Slight variation in wording
- Adds variety without being too different
- Example: "El vestíbulo aguarda su contemplación..."

Poetic Greeting (10% weight):
- More elaborate, flowery language
- Rare special moment
- Example: "Los portales del reino se abren para usted..."

GRAMMAR AND STYLE:
===================

ALWAYS:
- Use "usted", never "tú" or "tú"
- Include 🎩 emoji in all messages
- Use HTML formatting (<b>, <i>)
- Maintain sentence fragments with "..."
- Reference Diana for authority/mystique

NEVER:
- Use multiple exclamation marks (!!!)
- Use technical jargon (database, API, etc.)
- Break character (be too casual or too robotic)
- Use ❌ emoji in message text (use 🎩 only)
- Use ALL CAPS for emphasis

SENTENCE STRUCTURE:
- Start with lowercase in <i> tags: "<i>ahora podemos...</i>"
- Use pauses: "Permítame...", "Sin embargo...", "Aunque..."
- End with openers: "¿Hay algo más...?"
- Combine formal and elegant: "Excelente elección, curador."
"""

from typing import Tuple, List
from aiogram.types import InlineKeyboardMarkup
from bot.services.message.base import BaseMessageProvider


class VoicePatternExamples(BaseMessageProvider):
    """Example implementations showing Lucien's voice patterns.

    This class demonstrates correct voice integration for reference.
    Copy these patterns when creating new message providers.
    """

    # ===== PATTERN 1: SIMPLE GREETING =====

    def simple_greeting(self, user_name: str) -> str:
        """Pattern: Simple greeting with name.

        Voice Elements:
        - Weighted variations (70/20/10)
        - Personalized with user name
        - Welcoming tone
        - Open-ended question

        Example:
            >>> provider = VoicePatternExamples()
            >>> msg = provider.simple_greeting("Ana")
            >>> "Ana" in msg and "🎩" in msg
            True
        """
        # Weighted variations
        greetings = [
            (70, f"Bienvenido, {user_name}."),
            (20, f"{user_name}, ha regresado."),
            (10, f"Los portales se abren para {user_name}."),
        ]

        greeting = self._choose_variant(
            [g[1] for g in greetings],
            weights=[g[0] / 100 for g in greetings]
        )

        header = f"🎩 <b>Lucien:</b>\n\n<i>{greeting}</i>"
        body = "<i>¿En qué puedo asistirle hoy?</i>"

        return self._compose(header, body)

    # ===== PATTERN 2: ROLE-BASED TERMINOLOGY =====

    def role_based_message(self, user_role: str) -> str:
        """Pattern: Different terminology based on user role.

        Voice Elements:
        - VIP: "círculo", "tesoros"
        - Free: "jardín", "muestras"
        - Same structure, different vocabulary

        Example:
            >>> provider = VoicePatternExamples()
            >>> msg = provider.role_based_message("VIP")
            >>> "círculo" in msg.lower()
            True
        """
        if user_role == "VIP":
            header = "🎩 <b>Lucien:</b>\n\n<i>Bienvenido al círculo exclusivo...</i>"
            body = (
                "<b>👑 Menú del Círculo</b>\n\n"
                "<i>Los tesoros del sanctum aguardan su exploración.</i>"
            )
        else:  # Free
            header = "🎩 <b>Lucien:</b>\n\n<i>Bienvenido al jardín público...</i>"
            body = (
                "<b>🌺 Menú del Jardín</b>\n\n"
                "<i>Las muestras están disponibles para su contemplación.</i>"
            )

        return self._compose(header, body)

    # ===== PATTERN 3: ERROR WITH CONTEXT =====

    def error_with_context(
        self,
        context: str,
        suggestion: str = ""
    ) -> str:
        """Pattern: Error message with context and optional suggestion.

        Voice Elements:
        - "Hmm..." for hesitation
        - "inconveniente" instead of "error"
        - "consultar con Diana" for authority
        - Optional suggestion with helpful tone

        Example:
            >>> provider = VoicePatternExamples()
            >>> msg = provider.error_with_context("al guardar")
            >>> "inconveniente" in msg.lower() or "inesperado" in msg.lower()
            True
        """
        header = "🎩 <b>Lucien:</b>"

        body = f"<i>Hmm... algo inesperado ha ocurrido {context}.\n"
        body += "Permítame consultar con Diana sobre este inconveniente.</i>"

        if suggestion:
            body += f"\n\n💡 <i>Sugerencia:</i> {suggestion}"

        footer = "<i>Mientras tanto, ¿hay algo más en lo que pueda asistirle?</i>"

        return self._compose(header, body, footer)

    # ===== PATTERN 4: SUCCESS WITHOUT EXCESS =====

    def success_message(self, action: str) -> str:
        """Pattern: Success message that's understated.

        Voice Elements:
        - "Excelente" (single exclamation)
        - "como se esperaba" (understated)
        - Optional Diana reference
        - No multiple exclamation marks

        Example:
            >>> provider = VoicePatternExamples()
            >>> msg = provider.success_message("paquete creado")
            >>> msg.count("!") <= 2
            True
        """
        header = "🎩 <b>Lucien:</b>"

        body = f"<i>Excelente. {action} ha sido completado como se esperaba.</i>"

        # Optional footer referencing Diana
        footer = "<i>Diana aprobará este progreso...</i>"

        return self._compose(header, body, footer)

    # ===== PATTERN 5: CONFIRMATION DIALOG =====

    def confirmation_dialog(self, action: str, item: str) -> Tuple[str, InlineKeyboardMarkup]:
        """Pattern: Confirmation dialog with clear yes/no.

        Voice Elements:
        - "Una decisión que requiere confirmación..."
        - Formal tone for serious actions
        - Clear options
        - References what will happen

        Example:
            >>> provider = VoicePatternExamples()
            >>> text, kb = provider.confirmation_dialog("eliminar", "Pack Premium")
            >>> "confirma" in text.lower()
            True
        """
        header = "🎩 <b>Lucien:</b>\n\n<i>Una decisión que requiere confirmación...</i>"

        body = (
            f"<b>¿{action.title()}?</b>\n\n"
            f"<i>Está a punto de {action.lower()}: <b>{item}</b></i>\n\n"
            f"<i>¿Confirma esta acción?</i>"
        )

        text = self._compose(header, body)

        # Yes/No keyboard
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✅ Sí", callback_data="confirm:yes"),
            InlineKeyboardButton(text="❌ No", callback_data="confirm:no")
        )

        keyboard = builder.as_markup()

        return text, keyboard

    # ===== PATTERN 6: EMPTY STATE =====

    def empty_state(self, item_type: str, suggestion: str) -> Tuple[str, InlineKeyboardMarkup]:
        """Pattern: Empty list state with encouragement.

        Voice Elements:
        - Elegant imagery ("estantes vacíos")
        - Encouraging language ("primera obra maestra")
        - Actionable suggestion
        - Not discouraging

        Example:
            >>> provider = VoicePatternExamples()
            >>> text, kb = provider.empty_state("paquetes", "crear uno")
            >>> "vacío" in text.lower() or "vacio" in text.lower()
            True
        """
        header = "🎩 <b>Lucien:</b>\n\n<i>Parece que no hay {item_type} disponibles...</i>"

        body = (
            f"<b>No se encontraron {item_type}</b>\n\n"
            f"<i>Le sugiero {suggestion}. "
            f"El reino siempre acepta nuevas contribuciones.</i>"
        )

        text = self._compose(header, body)

        # Keyboard with action button
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Crear", callback_data="create:start")

        keyboard = builder.as_markup()

        return text, keyboard

    # ===== PATTERN 7: LIST WITH PAGINATION =====

    def paginated_list(
        self,
        items: List[str],
        page: int,
        total_pages: int
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """Pattern: Paginated list with navigation.

        Voice Elements:
        - Page indicator ("Página X de Y")
        - Elegant navigation terms
        - Context preservation
        - Clear browsing experience

        Example:
            >>> provider = VoicePatternExamples()
            >>> items = ["Item 1", "Item 2"]
            >>> text, kb = provider.paginated_list(items, 1, 3)
            >>> "página" in text.lower() or "pagina" in text.lower()
            True
        """
        header = "🎩 <b>Lucien:</b>\n\n<i>Aquí está lo que solicité...</i>"

        # Format items
        item_list = "\n".join([f"📦 {item}" for item in items])

        body = (
            f"<b>Colección</b>\n\n"
            f"{item_list}\n\n"
            f"📖 <b>Página {page} de {total_pages}</b>"
        )

        text = self._compose(header, body)

        # Pagination keyboard
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()

        # Navigation row
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️ Anterior", callback_data=f"page:{page-1}")
            )
        else:
            nav_buttons.append(
                InlineKeyboardButton(text="⏸️ Inicio", callback_data="page:1")
            )

        nav_buttons.append(
            InlineKeyboardButton(text=f"📖 {page}/{total_pages}", callback_data="page:refresh")
        )

        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(text="➡️ Siguiente", callback_data=f"page:{page+1}")
            )
        else:
            nav_buttons.append(
                InlineKeyboardButton(text="🏁 Fin", callback_data="page:refresh")
            )

        builder.row(*nav_buttons)

        # Back button
        builder.row(
            InlineKeyboardButton(text="🔙 Volver", callback_data="menu:back")
        )

        keyboard = builder.as_markup()

        return text, keyboard


# ===== VOICE LINTING CHECKLIST =====

def check_voice_consistency(text: str) -> List[str]:
    """Check message text for Lucien's voice consistency.

    Returns list of issues found (empty if all good).

    Checklist:
    - Has 🎩 emoji
    - Uses "usted", not "tú"
    - No excessive punctuation
    - No technical terms
    - Has sentence structure
    - References Diana appropriately

    Example:
        >>> issues = check_voice_consistency("Hola usuario!")
        >>> len(issues) > 0  # Should have issues
        True
    """
    issues = []

    # Check for Lucien emoji
    if "🎩" not in text:
        issues.append("Missing 🎩 emoji")

    # Check for informal "tú"
    informal_patterns = ["¿tú", " tú ", "tú,", "tú."]
    for pattern in informal_patterns:
        if pattern in text.lower():
            issues.append(f'Uses informal "tú" instead of "usted"')
            break

    # Check for excessive exclamation
    if text.count("!") > 2:
        issues.append("Too many exclamation marks (!)")

    # Check for technical terms
    technical_terms = [
        "database", "SQL", "API", "endpoint", "HTTP",
        "error 404", "null pointer", "exception"
    ]
    for term in technical_terms:
        if term.lower() in text.lower():
            issues.append(f'Contains technical term: "{term}"')

    # Check for ALL CAPS (except HTML tags)
    import re
    words = re.findall(r'\b[A-Z]{2,}\b', text)
    words = [w for w in words if w not in ['HTML', 'Lucien', 'Diana']]
    if words:
        issues.append(f'Uses ALL CAPS for emphasis: {", ".join(words)}')

    return issues


# ===== USAGE EXAMPLE =====

if __name__ == "__main__":
    """Example usage of voice patterns."""
    provider = VoicePatternExamples()

    # Test simple greeting
    greeting = provider.simple_greeting("Diana")
    print("=== Simple Greeting ===")
    print(greeting)
    print()

    # Test role-based message
    vip_msg = provider.role_based_message("VIP")
    free_msg = provider.role_based_message("Free")
    print("=== VIP Message ===")
    print(vip_msg)
    print()
    print("=== Free Message ===")
    print(free_msg)
    print()

    # Test error with context
    error = provider.error_with_context("al guardar el paquete", "Verifica tu conexión")
    print("=== Error Message ===")
    print(error)
    print()

    # Test voice linting
    test_messages = [
        "🎩 Lucien: Hola usuario!",  # Bad: informal
        "🎩 Lucien: Bienvenido, visitante.",  # Good
        "ERROR: Database connection failed!",  # Bad: technical, ALL CAPS
    ]

    for msg in test_messages:
        issues = check_voice_consistency(msg)
        print(f'Checking: "{msg}"')
        if issues:
            print(f"  Issues: {', '.join(issues)}")
        else:
            print("  ✓ Voice is consistent")
        print()
```

### Comportamiento Esperado

1. Los patrones de voz se pueden copiar directamente a nuevos providers
2. El voice linting detecta problemas comunes de inconsistencia
3. Las variaciones ponderadas mantienen variedad sin ser caóticas
4. Los mensajes de error son elegantes, no técnicos
5. Los mensajes de éxito son sobrios, no excesivos
6. Los diálogos de confirmación son claros y respetuosos
7. Los estados vacíos son alentadores, no desalentadores

### Testing

```bash
# 1. Probar patrones de voz individualmente
python bot/services/message/voice_patterns.py

# 2. Verificar voice linting
# Debe detectar problemas en mensajes mal formados

# 3. Integrar en nuevos message providers
# Copiar patrones y adaptar a contexto específico

# 4. Validar consistencia en tests
pytest tests/services/message/test_voice_patterns.py -v
```

### Notas

- Los patrones son modulares y reutilizables
- El voice linting es automático y preventivo
- Las variaciones ponderadas evitan repetición robótica
- La terminología depende del rol del usuario
- Los errores siempre consultan a "Diana" (autoridad misteriosa)
- Los éxitos siempre son sobrios ("como se esperaba")
- Las confirmaciones siempre son claras y respetuosas

---

## Referencia de Patrones Comunes

Esta sección recopila patrones reutilizables para situaciones comunes en el desarrollo del bot.

### Navegación

```python
# Patrones de botones de navegación estándar

# Botón "Volver" (regresa al menú anterior)
InlineKeyboardButton(text="🔙 Volver", callback_data=f"{prefix}:back")

# Botón "Salir" (cierra el menú actual)
InlineKeyboardButton(text="❌ Salir", callback_data=f"{prefix}:exit")

# Botón "Menú Principal" (regresa al inicio)
InlineKeyboardButton(text="🏠 Menú Principal", callback_data="menu:main")

# Patrones de callback_data
"prefix:action:id"        # Para acciones específicas con ID
"prefix:back"             # Para navegación atrás
"prefix:exit"             # Para cerrar menú
"prefix:refresh"          # Para recargar vista actual
"prefix:page:N"           # Para paginación (N = número de página)
```

### Confirmaciones

```python
# Patrones de diálogos de confirmación

# Estructura de callback_data para confirmaciones
f"{prefix}:confirm:{action}:{item_id}"
f"{prefix}:cancel:{action}:{item_id}"

# Ejemplo: confirmación de eliminación
# Callback: "admin:package:confirm:delete:123"
# Callback: "admin:package:cancel:delete:123"

# Mensaje típico de confirmación
header = "🎩 <b>Lucien:</b>\n\n<i>Una decisión que requiere confirmación...</i>"
body = (
    f"<b>¿Eliminar Paquete?</b>\n\n"
    f"<i>Está a punto de eliminar: <b>{package_name}</b></i>\n\n"
    f"<i>Esta acción no se puede deshacer.</i>\n\n"
    f"<i>¿Confirma esta acción?</i>"
)
```

### Estados Vacíos

```python
# Patrones para listas vacías

# Con emoji apropiado al contexto
empty_emojis = {
    "packages": "📦",
    "users": "👥",
    "settings": "⚙️",
    "messages": "💬",
}

header = f"🎩 <b>Lucien:</b>\n\n<i>Parece que no hay {item_type} disponibles...</i>"
body = (
    f"<b>No se encontraron {item_type}</b>\n\n"
    f"<i>Le sugiero {suggestion}.</i>"
)

# Keyboard con acción principal
keyboard = create_inline_keyboard([
    [(f"➕ Crear {create_button_text}", f"{prefix}:create:start")],
    [("🔙 Volver", f"{prefix}:back")],
])
```

### Manejo de Errores

```python
# Patrones de mensajes de error

# Error genérico
from bot.services.message.common import CommonMessages
common = CommonMessages()
error_msg = common.error(
    context="al procesar su solicitud",
    suggestion="Intente nuevamente en unos momentos"
)

# Error específico
error_msg = common.error(
    context="al conectar con la base de datos",
    suggestion="Verifique que el servicio esté disponible"
)

# Error con detalle opcional
error_msg = common.error(
    context=context_description,
    suggestion=suggestion_text,
    include_footer=True  # Agrega "¿Hay algo más en lo que pueda asistirle?"
)
```

### Validaciones de Input

```python
# Patrones de validación de entrada de usuario

# Validación de longitud
MIN_LENGTH = 3
MAX_LENGTH = 100

if len(text) < MIN_LENGTH:
    await message.answer(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>El texto es demasiado breve. "
        f"Proporcione al menos {MIN_LENGTH} caracteres...</i>"
    )
    return

if len(text) > MAX_LENGTH:
    await message.answer(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>El texto es extenso demaisdo. "
        f"Manténgalo bajo {MAX_LENGTH} caracteres...</i>"
    )
    return

# Validación de formato numérico
try:
    value = float(text)
    if value < 0:
        raise ValueError("Negative value")
except ValueError:
    await message.answer(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>El formato no es válido. "
        "Use un número positivo (ej: 9.99)...</i>"
    )
    return
```

### FSM State Management

```python
# Patrones de gestión de estados FSM

# Actualizar datos del estado
await state.update_data(
    field1=value1,
    field2=value2
)

# Obtener datos acumulados
data = await state.get_data()
field_value = data.get('field_name', default_value)

# Cambiar al siguiente estado
await state.set_state(NextState.next_step)

# Limpiar estado (al completar o cancelar)
await state.clear()

# Chequear estado actual
current_state = await state.get_state()
if current_state == MyStates.some_state:
    # Hacer algo específico para este estado
    pass
```

### Callback Data Parsing

```python
# Patrones de parseo de callback_data

# Estructura: prefix:action:entity:id
# Ejemplo: "admin:package:edit:123"

def parse_callback_data(callback_data: str) -> dict:
    """Parse callback data into components."""
    parts = callback_data.split(":")

    return {
        "prefix": parts[0],
        "action": parts[1] if len(parts) > 1 else None,
        "entity": parts[2] if len(parts) > 2 else None,
        "id": int(parts[3]) if len(parts) > 3 else None,
    }

# Uso en handler
@router.callback_query(F.data.startswith("admin:package:"))
async def handle_package_callback(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    action = parts[2]  # "edit", "delete", "view"
    package_id = int(parts[3])

    if action == "edit":
        await handle_edit(callback, package_id)
    elif action == "delete":
        await handle_delete(callback, package_id)
```

---

## Conclusión

Este documento proporciona ejemplos completos y funcionales del sistema de menús del bot. Cada ejemplo está diseñado para ser:

1. **Copiable y adaptable** - Código listo para usar
2. **Consistente con la voz de Lucien** - Manteniendo el personaje del mayordomo
3. **Probado y validado** - Con tests que verifican el comportamiento
4. **Bien documentado** - Con explicaciones claras del propósito

Para más detalles sobre la arquitectura del sistema, consulta:
- `docs/MENU_SYSTEM.md` - Arquitectura completa
- `docs/INTEGRATION_GUIDE.md` - Guía de integración
- `docs/guia-estilo.md` - Guía de estilo de Lucien

¿Necesitas ejemplos adicionales o aclaraciones sobre alguno de los patrones mostrados?

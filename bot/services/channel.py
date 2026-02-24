"""
Channel Service - Gestión de canales VIP y Free.

Responsabilidades:
- Configuración de canales (IDs, validación)
- Verificación de permisos del bot
- Envío de publicaciones a canales
- Validación de que canales estén configurados
"""
import logging
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import Message, Chat
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import BotConfig
from bot.utils.keyboards import get_reaction_keyboard

logger = logging.getLogger(__name__)


class ChannelService:
    """
    Service para gestionar canales VIP y Free.

    Flujo típico:
    1. Admin configura canal → setup_channel()
    2. Bot verifica permisos → verify_bot_permissions()
    3. Admin envía publicación → send_to_channel()
    """

    def __init__(self, session: AsyncSession, bot: Bot):
        """
        Inicializa el service.

        Args:
            session: Sesión de base de datos
            bot: Instancia del bot de Telegram
        """
        self.session = session
        self.bot = bot
        logger.debug("✅ ChannelService inicializado")

    # ===== CONFIGURACIÓN DE CANALES =====

    async def get_bot_config(self) -> BotConfig:
        """
        Obtiene la configuración del bot (singleton).

        Returns:
            BotConfig: Configuración global

        Raises:
            RuntimeError: Si BotConfig no existe en BD
        """
        config = await self.session.get(BotConfig, 1)

        if config is None:
            # Esto no debería pasar (init_db crea el registro)
            raise RuntimeError("BotConfig no encontrado en base de datos")

        return config

    async def get_bot_config_with_channels(self) -> BotConfig:
        """
        Obtiene la configuración del bot con canales precargados.

        Use este método cuando necesite acceder frecuentemente a:
        - config.vip_channel_id
        - config.free_channel_id
        - config.free_channel_invite_link

        Returns:
            BotConfig: Configuración global

        Raises:
            RuntimeError: Si BotConfig no existe en BD
        """
        result = await self.session.execute(
            select(BotConfig).where(BotConfig.id == 1)
        )
        config = result.scalar_one_or_none()

        if config is None:
            raise RuntimeError("BotConfig no encontrado en base de datos")

        return config

    async def setup_vip_channel(self, channel_id: str) -> Tuple[bool, str]:
        """
        Configura el canal VIP.

        Validaciones:
        - Verifica que el canal existe
        - Verifica que el bot es admin del canal
        - Verifica permisos necesarios (invite users)

        Args:
            channel_id: ID del canal (ej: "-1001234567890")

        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        # Verificar formato del ID
        if not channel_id.startswith("-100"):
            return False, "❌ ID de canal inválido (debe empezar con -100)"

        # Verificar que el canal existe y bot es admin
        try:
            chat = await self.bot.get_chat(channel_id)
        except TelegramBadRequest:
            return False, "❌ Canal no encontrado. Verifica el ID."
        except TelegramForbiddenError:
            return False, "❌ Bot no tiene acceso al canal. Agrégalo como administrador."
        except Exception as e:
            logger.error(f"Error al obtener chat {channel_id}: {e}")
            return False, f"❌ Error: {str(e)}"

        # Verificar permisos del bot
        is_valid, perm_message = await self.verify_bot_permissions(channel_id)
        if not is_valid:
            return False, perm_message

        # Guardar en configuración
        config = await self.get_bot_config()
        config.vip_channel_id = channel_id

        await self.session.commit()

        logger.info(f"✅ Canal VIP configurado: {channel_id} ({chat.title})")

        return True, f"✅ Canal VIP configurado: <b>{chat.title}</b>"

    async def setup_free_channel(self, channel_id: str) -> Tuple[bool, str]:
        """
        Configura el canal Free.

        Validaciones idénticas a setup_vip_channel().

        Args:
            channel_id: ID del canal

        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        # Validaciones idénticas
        if not channel_id.startswith("-100"):
            return False, "❌ ID de canal inválido (debe empezar con -100)"

        try:
            chat = await self.bot.get_chat(channel_id)
        except TelegramBadRequest:
            return False, "❌ Canal no encontrado. Verifica el ID."
        except TelegramForbiddenError:
            return False, "❌ Bot no tiene acceso al canal. Agrégalo como administrador."
        except Exception as e:
            logger.error(f"Error al obtener chat {channel_id}: {e}")
            return False, f"❌ Error: {str(e)}"

        is_valid, perm_message = await self.verify_bot_permissions(channel_id)
        if not is_valid:
            return False, perm_message

        # Guardar en configuración
        config = await self.get_bot_config()
        config.free_channel_id = channel_id

        await self.session.commit()

        logger.info(f"✅ Canal Free configurado: {channel_id} ({chat.title})")

        return True, f"✅ Canal Free configurado: <b>{chat.title}</b>"

    async def verify_bot_permissions(self, channel_id: str) -> Tuple[bool, str]:
        """
        Verifica que el bot tiene los permisos necesarios en el canal.

        Permisos requeridos:
        - can_invite_users: Para crear invite links
        - can_post_messages: Para enviar publicaciones (canales solamente)

        Args:
            channel_id: ID del canal

        Returns:
            Tuple[bool, str]: (tiene_permisos, mensaje)
        """
        try:
            # Obtener información del bot en el chat
            bot_member = await self.bot.get_chat_member(
                chat_id=channel_id,
                user_id=self.bot.id
            )

            # Verificar que es admin
            if bot_member.status not in ["administrator", "creator"]:
                return False, (
                    "❌ Bot no es administrador del canal. "
                    "Agrégalo como admin con permisos de invitación."
                )

            # Verificar permisos específicos
            if not bot_member.can_invite_users:
                return False, (
                    "❌ Bot no tiene permiso para invitar usuarios. "
                    "Actívalo en la configuración de administradores."
                )

            # Para canales (no supergrupos), verificar can_post_messages
            chat = await self.bot.get_chat(channel_id)
            if chat.type == "channel":
                if not bot_member.can_post_messages:
                    return False, (
                        "❌ Bot no tiene permiso para publicar mensajes. "
                        "Actívalo en la configuración de administradores."
                    )

            return True, "✅ Bot tiene todos los permisos necesarios"

        except Exception as e:
            logger.error(f"Error al verificar permisos en {channel_id}: {e}")
            return False, f"❌ Error al verificar permisos: {str(e)}"

    # ===== VERIFICACIÓN DE CONFIGURACIÓN =====

    async def is_vip_channel_configured(self) -> bool:
        """
        Verifica si el canal VIP está configurado.

        Returns:
            True si configurado, False si no
        """
        config = await self.get_bot_config()
        return config.vip_channel_id is not None and config.vip_channel_id != ""

    async def is_free_channel_configured(self) -> bool:
        """
        Verifica si el canal Free está configurado.

        Returns:
            True si configurado, False si no
        """
        config = await self.get_bot_config()
        return config.free_channel_id is not None and config.free_channel_id != ""

    async def get_vip_channel_id(self) -> Optional[str]:
        """
        Retorna el ID del canal VIP configurado.

        Returns:
            ID del canal, o None si no configurado
        """
        config = await self.get_bot_config()
        return config.vip_channel_id if config.vip_channel_id else None

    async def get_free_channel_id(self) -> Optional[str]:
        """
        Retorna el ID del canal Free configurado.

        Returns:
            ID del canal, o None si no configurado
        """
        config = await self.get_bot_config()
        return config.free_channel_id if config.free_channel_id else None

    # ===== ENVÍO DE MENSAJES =====

    async def send_to_channel(
        self,
        channel_id: str,
        text: Optional[str] = None,
        photo: Optional[str] = None,
        video: Optional[str] = None,
        add_reactions: bool = True,
        protect_content: bool = False,
        **kwargs
    ) -> Tuple[bool, str, Optional[Message]]:
        """
        Envía un mensaje al canal especificado.

        Soporta:
        - Solo texto
        - Solo foto (con caption opcional)
        - Solo video (con caption opcional)
        - Botones de reacción inline (opcional, default True)
        - Protección de contenido (opcional, default False)

        Args:
            channel_id: ID del canal
            text: Texto del mensaje
            photo: File ID o URL de foto
            video: File ID o URL de video
            add_reactions: Si agregar botones de reacción (default True)
            protect_content: Si proteger contenido contra descargas (default False)
            **kwargs: Parámetros adicionales (parse_mode, etc)

        Returns:
            Tuple[bool, str, Optional[Message]]:
                - bool: éxito
                - str: mensaje descriptivo
                - Optional[Message]: mensaje enviado (si éxito)
        """
        try:
            sent_message = None

            # Determinar tipo de mensaje
            if photo:
                # Mensaje con foto
                sent_message = await self.bot.send_photo(
                    chat_id=channel_id,
                    photo=photo,
                    caption=text,
                    protect_content=protect_content,
                    **kwargs
                )
            elif video:
                # Mensaje con video
                sent_message = await self.bot.send_video(
                    chat_id=channel_id,
                    video=video,
                    caption=text,
                    protect_content=protect_content,
                    **kwargs
                )
            elif text:
                # Solo texto
                sent_message = await self.bot.send_message(
                    chat_id=channel_id,
                    text=text,
                    protect_content=protect_content,
                    **kwargs
                )
            else:
                return False, "❌ Debes proporcionar texto, foto o video", None

            # Add reaction keyboard if requested
            if add_reactions and sent_message:
                keyboard = get_reaction_keyboard(
                    content_id=sent_message.message_id,
                    channel_id=channel_id
                )
                await sent_message.edit_reply_markup(reply_markup=keyboard)

            logger.info(f"✅ Mensaje enviado al canal {channel_id}")
            return True, "✅ Publicación enviada correctamente", sent_message

        except TelegramForbiddenError:
            return False, "❌ Bot no tiene permiso para publicar en el canal", None
        except TelegramBadRequest as e:
            return False, f"❌ Error al enviar: {str(e)}", None
        except Exception as e:
            logger.error(f"Error al enviar mensaje a {channel_id}: {e}")
            return False, f"❌ Error inesperado: {str(e)}", None

    async def forward_to_channel(
        self,
        channel_id: str,
        from_chat_id: int,
        message_id: int
    ) -> Tuple[bool, str]:
        """
        Reenvía un mensaje a un canal.

        Útil para broadcasting: admin reenvía mensaje a canales.

        Args:
            channel_id: ID del canal destino
            from_chat_id: ID del chat origen
            message_id: ID del mensaje a reenviar

        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            await self.bot.forward_message(
                chat_id=channel_id,
                from_chat_id=from_chat_id,
                message_id=message_id
            )

            logger.info(f"✅ Mensaje reenviado al canal {channel_id}")
            return True, "✅ Mensaje reenviado correctamente"

        except TelegramForbiddenError:
            return False, "❌ Bot no tiene permiso para reenviar al canal"
        except Exception as e:
            logger.error(f"Error al reenviar a {channel_id}: {e}")
            return False, f"❌ Error: {str(e)}"

    async def copy_to_channel(
        self,
        channel_id: str,
        from_chat_id: int,
        message_id: int
    ) -> Tuple[bool, str]:
        """
        Copia un mensaje a un canal (sin "Forwarded from").

        Diferencia con forward:
        - forward muestra "Forwarded from Chat X"
        - copy envía como nuevo mensaje (sin firma de origen)

        Args:
            channel_id: ID del canal destino
            from_chat_id: ID del chat origen
            message_id: ID del mensaje a copiar

        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            await self.bot.copy_message(
                chat_id=channel_id,
                from_chat_id=from_chat_id,
                message_id=message_id
            )

            logger.info(f"✅ Mensaje copiado al canal {channel_id}")
            return True, "✅ Mensaje copiado correctamente"

        except TelegramForbiddenError:
            return False, "❌ Bot no tiene permiso para publicar en el canal"
        except Exception as e:
            logger.error(f"Error al copiar a {channel_id}: {e}")
            return False, f"❌ Error: {str(e)}"

    async def copy_to_channel_with_reactions(
        self,
        channel_id: str,
        from_chat_id: int,
        message_id: int
    ) -> Tuple[bool, str, Optional[Message]]:
        """
        Copia un mensaje a un canal y agrega botones de reacción.

        Args:
            channel_id: ID del canal destino
            from_chat_id: ID del chat origen
            message_id: ID del mensaje a copiar

        Returns:
            Tuple[bool, str, Optional[Message]]: (éxito, mensaje, mensaje_enviado)
        """
        try:
            sent_message = await self.bot.copy_message(
                chat_id=channel_id,
                from_chat_id=from_chat_id,
                message_id=message_id
            )

            # Add reaction keyboard
            keyboard = get_reaction_keyboard(
                content_id=sent_message.message_id,
                channel_id=channel_id
            )
            await sent_message.edit_reply_markup(reply_markup=keyboard)

            logger.info(f"✅ Mensaje copiado al canal {channel_id} con reacciones")
            return True, "✅ Mensaje copiado con botones de reacción", sent_message

        except TelegramForbiddenError:
            return False, "❌ Bot no tiene permiso para publicar en el canal", None
        except Exception as e:
            logger.error(f"Error al copiar a {channel_id}: {e}")
            return False, f"❌ Error: {str(e)}", None

    # ===== INFORMACIÓN DE CANALES =====

    async def get_channel_info(self, channel_id: str) -> Optional[Chat]:
        """
        Obtiene información del canal.

        Args:
            channel_id: ID del canal

        Returns:
            Chat si existe, None si error
        """
        try:
            chat = await self.bot.get_chat(channel_id)
            return chat
        except Exception as e:
            logger.error(f"Error al obtener info de canal {channel_id}: {e}")
            return None

    async def get_channel_member_count(self, channel_id: str) -> Optional[int]:
        """
        Obtiene cantidad de miembros del canal.

        Args:
            channel_id: ID del canal

        Returns:
            Cantidad de miembros, o None si error
        """
        try:
            count = await self.bot.get_chat_member_count(channel_id)
            return count
        except Exception as e:
            logger.error(f"Error al obtener miembros de {channel_id}: {e}")
            return None

    # ===== GESTIÓN DE ENLACES DE INVITACIÓN =====

    async def get_or_create_free_channel_invite_link(self) -> Optional[str]:
        """
        Obtiene o crea un enlace de invitación para el canal Free.

        Este método:
        1. Verifica si ya existe un enlace almacenado en BotConfig
        2. Si existe, lo retorna
        3. Si no existe, crea uno nuevo vía API de Telegram y lo almacena

        El enlace es ÚNICO y COMPARTIDO para todos los usuarios (no uno por usuario).
        Esto es diferente a los enlaces VIP que son de un solo uso y expiran.

        Returns:
            str: URL del enlace de invitación, o None si no se pudo crear
        """
        try:
            config = await self.get_bot_config()

            # 1. Verificar si ya existe un enlace almacenado
            if config.free_channel_invite_link:
                logger.debug(f"🔗 Usando enlace Free existente: {config.free_channel_invite_link[:40]}...")
                return config.free_channel_invite_link

            # 2. No existe enlace, crear uno nuevo
            free_channel_id = config.free_channel_id
            if not free_channel_id:
                logger.error("❌ No hay canal Free configurado para crear enlace")
                return None

            # Verificar permisos antes de crear
            can_invite, perm_msg = await self.verify_bot_permissions(free_channel_id)
            if not can_invite:
                logger.error(f"❌ Bot no tiene permisos para crear enlaces: {perm_msg}")
                return None

            # Crear enlace de invitación (sin expiración, sin límite de usos)
            # member_limit=0 significa sin límite
            # expire_date=None significa que no expira
            from aiogram.types import ChatInviteLink

            invite_link_obj: ChatInviteLink = await self.bot.create_chat_invite_link(
                chat_id=free_channel_id,
                name="LosKinkys Free - Enlace General",
                creates_join_request=False,  # Aprobación automática
            )

            # Almacenar el enlace en la configuración
            config.free_channel_invite_link = invite_link_obj.invite_link
            await self.session.commit()

            logger.info(
                f"✅ Enlace Free creado y almacenado: {invite_link_obj.invite_link[:50]}..."
            )

            return invite_link_obj.invite_link

        except Exception as e:
            logger.error(f"❌ Error creando enlace de invitación Free: {e}", exc_info=True)
            return None

    async def revoke_free_channel_invite_link(self) -> Tuple[bool, str]:
        """
        Revoca el enlace de invitación actual del canal Free.

        Útil cuando el admin quiere invalidar el enlace anterior
        y forzar la creación de uno nuevo en la próxima solicitud.

        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            config = await self.get_bot_config()

            if not config.free_channel_invite_link:
                return False, "No hay enlace activo para revocar"

            free_channel_id = config.free_channel_id
            if not free_channel_id:
                return False, "Canal Free no configurado"

            # Revocar el enlace en Telegram
            try:
                await self.bot.revoke_chat_invite_link(
                    chat_id=free_channel_id,
                    invite_link=config.free_channel_invite_link
                )
            except Exception as revoke_error:
                logger.warning(f"⚠️ No se pudo revocar enlace en Telegram: {revoke_error}")
                # Continuar de todas formas para limpiar la BD

            # Limpiar el enlace almacenado
            old_link = config.free_channel_invite_link
            config.free_channel_invite_link = None
            await self.session.commit()

            logger.info(f"✅ Enlace Free revocado: {old_link[:50]}...")
            return True, "Enlace revocado. Se creará uno nuevo automáticamente."

        except Exception as e:
            logger.error(f"❌ Error revocando enlace Free: {e}")
            return False, f"Error al revocar: {str(e)}"

    # ===== VERIFICACIÓN DE ADMINISTRADORES DE CANALES =====

    async def is_user_channel_admin(self, user_id: int) -> bool:
        """
        Verifica si un usuario es administrador de los canales VIP o Free.

        Los administradores de canales tienen los mismos privilegios que los
        administradores configurados en ADMIN_IDS (variables de entorno).

        Args:
            user_id: ID de Telegram del usuario

        Returns:
            True si es admin del canal VIP o Free, False en caso contrario
        """
        try:
            config = await self.get_bot_config()

            # Verificar canal VIP
            if config.vip_channel_id:
                try:
                    member = await self.bot.get_chat_member(
                        chat_id=config.vip_channel_id,
                        user_id=user_id
                    )
                    if member.status in ["administrator", "creator"]:
                        logger.debug(f"👑 User {user_id} es admin del canal VIP")
                        return True
                except Exception as e:
                    logger.debug(f"⚠️ No se pudo verificar admin VIP para user {user_id}: {e}")

            # Verificar canal Free
            if config.free_channel_id:
                try:
                    member = await self.bot.get_chat_member(
                        chat_id=config.free_channel_id,
                        user_id=user_id
                    )
                    if member.status in ["administrator", "creator"]:
                        logger.debug(f"👑 User {user_id} es admin del canal Free")
                        return True
                except Exception as e:
                    logger.debug(f"⚠️ No se pudo verificar admin Free para user {user_id}: {e}")

            return False

        except Exception as e:
            logger.error(f"❌ Error verificando si user {user_id} es admin de canales: {e}")
            return False

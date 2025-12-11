# 🤖 Bot de Administración de Canales VIP/Free - Telegram

Bot para gestionar canales VIP (por invitación con tokens) y canales Free (con tiempo de espera) en Telegram, optimizado para ejecutarse en Termux.

## 📋 Requisitos

- Python 3.11+
- Termux (Android) o Linux
- Token de bot de Telegram (via @BotFather)

## 🚀 Instalación en Termux

```bash
# 1. Actualizar Termux
pkg update && pkg upgrade

# 2. Instalar Python
pkg install python

# 3. Clonar o crear el proyecto
mkdir telegram_vip_bot
cd telegram_vip_bot

# 4. Instalar dependencias
pip install -r requirements.txt --break-system-packages

# 5. Configurar variables de entorno
cp .env.example .env
nano .env  # Editar con tus valores
```

## ⚙️ Configuración

1. **Obtener Token del Bot:**
   - Hablar con @BotFather en Telegram
   - Ejecutar `/newbot` y seguir instrucciones
   - Copiar el token generado

2. **Obtener tu User ID:**
   - Hablar con @userinfobot
   - Copiar tu ID numérico

3. **Editar `.env`:**
   ```bash
   BOT_TOKEN=tu_token_aqui
   ADMIN_USER_IDS=tu_user_id_aqui
   ```

## 🏃 Ejecución

```bash
# Desarrollo
python main.py

# En background (Termux)
nohup python main.py > bot.log 2>&1 &
```

## 📁 Estructura del Proyecto

```
/
├── main.py              # Entry point
├── config.py            # Configuración
├── bot/
│   ├── database/        # Modelos y engine SQLAlchemy
│   ├── services/        # Lógica de negocio
│   ├── handlers/        # Handlers de comandos/callbacks
│   ├── middlewares/     # Middlewares (auth, DB)
│   ├── states/          # Estados FSM
│   ├── utils/           # Utilidades
│   └── background/      # Tareas programadas
```

## 🔧 Desarrollo

Este proyecto está en desarrollo iterativo. Consulta las tareas completadas:
- [ ] ONDA 1: MVP Funcional (T1-T17)
- [ ] ONDA 2: Features Avanzadas (T18-T33)
- [ ] ONDA 3: Optimización (T34-T44)

## 📝 Licencia

MIT License

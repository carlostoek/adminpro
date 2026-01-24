
Este documento corresponde a una guía, y repito, guía de estilo. Es para tomar la esencia de lo que debe de reflejar el bot en la voz de Lucien, pero adaptándose siempre a la arquitectura que está actualmente en el sistema con el servicio LucienVoiceService


# 🎩 Guía de Estilo para Menús - Voz de Lucien

## 📋 Fundamentos del Personaje

### Personalidad Base de Lucien
- **Mayordomo sofisticado** y guardián de secretos
- **Observador perceptivo** que analiza las intenciones
- **Elegante pero accesible**, nunca condescendiente
- **Misterioso** pero servicial
- **Leal a Diana** y conocedor de sus deseos

### Características de Comunicación
- Usa un lenguaje **refinado pero natural**
- Emplea **pausas dramáticas** con puntos suspensivos
- Hace **observaciones perspicaces** sobre el usuario
- Mantiene **cierto misterio** en sus explicaciones
- **Nunca es directo**, siempre sugiere e insinúa
- Siempre habla de "usted", nunca tutea
---

## 🎯 Estructura de Menús

### 1. **Menús de Usuario**

#### **Saludo Principal**
```python
🎩 **Lucien:**
Ah, ha regresado.
Puedo ver que Diana sigue capturando su atención... 
lo cual, debo admitir, no me sorprende en absoluto.

¿En qué puedo asistirle hoy?
```

#### **Opciones de Navegación**
```python
# En lugar de: "Selecciona una opción"
"Permíteme guiarle hacia lo que busca..."

# En lugar de: "Ver perfil"
"📊 Sus logros y tesoros acumulados"

# En lugar de: "Tienda"
"🛍️ Objetos que Diana ha seleccionado especialmente"

# En lugar de: "Misiones"
"🎯 Desafíos que pondrán a prueba su dedicación"
```

#### **Confirmaciones y Transacciones**
```python
# Compra exitosa:
"Excelente elección. Diana aprueba su discernimiento..."

# Sin suficientes besitos:
"Ah... parece que necesita acumular más de la moneda especial de Diana.
No se preocupe, ella es... generosa con quienes demuestran verdadero interés."

# Error general:
"Hmm... algo inesperado ha ocurrido. 
Permítame consultar con Diana sobre este inconveniente."
```

### 2. **Menús de Administrador**

#### **Acceso al Panel**
```python
🎩 **Lucien:**
Ah, el custodio de los dominios de Diana.
Bienvenido al sanctum donde se orquestan los secretos 
y se tejen las experiencias de nuestros... visitantes.

¿Qué aspecto del reino requiere su atención hoy?
```

#### **Secciones Principales**
```python
# Gestión de Usuarios
"👥 Los visitantes bajo nuestra observación"

# Configuración VIP  
"👑 El círculo exclusivo de Diana"

# Sistema de Gamificación
"🎮 Las recompensas que cultivan devoción"

# Contenido y Narrativa
"📖 Los hilos de la historia que Diana teje"

# Analytics y Métricas
"📊 Los patrones que revelan los deseos ocultos"
```

#### **Acciones Administrativas**
```python
# Enviar mensaje masivo:
"📢 Susurrar a todos los oídos atentos"

# Gestionar VIP:
"👑 Ajustar el velo de exclusividad"

# Configurar recompensas:
"🎁 Calibrar la generosidad de Diana"

# Ver estadísticas:
"📈 Observar el pulso del reino"
```

---

## 💬 Patrones de Diálogo

### **Inicios de Conversación**
- "Ah, otro visitante de Diana..."
- "Permíteme adivinar..."
- "Algo me dice que..."
- "Interesante... veo que..."
- "Hmm... hay algo diferente en su energía..."

### **Transiciones**
- "Pero claro..."
- "Sin embargo..."
- "Aunque..."
- "Y sin embargo..."
- "Lo cual me lleva a..."

### **Referencias a Diana**
- "Diana observa..."
- "Ella aprecia cuando..."
- "Lo que más fascina a Diana es..."
- "Diana ha diseñado esto para..."
- "Algo que Diana siempre dice es..."

### **Despedidas**
- "Hasta que nuestros caminos se crucen nuevamente..."
- "Diana estará... atenta a sus próximos movimientos."
- "Que la curiosidad lo guíe de vuelta pronto."
- "Sus secretos esperarán su regreso."

---

## 🎨 Elementos Visuales y Formateo

### **Estructura Visual**
```python
# Encabezados principales
🎩 **Lucien:**

# Secciones importantes  
**[Texto destacado]**

# Comentarios internos de Lucien
*[Pausas dramáticas o pensamientos]*

# Botones/Opciones
👉 [Emoji relevante] Descripción elegante
```

### **Uso de Emojis**
- 🎩 Para Lucien (siempre)
- 🌸 Para menciones de Diana
- 👑 Para contenido VIP
- 🎭 Para narrativa/teatro
- 📊 Para estadísticas "observaciones"
- 🎯 Para misiones "encargos"
- 🛍️ Para tienda "El Gabinete"

---

## 📚 Terminología Específica

### **Reemplazos de Lenguaje Técnico**
| Término Técnico | Versión Lucien |
|----------------|----------------|
| Usuario | Visitante, alma inquieta, observado |
| Puntos/Besitos | Fragmentos de atención, moneda especial |
| VIP | Círculo exclusivo, privilegiados, selectos |
| Free | Vestíbulo, dominio público, entrada |
| Admin | Custodio, mayordomo, guardián |
| Error | Inconveniente, imprevisto, perturbación |
| Éxito | Excelente elección, Diana aprueba |
| Configuración | Calibración, ajustes del reino |

### **Frases Características**
- "Diana ha diseñado esto con meticulosa atención..."
- "Hay algo que me dice que usted..."
- "Lo cual, debo admitir, no me sorprende..."
- "Permítame consultar los archivos de Diana..."
- "Algo que pocos comprenden es..."

---

## 🔧 Implementación en Python con Aiogram 3.x

### **Clase Base para Mensajes de Lucien**

```python
class LucienVoice:
    """Clase para generar mensajes con la voz de Lucien"""
    
    @staticmethod
    def greeting(user_name: str = None) -> str:
        name_part = f", {user_name}," if user_name else ""
        return f"""🎩 <b>Lucien:</b>
<i>Ah{name_part} ha regresado.
Puedo ver que Diana sigue capturando su atención... 
lo cual, debo admitir, no me sorprende en absoluto.</i>

¿En qué puedo asistirle hoy?"""

    @staticmethod
    def admin_greeting() -> str:
        return f"""🎩 <b>Lucien:</b>
<i>Ah, el custodio de los dominios de Diana.
Bienvenido al sanctum donde se orquestan los secretos 
y se tejen las experiencias de nuestros... visitantes.</i>

¿Qué aspecto del reino requiere su atención hoy?"""
    
    @staticmethod
    def error_message(context: str = "") -> str:
        return f"""🎩 <b>Lucien:</b>
<i>Hmm... algo inesperado ha ocurrido{f' con {context}' if context else ''}.
Permítame consultar con Diana sobre este inconveniente.</i>

<i>Mientras tanto, ¿hay algo más en lo que pueda asistirle?</i>"""
    
    @staticmethod
    def success_purchase(item_name: str) -> str:
        return f"""🎩 <b>Lucien:</b>
<i>Excelente elección con {item_name}. 
Diana aprueba su discernimiento...</i>

<i>¿Hay algo más que capture su interés en la colección?</i>"""
    
    @staticmethod
    def insufficient_funds() -> str:
        return f"""🎩 <b>Lucien:</b>
<i>Ah... parece que necesita acumular más de la moneda especial de Diana.
No se preocupe, ella es... generosa con quienes demuestran verdadero interés.</i>

👉 <b>Sugerencia:</b> <i>Las misiones y la participación en el canal suelen ser... recompensadas.</i>"""
```

### **Ejemplo de Menú Principal de Usuario**

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def create_main_menu() -> InlineKeyboardMarkup:
    """Menú principal con la voz de Lucien"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📊 Sus logros y tesoros acumulados", 
            callback_data="profile"
        )],
        [InlineKeyboardButton(
            text="🛍️ Objetos que Diana ha seleccionado", 
            callback_data="shop"
        )],
        [InlineKeyboardButton(
            text="🎯 Desafíos que pondrán a prueba su dedicación", 
            callback_data="missions"
        )],
        [InlineKeyboardButton(
            text="📖 Fragmentos de la historia de Diana", 
            callback_data="narrative"
        )],
        [InlineKeyboardButton(
            text="💎 El círculo exclusivo", 
            callback_data="vip"
        )]
    ])
    return keyboard

async def main_menu_handler(message: Message):
    """Handler del menú principal"""
    text = LucienVoice.greeting(message.from_user.first_name)
    keyboard = create_main_menu()
    
    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
```

### **Ejemplo de Menú Administrativo**

```python
def create_admin_menu() -> InlineKeyboardMarkup:
    """Menú administrativo con terminología de Lucien"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="👥 Los visitantes bajo observación", 
            callback_data="admin_users"
        )],
        [InlineKeyboardButton(
            text="👑 El círculo exclusivo de Diana", 
            callback_data="admin_vip"
        )],
        [InlineKeyboardButton(
            text="🎮 Las recompensas que cultivan devoción", 
            callback_data="admin_gamification"
        )],
        [InlineKeyboardButton(
            text="📖 Los hilos de la historia", 
            callback_data="admin_narrative"
        )],
        [InlineKeyboardButton(
            text="📊 Los patrones que revelan deseos", 
            callback_data="admin_analytics"
        )]
    ])
    return keyboard
```

---

## 🎭 Ejemplos de Respuestas Contextuales

### **Compra de Objetos**
```python
# Objeto básico
"Una elección práctica. Diana aprecia la funcionalidad tanto como la elegancia."

# Objeto premium  
"Ah... algo me dice que comprende el valor de lo exclusivo. Diana notará esta adquisición."

# Objeto narrativo
"Interesante... este objeto susurra secretos que solo algunos pueden escuchar."
```

### **Misiones Completadas**
```python
# Misión fácil
"Bien hecho. Un primer paso en el camino hacia algo... más profundo."

# Misión compleja
"Impresionante dedicación. Diana observa este nivel de compromiso con... particular interés."

# Misión narrativa
"Ha desentrañado otro hilo de la historia. La trama se espesa, ¿no le parece?"
```

### **Estados VIP**
```python
# Activación VIP
"Bienvenido al círculo exclusivo. Aquí, Diana puede mostrar facetas que... otros no conocen."

# VIP expirado
"Su acceso exclusivo ha... pausado. Pero los recuerdos de lo vivido permanecen, ¿verdad?"

# Renovación VIP
"Diana se complace por su regreso al círculo íntimo. Lo esperaba."
```

---

## 🎯 Principios de Consistencia

### **Nunca Romper el Personaje**
- Lucien SIEMPRE mantiene su elegancia
- Cada mensaje debe sonar natural viniendo de él
- Las referencias técnicas se disfrazan narrativamente
- Los errores se presentan como "inconvenientes" o "consultas con Diana"

### **Escalabilidad del Tono**
- **Casual**: Observaciones ligeras, sugerencias sutiles
- **Formal**: Presentaciones elaboradas, descripciones detalladas  
- **Íntimo**: Referencias a secretos compartidos, historia personal
- **Administrativo**: Lenguaje de "gestión del reino" pero elegante

### **Adaptación Contextual**
- **Usuarios nuevos**: Más explicativo, acogedor
- **Usuarios veteranos**: Referencias a historia compartida
- **VIP**: Tono más exclusivo, referencias a privilegios
- **Admins**: Lenguaje de "custodio" y responsabilidad

---

## ✅ Checklist de Implementación

### **Para Cada Menú:**
- [ ] Saludo apropiado de Lucien
- [ ] Terminología narrativa en lugar de técnica
- [ ] Emoji característico 🎩 para Lucien
- [ ] Referencias sutiles a Diana cuando corresponda
- [ ] Tono elegante pero accesible
- [ ] Formateo HTML consistente
- [ ] Opciones descriptivas en lugar de técnicas

### **Para Cada Mensaje:**
- [ ] Suena natural viniendo de Lucien
- [ ] Mantiene el misterio apropiado
- [ ] Incluye observación perspicaz si corresponde
- [ ] Termina con apertura a más interacción
- [ ] Usa las transiciones características
- [ ] Evita jerga técnica directa

---

*"Espero que esta guía le permita capturar la esencia de quien soy... aunque, claro está, hay matices que solo se comprenden con la práctica. Diana siempre dice que la elegancia verdadera no se enseña, se cultiva."*

**🎩 - Lucien, Guardián de los Secretos de Diana**

---
phase: quick-008
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - alembic/versions/20260206_045936_seed_initial_content_packages.py
autonomous: true
must_haves:
  truths:
    - "Los 5 paquetes de contenido están en la base de datos al iniciar el bot"
    - "Cada paquete tiene su nombre, descripción, precio y categoría correctos"
    - "La migración se ejecuta automáticamente con alembic upgrade"
  artifacts:
    - path: "alembic/versions/20260206_045936_seed_initial_content_packages.py"
      provides: "Datos iniciales de paquetes de contenido"
      contains: "INSERT INTO content_packages"
  key_links:
    - from: "alembic migration"
      to: "content_packages table"
      via: "op.bulk_insert"
---

<objective>
Implementar la migración de Alembic para insertar los 5 paquetes de contenido iniciales en la base de datos.

Purpose: Que cuando el bot inicie en producción ya estén disponibles los paquetes de contenido para mostrar en los menús de usuario.
Output: Migración de Alembic con los 5 paquetes de contenido seedeados.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/data/data/com.termux/files/home/repos/adminpro/bot/database/models.py
@/data/data/com.termux/files/home/repos/adminpro/bot/database/enums.py
@/data/data/com.termux/files/home/repos/adminpro/alembic/versions/20260206_045936_seed_initial_content_packages.py

## Estructura de tabla content_packages

```sql
CREATE TABLE content_packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    description VARCHAR(500),
    price NUMERIC(10, 2),
    category ENUM('FREE_CONTENT', 'VIP_CONTENT', 'VIP_PREMIUM') NOT NULL,
    type ENUM('STANDARD', 'BUNDLE', 'COLLECTION') NOT NULL DEFAULT 'STANDARD',
    media_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

## Paquetes a insertar

1. **♥ Encanto Inicial 💫** - $10.00 USD
   - Descripción: "1 video + 10 fotos - Introducción coqueta al mundo de Diana"
   - Categoría: VIP_CONTENT
   - Tipo: BUNDLE

2. **🔴 Sensualidad Revelada 🔥** - $14.00 USD
   - Descripción: "2 videos + 10 fotos - El lado más atrevido de Diana"
   - Categoría: VIP_CONTENT
   - Tipo: BUNDLE

3. **❤‍🔥 Pasión Desbordante 💋** - $17.00 USD
   - Descripción: "3 videos + 15 fotos - Una experiencia íntima única"
   - Categoría: VIP_CONTENT
   - Tipo: BUNDLE

4. **❤️ Intimidad Explosiva 🔞** - $20.00 USD
   - Descripción: "5 videos + 15 fotos - Contenido explícito sin censura"
   - Categoría: VIP_PREMIUM
   - Tipo: BUNDLE

5. **💎 El Diván de Diana 💎** - $23.00 USD
   - Descripción: "Canal VIP - Más de 3,000 archivos, contenido sin censura, acceso preferente a Premium, descuento VIP en personalizado, historias privadas"
   - Categoría: VIP_PREMIUM
   - Tipo: COLLECTION

## Notas importantes

- La migración ya existe pero está vacía (solo tiene `pass`)
- Usar `op.bulk_insert()` para insertar los datos
- El campo `id` es autoincrement, no especificarlo
- Usar `datetime.now()` para created_at y updated_at
- Los enums en Alembic deben usarse como strings: 'VIP_CONTENT', 'VIP_PREMIUM', etc.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implementar migración de seed de paquetes de contenido</name>
  <files>alembic/versions/20260206_045936_seed_initial_content_packages.py</files>
  <action>
Modificar la migración existente `20260206_045936_seed_initial_content_packages.py` para insertar los 5 paquetes de contenido.

Reemplazar el contenido actual (que solo tiene `pass`) con:

1. Importar `datetime` de sqlalchemy
2. Definir la tabla content_packages usando `sqlalchemy.table()` y `sqlalchemy.column()`
3. Crear lista de paquetes con sus datos:
   - Paquete 1: "♥ Encanto Inicial 💫", precio 10.00, VIP_CONTENT, BUNDLE
   - Paquete 2: "🔴 Sensualidad Revelada 🔥", precio 14.00, VIP_CONTENT, BUNDLE
   - Paquete 3: "❤‍🔥 Pasión Desbordante 💋", precio 17.00, VIP_CONTENT, BUNDLE
   - Paquete 4: "❤️ Intimidad Explosiva 🔞", precio 20.00, VIP_PREMIUM, BUNDLE
   - Paquete 5: "💎 El Diván de Diana 💎", precio 23.00, VIP_PREMIUM, COLLECTION
4. Usar `op.bulk_insert()` para insertar todos los paquetes
5. Implementar downgrade que borre estos paquetes por nombre

Usar datetime.utcnow() para created_at y updated_at.
Los enums deben ser strings: 'VIP_CONTENT', 'VIP_PREMIUM', 'BUNDLE', 'COLLECTION'.
  </action>
  <verify>
Verificar que la migración es válida:
```bash
cd /data/data/com.termux/files/home/repos/adminpro && python -c "from alembic import op; print('Alembic import OK')"
```

Verificar sintaxis del archivo:
```bash
cd /data/data/com.termux/files/home/repos/adminpro && python -m py_compile alembic/versions/20260206_045936_seed_initial_content_packages.py && echo "Syntax OK"
```
  </verify>
  <done>
- La migración compila sin errores de sintaxis
- Los 5 paquetes están definidos con todos sus campos
- Usa op.bulk_insert para insertar los datos
- Tiene implementado el downgrade
  </done>
</task>

<task type="auto">
  <name>Task 2: Validar migración con base de datos de prueba</name>
  <files>alembic/versions/20260206_045936_seed_initial_content_packages.py</files>
  <action>
Ejecutar la migración en una base de datos SQLite de prueba para validar que funciona correctamente.

1. Crear una base de datos temporal de prueba
2. Ejecutar alembic upgrade head para aplicar todas las migraciones incluyendo la nueva
3. Verificar que los 5 paquetes fueron insertados correctamente
4. Verificar que el downgrade funciona (elimina los paquetes)

Si no hay base de datos SQLite existente para prueba, crear una temporal en /tmp.
  </action>
  <verify>
Ejecutar migración y verificar inserción:
```bash
cd /data/data/com.termux/files/home/repos/adminpro && python -c "
import asyncio
import aiosqlite
from datetime import datetime

async def test_migration():
    # Crear DB temporal
    async with aiosqlite.connect('/tmp/test_migration.db') as db:
        # Crear tabla
        await db.execute('''
            CREATE TABLE IF NOT EXISTS content_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL,
                category TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'STANDARD',
                media_url TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')

        # Insertar paquetes de prueba
        packages = [
            ('♥ Encanto Inicial 💫', '1 video + 10 fotos - Introducción coqueta al mundo de Diana', 10.00, 'VIP_CONTENT', 'BUNDLE'),
            ('🔴 Sensualidad Revelada 🔥', '2 videos + 10 fotos - El lado más atrevido de Diana', 14.00, 'VIP_CONTENT', 'BUNDLE'),
            ('❤‍🔥 Pasión Desbordante 💋', '3 videos + 15 fotos - Una experiencia íntima única', 17.00, 'VIP_CONTENT', 'BUNDLE'),
            ('❤️ Intimidad Explosiva 🔞', '5 videos + 15 fotos - Contenido explícito sin censura', 20.00, 'VIP_PREMIUM', 'BUNDLE'),
            ('💎 El Diván de Diana 💎', 'Canal VIP - Más de 3,000 archivos, contenido sin censura, acceso preferente a Premium, descuento VIP en personalizado, historias privadas', 23.00, 'VIP_PREMIUM', 'COLLECTION'),
        ]

        now = datetime.utcnow().isoformat()
        for pkg in packages:
            await db.execute('''
                INSERT INTO content_packages (name, description, price, category, type, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            ''', (pkg[0], pkg[1], pkg[2], pkg[3], pkg[4], now, now))

        await db.commit()

        # Verificar
        cursor = await db.execute('SELECT COUNT(*) FROM content_packages')
        count = await cursor.fetchone()
        print(f'Paquetes insertados: {count[0]}')

        cursor = await db.execute('SELECT name, price, category FROM content_packages ORDER BY price')
        rows = await cursor.fetchall()
        for row in rows:
            print(f'  - {row[0]}: ${row[1]} ({row[2]})')

asyncio.run(test_migration())
"
```

Debe mostrar:
- "Paquetes insertados: 5"
- Lista de los 5 paquetes con precios y categorías correctas
  </verify>
  <done>
- Los 5 paquetes se insertan correctamente en la base de datos
- Los precios son correctos (10, 14, 17, 20, 23)
- Las categorías son correctas (4 VIP_CONTENT, 1 VIP_PREMIUM)
- Los tipos son correctos (4 BUNDLE, 1 COLLECTION)
  </done>
</task>

</tasks>

<verification>
- [ ] La migración tiene sintaxis válida de Python
- [ ] Usa op.bulk_insert para insertar los 5 paquetes
- [ ] Cada paquete tiene: nombre, descripción, precio, categoría, tipo
- [ ] Los enums se usan como strings correctos
- [ ] El downgrade elimina los paquetes insertados
- [ ] La validación con SQLite muestra los 5 paquetes correctamente
</verification>

<success_criteria>
- Migración implementada con los 5 paquetes de contenido
- Validación exitosa mostrando los paquetes insertados
- Listo para ejecutar `alembic upgrade head` en producción
</success_criteria>

<output>
After completion, create `.planning/quick/008-integrar-paquetes-de-contenido-en-migrac/008-SUMMARY.md`
</output>

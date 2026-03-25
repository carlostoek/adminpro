
🔍 Lo que tienes que vigilar mientras implementas (agrégalo al contexto de la fase)
No avances rápido. Valida esto:
1. 🔴 Punto único de verdad
Debes poder responder sin dudar:
“¿De dónde sale el rol que usa el sistema?”
Si la respuesta no es: → resolve_user_context()
entonces ya perdiste consistencia.
2. 🔴 Propagación real del contexto
No basta con calcularlo.
Debes asegurarte que:
handlers lo reciben
services lo reciben
middlewares lo respetan
Si en algún punto vuelves a consultar DB directamente: → rompiste el sistema
3. 🔴 Visibilidad constante
Si en algún momento no sabes en qué modo estás: → vas a cometer errores tú mismo como admin
El sistema debe recordártelo SIEMPRE.

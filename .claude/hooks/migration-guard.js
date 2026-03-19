#!/usr/bin/env node
/**
 * migration-guard.js
 * PostToolUse hook: detecta modificaciones a modelos SQLAlchemy
 * y emite feedback para que Claude invoque el auditor de migraciones.
 *
 * Claude Code pasa el evento como JSON en stdin (fd 0).
 * stdout → feedback visible para Claude.
 * Exit 0 = continuar | Exit 2 = bloquear con error.
 */

const fs = require('fs');

// Leer stdin de forma síncrona (fd=0 es stdin)
let raw = '';
try {
  raw = fs.readFileSync('/dev/stdin', 'utf8');
} catch (e) {
  process.exit(0);
}

let event = {};
try {
  event = JSON.parse(raw);
} catch (e) {
  process.exit(0);
}

const tool = event.tool_name || '';
const params = event.tool_input || {};

// Solo reaccionar a herramientas que escriben archivos
if (!['Write', 'Edit'].includes(tool)) process.exit(0);

const filePath = params.file_path || '';

// Patrones de archivos de esquema SQLAlchemy y migraciones
const MODEL_PATTERNS = [
  /bot[/\\]database[/\\]models\.py$/,
  /bot[/\\]database[/\\]base\.py$/,
  /alembic[/\\]versions[/\\].*\.py$/,  // Migraciones Alembic
];

const isModel = MODEL_PATTERNS.some(p => p.test(filePath));
if (!isModel) process.exit(0);

// Emitir feedback a Claude
const message = [
  `⚠️  MIGRATION GUARD: cambio detectado en ${filePath}`,
  '',
  'Debes invocar el agente alembic-migration-auditor ANTES de continuar:',
  '  subagent_type: alembic-migration-auditor',
  `  prompt: "Se modificó ${filePath}. Verifica si se requiere migración Alembic,`,
  '           créala si es necesario, y audita compatibilidad SQLite/PostgreSQL."',
  '',
  'No continúes con el siguiente paso del plan hasta que el auditor complete su revisión.',
].join('\n');

process.stdout.write(message + '\n');
process.exit(0);

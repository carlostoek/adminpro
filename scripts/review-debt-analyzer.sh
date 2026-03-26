#!/bin/bash
# ============================================================
#  review-debt-analyzer.sh
#  Auditoría automatizada de reviews pendientes en PRs antiguos
#
#  Uso:
#    chmod +x review-debt-analyzer.sh
#    ./review-debt-analyzer.sh [opciones]
#
#  Opciones:
#    -l, --limit N       Número de PRs a analizar (default: 30)
#    -b, --base BRANCH   Rama base del repo (default: main)
#    -o, --output DIR    Directorio de salida (default: review-audit)
#    -i, --issues        Crear GitHub Issues automáticamente para pendientes
#    -f, --fix-branch    Crear rama de fixes al final
#    -h, --help          Mostrar ayuda
#
#  Ejemplo:
#    ./review-debt-analyzer.sh --limit 50 --issues --fix-branch
# ============================================================

set -euo pipefail

# ─── Colores ────────────────────────────────────────────────
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ─── Defaults ───────────────────────────────────────────────
LIMIT=30
BASE_BRANCH="main"
OUTPUT_DIR="review-audit"
CREATE_ISSUES=false
CREATE_FIX_BRANCH=false
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ─── Contadores globales ─────────────────────────────────────
TOTAL_PRS=0
PRS_WITH_COMMENTS=0
TOTAL_COMMENTS=0
FILES_EXIST=0
FILES_MISSING=0
STILL_VALID=0
ALREADY_FIXED=0
NOT_APPLICABLE=0

# ─── Funciones de UI ────────────────────────────────────────
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║     📊 Review Debt Analyzer                      ║${NC}"
    echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "\n${BOLD}${CYAN}▶ $1${NC}"
}

print_ok() {
    echo -e "  ${GREEN}✅ $1${NC}"
}

print_warn() {
    echo -e "  ${YELLOW}⚠️  $1${NC}"
}

print_err() {
    echo -e "  ${RED}❌ $1${NC}"
}

print_info() {
    echo -e "  ${BLUE}ℹ️  $1${NC}"
}

show_help() {
    grep '^#  ' "$0" | sed 's/^#  //'
    exit 0
}

# ─── Parsear argumentos ──────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--limit)       LIMIT="$2";        shift 2 ;;
        -b|--base)        BASE_BRANCH="$2";  shift 2 ;;
        -o|--output)      OUTPUT_DIR="$2";   shift 2 ;;
        -i|--issues)      CREATE_ISSUES=true; shift ;;
        -f|--fix-branch)  CREATE_FIX_BRANCH=true; shift ;;
        -h|--help)        show_help ;;
        *)                echo "Opción desconocida: $1"; exit 1 ;;
    esac
done

# ─── Limpiar archivos temporales residuales ───────────────────
rm -f /tmp/rda_rc_*.json /tmp/rda_ic_*.json 2>/dev/null || true

# ─── Verificar dependencias ──────────────────────────────────
check_deps() {
    print_step "Verificando dependencias..."

    local missing=()

    for cmd in gh git jq; do
        if command -v "$cmd" &>/dev/null; then
            print_ok "$cmd disponible ($(${cmd} --version 2>&1 | head -1))"
        else
            print_err "$cmd no encontrado"
            missing+=("$cmd")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo ""
        echo -e "${RED}Instala las dependencias faltantes:${NC}"
        for dep in "${missing[@]}"; do
            case $dep in
                gh)  echo "  brew install gh  /  https://cli.github.com" ;;
                jq)  echo "  brew install jq  /  apt install jq" ;;
                git) echo "  brew install git / apt install git" ;;
            esac
        done
        exit 1
    fi

    # Verificar autenticación de gh
    if ! gh auth status &>/dev/null; then
        print_err "GitHub CLI no autenticado. Ejecuta: gh auth login"
        exit 1
    fi
    print_ok "GitHub CLI autenticado"
}

# ─── Preparar directorio de salida ───────────────────────────
setup_output() {
    print_step "Preparando directorio de salida..."

    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR/prs"
    mkdir -p "$OUTPUT_DIR/reports"

    print_ok "Directorio creado: $OUTPUT_DIR/"
}

# ─── Obtener repositorio actual ──────────────────────────────
get_repo_info() {
    print_step "Detectando repositorio..."

    REPO_FULL=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")

    if [ -z "$REPO_FULL" ]; then
        print_err "No se pudo detectar el repositorio."
        print_info "Asegúrate de estar dentro de un repositorio Git con remoto en GitHub."
        exit 1
    fi

    REPO_OWNER=$(echo "$REPO_FULL" | cut -d'/' -f1)
    REPO_NAME=$(echo "$REPO_FULL" | cut -d'/' -f2)

    print_ok "Repositorio: $REPO_FULL"
    print_info "Analizando los últimos $LIMIT PRs mergeados..."
}

# ─── Fase 1: Extraer PRs mergeados ───────────────────────────
fetch_merged_prs() {
    print_step "Fase 1/4 — Extrayendo PRs mergeados..."

    gh pr list \
        --state merged \
        --limit "$LIMIT" \
        --json number,title,mergedAt,author,baseRefName \
        > "$OUTPUT_DIR/merged_prs.json"

    TOTAL_PRS=$(jq '. | length' "$OUTPUT_DIR/merged_prs.json")
    print_ok "$TOTAL_PRS PRs mergeados encontrados"
}

# ─── Fase 2: Extraer comentarios de cada PR ──────────────────
fetch_pr_comments() {
    print_step "Fase 2/4 — Extrayendo comentarios de cada PR..."

    local pr_list
    pr_list=$(jq -r '.[].number' "$OUTPUT_DIR/merged_prs.json")

    echo "[]" > "$OUTPUT_DIR/all_comments.json"

    local pr_count=0
    for pr_num in $pr_list; do
        pr_count=$((pr_count + 1))
        local pr_title
        pr_title=$(jq -r --argjson n "$pr_num" '.[] | select(.number == $n) | .title' "$OUTPUT_DIR/merged_prs.json")
        local pr_merged_at
        pr_merged_at=$(jq -r --argjson n "$pr_num" '.[] | select(.number == $n) | .mergedAt' "$OUTPUT_DIR/merged_prs.json")

        printf "  [%2d/%d] PR #%-5s %s\n" "$pr_count" "$TOTAL_PRS" "$pr_num" "$pr_title"

        # Obtener review comments — directo a archivo (evita "Argument list too long")
        gh api \
            "repos/$REPO_OWNER/$REPO_NAME/pulls/$pr_num/comments" \
            2>/dev/null > /tmp/rda_rc_${pr_num}.json || echo "[]" > /tmp/rda_rc_${pr_num}.json


        # Obtener issue comments (en la conversación general)
        gh api \
            "repos/$REPO_OWNER/$REPO_NAME/issues/$pr_num/comments" \
            2>/dev/null > /tmp/rda_ic_${pr_num}.json || echo "[]" > /tmp/rda_ic_${pr_num}.json

        local comment_count
        comment_count=$(jq '. | length' /tmp/rda_rc_${pr_num}.json)
        TOTAL_COMMENTS=$((TOTAL_COMMENTS + comment_count))

        if [ "$comment_count" -gt 0 ]; then
            PRS_WITH_COMMENTS=$((PRS_WITH_COMMENTS + 1))
            print_info "PR #$pr_num → $comment_count comentarios de código"
        fi

        # Guardar por PR — usando archivos temporales para evitar
        # "Argument list too long" con JSON grandes en --argjson
        local pr_file="$OUTPUT_DIR/prs/pr_${pr_num}.json"
        jq -n \
            --argjson num "$pr_num" \
            --arg title "$pr_title" \
            --arg merged "$pr_merged_at" \
            --slurpfile rc /tmp/rda_rc_${pr_num}.json \
            --slurpfile ic /tmp/rda_ic_${pr_num}.json \
            '{
                pr_number: $num,
                title: $title,
                merged_at: $merged,
                review_comments: ($rc | first // []),
                issue_comments: ($ic | first // [])
            }' > "$pr_file"

        rm -f /tmp/rda_rc_${pr_num}.json /tmp/rda_ic_${pr_num}.json
    done

    print_ok "Extracción completa: $TOTAL_COMMENTS comentarios en $PRS_WITH_COMMENTS PRs"
}

# ─── Fase 3: Evaluar relevancia ───────────────────────────────
evaluate_comments() {
    print_step "Fase 3/4 — Evaluando relevancia en código actual..."

    local eval_output="$OUTPUT_DIR/reports/evaluation_${TIMESTAMP}.md"

    cat > "$eval_output" << HEADER
# 📋 Evaluación de Reviews Pendientes

- **Repositorio:** $REPO_FULL
- **Generado:** $(date)
- **PRs analizados:** $TOTAL_PRS
- **PRs con comentarios:** $PRS_WITH_COMMENTS
- **Total comentarios:** $TOTAL_COMMENTS

---

HEADER

    for pr_file in "$OUTPUT_DIR/prs"/pr_*.json; do
        [ -f "$pr_file" ] || continue

        local pr_num pr_title pr_merged
        pr_num=$(jq -r '.pr_number' "$pr_file")
        pr_title=$(jq -r '.title' "$pr_file")
        pr_merged=$(jq -r '.merged_at' "$pr_file")

        local comment_count
        comment_count=$(jq '.review_comments | length' "$pr_file")
        [ "$comment_count" -eq 0 ] && continue

        echo "" >> "$eval_output"
        echo "## PR #$pr_num — $pr_title" >> "$eval_output"
        echo "**Mergeado:** $pr_merged" >> "$eval_output"
        echo "" >> "$eval_output"

        # Evaluar cada review comment
        jq -c '.review_comments[]' "$pr_file" | while read -r comment; do
            local file line body user created diff_hunk
            file=$(echo "$comment"      | jq -r '.path // "desconocido"')
            line=$(echo "$comment"      | jq -r '.line // .original_line // "?"')
            body=$(echo "$comment"      | jq -r '.body')
            user=$(echo "$comment"      | jq -r '.user.login')
            created=$(echo "$comment"   | jq -r '.created_at')
            diff_hunk=$(echo "$comment" | jq -r '.diff_hunk // ""')

            echo "### 📄 \`$file\` — Línea $line" >> "$eval_output"
            echo "" >> "$eval_output"
            echo "| Campo | Valor |" >> "$eval_output"
            echo "|---|---|" >> "$eval_output"
            echo "| Autor | @$user |" >> "$eval_output"
            echo "| Fecha | $created |" >> "$eval_output"
            echo "" >> "$eval_output"
            echo "**Comentario:**" >> "$eval_output"
            echo "" >> "$eval_output"
            echo "> $(echo "$body" | head -5)" >> "$eval_output"
            echo "" >> "$eval_output"

            # ── Verificar si el archivo existe actualmente ──
            if [ -f "$file" ]; then
                FILES_EXIST=$((FILES_EXIST + 1)) 2>/dev/null || true
                echo "- ✅ **Archivo existe en el código actual**" >> "$eval_output"

                # Mostrar código actual en esa línea
                if [[ "$line" =~ ^[0-9]+$ ]]; then
                    local ctx_start ctx_end
                    ctx_start=$(( line > 3 ? line - 3 : 1 ))
                    ctx_end=$(( line + 3 ))
                    local current_code
                    current_code=$(sed -n "${ctx_start},${ctx_end}p" "$file" 2>/dev/null || echo "(no se pudo leer)")

                    echo "" >> "$eval_output"
                    echo "<details>" >> "$eval_output"
                    echo "<summary>👀 Código actual (líneas $ctx_start–$ctx_end)</summary>" >> "$eval_output"
                    echo "" >> "$eval_output"
                    echo '```' >> "$eval_output"
                    echo "$current_code" >> "$eval_output"
                    echo '```' >> "$eval_output"
                    echo "" >> "$eval_output"
                    echo "</details>" >> "$eval_output"
                fi
            else
                FILES_MISSING=$((FILES_MISSING + 1)) 2>/dev/null || true
                echo "- ❌ **Archivo NO existe** (puede haber sido renombrado/eliminado)" >> "$eval_output"

                # Intentar buscar archivo similar
                local basename
                basename=$(basename "$file")
                local found_files
                found_files=$(find . \
                    -name "$basename" \
                    -not -path "./.git/*" \
                    -not -path "./node_modules/*" \
                    2>/dev/null | head -3)

                if [ -n "$found_files" ]; then
                    echo "  - 🔍 Posibles archivos relacionados encontrados:" >> "$eval_output"
                    while IFS= read -r found; do
                        echo "    - \`$found\`" >> "$eval_output"
                    done <<< "$found_files"
                fi
            fi

            # ── Snippet del diff original para contexto ──
            if [ -n "$diff_hunk" ]; then
                echo "" >> "$eval_output"
                echo "<details>" >> "$eval_output"
                echo "<summary>🔀 Diff original del PR</summary>" >> "$eval_output"
                echo "" >> "$eval_output"
                echo '```diff' >> "$eval_output"
                echo "$diff_hunk" | head -20 >> "$eval_output"
                echo '```' >> "$eval_output"
                echo "" >> "$eval_output"
                echo "</details>" >> "$eval_output"
            fi

            # ── Checklist de acción manual ──
            echo "" >> "$eval_output"
            echo "**🎯 Evaluación (completar manualmente):**" >> "$eval_output"
            echo "" >> "$eval_output"
            echo "- [ ] El problema descrito **sigue siendo válido**" >> "$eval_output"
            echo "- [ ] Requiere acción / fix" >> "$eval_output"
            echo "- [ ] Ya fue corregido en commits posteriores" >> "$eval_output"
            echo "- [ ] Ya no aplica (código refactorizado / feature eliminada)" >> "$eval_output"
            echo "" >> "$eval_output"
            echo "**Prioridad:** ⬜ Alta &nbsp;&nbsp; ⬜ Media &nbsp;&nbsp; ⬜ Baja" >> "$eval_output"
            echo "" >> "$eval_output"
            echo "---" >> "$eval_output"
            echo "" >> "$eval_output"
        done
    done

    print_ok "Evaluación generada: $eval_output"
    echo "$eval_output"
}

# ─── Fase 4: Generar reporte ejecutivo ────────────────────────
generate_report() {
    print_step "Fase 4/4 — Generando reporte ejecutivo..."

    local report="$OUTPUT_DIR/reports/executive_report_${TIMESTAMP}.md"

    cat > "$report" << REPORT
# 📊 Reporte Ejecutivo — Deuda Técnica de Reviews

- **Repositorio:** $REPO_FULL
- **Generado:** $(date)
- **Rama base:** $BASE_BRANCH

---

## 📈 Resumen General

| Métrica | Valor |
|---|---|
| PRs analizados | $TOTAL_PRS |
| PRs con comentarios de código | $PRS_WITH_COMMENTS |
| Total comentarios encontrados | $TOTAL_COMMENTS |

---

## 🗂️ PRs con Más Comentarios Pendientes

REPORT

    # Top PRs por número de comentarios
    for pr_file in "$OUTPUT_DIR/prs"/pr_*.json; do
        [ -f "$pr_file" ] || continue
        local count pr_num pr_title
        count=$(jq '.review_comments | length' "$pr_file")
        pr_num=$(jq -r '.pr_number' "$pr_file")
        pr_title=$(jq -r '.title' "$pr_file")
        [ "$count" -eq 0 ] && continue
        echo "| #$pr_num | $pr_title | $count comentarios |" >> "$report"
    done

    cat >> "$report" << FOOTER

---

## 📋 Plan de Acción Sugerido

\`\`\`
1. Revisar evaluation_${TIMESTAMP}.md y completar los checkboxes
2. Clasificar cada comentario: válido / ya corregido / no aplica
3. Para los válidos: crear issues con label 'tech-debt'
4. Aplicar fixes en rama dedicada: fix/pending-reviews-${TIMESTAMP}
5. PR de cierre que referencia todos los issues
\`\`\`

## 📁 Archivos Generados

\`\`\`
$OUTPUT_DIR/
├── merged_prs.json              ← Lista de PRs analizados
├── prs/
│   └── pr_NNN.json              ← Comentarios por PR
└── reports/
    ├── evaluation_${TIMESTAMP}.md   ← Evaluación detallada (COMPLETAR)
    └── executive_report_${TIMESTAMP}.md  ← Este reporte
\`\`\`

---
*Generado por review-debt-analyzer.sh*
FOOTER

    print_ok "Reporte ejecutivo: $report"
}

# ─── Opcional: Crear GitHub Issues ───────────────────────────
create_github_issues() {
    print_step "Creando GitHub Issues para reviews pendientes..."

    local issues_created=0

    for pr_file in "$OUTPUT_DIR/prs"/pr_*.json; do
        [ -f "$pr_file" ] || continue

        local pr_num pr_title
        pr_num=$(jq -r '.pr_number' "$pr_file")
        pr_title=$(jq -r '.title' "$pr_file")
        local comment_count
        comment_count=$(jq '.review_comments | length' "$pr_file")
        [ "$comment_count" -eq 0 ] && continue

        # Construir body del issue
        local issue_body
        issue_body="## Review pendiente de PR #$pr_num\n\n"
        issue_body+="**Título original:** $pr_title\n\n"
        issue_body+="**Comentarios encontrados:**\n\n"

        while IFS= read -r comment; do
            local file body user
            file=$(echo "$comment" | jq -r '.path // "desconocido"')
            body=$(echo "$comment" | jq -r '.body' | head -3)
            user=$(echo "$comment" | jq -r '.user.login')

            issue_body+="- \`$file\` — @$user: $(echo "$body" | head -c 100)...\n"
        done < <(jq -c '.review_comments[]' "$pr_file")

        issue_body+="\n**Acción requerida:** Evaluar si estos comentarios siguen siendo válidos.\n"
        issue_body+="\n*Generado automáticamente por review-debt-analyzer.sh*"

        local issue_url
        issue_url=$(gh issue create \
            --title "tech-debt: Reviews pendientes de PR #$pr_num" \
            --body "$(printf '%b' "$issue_body")" \
            --label "tech-debt" \
            2>/dev/null || echo "")

        if [ -n "$issue_url" ]; then
            print_ok "Issue creado: $issue_url"
            issues_created=$((issues_created + 1))
        else
            print_warn "No se pudo crear issue para PR #$pr_num (¿existe el label 'tech-debt'?)"
        fi
    done

    print_ok "$issues_created issues creados"
}

# ─── Opcional: Crear rama de fixes ───────────────────────────
create_fix_branch() {
    print_step "Creando rama para aplicar fixes..."

    local branch="fix/pending-reviews-${TIMESTAMP}"

    if git rev-parse --git-dir &>/dev/null; then
        git fetch origin "$BASE_BRANCH" --quiet 2>/dev/null || true
        git checkout "$BASE_BRANCH" --quiet
        git pull origin "$BASE_BRANCH" --quiet 2>/dev/null || true
        git checkout -b "$branch" --quiet

        print_ok "Rama creada: $branch"
        print_info "Cuando termines los fixes:"
        echo ""
        echo -e "    ${CYAN}git add -A${NC}"
        echo -e "    ${CYAN}git commit -m 'fix: reviews pendientes de PRs antiguos'${NC}"
        echo -e "    ${CYAN}git push origin $branch${NC}"
        echo -e "    ${CYAN}gh pr create --title 'fix: Reviews pendientes' --body 'Cierra deuda técnica de reviews antiguos'${NC}"
        echo ""
    else
        print_warn "No estás en un repositorio Git local. Omitiendo creación de rama."
    fi
}

# ─── Resumen final ───────────────────────────────────────────
print_summary() {
    echo ""
    echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║              ✅ Auditoría Completa               ║${NC}"
    echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}PRs analizados:${NC}           $TOTAL_PRS"
    echo -e "  ${BOLD}PRs con comentarios:${NC}      $PRS_WITH_COMMENTS"
    echo -e "  ${BOLD}Total comentarios:${NC}        $TOTAL_COMMENTS"
    echo ""
    echo -e "  ${BOLD}Archivos que aún existen:${NC} $FILES_EXIST"
    echo -e "  ${BOLD}Archivos no encontrados:${NC}  $FILES_MISSING"
    echo ""
    echo -e "  ${BOLD}Reportes generados en:${NC}    ./$OUTPUT_DIR/reports/"
    echo ""
    echo -e "  ${YELLOW}📌 Próximo paso:${NC}"
    echo -e "     Abre ${CYAN}$OUTPUT_DIR/reports/evaluation_${TIMESTAMP}.md${NC}"
    echo -e "     y completa los checkboxes de cada comentario."
    echo ""
}

# ─── MAIN ────────────────────────────────────────────────────
main() {
    print_header
    check_deps
    setup_output
    get_repo_info
    fetch_merged_prs
    fetch_pr_comments
    evaluate_comments
    generate_report

    if [ "$CREATE_ISSUES" = true ]; then
        create_github_issues
    fi

    if [ "$CREATE_FIX_BRANCH" = true ]; then
        create_fix_branch
    fi

    print_summary
}

main "$@"

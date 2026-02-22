#!/bin/bash
set -e

# Variables de entorno esperadas:
# - GIT_BRANCH: Rama del PR a testear
# - GITHUB_TOKEN: Token para clonar
# - TASK_ID: ID del task (para reporting)
# - GITHUB_REPO: Repositorio (ej: user/repo)

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "========================================"
echo "🚀 PRISM Test Container"
echo "Task: $TASK_ID"
echo "Branch: $GIT_BRANCH"
echo "========================================"

# Validar variables requeridas
if [ -z "$GIT_BRANCH" ]; then
    log_error "GIT_BRANCH no está definido"
    exit 1
fi

if [ -z "$GITHUB_REPO" ]; then
    log_error "GITHUB_REPO no está definido"
    exit 1
fi

# 1. Clona el repositorio
log_info "📦 Clonando repositorio..."
REPO_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git"

if ! git clone --depth 1 --branch "$GIT_BRANCH" "$REPO_URL" . 2>&1; then
    log_error "Fallo al clonar repositorio"
    exit 1
fi

log_success "Repositorio clonado"

# 2. Instala dependencias
log_info "⬇️ Instalando dependencias con uv..."
if ! uv sync 2>&1; then
    log_error "Fallo al instalar dependencias"
    exit 1
fi

log_success "Dependencias instaladas"

# 3. Instala playwright browsers
log_info "🎭 Instalando browsers de Playwright..."
if ! uv run playwright install chromium 2>&1; then
    log_warning "Fallo al instalar browsers (puede ser opcional)"
fi

# 4. Inicia web terminal en background
log_info "🖥️ Iniciando web terminal (ttyd)..."
ttyd -p 7681 -W bash &
TTYD_PID=$!

# Verifica que ttyd inició
sleep 2
if ! kill -0 $TTYD_PID 2>/dev/null; then
    log_error "Fallo al iniciar ttyd"
    exit 1
fi

log_success "Web terminal iniciado en puerto 7681"

# 5. Ejecuta quality gates
log_info "🔍 Ejecutando quality gates..."

# Configurar variables de entorno para los gates
export PRISM_TASK_ID="$TASK_ID"
export PRISM_BRANCH="$GIT_BRANCH"

# Ejecutar quality gates
if uv run python -m prism.pipeline.quality_gates run --task-id "$TASK_ID" 2>&1; then
    log_success "Todos los quality gates pasaron"
    
    # Actualiza estado del contenedor
    echo "ready_for_qa" > /tmp/prism_status
    
    # Notificar a Flux (si hay endpoint configurado)
    if [ -n "$FLUX_WEBHOOK_URL" ]; then
        log_info "Notificando a Flux..."
        curl -X POST "$FLUX_WEBHOOK_URL/container-ready" \
            -H "Content-Type: application/json" \
            -d "{\"task_id\": \"$TASK_ID\", \"status\": \"ready\", \"container\": \"$(hostname)\"}" \
            2>/dev/null || log_warning "No se pudo notificar a Flux"
    fi
else
    log_error "Quality gates fallaron"
    echo "failed" > /tmp/prism_status
    
    # Mantener contenedor vivo por 30 min para debugging
    log_warning "Contenedor se mantendrá vivo por 30 minutos para debugging"
    sleep 1800
    exit 1
fi

# 6. Mantiene contenedor vivo hasta que QA termine
echo ""
echo "========================================"
log_success "✅ Contenedor listo para QA review"
echo "========================================"
echo ""
echo "Web Terminal: http://localhost:7681"
echo "Task ID: $TASK_ID"
echo ""
echo "⏳ Esperando aprobación de QA..."
echo "   (Escribe 'exit' para salir del terminal)"
echo ""

# Loop principal: verifica estado cada 10 segundos
COUNTER=0
MAX_WAIT=14400  # 4 horas máximo

while [ $COUNTER -lt $MAX_WAIT ]; do
    # Verifica si hay archivo de estado de QA
    if [ -f "/tmp/qa_decision" ]; then
        DECISION=$(cat /tmp/qa_decision)
        
        if [ "$DECISION" = "approved" ]; then
            log_success "✅ QA aprobó el PR"
            
            # Notificar aprobación
            if [ -n "$FLUX_WEBHOOK_URL" ]; then
                curl -X POST "$FLUX_WEBHOOK_URL/qa-approved" \
                    -H "Content-Type: application/json" \
                    -d "{\"task_id\": \"$TASK_ID\", \"status\": \"approved\"}" \
                    2>/dev/null || true
            fi
            
            # Esperar 30 minutos más y luego salir
            log_info "Contenedor se mantendrá vivo por 30 minutos más..."
            sleep 1800
            exit 0
            
        elif [ "$DECISION" = "rejected" ]; then
            log_error "❌ QA rechazó el PR"
            
            # Notificar rechazo
            if [ -n "$FLUX_WEBHOOK_URL" ]; then
                curl -X POST "$FLUX_WEBHOOK_URL/qa-rejected" \
                    -H "Content-Type: application/json" \
                    -d "{\"task_id\": \"$TASK_ID\", \"status\": \"rejected\"}" \
                    2>/dev/null || true
            fi
            
            # Mantener contenedor vivo por 30 min para debugging
            log_warning "Contenedor se mantendrá vivo por 30 minutos para debugging"
            sleep 1800
            exit 1
        fi
    fi
    
    # Verifica si ttyd sigue corriendo
    if ! kill -0 $TTYD_PID 2>/dev/null; then
        log_error "Web terminal (ttyd) se detuvo"
        exit 1
    fi
    
    sleep 10
    COUNTER=$((COUNTER + 10))
done

# Timeout
log_warning "⏰ Timeout: 4 horas sin decisión de QA"
exit 0

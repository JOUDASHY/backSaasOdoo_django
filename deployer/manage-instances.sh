#!/bin/bash
#
# Gestion des instances Odoo (copie du script racine) placé dans saas_backend/deployer
# Usage: ./manage-instances.sh <action> [nom_instance]
# Actions: list, start, stop, restart, logs, remove, status
#
set -e

ACTION="${1}"
INSTANCE_NAME="${2}"
FORCE_FLAG="${3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTANCES_DIR="${SCRIPT_DIR}/instances"

if [ -z "${ACTION}" ]; then
    echo "❌ Erreur: Vous devez fournir une action"
    echo ""
    echo "Usage: $0 <action> [nom_instance]"
    echo ""
    echo "Actions disponibles:"
    echo "  list              - Lister toutes les instances"
    echo "  start <nom>       - Démarrer une instance"
    echo "  stop <nom>        - Arrêter une instance"
    echo "  restart <nom>     - Redémarrer une instance"
    echo "  logs <nom>        - Voir les logs d'une instance"
    echo "  remove <nom>      - Supprimer une instance (avec confirmation)"
    echo "  status <nom>      - Voir le statut d'une instance"
    exit 1
fi

list_instances() {
    echo "📋 Instances disponibles:"
    echo ""
    if [ ! -d "${INSTANCES_DIR}" ] || [ -z "$(ls -A ${INSTANCES_DIR} 2>/dev/null)" ]; then
        echo "   Aucune instance trouvée"
        return
    fi
    
    for instance in "${INSTANCES_DIR}"/*; do
        if [ -d "${instance}" ]; then
            name=$(basename "${instance}")
            if docker ps -a --format "{{.Names}}" | grep -q "odoo_${name}"; then
                if docker ps --format "{{.Names}}" | grep -q "odoo_${name}"; then
                    status="🟢 En cours"
                    port=$(docker port "odoo_${name}" 2>/dev/null | grep "8069" | cut -d: -f2 || echo "N/A")
                else
                    status="🔴 Arrêtée"
                    port="N/A"
                fi
                echo "   - ${name}: ${status} (Port: ${port})"
            else
                echo "   - ${name}: ⚪ Non déployée"
            fi
        fi
    done
}

get_instance_info() {
    local name="${1}"
    if [ -z "${name}" ]; then
        echo "❌ Erreur: Nom d'instance requis"
        exit 1
    fi
    
    local instance_dir="${INSTANCES_DIR}/${name}"
    if [ ! -d "${instance_dir}" ]; then
        echo "❌ Erreur: Instance '${name}' non trouvée"
        exit 1
    fi
    
    echo "${instance_dir}"
}

start_instance() {
    local instance_dir=$(get_instance_info "${INSTANCE_NAME}")
    echo "🚀 Démarrage de l'instance: ${INSTANCE_NAME}"
    cd "${instance_dir}"
    docker compose up -d
    echo "✅ Instance démarrée"
    echo "🌐 URL: http://localhost:$(docker port "odoo_${INSTANCE_NAME}" 2>/dev/null | grep "8069" | cut -d: -f2 || echo "N/A")"
}

stop_instance() {
    local instance_dir=$(get_instance_info "${INSTANCE_NAME}")
    echo "🛑 Arrêt de l'instance: ${INSTANCE_NAME}"
    cd "${instance_dir}"
    docker compose down
    echo "✅ Instance arrêtée"
}

restart_instance() {
    local instance_dir=$(get_instance_info "${INSTANCE_NAME}")
    echo "🔄 Redémarrage de l'instance: ${INSTANCE_NAME}"
    cd "${instance_dir}"
    docker compose restart
    echo "✅ Instance redémarrée"
}

show_logs() {
    local instance_dir=$(get_instance_info "${INSTANCE_NAME}")
    echo "📄 Logs de l'instance: ${INSTANCE_NAME}"
    echo "   (Appuyez sur Ctrl+C pour quitter)"
    echo ""
    docker logs -f "odoo_${INSTANCE_NAME}"
}

show_status() {
    local instance_dir=$(get_instance_info "${INSTANCE_NAME}")
    echo "📊 Statut de l'instance: ${INSTANCE_NAME}"
    echo ""
    
    if docker ps --format "{{.Names}}" | grep -q "odoo_${INSTANCE_NAME}"; then
        echo "🟢 Statut: En cours d'exécution"
        echo ""
        echo "Conteneurs:"
        docker ps --filter "name=${INSTANCE_NAME}" --format "  - {{.Names}}: {{.Status}}"
        echo ""
        echo "Ports:"
        docker port "odoo_${INSTANCE_NAME}" 2>/dev/null | sed 's/^/  - /' || echo "  Aucun port exposé"
        echo ""
        echo "Volumes:"
        docker volume ls --filter "name=${INSTANCE_NAME}" --format "  - {{.Name}}"
    else
        echo "🔴 Statut: Arrêtée ou non déployée"
    fi
}

remove_instance() {
    local instance_dir=$(get_instance_info "${INSTANCE_NAME}")
    echo "⚠️  Suppression de l'instance: ${INSTANCE_NAME}"
    echo ""

    # Si le script est appelé avec le 3ème argument \"--force\", on ne pose pas la question
    if [ "${FORCE_FLAG}" != "--force" ]; then
        read -p "Voulez-vous vraiment supprimer cette instance ? (o/N) " confirm
        if [[ ! "${confirm}" =~ ^[oO]$ ]]; then
            echo "Abandon."
            exit 0
        fi
    fi
    
    cd "${instance_dir}"
    docker compose down
    docker volume rm "${INSTANCE_NAME}_db_data" "${INSTANCE_NAME}_data" 2>/dev/null || true
    cd "${SCRIPT_DIR}"
    rm -rf "${instance_dir}"
    echo "✅ Instance supprimée"
}

case "${ACTION}" in
    list)
        list_instances
        ;;
    start)
        start_instance
        ;;
    stop)
        stop_instance
        ;;
    restart)
        restart_instance
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    remove)
        remove_instance
        ;;
    *)
        echo "❌ Action inconnue: ${ACTION}"
        exit 1
        ;;
esac


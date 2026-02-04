#!/bin/bash
#
# Ce fichier est désormais un wrapper inutile (le vrai script est dans deployer/).
# On le laisse pour compatibilité, mais il redirige vers deployer/manage-instances.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/deployer/manage-instances.sh" "$@"


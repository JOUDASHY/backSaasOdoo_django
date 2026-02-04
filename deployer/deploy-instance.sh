#!/bin/bash
#
# Déploiement d'une instance Odoo (copie du script racine) placé dans saas_backend/deployer
# Usage: ./deploy-instance.sh <nom_instance> [domaine] [port] [odoo_version] [admin_password] [modules_csv]
#
set -e

INSTANCE_NAME="${1}"
DOMAIN="${2:-${INSTANCE_NAME}.localhost}"
PORT="${3:-8070}"
ODOO_VERSION="${4:-18}"
ADMIN_PASSWORD="${5:-admin}"
MODULES="${6:-base}"
DB_NAME="${INSTANCE_NAME}"
DB_USER="${INSTANCE_NAME}"
DB_PASSWORD="$(openssl rand -hex 16)"

# Répertoire absolu du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${INSTANCE_NAME}" ]; then
    echo "❌ Erreur: Vous devez fournir un nom d'instance"
    echo "Usage: $0 <nom_instance> [domaine]"
    exit 1
fi

echo "🚀 Déploiement de l'instance Odoo: ${INSTANCE_NAME}"
echo "📋 Configuration:"
echo "   - Nom: ${INSTANCE_NAME}"
echo "   - Domaine: ${DOMAIN}"
echo "   - Port: ${PORT}"
echo "   - Base de données: ${DB_NAME}"
echo ""

# Créer le répertoire pour l'instance (local à saas_backend/deployer)
INSTANCE_DIR="${SCRIPT_DIR}/instances/${INSTANCE_NAME}"
mkdir -p "${INSTANCE_DIR}"

# Créer le module de restriction des modules
MODULE_RESTRICTION_DIR="${INSTANCE_DIR}/addons/saas_module_restriction"
mkdir -p "${MODULE_RESTRICTION_DIR}/models"
mkdir -p "${MODULE_RESTRICTION_DIR}/views"
mkdir -p "${MODULE_RESTRICTION_DIR}/security"

# __manifest__.py
cat > "${MODULE_RESTRICTION_DIR}/__manifest__.py" <<'MANIFEST_EOF'
# -*- coding: utf-8 -*-
{
    'name': 'SaaS Module Restriction',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Restrict module installation based on plan allowed modules',
    'description': """
        This module restricts the installation of modules based on a whitelist
        defined in environment variable ALLOWED_MODULES.
        Only modules in the whitelist can be installed by users.
    """,
    'author': 'Odoo SaaS Platform',
    'depends': ['base'],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
    'data': [
        'views/ir_module_module_views.xml',
        'views/upgrade_wizard_views.xml',
        'security/ir.model.access.csv',
    ],
}
MANIFEST_EOF

# __init__.py principal
cat > "${MODULE_RESTRICTION_DIR}/__init__.py" <<'INIT_EOF'
# -*- coding: utf-8 -*-
from . import models
INIT_EOF

# __init__.py models
cat > "${MODULE_RESTRICTION_DIR}/models/__init__.py" <<'MODELS_INIT_EOF'
# -*- coding: utf-8 -*-
from . import ir_module_module
from . import upgrade_wizard
MODELS_INIT_EOF

# Modèle de restriction
cat > "${MODULE_RESTRICTION_DIR}/models/ir_module_module.py" <<'MODEL_EOF'
# -*- coding: utf-8 -*-

import os
import logging
from odoo import models, api, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    can_install = fields.Boolean(
        string='Can Install',
        compute='_compute_can_install',
        help='Whether this module can be installed based on the plan restrictions'
    )
    needs_upgrade = fields.Boolean(
        string='Needs Upgrade',
        compute='_compute_needs_upgrade',
        help='True when the module is not allowed by the current plan'
    )

    def _get_allowed_modules(self):
        """Get list of allowed modules from environment variable"""
        allowed_str = os.environ.get('ALLOWED_MODULES', '')
        if not allowed_str:
            return None
        
        allowed_list = [m.strip() for m in allowed_str.split(',') if m.strip()]
        if 'base' not in allowed_list:
            allowed_list.append('base')
        if 'web' not in allowed_list:
            allowed_list.append('web')
        
        return set(allowed_list)

    @api.depends('name', 'state')
    def _compute_can_install(self):
        """Compute whether the module can be installed based on plan restrictions"""
        allowed_modules = self._get_allowed_modules()
        if allowed_modules is None:
            # No restriction configured, allow all
            for module in self:
                module.can_install = True
            return
        
        for module in self:
            # Only show install button if module is not installed and is in allowed list
            module.can_install = module.state == 'uninstalled' and module.name in allowed_modules

    @api.depends('name', 'state')
    def _compute_needs_upgrade(self):
        allowed_modules = self._get_allowed_modules()
        if allowed_modules is None:
            for module in self:
                module.needs_upgrade = False
            return

        for module in self:
            module.needs_upgrade = module.state == 'uninstalled' and module.name not in allowed_modules

    def _get_upgrade_url(self, module_name: str):
        """
        URL vers la page 'upgrade plan' de ton portail SaaS.
        Configurable via SAAS_PORTAL_UPGRADE_URL.
        """
        base_url = os.environ.get("SAAS_PORTAL_UPGRADE_URL", "http://localhost:3000/dashboard/subscription")
        sep = "&" if "?" in base_url else "?"
        return f"{base_url}{sep}module={module_name}"

    def action_request_upgrade(self):
        """Bouton UI: ouvre une modale de confirmation (wizard)."""
        self.ensure_one()
        wizard = self.env["saas.module.upgrade.wizard"].create_for_module(self.name)
        lang = self.env.context.get("lang") or self.env.user.lang or "en_US"
        window_title = "Mettre à niveau le forfait" if (lang and (lang.startswith("fr") or lang == "fr_FR")) else "Upgrade plan"
        return {
            "type": "ir.actions.act_window",
            "name": window_title,
            "res_model": "saas.module.upgrade.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def _check_module_allowed(self, module_name):
        """Check if a module is in the allowed list"""
        allowed_modules = self._get_allowed_modules()
        if allowed_modules is None:
            return True
        return module_name in allowed_modules

    def button_immediate_install(self):
        """Override install to check if module is allowed"""
        for module in self:
            if not self._check_module_allowed(module.name):
                allowed_modules = self._get_allowed_modules()
                if allowed_modules:
                    allowed_list = sorted(list(allowed_modules))
                    raise UserError(_(
                        "Module '%s' is not allowed in your plan.\n\n"
                        "Allowed modules: %s\n\n"
                        "Please contact support to upgrade your plan if you need this module."
                    ) % (module.name, ', '.join(allowed_list)))
        return super().button_immediate_install()

    def button_install(self):
        """Override install (non-immediate) to check if module is allowed"""
        for module in self:
            if not self._check_module_allowed(module.name):
                allowed_modules = self._get_allowed_modules()
                if allowed_modules:
                    allowed_list = sorted(list(allowed_modules))
                    raise UserError(_(
                        "Module '%s' is not allowed in your plan.\n\n"
                        "Allowed modules: %s\n\n"
                        "Please contact support to upgrade your plan if you need this module."
                    ) % (module.name, ', '.join(allowed_list)))
        return super().button_install()
MODEL_EOF

# Wizard
cat > "${MODULE_RESTRICTION_DIR}/models/upgrade_wizard.py" <<'WIZ_EOF'
# -*- coding: utf-8 -*-

import os

from odoo import api, fields, models, _


class SaasModuleUpgradeWizard(models.TransientModel):
    _name = "saas.module.upgrade.wizard"
    _description = "SaaS: Upgrade Plan Confirmation"

    module_name = fields.Char(string="Module Name", readonly=True)
    title = fields.Char(string="Upgrade required", readonly=True, compute="_compute_title_explanation", store=False)
    explanation = fields.Text(readonly=True, compute="_compute_title_explanation", store=False)
    upgrade_url = fields.Char(readonly=True)

    @api.model
    def _get_upgrade_base_url(self):
        return os.environ.get("SAAS_PORTAL_UPGRADE_URL", "http://localhost:3000/dashboard/subscription")

    @api.model
    def _get_texts_for_lang(self, lang):
        if lang and (lang.startswith("fr") or lang == "fr_FR"):
            return {
                "title": "Mise à niveau requise",
                "explanation": (
                    "Ce module n'est pas inclus dans votre forfait actuel.\\n\\n"
                    "Pour l'activer, veuillez mettre à niveau votre abonnement. "
                    "Après la mise à niveau, vous pourrez revenir et activer le module."
                ),
            }
        return {
            "title": "Upgrade required",
            "explanation": (
                "This module is not included in your current plan.\\n\\n"
                "To activate it, please upgrade your subscription. "
                "After upgrading, you can come back and activate the module."
            ),
        }

    @api.depends("module_name")
    def _compute_title_explanation(self):
        for w in self:
            lang = w.env.context.get("lang") or w.env.user.lang or "en_US"
            texts = w._get_texts_for_lang(lang)
            w.title = texts["title"]
            w.explanation = texts["explanation"]

    @api.model
    def create_for_module(self, module_name: str):
        base_url = self._get_upgrade_base_url()
        sep = "&" if "?" in base_url else "?"
        upgrade_url = f"{base_url}{sep}module={module_name}"
        return self.create(
            {
                "module_name": module_name,
                "upgrade_url": upgrade_url,
            }
        )

    def action_confirm_upgrade(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": self.upgrade_url, "target": "new"}

    def action_cancel(self):
        return {"type": "ir.actions.act_window_close"}
WIZ_EOF

# Traductions (FR) — format Odoo
mkdir -p "${MODULE_RESTRICTION_DIR}/i18n"
cat > "${MODULE_RESTRICTION_DIR}/i18n/fr.po" <<'FR_PO_EOF'
# Translation of Odoo Server.
# This file contains the translation of the following modules:
# 	* saas_module_restriction
#. module: saas_module_restriction
msgid ""
msgstr ""
"Project-Id-Version: Odoo Server 18.0\n"
"POT-Creation-Date: 2026-02-02 00:00+0000\n"
"PO-Revision-Date: 2026-02-02 00:00+0000\n"
"Language: fr\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=2; plural=(n > 1);\n"

#. module: saas_module_restriction
#: code:addons/saas_module_restriction/models/ir_module_module.py:0
msgid "Upgrade plan"
msgstr "Mettre à niveau le forfait"

#. module: saas_module_restriction
#: code:addons/saas_module_restriction/models/upgrade_wizard.py:0
msgid "Upgrade required"
msgstr "Mise à niveau requise"

#. module: saas_module_restriction
#: code:addons/saas_module_restriction/models/upgrade_wizard.py:0
msgid ""
"This module is not included in your current plan.\n"
"\n"
"To activate it, please upgrade your subscription. After upgrading, you can "
"come back and activate the module."
msgstr ""
"Ce module n’est pas inclus dans votre forfait actuel.\n"
"\n"
"Pour l’activer, veuillez mettre à niveau votre abonnement. Après la mise à "
"niveau, vous pourrez revenir et activer le module."

#. module: saas_module_restriction
#: model:ir.model.fields,field_description:saas_module_restriction.field_saas_module_upgrade_wizard__module_name
msgid "Module Name"
msgstr "Nom du module"

#. module: saas_module_restriction
#: model:ir.model.fields,field_description:saas_module_restriction.field_saas_module_upgrade_wizard__title
msgid "Upgrade required"
msgstr "Mise à niveau requise"

#. module: saas_module_restriction
#: model_terms:ir.ui.view,arch_db:saas_module_restriction.view_module_form_saas_restrict
msgid "Upgrade plan"
msgstr "Mettre à niveau le forfait"

#. module: saas_module_restriction
#: model_terms:ir.ui.view,arch_db:saas_module_restriction.view_module_kanban_saas_restrict
msgid "Upgrade plan"
msgstr "Mettre à niveau le forfait"

#. module: saas_module_restriction
#: model_terms:ir.ui.view,arch_db:saas_module_restriction.view_saas_module_upgrade_wizard_form
msgid "Upgrade plan"
msgstr "Mettre à niveau le forfait"

#. module: saas_module_restriction
#: model_terms:ir.ui.view,arch_db:saas_module_restriction.view_saas_module_upgrade_wizard_form
msgid "Upgrade now"
msgstr "Mettre à niveau maintenant"

#. module: saas_module_restriction
#: model_terms:ir.ui.view,arch_db:saas_module_restriction.view_saas_module_upgrade_wizard_form
msgid "Cancel"
msgstr "Annuler"
FR_PO_EOF

# Vues XML pour masquer Installer et afficher "Mettre à niveau le forfait"
cat > "${MODULE_RESTRICTION_DIR}/views/ir_module_module_views.xml" <<'VIEWS_EOF'
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_module_form_saas_restrict" model="ir.ui.view">
        <field name="name">ir.module.module.form.saas.restrict</field>
        <field name="model">ir.module.module</field>
        <field name="inherit_id" ref="base.module_form"/>
        <field name="arch" type="xml">
            <xpath expr="//button[@name='button_immediate_install']" position="attributes">
                <attribute name="invisible">to_buy or state != 'uninstalled' or not can_install</attribute>
            </xpath>
            <xpath expr="//button[@name='button_immediate_install']" position="after">
                <button name="action_request_upgrade"
                        type="object"
                        string="Mettre à niveau le forfait"
                        class="btn-primary"
                        invisible="not needs_upgrade"/>
            </xpath>
        </field>
    </record>

    <record id="view_module_kanban_saas_restrict" model="ir.ui.view">
        <field name="name">ir.module.module.kanban.saas.restrict</field>
        <field name="model">ir.module.module</field>
        <field name="inherit_id" ref="base.module_view_kanban"/>
        <field name="arch" type="xml">
            <xpath expr="//button[@name='button_immediate_install']" position="attributes">
                <attribute name="invisible">to_buy or state != 'uninstalled' or not can_install</attribute>
            </xpath>
            <xpath expr="//button[@name='button_immediate_install']" position="after">
                <button name="action_request_upgrade"
                        type="object"
                        string="Mettre à niveau le forfait"
                        class="btn-primary"
                        invisible="not needs_upgrade"/>
            </xpath>
        </field>
    </record>
</odoo>
VIEWS_EOF

cat > "${MODULE_RESTRICTION_DIR}/views/upgrade_wizard_views.xml" <<'WIZ_VIEW_EOF'
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_saas_module_upgrade_wizard_form" model="ir.ui.view">
        <field name="name">saas.module.upgrade.wizard.form</field>
        <field name="model">saas.module.upgrade.wizard</field>
        <field name="arch" type="xml">
            <form string="Upgrade plan">
                <sheet>
                    <h2><field name="title" readonly="1"/></h2>
                    <group>
                        <field name="module_name" readonly="1"/>
                    </group>
                    <group>
                        <field name="explanation" readonly="1" nolabel="1"/>
                    </group>
                </sheet>
                <footer>
                    <button name="action_confirm_upgrade" type="object" class="btn-primary" string="Upgrade now"/>
                    <button name="action_cancel" type="object" class="btn-secondary" string="Cancel"/>
                </footer>
            </form>
        </field>
    </record>
</odoo>
WIZ_VIEW_EOF

cat > "${MODULE_RESTRICTION_DIR}/security/ir.model.access.csv" <<'ACCESS_EOF'
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_saas_module_upgrade_wizard,access_saas_module_upgrade_wizard,model_saas_module_upgrade_wizard,base.group_system,1,1,1,1
ACCESS_EOF

# docker-compose spécifique à l'instance
cat > "${INSTANCE_DIR}/docker-compose.yml" <<EOF
version: "3.8"

services:
  db_${INSTANCE_NAME}:
    image: postgres:16
    container_name: odoo_db_${INSTANCE_NAME}
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - ${INSTANCE_NAME}_db_data:/var/lib/postgresql/data
    networks:
      - odoo_network

  odoo_${INSTANCE_NAME}:
    image: odoo:${ODOO_VERSION}
    container_name: odoo_${INSTANCE_NAME}
    restart: unless-stopped
    depends_on:
      - db_${INSTANCE_NAME}
    environment:
      HOST: db_${INSTANCE_NAME}
      PORT: 5432
      USER: ${DB_USER}
      PASSWORD: ${DB_PASSWORD}
      PGDATABASE: ${DB_NAME}
      ALLOWED_MODULES: ${MODULES}
    ports:
      - "${PORT}:8069"
    volumes:
      - ${INSTANCE_NAME}_data:/var/lib/odoo
      - ${SCRIPT_DIR}/instances/${INSTANCE_NAME}/addons:/mnt/extra-addons
    networks:
      - odoo_network

volumes:
  ${INSTANCE_NAME}_db_data:
  ${INSTANCE_NAME}_data:

networks:
  odoo_network:
    external: true
EOF

# Créer le réseau Docker si nécessaire
docker network create odoo_network 2>/dev/null || true

echo "✅ Configuration créée dans ${INSTANCE_DIR}/docker-compose.yml"
echo ""
echo "🚀 Démarrage de l'instance..."
cd "${INSTANCE_DIR}"
docker compose up -d

echo "⏳ Attente du démarrage de la base de données..."
sleep 5

# Attendre que PostgreSQL soit prêt et initialiser Odoo avec les modules
echo "⏳ Initialisation de la base de données Odoo (Modules: ${MODULES})..."
MAX_RETRIES=30
RETRY=0
INIT_SUCCESS=false
while [ ${RETRY} -lt ${MAX_RETRIES} ]; do
    if docker exec odoo_${INSTANCE_NAME} odoo --stop-after-init -d ${DB_NAME} -r ${DB_USER} -w ${DB_PASSWORD} --db_host=db_${INSTANCE_NAME} --db_port=5432 -i ${MODULES} >/dev/null 2>&1; then
        echo "✅ Base de données initialisée avec succès!"
        echo "🔐 Configuration du mot de passe administrateur..."
        docker exec odoo_db_${INSTANCE_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "UPDATE res_users SET password='${ADMIN_PASSWORD}' WHERE id=2;" >/dev/null 2>&1
        INIT_SUCCESS=true
        break
    fi
    RETRY=$((RETRY + 1))
    if [ ${RETRY} -lt ${MAX_RETRIES} ]; then
        echo "   Tentative ${RETRY}/${MAX_RETRIES}..."
        sleep 2
    fi
done

if [ "${INIT_SUCCESS}" != "true" ]; then
    echo "⚠️  L'initialisation automatique a échoué. Initialisez manuellement:"
    echo "   docker exec odoo_${INSTANCE_NAME} odoo --stop-after-init -d ${DB_NAME} -r ${DB_USER} -w ${DB_PASSWORD} --db_host=db_${INSTANCE_NAME} --db_port=5432 -i base"
else
    echo "🔄 Redémarrage du conteneur Odoo..."
    docker restart odoo_${INSTANCE_NAME} >/dev/null 2>&1
    sleep 3
fi

echo ""
echo "✅ Instance déployée et prête!"
echo ""
echo "🔐 Informations de connexion:"
echo "   - Base de données: ${DB_NAME}"
echo "   - Utilisateur DB: ${DB_USER}"
echo "   - Mot de passe DB: ${DB_PASSWORD}"
echo "   - URL: http://localhost:${PORT}"
echo ""
echo "📝 Accédez à l'URL pour finaliser la configuration (créer votre compte admin)"
echo ""


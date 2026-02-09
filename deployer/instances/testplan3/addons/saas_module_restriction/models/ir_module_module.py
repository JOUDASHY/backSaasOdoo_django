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
            # Autoriser installation/activation seulement si le module est
            # 'uninstalled' ou 'to_buy' ET présent dans la liste autorisée.
            module.can_install = module.state in ('uninstalled', 'to_buy') and module.name in allowed_modules

    @api.depends('name', 'state')
    def _compute_needs_upgrade(self):
        allowed_modules = self._get_allowed_modules()
        if allowed_modules is None:
            for module in self:
                module.needs_upgrade = False
            return

        for module in self:
            # Demander une mise à niveau si le module est installable/activable
            # (uninstalled/to_buy) mais non inclus dans les modules autorisés.
            module.needs_upgrade = module.state in ('uninstalled', 'to_buy') and module.name not in allowed_modules

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
        """
        Override install to check if module is allowed.
        - Si autorisé: comportement normal d'Odoo.
        - Si NON autorisé: au lieu d'une erreur technique, on ouvre le wizard
          "Mettre à niveau le forfait" (un seul bouton côté UI: Activer).
        """
        for module in self:
            if not self._check_module_allowed(module.name):
                # Ouvrir directement le wizard d'upgrade pour ce module
                return module.action_request_upgrade()
        return super().button_immediate_install()

    def button_install(self):
        """
        Override install (non-immediate) pour la même logique que ci‑dessus.
        """
        for module in self:
            if not self._check_module_allowed(module.name):
                return module.action_request_upgrade()
        return super().button_install()

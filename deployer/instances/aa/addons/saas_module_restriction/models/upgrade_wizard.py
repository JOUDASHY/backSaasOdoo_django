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

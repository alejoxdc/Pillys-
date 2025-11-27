from odoo import models, fields, api, SUPERUSER_ID


class WhatsappTemplate(models.Model):
    _inherit = "whatsapp.template"

    create_server_action = fields.Boolean(string="Create Server Action")
    utm_campaign_id = fields.Many2one("utm.campaign", string="Campaign")

    def write(self, vals):
        res = super(WhatsappTemplate, self).write(vals)
        if vals.get("create_server_action"):
            self.create_whatsapp_server_action()
        return res

    def create_whatsapp_server_action(self):
        for record in self:
            # Define the server action values
            action_vals = {
                "name": "Send WhatsApp Message with template " + record.name,
                "model_id": record.model_id.id,
                "state": "code",
                "code": """
wa_tamplate = env["whatsapp.template"].browse(%s)
action = record._send_template(wa_tamplate)
                """ % record.id,
            }

            # Create the server action
            self.env["ir.actions.server"].create(action_vals)

    def search_for_templates_to_send(self, search_str, limit=10):
        # get the id of the model res.partner
        partner_model_id = self.env["ir.model"].search([("model", "=", "res.partner")]).id
        
        # search for templates that match the search_str with a limit and additional conditions
        templates = self.env["whatsapp.template"].search([
            ("model_id", "=", partner_model_id),
            ("name", "ilike", search_str),
            ("status", "=", "approved"),
            ("variable_ids", "not in", self.env["whatsapp.template.variable"].search([("field_type", "=", "free_text")]).ids),
        ], limit=limit)
        
        templates_list = []
        
        # for each template, get the template name and id and add it to the templates_list as objects
        for template in templates:
            templates_list.append({
                "body": template.body,
                "name": template.name,
                "id": template.id,
            })
        
        # return an array of template objects
        return templates_list
from odoo import _, api, fields, models
from odoo.exceptions import UserError

class ResPartnerInherit(models.Model):
    _inherit = "res.partner"

    tribute_id = fields.Many2one("dian.tributes", string="Tributos", required=False)
    fiscal_responsability_ids = fields.Many2many(
        "dian.fiscal.responsability", string="Responsabilidad fiscal", required=False
    )
    is_foreign = fields.Char("Is foreign")


    def _check_vat_fe(self):
        error = []
        if not self.vat_co:
            error.append(f"Cliente / Proveedor no tiene Numero De NIT/CC {self.name}")
        if not self.tribute_id:
            error.append(f"Cliente / Proveedor no tiene Tributo {self.name}")
        if not self.fiscal_responsability_ids:
            error.append(f"Cliente / Proveedor no tiene responsabilidades {self.name}")
        if not self.city_id and self.country_id.code == "CO":
           error.append(f"Cliente / Proveedor no tiene Ciudad / Municipio {self.name}")
        if not self.street:
            error.append(f"Cliente / Proveedor no tiene  Direccion {self.name}")
        if not self.state_id and self.country_id.code == "CO":
            error.append(f"Cliente / Proveedor no tiene  Departamento {self.name}")
        return  error

    #@api.constrains('country_id', 'state_ids', 'foreign_vat')
    def check_info_partner(self):
        result_error = self._check_vat_fe()
        if result_error:
            raise UserError("\n".join(result_error))
        return True
    
    # @api.model
    # def create(self, values):
    #     super(ResPartnerInherit, self).create(values)
    #     self.check_info_partner()

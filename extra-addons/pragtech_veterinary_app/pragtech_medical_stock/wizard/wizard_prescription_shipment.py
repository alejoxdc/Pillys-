from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import api, fields, models, tools, _


class make_medical_prescription_shipment(models.TransientModel):
    _name = 'medical.prescription.shipment'

    def create_prescription_shipment(self):
        shipment_obj = self.env['stock.picking']
        context = dict(self._context or {})
        move_obj = self.env['stock.move']
        prescription_obj = self.env['medical.prescription.order']
        prescriptions = prescription_obj.browse(context.get('active_ids'))
        picking_type_obj = self.env["stock.picking.type"]
        picking_type_ids = picking_type_obj.search([('code', '=', 'outgoing'), ('name', '=', 'Delivery Orders')])
        shipment_data = {}
        for prescription in prescriptions:
            shipment_data['partner_id'] = prescription.name.partner_id.id
            shipment_data['company_id'] = prescription.user_id.company_id.id
            shipment_data['origin'] = 'outgoing shipment' + ' for ' + prescription.prescription_id
            shipment_data['location_id'] = 12
            #             shipment_data['location_id'] = prescription.pharmacy.warehouse.id
            shipment_data['location_dest_id'] = 9
            shipment_data['prescription_order'] = prescription.id
            shipment_data['picking_type_id'] = picking_type_ids[0].id
            shipment = shipment_obj.create(shipment_data)
            stock_picking_vals = shipment
            shipment.write(
                {
                    'state': 'draft',
                })
            ship_ids = shipment_obj.search([])
            val = prescription.pharmacy.property_stock_customer.id
            for line in prescription.prescription_line:
                shipment_line_data = {}
                shipment_line_data['product_id'] = line.medicament.name.id
                shipment_line_data['product_uom'] = line.medicament.name.uom_id.id
                shipment_line_data['product_uom_qty'] = line.quantity
                shipment_line_data['location_id'] = 12
                shipment_line_data['location_dest_id'] = 9  # stock_picking_vals.location_dest_id.id
                shipment_line_data['price_unit'] = 1
                shipment_line_data['picking_id'] = shipment.id
                shipment_line_data['name'] = line.id
                if shipment_line_data['product_uom'] == False:
                    raise osv.except_osv(("Prescription Warning!!\nProduct unit not specified!!"))
                move_obj.create(shipment_line_data)
        return True

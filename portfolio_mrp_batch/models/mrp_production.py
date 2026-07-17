from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    enable_batch_scaling = fields.Boolean(string="Enable Batch Scaling")
    batch_count = fields.Float(default=1.0)
    machine_size = fields.Float(default=1.0)

    @api.constrains("batch_count", "machine_size")
    def _check_positive_scaling(self):
        for production in self:
            if production.batch_count < 0 or production.machine_size < 0:
                raise ValidationError("Batch count and machine size cannot be negative.")

    @api.onchange("enable_batch_scaling", "batch_count", "machine_size")
    def _onchange_batch_scaling(self):
        self._apply_batch_scaling()

    def write(self, vals):
        result = super().write(vals)
        triggers = {"enable_batch_scaling", "batch_count", "machine_size"}
        if triggers.intersection(vals) and not self.env.context.get("skip_batch_scaling"):
            self.with_context(skip_batch_scaling=True)._apply_batch_scaling()
        return result

    def _apply_batch_scaling(self):
        for production in self.filtered("enable_batch_scaling"):
            factor = production.batch_count * production.machine_size
            if float_compare(production.product_qty, factor, precision_rounding=production.product_uom_id.rounding):
                production.with_context(skip_batch_scaling=True).product_qty = factor
            for move in production.move_raw_ids.filtered(lambda item: item.state not in ("done", "cancel")):
                base_qty = move.bom_line_id.product_qty if move.bom_line_id else 0.0
                move.product_uom_qty = base_qty * factor

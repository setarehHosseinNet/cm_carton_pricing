from odoo import models, fields

class CartonCliche(models.Model):
    _name = "cm.carton.cliche"
    _description = "کلیشه چاپ کارتن"

    customer_product_id = fields.Many2one(
        "cm.carton.customer_product",
        string="محصول مشتری",
        required=True,
        ondelete="cascade",
    )

    name = fields.Char(
        string="نام کلیشه",
        required=True,
    )

    color = fields.Char(
        string="رنگ",
    )

    side = fields.Selection(
        [
            ("top", "بالا"),
            ("bottom", "پایین"),
            ("left", "چپ"),
            ("right", "راست"),
            ("front", "روبرو"),
            ("back", "پشت"),
        ],
        string="سمت چاپ",
    )

    cliche_cost = fields.Monetary(
        string="هزینه ساخت کلیشه",
        currency_field="currency_id",
    )

    print_cost_per_1000 = fields.Monetary(
        string="هزینه چاپ به ازای هر ۱۰۰۰ کارتن",
        currency_field="currency_id",
    )

    is_active = fields.Boolean(
        string="فعال؟",
        default=True,
    )

    is_laminate = fields.Boolean(
        string="چاپ لمینتی؟",
        default=False,
    )

    active = fields.Boolean(
        string="فعال؟",
        default=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="ارز",
        default=lambda self: self.env.company.currency_id.id,
    )

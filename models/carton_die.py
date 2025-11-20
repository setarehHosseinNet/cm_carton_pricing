from odoo import models, fields, _


class CartonDie(models.Model):
    _name = "cm.carton.die"
    _description = "قالب دایکات / لمینتی"
    _order = "name asc"

    # ----------------- شناسه قالب -----------------
    name = fields.Char(
        string="نام قالب",
        required=True,
        help="مثلاً: قالب دایکات نوشابه ۱.۵ لیتری، قالب لمینتی جعبه مادر و ..."
    )

    code = fields.Char(
        string="کد قالب",
        help="کد داخلی برای ردیابی قالب (مثلاً: DIE-0001)."
    )

    # ----------------- ارتباط با محصول اختصاصی -----------------
    customer_product_id = fields.Many2one(
        "cm.carton.customer_product",
        string="محصول اختصاصی مشتری",
        ondelete="cascade",
        help="اگر این قالب مخصوص یک محصول خاص مشتری است، اینجا انتخاب کن."
    )

    # ----------------- ابعاد تیغه به تیغه -----------------
    blade_width_mm = fields.Float(
        string="عرض تیغه به تیغه (mm)",
        help="عرض بلنک روی قالب، تیغه به تیغه، بر حسب میلی‌متر."
    )
    blade_length_mm = fields.Float(
        string="طول تیغه به تیغه (mm)",
        help="طول بلنک روی قالب، تیغه به تیغه، بر حسب میلی‌متر."
    )

    cavities_per_sheet = fields.Integer(
        string="تعداد ضرب در هر ورق",
        default=1,
        help="اگر روی هر ورق دو تا یا چندتا از این قالب می‌خورد، تعداد را اینجا وارد کن."
    )

    has_lamination = fields.Boolean(
        string="برای لمینت استفاده می‌شود؟",
        help="اگر این قالب مخصوص کارهای لمینتی است، این گزینه را فعال کن."
    )

    # ----------------- هزینه‌ها -----------------
    die_cost = fields.Monetary(
        string="هزینه ساخت قالب",
        currency_field="currency_id",
        help="هزینه یک‌باره ساخت این قالب (برای استهلاک روی سفارش‌ها در نظر گرفته می‌شود)."
    )

    # ----------------- فایل‌های طرح قالب -----------------
    design_attachment_ids = fields.Many2many(
        "ir.attachment",
        string="فایل‌های طرح قالب",
        help="فایل CDR/PDF/AI و... مرتبط با این قالب برای استفاده در دفعات بعد."
    )

    file_attachment_id = fields.Many2one(
        "ir.attachment",
        string="فایل اصلی قالب",
        help="اگر فقط یک فایل کلیدی برای این قالب داری، اینجا هم می‌توانی نگه داری."
    )

    # ----------------- وضعیت و ارز -----------------
    is_active = fields.Boolean(
        string="فعال؟",
        default=True,
        help="اگر قالب از رده خارج شد، می‌توانی تیک فعال را برداری تا دیگر در انتخاب‌ها نیاید."
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="ارز",
        default=lambda self: self.env.company.currency_id.id,
    )

    # ----------------- نمایش نام در دراپ‌داون‌ها -----------------
    def name_get(self):
        """
        نمایش قالب به صورت:
        «نام قالب [کد] - محصول مشتری»
        تا در انتخاب‌ها راحت‌تر تشخیص داده شود.
        """
        result = []
        for rec in self:
            parts = [rec.name]
            if rec.code:
                parts.append(f"[{rec.code}]")
            if rec.customer_product_id:
                parts.append(rec.customer_product_id.display_name or rec.customer_product_id.name)
            name = " - ".join(parts)
            result.append((rec.id, name))
        return result

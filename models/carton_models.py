# cm_carton_pricing/models/carton_models.py
from math import floor, ceil

from odoo import api, fields, models, _
from odoo.exceptions import UserError


# =========================================================
#   محصول اختصاصی مشتری (کارتن / ورق)
# =========================================================
class CartonCustomerProduct(models.Model):
    _name = "cm.carton.customer_product"
    _description = "محصول اختصاصی مشتری (کارتن/ورق)"
    _rec_name = "display_name"

    # ----------------- اطلاعات پایه -----------------
    partner_id = fields.Many2one(
        "res.partner",
        string="مشتری",
        required=True,
        ondelete="cascade",
    )

    name = fields.Char(
        string="نام داخلی محصول",
        required=True,
        help="مثال: کارتن ۵ لایه دایکاتی نوشابه ۱.۵ لیتری",
    )

    code = fields.Char(
        string="کد محصول",
        help="کد داخلی برای ردیابی سریع (مثلاً CM-000123)",
    )

    carton_type = fields.Selection(
        [
            ("normal", "کارتن معمولی"),
            ("diecut", "دایکاتی"),
            ("laminated", "لمینتی"),
            ("sheet", "ورق"),
        ],
        string="نوع محصول",
        required=True,
        default="normal",
    )

    length = fields.Float(string="طول کارتن (cm)")
    width = fields.Float(string="عرض کارتن (cm)")
    height = fields.Float(string="ارتفاع کارتن (cm)")

    layer_count = fields.Selection(
        [
            ("3", "سه لایه"),
            ("5", "پنج لایه"),
        ],
        string="تعداد لایه",
        default="5",
    )

    flute_step = fields.Selection(
        [
            ("B", "B"),
            ("C", "C"),
            ("E", "E"),
            ("BC", "BC"),
            ("BE", "BE"),
        ],
        string="گام فلوت پیشنهادی",
    )

    # ----------------- ساختار و درب -----------------
    piece_type = fields.Selection(
        [
            ("one_piece", "یک تکه"),
            ("half_carton", "نیم کارتن"),
            ("four_piece", "چهار تکه"),
        ],
        string="نوع تکه",
    )

    door_type = fields.Selection(
        [
            ("open_uneven", "درب باز نامتوازن"),
            ("closed", "درب بسته"),
            ("double", "درب دوبل"),
        ],
        string="نوع درب",
    )

    door_count = fields.Selection(
        [
            ("1", "تک درب"),
            ("2", "دو درب"),
        ],
        string="تعداد درب",
    )

    # ----------------- وضعیت چاپ و نمونه -----------------
    has_print = fields.Boolean(string="چاپ دارد؟")
    is_dimension_by_sample = fields.Boolean(string="ابعاد بر اساس نمونه است؟")
    has_sample = fields.Boolean(string="نمونه فیزیکی دارد؟")

    # ----------------- آپشن‌های پیش‌فرض خدمات -----------------
    has_new_cliche_default = fields.Boolean(string="نیاز به کلیشه جدید (پیش‌فرض)")
    has_mankan_default = fields.Boolean(string="نیاز به منگنه/منگنه‌کاری (پیش‌فرض)")
    has_handle_hole_default = fields.Boolean(string="نیاز به جای دسته (پیش‌فرض)")
    has_punch_default = fields.Boolean(string="نیاز به پانچ (پیش‌فرض)")
    has_pallet_wrap_default = fields.Boolean(string="نیاز به پالت‌کشی (پیش‌فرض)")

    has_been_produced = fields.Boolean(
        string="قبلاً تولید شده؟",
        help="بعد از اولین سفارش تأیید شده به‌صورت خودکار تیک می‌خورد.",
        default=False,
    )

    default_quantity = fields.Integer(
        string="تیراژ پیشنهادی",
        default=1000,
        help="تیراژ رایج این محصول برای این مشتری؛ در استعلام‌های جدید به‌صورت پیش‌فرض پر می‌شود.",
    )

    # ----------------- فروش در اودو -----------------
    sale_product_id = fields.Many2one(
        "product.product",
        string="محصول فروش در اودو",
        help="محصول (غیرانباری یا انباری) که نماینده این کارتن در سفارش فروش است.",
    )

    # ----------------- قالب و کلیشه‌ها -----------------
    die_id = fields.Many2one(
        "cm.carton.die",
        string="قالب دایکات",
        ondelete="set null",
    )

    cliche_ids = fields.One2many(
        comodel_name="cm.carton.cliche",
        inverse_name="customer_product_id",
        string="کلیشه‌ها",
    )

    # ----------------- سایر -----------------
    note = fields.Text(string="توضیحات فنی")

    display_name = fields.Char(
        string="نام نمایش",
        compute="_compute_display_name",
        store=True,
    )

    @api.depends("partner_id", "name", "code")
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.partner_id:
                parts.append(rec.partner_id.name)
            if rec.name:
                parts.append(rec.name)
            if rec.code:
                parts.append(f"[{rec.code}]")
            rec.display_name = " - ".join(parts) if parts else rec.name


# =========================================================
#   استعلام قیمت کارتن / ورق
# =========================================================
class CartonPriceInquiry(models.Model):
    _name = "cm.carton.price_inquiry"
    _description = "استعلام قیمت کارتن و ورق"
    _order = "create_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # ----------------- انتخاب وضعیت -----------------
    STATE_SELECTION = [
        ("draft", "پیش‌نویس"),
        ("waiting_quotes", "در انتظار استعلامات"),
        ("calculated", "محاسبه شده"),
        ("sent", "ارسال به مشتری"),
        ("accepted", "تأیید شده"),
        ("rejected", "رد شده"),
    ]

    FLOW_MODE_SELECTION = [
        ("quick", "مسیر سریع (محاسبه مستقیم)"),
        ("full", "مسیر کامل با استعلام طراحی/چاپ/منگنه/حمل/پالت"),
    ]

    # ----------------- فیلدهای اصلی -----------------
    partner_id = fields.Many2one(
        "res.partner",
        string="مشتری",
        required=True,
        tracking=True,
    )

    customer_product_id = fields.Many2one(
        "cm.carton.customer_product",
        string="محصول اختصاصی مشتری",
        domain="[('partner_id', '=', partner_id)]",
        tracking=True,
    )

    carton_type = fields.Selection(
        related="customer_product_id.carton_type",
        string="نوع کارتن",
        store=True,
        readonly=False,
        tracking=True,
    )

    quantity = fields.Integer(
        string="تیراژ (تعداد کارتن)",
        required=True,
        default=1000,
        tracking=True,
    )

    flow_mode = fields.Selection(
        FLOW_MODE_SELECTION,
        string="نوع فرآیند استعلام",
        default="quick",
        tracking=True,
        help=(
            "مسیر سریع: برای کارهای ورق و کارتن معمولی ساده یا کارهایی که قبلاً تولید شده‌اند و "
            "نیاز به استعلام طراحی/چاپ/منگنه/پالت‌کشی ندارند.\n"
            "مسیر کامل: برای کارهای جدید/دایکاتی/لمینتی/دارای چاپ و خدمات خاص."
        ),
    )

    # ----------------- قالب و لمینت -----------------
    die_id = fields.Many2one(
        "cm.carton.die",
        string="قالب دایکات/لمینتی",
        help="اگر برای این محصول قالب تعریف شده، اینجا انتخاب شود.",
        tracking=True,
    )

    lamination_price_per_m2 = fields.Float(
        string="هزینه لمینت هر مترمربع",
        help="فقط برای کارتن‌های لمینتی استفاده می‌شود.",
    )

    # ----------------- نیاز به استعلام‌های جزئی -----------------
    need_design_quote = fields.Boolean(string="نیاز به استعلام طراحی/کلیشه؟")
    need_print_quote = fields.Boolean(string="نیاز به استعلام چاپ؟")
    need_staple_quote = fields.Boolean(string="نیاز به استعلام منگنه؟")
    need_punch_quote = fields.Boolean(string="نیاز به استعلام پانچ؟")
    need_pallet_quote = fields.Boolean(string="نیاز به استعلام پالت‌کشی؟")
    need_shipping_quote = fields.Boolean(string="نیاز به استعلام حمل؟")

    sub_quote_ids = fields.One2many(
        comodel_name="cm.carton.sub_quote",
        inverse_name="price_inquiry_id",
        string="استعلامات جزئی",
    )

    # ----------------- ابعاد شیت / قالب -----------------
    flat_width_mm = fields.Float(
        string="عرض خوابیده روی ورق (mm)",
        help="از روی طول/عرض/ارتفاع محصول یا ابعاد قالب محاسبه می‌شود.",
        readonly=True,
    )
    flat_length_mm = fields.Float(
        string="طول خوابیده روی ورق (mm)",
        help="از روی طول/عرض/ارتفاع محصول یا ابعاد قالب محاسبه می‌شود.",
        readonly=True,
    )

    die_width_mm = fields.Float(
        string="عرض بلنک/قالب (mm)",
        help="در صورت نیاز، بعد از طراحی وارد می‌شود.",
    )
    die_length_mm = fields.Float(
        string="طول بلنک/قالب (mm)",
        help="در صورت نیاز، بعد از طراحی وارد می‌شود.",
    )

    industrial_width_mm = fields.Float(
        string="عرض صنعتی انتخاب‌شده (cm)",
        help="یکی از عرض‌های 80،90،95،100,...،140 که سیستم یا اپراتور انتخاب می‌کند.",
        tracking=True,
    )

    suggestion_ids = fields.One2many(
        comodel_name="cm.carton.sheet_suggestion",
        inverse_name="price_inquiry_id",
        string="پیشنهادهای عرض ورق",
    )

    # ----------------- هزینه‌ها -----------------
    paper_price_per_m2 = fields.Float(
        string="قیمت هر مترمربع ورق (ترکیب کاغذها)",
        help="در نسخه‌ی پیشرفته می‌توانی از BOM و قیمت کاغذ استفاده کنی.",
    )

    material_cost_total = fields.Monetary(
        string="جمع هزینه مواد",
        currency_field="currency_id",
        readonly=True,
    )

    overhead_cost_total = fields.Monetary(
        string="جمع هزینه سربار",
        currency_field="currency_id",
        readonly=True,
    )

    die_cost = fields.Monetary(
        string="هزینه ساخت قالب (دایکات / معمولی)",
        currency_field="currency_id",
    )
    cliche_cost = fields.Monetary(
        string="هزینه کلیشه",
        currency_field="currency_id",
    )
    design_cost = fields.Monetary(
        string="هزینه طراحی",
        currency_field="currency_id",
    )
    punch_cost_total = fields.Monetary(
        string="هزینه پانچ",
        currency_field="currency_id",
    )
    pallet_wrap_cost_total = fields.Monetary(
        string="هزینه پالت‌کشی",
        currency_field="currency_id",
    )
    shipping_cost = fields.Monetary(
        string="هزینه حمل",
        currency_field="currency_id",
    )

    base_cost_per_carton = fields.Monetary(
        string="مایه کار هر کارتن",
        currency_field="currency_id",
        readonly=True,
    )

    payment_type = fields.Selection(
        [
            ("cash", "نقدی"),
            ("credit", "مدت‌دار"),
        ],
        string="نوع پرداخت",
        default="cash",
        tracking=True,
    )

    margin_cash_percent = fields.Float(
        string="درصد سود نقدی",
        default=10.0,
    )
    margin_credit_percent = fields.Float(
        string="درصد سود مدت‌دار",
        default=15.0,
    )
    tax_percent = fields.Float(
        string="درصد مالیات",
        default=9.0,
    )

    sale_price_cash = fields.Monetary(
        string="قیمت واحد نقدی",
        currency_field="currency_id",
        readonly=True,
    )
    sale_price_credit = fields.Monetary(
        string="قیمت واحد مدت‌دار",
        currency_field="currency_id",
        readonly=True,
    )
    unit_price_with_tax = fields.Monetary(
        string="قیمت واحد با مالیات",
        currency_field="currency_id",
        readonly=True,
    )
    total_price_with_tax = fields.Monetary(
        string="قیمت کل با مالیات",
        currency_field="currency_id",
        readonly=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="ارز",
        default=lambda self: self.env.company.currency_id.id,
    )

    state = fields.Selection(
        selection=STATE_SELECTION,
        string="وضعیت",
        default="draft",
        tracking=True,
    )

    is_pending = fields.Boolean(
        string="در انتظار اقدام؟",
        compute="_compute_is_pending",
        store=False,
    )

    sale_order_id = fields.Many2one(
        "sale.order",
        string="سفارش فروش",
        readonly=True,
    )

    crm_lead_id = fields.Many2one(
        "crm.lead",
        string="فرصت فروش (CRM)",
        readonly=True,
    )

    rejection_reason = fields.Text(string="علت رد پیشنهاد")
    rejection_attachment_ids = fields.Many2many(
        "ir.attachment",
        string="پیوست‌های رد پیشنهاد",
    )

    # =====================================================
    #   کمکی‌ها
    # =====================================================
    @api.depends("state")
    def _compute_is_pending(self):
        for rec in self:
            rec.is_pending = rec.state in (
                "draft",
                "waiting_quotes",
                "calculated",
                "sent",
            )

    @api.onchange("customer_product_id")
    def _onchange_customer_product_id(self):
        """براساس محصول، مسیر سریع/کامل و نیاز به استعلامات را حدس می‌زند."""
        for rec in self:
            product = rec.customer_product_id
            if not product:
                rec.flow_mode = "quick"
                rec.need_design_quote = False
                rec.need_print_quote = False
                rec.need_staple_quote = False
                rec.need_punch_quote = False
                rec.need_pallet_quote = False
                rec.need_shipping_quote = False
                continue

            # تیراژ پیشنهادی
            if product.default_quantity:
                rec.quantity = product.default_quantity

            # نیازها از روی محصول
            rec.need_print_quote = bool(product.has_print)
            rec.need_design_quote = bool(
                product.has_print and product.has_new_cliche_default
            )
            rec.need_staple_quote = bool(product.has_mankan_default)
            rec.need_punch_quote = bool(product.has_punch_default)
            rec.need_pallet_quote = bool(product.has_pallet_wrap_default)
            rec.need_shipping_quote = False

            extra_services_needed = any(
                [
                    rec.need_design_quote,
                    rec.need_print_quote,
                    rec.need_staple_quote,
                    rec.need_punch_quote,
                    rec.need_pallet_quote,
                    rec.need_shipping_quote,
                ]
            )

            simple_type = product.carton_type in ("sheet", "normal")
            already_produced = product.has_been_produced

            if (simple_type or already_produced) and not extra_services_needed:
                rec.flow_mode = "quick"
            else:
                rec.flow_mode = "full"

    @api.model
    def action_open_pending_inquiries(self):
        """اکشن لیست استعلام‌های انجام‌نشده."""
        return {
            "type": "ir.actions.act_window",
            "name": _("استعلام‌های در انتظار"),
            "res_model": "cm.carton.price_inquiry",
            "view_mode": "list,form",
            "domain": [
                ("state", "in", ["draft", "waiting_quotes", "calculated", "sent"])
            ],
            "target": "current",
        }

    def _notify_state_change(self, body, activity_summary=None):
        """
        پیام + اکتیویتی TODO به روش سازگار با Odoo 18.
        """
        Activity = self.env["mail.activity"]
        IrModel = self.env["ir.model"]

        try:
            todo_type = self.env.ref("mail.mail_activity_data_todo")
        except ValueError:
            todo_type = False

        try:
            model_rec = IrModel._get(self._name)
        except ValueError:
            model_rec = False

        for rec in self:
            rec.message_post(body=body, subtype_xmlid="mail.mt_comment")

            if not todo_type or not model_rec:
                continue

            Activity.create(
                {
                    "res_model_id": model_rec.id,
                    "res_id": rec.id,
                    "activity_type_id": todo_type.id,
                    "user_id": self.env.user.id,
                    "summary": activity_summary or _("پیگیری استعلام قیمت"),
                }
            )

    # =====================================================
    #   لاجیک اصلی
    # =====================================================
    def _check_basic_inputs(self):
        for rec in self:
            if not rec.partner_id:
                raise UserError(_("لطفاً مشتری را انتخاب کنید."))
            if not rec.customer_product_id:
                raise UserError(_("لطفاً محصول اختصاصی مشتری را انتخاب کنید."))
            if not rec.quantity or rec.quantity <= 0:
                raise UserError(_("تیراژ باید بزرگ‌تر از صفر باشد."))

            product = rec.customer_product_id
            if (
                product.carton_type in ("normal", "sheet")
                and not (product.length and product.width and product.height)
            ):
                raise UserError(
                    _(
                        "برای محصول اختصاصی مشتری، ابعاد طول/عرض/ارتفاع تکمیل نشده است.\n"
                        "لطفاً در فرم محصول، ابعاد را وارد کنید."
                    )
                )

    def _ensure_sub_quotes(self):
        """در حالت full، استعلام‌های جزئی لازم را می‌سازد."""
        for rec in self:
            if rec.flow_mode != "full":
                continue

            type_map = {
                "design": rec.need_design_quote,
                "print": rec.need_print_quote,
                "staple": rec.need_staple_quote,
                "punch": rec.need_punch_quote,
                "pallet": rec.need_pallet_quote,
                "shipping": rec.need_shipping_quote,
            }

            existing_by_type = {sq.type: sq for sq in rec.sub_quote_ids}
            created_any = False

            for t, needed in type_map.items():
                if not needed or t in existing_by_type:
                    continue
                self.env["cm.carton.sub_quote"].create(
                    {
                        "price_inquiry_id": rec.id,
                        "type": t,
                        "required": True,
                    }
                )
                created_any = True

            if created_any:
                rec.state = "waiting_quotes"
                rec._notify_state_change(
                    body=_(
                        "استعلام‌های جزئی (طراحی/چاپ/منگنه/پالت/حمل) برای این استعلام ایجاد شد."
                    ),
                    activity_summary=_("هزینه‌های استعلام‌های جزئی را تکمیل کنید."),
                )

    def _all_required_sub_quotes_ready(self):
        """
        آیا تمامی استعلام‌های لازم، هزینه دارند و در وضعیت «received» یا «approved» هستند؟
        """
        for rec in self:
            if rec.flow_mode != "full":
                return True

            required_quotes = rec.sub_quote_ids.filtered(lambda q: q.required)
            if not required_quotes:
                return False

            for q in required_quotes:
                if q.state not in ("received", "approved") or q.estimated_cost <= 0.0:
                    return False
        return True

    def _apply_sub_quote_costs(self):
        """
        هزینه‌های استعلام جزئی را روی فیلدهای هزینه اعمال می‌کند.
        فعلاً طراحی/کلیشه/قالب در type=design جمع شده‌اند.
        """

        for rec in self:
            if rec.flow_mode != "full":
                continue

            def sum_type(t):
                return sum(
                    rec.sub_quote_ids.filtered(lambda q: q.type == t).mapped(
                        "estimated_cost"
                    )
                )

            rec.design_cost = sum_type("design")
            rec.cliche_cost = sum_type("design")
            rec.die_cost = sum_type("design")
            rec.punch_cost_total = sum_type("punch")
            rec.pallet_wrap_cost_total = sum_type("pallet")
            rec.shipping_cost = sum_type("shipping")

    def _compute_flat_dimensions(self):
        """
        محاسبه طول و عرض خوابیده روی ورق
        """
        side_margin_mm = 20.0  # حاشیه ۲ سانت از هر طرف

        for rec in self:
            product = rec.customer_product_id
            if not product:
                rec.flat_length_mm = 0.0
                rec.flat_width_mm = 0.0
                continue

            carton_type = product.carton_type or "normal"

            # --- دایکاتی / لمینتی ---
            if carton_type in ("diecut", "laminated"):
                die = rec.die_id or product.die_id

                if die and die.blade_length_mm and die.blade_width_mm:
                    base_L = die.blade_length_mm
                    base_W = die.blade_width_mm
                elif rec.die_length_mm and rec.die_width_mm:
                    base_L = rec.die_length_mm
                    base_W = rec.die_width_mm
                else:
                    if rec.flow_mode == "full":
                        raise UserError(
                            _(
                                "برای کارتن‌های دایکاتی/لمینتی باید ابتدا قالب با ابعاد تیغه به تیغ "
                                "یا ابعاد بلنک (طول/عرض) تعریف شود."
                            )
                        )
                    if not (product.length and product.width and product.height):
                        rec.flat_length_mm = 0.0
                        rec.flat_width_mm = 0.0
                        continue
                    base_L = (product.length or 0.0) * 10.0
                    base_W = (product.width or 0.0) * 10.0

                rec.flat_length_mm = base_L + 2 * side_margin_mm
                rec.flat_width_mm = base_W + 2 * side_margin_mm
                continue

            # --- کارتن معمولی ---
            if carton_type == "normal":
                L = (product.length or 0.0) * 10.0
                W = (product.width or 0.0) * 10.0
                H = (product.height or 0.0) * 10.0

                if not (L and W and H):
                    rec.flat_length_mm = 0.0
                    rec.flat_width_mm = 0.0
                    continue

                glue_allowance_mm = 40.0

                flat_length = 2 * (L + W) + glue_allowance_mm + 2 * side_margin_mm
                flap_up_mm = W / 2 + 10.0
                flap_down_mm = W / 2 + 10.0
                flat_width = H + flap_up_mm + flap_down_mm + 2 * side_margin_mm

                rec.flat_length_mm = flat_length
                rec.flat_width_mm = flat_width
                continue

            # --- ورق ساده ---
            if carton_type == "sheet":
                L = (product.length or 0.0) * 10.0
                W = (product.width or 0.0) * 10.0
                if not (L and W):
                    rec.flat_length_mm = 0.0
                    rec.flat_width_mm = 0.0
                    continue

                rec.flat_length_mm = L + 2 * side_margin_mm
                rec.flat_width_mm = W + 2 * side_margin_mm
                continue

            # --- حالت‌های احتیاطی ---
            L = (product.length or 0.0) * 10.0
            W = (product.width or 0.0) * 10.0
            H = (product.height or 0.0) * 10.0
            if not (L and W and H):
                rec.flat_length_mm = 0.0
                rec.flat_width_mm = 0.0
                continue

            rec.flat_length_mm = 2 * (L + W) + 2 * side_margin_mm
            rec.flat_width_mm = H + W + 2 * side_margin_mm

    def _generate_sheet_suggestions(self):
        """
        از روی ابعاد شیت و تیراژ، پیشنهاد عرض‌های صنعتی مختلف را تولید می‌کند.
        """
        industrial_widths_cm = [
            80,
            90,
            95,
            100,
            105,
            110,
            115,
            120,
            125,
            130,
            135,
            140,
        ]
        side_margin_cm = 2.0

        for rec in self:
            rec.suggestion_ids.unlink()

            flat_w_cm = rec.flat_width_mm / 10.0
            flat_l_cm = rec.flat_length_mm / 10.0

            if flat_w_cm <= 0 or flat_l_cm <= 0:
                continue

            suggestions_vals = []

            for width_cm in industrial_widths_cm:
                usable_width = width_cm - 2 * side_margin_cm
                if usable_width <= 0:
                    continue

                carton_per_row = floor(usable_width / flat_w_cm)
                if carton_per_row <= 0:
                    continue

                used_width = carton_per_row * flat_w_cm
                waste_width = usable_width - used_width
                waste_percent = (waste_width / width_cm) * 100.0

                row_count = ceil(rec.quantity / carton_per_row)
                total_length = row_count * flat_l_cm  # cm

                suggestions_vals.append(
                    {
                        "price_inquiry_id": rec.id,
                        "industrial_width_cm": width_cm,
                        "carton_per_row": carton_per_row,
                        "waste_cm": waste_width,
                        "waste_percent": waste_percent,
                        "total_length_cm": total_length,
                    }
                )

            if suggestions_vals:
                self.env["cm.carton.sheet_suggestion"].create(suggestions_vals)
                if not rec.industrial_width_mm:
                    best = min(suggestions_vals, key=lambda v: v["waste_percent"])
                    rec.industrial_width_mm = best["industrial_width_cm"]

    def _compute_costs_from_excel_logic_placeholder(self):
        """
        فعلاً منطق ساده جایگزین اکسل.
        """
        for rec in self:
            ct = rec.carton_type
            if ct == "normal":
                material, overhead = rec._compute_normal_carton_from_excel()
            elif ct == "diecut":
                material, overhead = rec._compute_diecut_carton_from_excel()
            elif ct == "laminated":
                material, overhead = rec._compute_laminated_carton_from_excel()
            elif ct == "sheet":
                material, overhead = rec._compute_sheet_from_excel()
            else:
                material, overhead = 0.0, 0.0

            rec.material_cost_total = material
            rec.overhead_cost_total = overhead

    def _compute_normal_carton_from_excel(self):
        area_m2 = (self.flat_width_mm / 1000.0) * (self.flat_length_mm / 1000.0)
        total_area_m2 = area_m2 * (self.quantity or 0.0)
        material = total_area_m2 * (self.paper_price_per_m2 or 0.0)
        overhead = material * 0.10
        return material, overhead

    def _compute_diecut_carton_from_excel(self):
        """
        مایه‌کاری دایکاتی (ساده‌شده از فایل دایکاتی.xlsx).
        """
        die = self.die_id or self.customer_product_id.die_id
        if not die or not die.blade_length_mm or not die.blade_width_mm:
            raise UserError(_("برای دایکاتی، قالب با ابعاد تیغه به تیغ الزامی است."))

        cavities = die.cavities_per_sheet or 1
        qty = self.quantity or 0

        sheet_area_m2 = (die.blade_length_mm / 1000.0) * (
            die.blade_width_mm / 1000.0
        )
        sheets_needed = ceil(qty / cavities) if cavities > 0 else 0
        total_area_m2 = sheet_area_m2 * sheets_needed

        material = total_area_m2 * (self.paper_price_per_m2 or 0.0)
        material += die.die_cost or 0.0

        overhead = material * 0.15
        return material, overhead

    def _compute_laminated_carton_from_excel(self):
        """
        مایه‌کاری لمینتی (ساده‌شده از فایل لمینتی.xlsx).
        """
        die = self.die_id or self.customer_product_id.die_id
        if not die or not die.blade_length_mm or not die.blade_width_mm:
            raise UserError(_("برای لمینتی، قالب با ابعاد تیغه به تیغ الزامی است."))

        cavities = die.cavities_per_sheet or 1
        qty = self.quantity or 0

        sheet_area_m2 = (die.blade_length_mm / 1000.0) * (
            die.blade_width_mm / 1000.0
        )
        sheets_needed = ceil(qty / cavities) if cavities > 0 else 0
        total_area_m2 = sheet_area_m2 * sheets_needed

        material = total_area_m2 * (self.paper_price_per_m2 or 0.0)
        lam_cost = total_area_m2 * (self.lamination_price_per_m2 or 0.0)
        material = material + lam_cost + (die.die_cost or 0.0)

        overhead = material * 0.15
        return material, overhead

    def _compute_sheet_from_excel(self):
        return self._compute_normal_carton_from_excel()

    def _compute_prices(self):
        for rec in self:
            if rec.quantity <= 0:
                continue

            total_cost = (
                rec.material_cost_total
                + rec.overhead_cost_total
                + rec.die_cost
                + rec.cliche_cost
                + rec.design_cost
                + rec.punch_cost_total
                + rec.pallet_wrap_cost_total
                + rec.shipping_cost
            )

            rec.base_cost_per_carton = (
                total_cost / rec.quantity if rec.quantity else 0.0
            )

            rec.sale_price_cash = rec.base_cost_per_carton * (
                1.0 + (rec.margin_cash_percent or 0.0) / 100.0
            )
            rec.sale_price_credit = rec.base_cost_per_carton * (
                1.0 + (rec.margin_credit_percent or 0.0) / 100.0
            )

            unit_price = (
                rec.sale_price_cash
                if rec.payment_type == "cash"
                else rec.sale_price_credit
            )

            rec.unit_price_with_tax = unit_price * (
                1.0 + (rec.tax_percent or 0.0) / 100.0
            )
            rec.total_price_with_tax = rec.unit_price_with_tax * rec.quantity

    # -----------------------------------------------------
    #   دکمه‌ها
    # -----------------------------------------------------
    def action_compute(self):
        """
        دکمه «محاسبه».
        """
        for rec in self:
            rec._check_basic_inputs()

            if rec.flow_mode == "full":
                rec._ensure_sub_quotes()

                if rec.carton_type in ("diecut", "laminated"):
                    die = rec.die_id or rec.customer_product_id.die_id
                    has_die_dims = (
                        die and die.blade_length_mm and die.blade_width_mm
                    )
                    has_blank_dims = rec.die_length_mm and rec.die_width_mm
                    if not (has_die_dims or has_blank_dims):
                        raise UserError(
                            _(
                                "این استعلام در مسیر کامل و از نوع دایکاتی/لمینتی است.\n"
                                "ابتدا باید طراحی/قالب نهایی شود و ابعاد قالب (تیغه به تیغ یا بلنک) "
                                "وارد گردد."
                            )
                        )

                if not rec._all_required_sub_quotes_ready():
                    raise UserError(
                        _(
                            "تمامی استعلام‌های جزئی لازم (طراحی/چاپ/منگنه/پالت/حمل) هنوز پاسخ کامل ندارند.\n"
                            "لطفاً هزینه‌ها را در فرم استعلام‌های جزئی تکمیل و تأیید کنید."
                        )
                    )

                rec._apply_sub_quote_costs()

            rec._compute_flat_dimensions()
            rec._generate_sheet_suggestions()
            rec._compute_costs_from_excel_logic_placeholder()
            rec._compute_prices()
            rec.state = "calculated"

        self._notify_state_change(
            body=_("محاسبه استعلام قیمت انجام شد."),
            activity_summary=_("نتیجه استعلام را بررسی کنید."),
        )

    def action_mark_sent(self):
        self.write({"state": "sent"})
        self._notify_state_change(
            body=_("استعلام قیمت برای مشتری ارسال شد."),
            activity_summary=_("پیگیری پاسخ مشتری برای استعلام قیمت."),
        )

    def action_accept(self):
        for rec in self:
            rec._create_sale_order_on_accept()
            rec.state = "accepted"

            if rec.customer_product_id and not rec.customer_product_id.has_been_produced:
                rec.customer_product_id.has_been_produced = True

        self._notify_state_change(
            body=_("استعلام قیمت توسط مشتری تأیید شد و سفارش فروش ایجاد گردید."),
            activity_summary=_("پیگیری اجرای سفارش فروش مربوط به این استعلام."),
        )

    def _create_sale_order_on_accept(self):
        for rec in self:
            if rec.sale_order_id:
                continue

            product = rec.customer_product_id.sale_product_id
            if not product:
                raise UserError(
                    _(
                        "برای محصول اختصاصی مشتری، محصول فروش (product) تعریف نشده است.\n"
                        "لطفاً در فرم محصول اختصاصی، محصول فروش را مشخص کنید."
                    )
                )

            order_vals = {
                "partner_id": rec.partner_id.id,
                "origin": f"Carton PI #{rec.id}",
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": rec.quantity,
                            "price_unit": rec.unit_price_with_tax,
                            "name": product.display_name,
                        },
                    )
                ],
            }
            sale = self.env["sale.order"].create(order_vals)
            rec.sale_order_id = sale.id

    def action_reject(self):
        self.write({"state": "rejected"})
        self._notify_state_change(
            body=_("استعلام قیمت رد شد."),
            activity_summary=_("بررسی علت رد و برنامه‌ریزی تماس بعدی با مشتری."),
        )


# =========================================================
#   قالب دایکات / لمینتی
# =========================================================
class CartonDie(models.Model):
    _name = "cm.carton.die"
    _description = "قالب دایکات / لمینتی"

    name = fields.Char(string="نام قالب", required=True)
    code = fields.Char(string="کد قالب")

    partner_id = fields.Many2one(
        "res.partner",
        string="سازنده / چاپخانه",
    )

    product_id = fields.Many2one(
        "cm.carton.customer_product",
        string="محصول اختصاصی مشتری",
        ondelete="set null",
    )

    blade_length_mm = fields.Float(string="طول تیغه به تیغ (mm)")
    blade_width_mm = fields.Float(string="عرض تیغه به تیغ (mm)")

    cavities_per_sheet = fields.Integer(
        string="تعداد قالب در هر ورق",
        default=1,
        help="اگر روی یک ورق چند ضرب قالب داریم، اینجا تعداد را وارد کن.",
    )

    has_lamination = fields.Boolean(string="برای لمینت استفاده می‌شود؟")

    die_cost = fields.Monetary(
        string="هزینه ساخت قالب",
        currency_field="currency_id",
    )

    is_active = fields.Boolean(string="فعال؟", default=True)

    design_attachment_ids = fields.Many2many(
        "ir.attachment",
        string="فایل‌های طرح قالب",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="ارز",
        default=lambda self: self.env.company.currency_id.id,
    )


# =========================================================
#   پیشنهاد چیدمان روی عرض‌های مختلف ورق
# =========================================================
class CartonSheetSuggestion(models.Model):
    _name = "cm.carton.sheet_suggestion"
    _description = "پیشنهاد چیدمان روی عرض‌های مختلف ورق"
    _order = "industrial_width_cm asc"

    price_inquiry_id = fields.Many2one(
        "cm.carton.price_inquiry",
        string="استعلام قیمت",
        ondelete="cascade",
        required=True,
    )

    industrial_width_cm = fields.Float(string="عرض صنعتی (cm)")
    carton_per_row = fields.Integer(string="تعداد کارتن در هر ردیف")
    waste_cm = fields.Float(string="ضایعات عرضی (cm)")
    waste_percent = fields.Float(string="درصد ضایعات عرضی")
    total_length_cm = fields.Float(string="طول صنعتی کل (cm)")


# =========================================================
#   استعلام‌های جزئی (طراحی / چاپ / منگنه / پالت / حمل)
# =========================================================
class CartonSubQuote(models.Model):
    _name = "cm.carton.sub_quote"
    _description = "استعلام جزئی (طراحی/چاپ/منگنه/پانچ/پالت/حمل)"

    price_inquiry_id = fields.Many2one(
        "cm.carton.price_inquiry",
        string="استعلام اصلی",
        ondelete="cascade",
        required=True,
    )

    type = fields.Selection(
        [
            ("design", "طراحی"),
            ("print", "چاپ"),
            ("staple", "منگنه/مکانیکی"),
            ("punch", "پانچ"),
            ("pallet", "پالت‌کشی"),
            ("shipping", "حمل"),
        ],
        string="نوع استعلام",
        required=True,
    )

    required = fields.Boolean(string="اجباری؟", default=True)

    partner_id = fields.Many2one("res.partner", string="طرف استعلام")

    estimated_cost = fields.Monetary(
        string="هزینه برآوردی",
        currency_field="currency_id",
    )

    state = fields.Selection(
        [
            ("draft", "پیش‌نویس"),
            ("sent", "ارسال شده"),
            ("received", "دریافت قیمت"),
            ("approved", "تأیید شده"),
        ],
        string="وضعیت",
        default="draft",
    )

    note = fields.Text(string="توضیحات")

    currency_id = fields.Many2one(
        "res.currency",
        string="ارز",
        default=lambda self: self.env.company.currency_id.id,
    )


# =========================================================
#   کلیشه چاپ
# =========================================================
class CartonCliche(models.Model):
    _name = "cm.carton.cliche"
    _description = "کلیشه چاپ برای محصول اختصاصی مشتری"

    customer_product_id = fields.Many2one(
        "cm.carton.customer_product",
        string="محصول اختصاصی",
        required=True,
        ondelete="cascade",
    )

    name = fields.Char(
        string="نام کلیشه",
        required=True,
        help="مثلاً: کلیشه لوگو، کلیشه وجه A و ...",
    )

    color = fields.Char(
        string="رنگ / رنگ‌ها",
        help="مثلاً: قرمز + مشکی",
    )

    side = fields.Selection(
        [
            ("front", "رو"),
            ("back", "پشت"),
            ("both", "دو رو"),
        ],
        string="سمت چاپ",
    )

    cliche_cost = fields.Monetary(
        string="هزینه ساخت کلیشه",
        currency_field="currency_id",
    )

    print_cost_per_1000 = fields.Monetary(
        string="هزینه چاپ هر ۱۰۰۰ عدد",
        currency_field="currency_id",
    )

    design_file_id = fields.Many2one(
        "ir.attachment",
        string="فایل طرح",
        help="فایل طرح نهایی برای استفاده در سفارش‌های بعدی",
    )

    is_laminate = fields.Boolean(
        string="چاپ لمینتی؟",
        help="اگر True باشد، این کلیشه/طرح برای چاپ لمینتی استفاده می‌شود.",
    )

    active = fields.Boolean(  # این با ویو «active» هماهنگ است
        string="فعال؟",
        default=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="ارز",
        default=lambda self: self.env.company.currency_id.id,
    )

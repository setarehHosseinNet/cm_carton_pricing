# cm_carton_pricing/__manifest__.py
{
    "name": "Carton Customer Pricing (Excel-Based)",
    "summary": "محاسبه قیمت و مصرف ورق برای کارتن اختصاصی مشتری بر اساس منطق ساده‌شده اکسل",
    "description": """
کارتن اختصاصی مشتری - قیمت‌گذاری بر اساس منطق اکسل
=================================================
- تعریف محصول اختصاصی برای هر مشتری (کارتن، دایکاتی، لمینتی، ورق)
- ثبت ابعاد، گام فلوت، قالب، کلیشه و تنظیمات پیش‌فرض
- استعلام قیمت با دو مسیر:
  * مسیر سریع (quick): محاسبه مستقیم بر اساس ابعاد کارتن/ورق
  * مسیر کامل (full): با استعلام جزئی طراحی، چاپ، منگنه، پانچ، پالت‌کشی، حمل
- محاسبه مایه‌کاری، ضایعات عرضی، قیمت نقد و مدت‌دار، و مالیات
- ایجاد سفارش فروش از روی استعلام تأییدشده
    """,

    "version": "18.0.1.0.0",
    "author": "Hossein Setareh",
    "website": "https://mohammadcarton.com",
    "category": "Manufacturing",
    "license": "OEEL-1",

    # ============================
    #   وابستگی‌ها
    # ============================
    "depends": [
        "base",
        "mail",             # برای mail.thread و mail.activity.mixin
        "sale_management",  # سفارش فروش
        "crm",              # فرصت‌های فروش (اختیاری ولی استفاده‌شده در مدل)
        "mrp",              # برای ارتباط‌های بعدی با BOM و تولید
    ],

    # ============================
    #   داده‌ها (views / security)
    # ============================
    "data": [
        "security/ir.model.access.csv",
        "views/carton_customer_product_views.xml",
        "views/carton_price_inquiry_views.xml",
        "views/menu_views.xml",
    ],

    # اگر بعداً data اولیه مثل پارامترهای پیش‌فرض یا activity type اختصاصی داشتی،
    # می‌تونی این‌جا یک data/xxx_data.xml هم اضافه کنی.

    "installable": True,
    "application": True,
}

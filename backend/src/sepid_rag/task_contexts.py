"""Participant-task context supplied to the model on every SWTS turn."""

from __future__ import annotations


TASK_CONTEXT_VERSION = "sepid-swts-task-context-v1"

COMMON_CONTEXT = """شما و پنج نفر از دوستان و اعضای خانواده قصد دارید سفری پنج‌روزه به جزیره سپید داشته باشید. کارهای آماده‌سازی سفر بین اعضای گروه تقسیم شده و از شما خواسته شده است در چند بخش به گروه کمک کنید.

جزیره سپید کاملاً خیالی است، هیچ‌کدام قبلاً به آنجا نرفته‌اید و فقط اطلاعات موجود در این سامانه معتبر است."""

TASK_CONTEXTS = {
    "task_1": {
        "title": "شناخت گزینه‌های اقامت",
        "problem": "گروه هنوز نمی‌داند در جزیره سپید چه گزینه‌هایی برای اقامت وجود دارد و این گزینه‌ها از نظر موقعیت، ظرفیت، هزینه، امکانات و مقررات چه تفاوت‌هایی دارند.",
        "objective": "کاربر باید در پایان بداند هر گزینه چه ویژگی‌هایی دارد و کدام گزینه‌ها با نیازهای گروه سازگارند.",
        "core_scope": "گزینه‌های اقامت، موقعیت، ظرفیت، هزینه، امکانات، غذا، مقررات، رزرو و تناسب با گروه",
        "adjacent_scope": "دسترسی محلی، فاصله‌ها و خدماتی که مستقیماً بر انتخاب اقامت اثر می‌گذارند",
    },
    "task_2": {
        "title": "مقایسه زمان‌های سفر",
        "problem": "گروه هنوز درباره زمان سفر تصمیم نگرفته است. اعضای گروه به طبیعت‌گردی، فعالیت‌های ساحلی، جاذبه‌ها و رویدادهای محلی علاقه دارند، اما آب‌وهوا، هزینه، شلوغی و امکان استفاده از مکان‌ها و فعالیت‌ها در طول سال یکسان نیست.",
        "objective": "کاربر باید زمان‌های سفر را مقایسه کند و به ترجیحی برسد که دلایل و مصالحه‌های آن روشن باشد.",
        "core_scope": "بازه‌های سفر، آب‌وهوا، هزینه، شلوغی، رویدادها، جاذبه‌ها، دسترسی و محدودیت فعالیت‌ها",
        "adjacent_scope": "اثر فصل بر اقامت، رفت‌وآمد یا تجربه گروه",
    },
    "task_3": {
        "title": "درک زندگی و تعامل محترمانه",
        "problem": "گروه احتمالاً با ساکنان جزیره تعامل دارد، از محله‌ها و فضاهای عمومی دیدن می‌کند و در آیین‌ها یا فعالیت‌های محلی حاضر می‌شود. اعضای گروه با زبان، باورها، رسوم، نشانه‌ها، روایت‌ها و حساسیت‌های مردم آشنا نیستند.",
        "objective": "کاربر باید برداشت منسجمی از زندگی جزیره و شیوه تعامل محترمانه با مردم در موقعیت‌های گوناگون شکل دهد.",
        "core_scope": "زبان و ارتباط، زندگی روزمره، جامعه، باورها، رسوم، نشانه‌ها، روایت‌ها، حریم، طبیعت و رفتار محترمانه",
        "adjacent_scope": "خدمات عمومی، امنیت و قواعدی که مستقیماً بر تعامل بازدیدکننده با مردم اثر می‌گذارند",
    },
}

TASK_TOPIC_SCOPE = {
    "task_1": {
        "core": {"accommodation"},
        "adjacent": {"transport_access", "food_services"},
    },
    "task_2": {
        "core": {"travel_periods", "attractions"},
        "adjacent": {"transport_access", "accommodation"},
    },
    "task_3": {
        "core": {"language_culture"},
        "adjacent": {
            "overview",
            "society_governance",
            "health_safety",
            "visitor_feedback",
        },
    },
}


def classify_task_relevance(task_id: str, topic_ids: tuple[str, ...]) -> str:
    """Classify topic relevance consistently instead of asking the LLM to guess."""

    scope = TASK_TOPIC_SCOPE.get(task_id)
    if scope is None:
        return "free_chat"
    topics = set(topic_ids)
    if topics & scope["core"]:
        return "core"
    if topics & scope["adjacent"]:
        return "adjacent"
    return "outside_task"


def task_reminder(task_id: str) -> str:
    task = TASK_CONTEXTS.get(task_id)
    if task is None:
        return ""
    return f"یادآوری: موضوع فعالیت فعلی «{task['title']}» است."


def format_task_context(task_id: str) -> str:
    """Return neutral scope guidance; free chat intentionally has no task boundary."""

    task = TASK_CONTEXTS.get(task_id)
    if task is None:
        return """حالت: گفت‌وگوی آزاد
دامنه: همه موضوع‌های موجود در منابع جزیره سپید. به پرسش کاربر مستقیماً پاسخ دهید و هیچ هدف فعالیتی را به او تحمیل نکنید."""

    return f"""نسخه زمینه فعالیت: {TASK_CONTEXT_VERSION}
زمینه مشترک:
{COMMON_CONTEXT}

فعالیت فعلی: {task['title']}
مسئله: {task['problem']}
هدف: {task['objective']}
دامنه اصلی: {task['core_scope']}
دامنه مجاور: {task['adjacent_scope']}

سیاست مرزبندی:
- پرسش در دامنه اصلی را طبیعی و کامل، فقط با اطلاعات بازیابی‌شده پاسخ دهید.
- پرسش مجاور را کوتاه پاسخ دهید و تنها ارتباط واقعی آن با مسئله فعلی را در یک جمله روشن کنید.
- اگر پرسش روشن اما خارج از مسئله این فعالیت است، اطلاعات را پنهان نکنید: پاسخ کوتاه و دقیق بدهید و فقط یادآوری کنید که تصمیم فعلی گروه درباره «{task['title']}» است.
- اگر پاسخ در منابع نیست، دقیقاً همان شکاف را بگویید؛ هدف فعالیت مجوز ساختن پاسخ نیست.
- سؤال بعدی مشخص پیشنهاد نکنید، کاربر را به مسیر ازپیش‌تعیین‌شده هل ندهید و نتیجه نهایی را به جای او انتخاب نکنید.
- این زمینه فقط دامنه و هدف را مشخص می‌کند و منبع واقعیت درباره جزیره نیست."""

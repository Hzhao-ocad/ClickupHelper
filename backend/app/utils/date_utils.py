from datetime import datetime, date, timedelta


def get_weekday_offset(day_name: str, from_date: date) -> int:
    """Return days from from_date until the next occurrence of day_name."""
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    target_idx = days.index(day_name.lower())
    cur_idx = from_date.weekday()
    if target_idx <= cur_idx:
        return (7 - cur_idx) + target_idx
    return target_idx - cur_idx


def resolve_relative_dates(ref_date: date | None = None) -> dict[str, str]:
    """
    Build a dictionary of pre-computed relative date examples for the LLM prompt.
    """
    today = ref_date or date.today()
    examples = {}

    examples["today"] = today.isoformat()
    examples["tomorrow"] = (today + timedelta(days=1)).isoformat()
    examples["yesterday"] = (today - timedelta(days=1)).isoformat()

    # Next <day>
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        key = f"next {day}"
        offset = get_weekday_offset(day, today)
        examples[key] = (today + timedelta(days=offset)).isoformat()

    # This <day>
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        key = f"this {day}"
        cur_idx = today.weekday()
        target_idx = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(day)
        if target_idx < cur_idx:
            offset = target_idx - cur_idx
            examples[key] = (today + timedelta(days=offset)).isoformat()
        else:
            examples[key] = (today + timedelta(days=target_idx - cur_idx)).isoformat()

    # Relative periods
    examples["next week"] = f"{(today + timedelta(days=7 - today.weekday())).isoformat()} to {(today + timedelta(days=13 - today.weekday())).isoformat()}"
    examples["in 1 week"] = (today + timedelta(days=7)).isoformat()
    examples["in 2 weeks"] = (today + timedelta(days=14)).isoformat()
    examples["in 1 month"] = (today + timedelta(days=30)).isoformat()
    examples["end of day"] = today.isoformat()
    examples["end of week"] = (today + timedelta(days=6 - today.weekday())).isoformat()
    examples["end of month"] = _end_of_month(today).isoformat()

    return examples


def _end_of_month(d: date) -> date:
    next_month = d.replace(day=28) + timedelta(days=4)
    return next_month - timedelta(days=next_month.day)

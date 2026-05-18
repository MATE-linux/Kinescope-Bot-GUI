# ---------- Функции для форматирования времени (режим 3) ----------
def format_time_sign(total_minutes):
    if total_minutes < 0:
        return -1, -total_minutes
    elif total_minutes > 0:
        return 1, total_minutes
    else:
        return 0, 0

def format_countdown_message(template, remaining_minutes, azat_factor):
    sign, abs_min = format_time_sign(remaining_minutes)
    hours = abs_min // 60
    minutes = abs_min % 60
    if sign == -1:
        hours_str = "-0" if hours == 0 else str(-hours)
    else:
        hours_str = str(hours)

    azat_min_total = int(remaining_minutes / azat_factor)
    sign_a, abs_azat_min = format_time_sign(azat_min_total)
    azat_hours = abs_azat_min // 60
    azat_minutes = abs_azat_min % 60
    if sign_a == -1:
        azat_hours_str = "-0" if azat_hours == 0 else str(-azat_hours)
    else:
        azat_hours_str = str(azat_hours)

    replacements = {
        "{minutes}": str(remaining_minutes),
        "{hours}": hours_str,
        "{minutes_mod}": str(minutes),
        "{azat_minutes}": str(azat_min_total),
        "{azat_hours}": azat_hours_str,
        "{azat_minutes_mod}": str(azat_minutes),
    }
    result = template
    for k, v in replacements.items():
        result = result.replace(k, v)
    return result
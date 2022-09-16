import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    result = datetime.datetime.now().year
    return {
        'year': int(result)
    }

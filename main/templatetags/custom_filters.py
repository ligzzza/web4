from django import template

register = template.Library()


@register.filter
def ru_plural(value, variants):
    """Склонение слов: 1 отзыв, 2 отзыва, 5 отзывов"""
    variants = variants.split(',')
    value = abs(int(value))

    if value % 10 == 1 and value % 100 != 11:
        return variants[0]
    elif 2 <= value % 10 <= 4 and (value % 100 < 10 or value % 100 >= 20):
        return variants[1]
    else:
        return variants[2]
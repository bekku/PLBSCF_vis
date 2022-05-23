from django import template

register = template.Library()

@register.filter
def get_type(value):
    return type(value)

@register.filter
def Isif_float(value):
    return type(value) == float

from django import template
import dateutil.parser

register = template.Library()

@register.filter
def humanize_duration(value):
     t = divmod(value* 60, 60)
     h = 'hours' if t[0] > 1 else 'hour'
     m = 'minutes' if t[1] > 1 else 'minute'
     return '{0:02.0f} {2} and {1:02.0f} {3}'.format(t[0],t[1], h, m)

@register.filter
def format_event_date(value):
     str_date = value.get('dateTime', value.get('date'))
     return dateutil.parser.parse(str_date).strftime("%b %d, %H:%M %p")


@register.filter
def multi_sum(value, arg):
     result = 0
     for item in value:
          result = result + item[arg]
     return result


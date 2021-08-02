from django.contrib import admin
import datetime

from .models import AdvUser, SubRubric, SuperRubric, AdditionalImage, Bb
from .utilities import send_activation_notification
from .forms import SubRubricForm

def send_activation_notifications(modeladmin, request, queryset): # действие, которое разошлет пользователям письма с предписаниями выполнить активацию
    for rec in queryset: # перебираем всех выбранных пользователей
        if not rec.is_activated:
            send_activation_notification(rec) # КТО Не ВЫПОЛНИЛ аКТИВацИЮ, ВЫЗЫВаеМ фуНКЦИЮ send_activation_notification,
            # объявленную ранее в модуле utilities.py и непосредственно производящую отправку писем.
    modeladmin.message_user(request, 'Письма с требованиями отправлены')
send_activation_notifications.short_description ='Отправка писем с требованиями активации'

class NoneactivatedFilter(admin.SimpleListFilter):
    title = 'Прошли активацию?'
    parameter_name = 'actstate'

    def lookups(self, request, model_admin):
        return (
            ('activated', 'Прошли'),
            ('threedays', 'Не прошли более 3 дней'),
            ('week', 'Не прошли более недели'),
        )
    def queryset(self, request, queryset):
        val = self.value()
        if val =='activated':
            return queryset.filter(is_active=True, is_activated=True)
        elif val == 'threedays':
            d = datetime.date.today() - datetime.timedelta(days=3)
            return queryset.filter(is_active=False, is_activated=False, date_joined=d)
        elif val == 'week':
            d = datetime.date.today() - datetime.timedelta(weeks=1)
            return queryset.filter(is_active=False, is_activated=False, date_joined=d)

class AdvUserAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_activated', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = (NoneactivatedFilter,)
    fields = (('username', 'email'), ('first_name', 'last_name'), ('send_messages', 'is_active', 'is_activated'),
              ('is_staff', 'is_superuser'), 'groups', 'user_permissions', ('last_login', 'date_joined'))
    readonly_fields = ('last_login', 'date_joined')
    actions = (send_activation_notifications,)

admin.site.register(AdvUser, AdvUserAdmin)

# встроенный редактор, чтобы пользователь, добавив новую надрубрику, смог сразу же заполнить ее подрубриками
#Из формы для ввода и правки надрубрик мы исключим поле надрубрики (super rubric),
class SubRubricInLine(admin.TabularInline):
    model = SubRubric

class SuperRubricAdmin(admin.ModelAdmin):
    exclude = ('super_rubric',)
    inlines = (SubRubricInLine,)

admin.site.register(SuperRubric, SuperRubricAdmin)

# класс редактора
class SubRubricAdmin(admin.ModelAdmin):
    form = SubRubricForm

admin.site.register(SubRubric,SubRubricAdmin)

# встроенный редактор дополнительных иллюстраций
class AdditionalImageInLine(admin.TabularInline):
    model = AdditionalImage

class BdAdmin(admin.ModelAdmin):
    list_display = ('rubric', 'title', 'content', 'author', 'created_at')
    fields = (('rubric', 'author'), 'title', 'content', 'price', 'contacts', 'image', 'is_active')
    inlines = (AdditionalImageInLine,)

admin.site.register(Bb, BdAdmin)
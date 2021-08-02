from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from captcha.fields import CaptchaField

from .models import AdvUser, SubRubric, SuperRubric, Bb, AdditionalImage, Comment
from .apps import user_registered

class ChangeUserInfoForm(forms.ModelForm):
    email = forms.EmailField(required=True, label='Адрес электронной почты')

    class Meta:
        model = AdvUser
        fields = ('username', 'email', 'first_name', 'last_name', 'send_messages')

class RegisterUserForm(forms.ModelForm):
    email = forms.EmailField(required=True, label= "Адрес электронной почты")
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput,
                                help_text=password_validation.password_validators_help_text_html)
    password2 = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput,
                                help_text=password_validation.password_validators_help_text_html)

    def clean_password1(self): #выполняем валидацию пароля, введенного в первое поле
        password1 = self.cleaned_data['password1']
        if password1:
            password_validation.validate_password(password1)
        return password1

    def clean(self): #проверяем, совпадают ли оба введенных пароля.
        super().clean()
        password1 = self.cleaned_data['password1']
        password2 = self.cleaned_data['password2']
        if password1 and password2 and password1 != password2:
            errors = {'password2':ValidationError('Введенные пароли не совпадают', code='password_mismatch')}
            raise ValidationError(errors)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_active = False # признак, является ли пользователь активным
        user.is_activated = False # признак, выполнил ли пользователь процедуру активации тем самым сообщая
        # фреймворку, что этот пользователь еще не может выполнять вход на сайт
        if commit:
            user.save()
        user_registered.send(RegisterUserForm, instance=user)
        return user

    class Meta:
        model = AdvUser
        fields = ('username', 'email', 'password1', 'password2', 'first_name', 'last_name', 'send_messages')

# У подрубрик сделаем поле надрубрики (super rubric) обязательным для заполнения.
class SubRubricForm(forms.ModelForm):
    super_rubric = forms.ModelChoiceField(
        queryset=SuperRubric.objects.filter(super_rubric__isnull=True), empty_label=None, label='Надрубрика', required=True) # убрали пустой пункт у раскрывающегося списка
#    присвоев параметру empty_label=None

    class Meta:
        model = SubRubric
        fields = '__all__'

# форма поиска, не связанная с моделью
class SearchForm(forms.Form):
    keyword = forms.CharField(required=False, max_length=20, label='')

# форма для ввода объявления
class BbForm(forms.ModelForm):
    class Meta:
        model = Bb
        fields = '__all__'
        widgets = {'author': forms.HiddenInput} # поле автора объявления зададим в качестве элемента управления Hiddenlnput,
        # т. е. скрытое поле — так как значения туда будут заноситься программно.

# форма для дополнительных иллюстраций
AIFormSet = forms.inlineformset_factory(Bb, AdditionalImage, fields='__all__')

# Форма для комментариев зарегистрированных пользователей
class UserCommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        exclude = ('is_active',)
        widgets = {'bb':forms.HiddenInput}

# Форма для комментариев гостей
class GuestCommentForm(forms.ModelForm):
    captcha = CaptchaField(label='Введите текст с картинки', error_messages={'invalid':'Неправильный текст'})

    class Meta:
        model = Comment
        exclude = ('is_active',)
        widgets = {'bb':forms.HiddenInput}
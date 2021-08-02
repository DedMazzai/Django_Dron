from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import UpdateView, CreateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView
from django.core.signing import BadSignature
from django.contrib.auth import logout
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import AdvUser, SubRubric, Bb, Comment
from .forms import ChangeUserInfoForm, RegisterUserForm, SearchForm, BbForm, AIFormSet, UserCommentForm, GuestCommentForm
from .utilities import signer

def index(request):
    bbs = Bb.objects.filter(is_active=True)[:10]
    context = {'bbs':bbs}
    return render(request, 'main/index.html', context)

def other_page(request, page):
    try:
        template = get_template('main/' + page + '.html')
    except TemplateDoesNotExist:
        raise Http404
    return HttpResponse(template.render(request=request))

# Реализует вход на сайт. При получении запроса по HTTP-методу GET он выводит на экран страницу входа с формой,
# в которую следует занести имя и пароль пользователя. При получении POST-запроса (после отправки формы) он ищет в
# списке пользователя с указанными именем и паролем. Если такой пользователь обнаружился,  выполняется перенаправление
# по интернет-адресу, взятому из GET- или POST параметра next, или, если такой параметр отсутствует, из параметра login_
# redirect-url настроек проекта.
class BBLoginView(LoginView):
    template_name = 'main/login.html' # путь к шаблону страницы входа

@login_required # допускает к странице только пользователей, выполнивших вход
def profile(request):
    bbs = Bb.objects.filter(author=request.user.pk) # фильтруем объявления по значению поля author
    context = {'bbs':bbs}
    return render(request, 'main/profile.html', context)

class BBLogoutView(LoginRequiredMixin, LogoutView): # LoginRequiredMixin — допускает к странице только пользователей, выполнивших вход.
    template_name = 'main/logout.html'

# Смена данных пользователя
class ChangeUserInfoView(SuccessMessageMixin, LoginRequiredMixin,UpdateView):
    model = AdvUser
    template_name = 'main/change_user_info.html'
    form_class = ChangeUserInfoForm
    success_url = reverse_lazy('main:profile')
    success_message = "Данные пользователя изменены"

    def setup(self, request, *args, **kwargs): # получение ключа текущего пользователя
        self.user_id = request.user.pk # извлекаем ключь пользователя из объекта текщего пользователя, хранящегося в атрибуте user и сохраняем его в user_id
        return super().setup(request, *args, **kwargs)

    def get_object(self, queryset=None): # Извлечение исправляемой записи
        if not queryset:
            queryset = self.get_queryset() # возвращает набор записей модели AdvUser
        return get_object_or_404(queryset, pk=self.user_id) # ищем запись, представляющую текущего пользователя и возвращаем ее

# смена пароля
class BBPasswordChangeView(SuccessMessageMixin, LoginRequiredMixin, PasswordChangeView):
    template_name = 'main/password_change.html'
    success_url = reverse_lazy('main:profile')
    success_message = "Пароль пользователя изменен"

# регистрация пользователя
class RegisterUserView(CreateView):
    model = AdvUser
    template_name = 'main/register_user.html'
    form_class = RegisterUserForm
    success_url = reverse_lazy('main:register_done')

class RegisterDoneView(TemplateView):
    template_name = 'main/register_done.html'

# Активация нового пользователя
def user_activate(request, sign):
    try:
        username = signer.unsign(sign) # извлекаем из идентификатора пользователя его имя
    except BadSignature: # Если цифровая подпись оказалась скомпрометированной, выводим страницу с сообщением о неуспехе активации
        return render(request, 'main/bad_signature.html')
    user = get_object_or_404(AdvUser, username=username)
    if user.is_activated: # если пользователь был активирован ранее (поле is activated уже хранит значение True) — выводим страницу с сообщением что активация уже произошла
        template = 'main/user_is_activated.html'
    else:
        template = 'main/activation_done.html'
        user.is_active = True # делаем пользователя активным
        user.is_activated = True # делаем пользователя активным
        user.save()
    return render(request, template)

# удаление пользователя
class DeleteUserView(LoginRequiredMixin, DeleteView):
    model = AdvUser
    template_name = 'main/delete_user.html'
    success_url = reverse_lazy('main:index')

    def setup(self, request, *args, **kwargs): # сохранили ключ текущего пользователя
        self.user_id = request.user.pk
        return super().setup(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        logout(request) # Перед удалением текущего пользователя необходимо выполнить выход
        messages.add_message(request, messages.SUCCESS, 'Пользователь удален') # сообщение об успешном удалении пользователя
        return super().post(request, *args, **kwargs)

    def get_object(self, queryset=None): # отыскали по ключу пользователя, подлежащего удалению
        if not queryset:
            queryset = self.get_queryset()
        return get_object_or_404(queryset, pk=self.user_id)

def by_rubric(request, pk):
    rubric = get_object_or_404(SubRubric,pk=pk) # извлекаем выбранную посетителем рубрику
    bbs = Bb.objects.filter(is_active=True, rubric=pk) # выбираем объявления, относящиеся к этой рубрике и помеченные для вывода
    # выполняем фильтрацию уже отобранных объявлений по введенному посетителем искомому слову, взятому из GET-параметра keyword.
    if 'keyword' in request.GET:
        keyword = request.GET['keyword'] # получаем искомое слово непосредственно из GET-параметра keyword.
        # формируем на основе полученного слова условие фильтрации, применив объект Q, и выполняем фильтрацию объявлений.
        q = Q(title__icontains=keyword) | Q(content__icontaints=keyword)
        bbs = bbs.filter(q)
    else:
        keyword = ''
    # создаем экземпляр формы SearchForm, чтобы вывести ее на экран. Конструктору ее класса в параметре initial передаем
    # полученное ранее искомое слово, чтобы оно присутствовало в выведенной на экран форме
    form = SearchForm(initial={'keyword':keyword})
    paginator = Paginator(bbs, 2)
    if 'page' in request.GET:
        page_num = request.GET['page']
    else:
        page_num = 1
    page = paginator.get_page(page_num)
    context = {'rubric': rubric, 'page': page, 'bbs':page.object_list, 'form':form}
    return render(request, 'main/by_rubric.html', context)

def detail(request, rubric_pk, pk):
    bb = Bb.objects.get(pk=pk)
    ais = bb.additionalimage_set.all()
    comments = Comment.objects.filter(bb=pk, is_active=True)
    initial = {'bb':bb.pk} # ключ выводящегося на странице объявления — с ним будет связан добавляемый комментарий
    if request.user.is_authenticated: # Если текущий пользователь выполнил вход на сайт, заносим его имя в поле author этой формы комментария
        initial['author'] = request.user.username
        form_class = UserCommentForm
    else:
        form_class = GuestCommentForm
    form = form_class(initial=initial)
    if request.method =="POST":
        c_form = form_class(request.POST)
        if c_form.is_valid():
            c_form.save()
            messages.add_message(request, messages.SUCCESS, 'Комментарий добавлен')
        else:
            form = c_form
            messages.add_message(request, messages.WARNING, 'Комментарий не добавлен')
    context = {'bb':bb, 'ais':ais, 'comments':comments, 'form':form}
    return render(request, 'main/detail.html', context)

@ login_required
def profile_bb_detail(request, pk):
    bb = get_object_or_404(Bb, pk=pk)
    ais = bb.additionalimage_set.all()
    context = {'bb':bb, 'ais':ais}
    return render(request, 'main/profile_bb_detail.html', context)

@login_required
def profile_bb_add(request):
    if request.method == 'POST':
        form = BbForm(request.POST, request.FILES) # при создании объектов формы и набора форм, мы должны передать
        # конструкторам их классов вторым позиционным параметром словарь со всеми полученными файлами (он хранится
        # в атрибуте files объекта запроса). Если мы не сделаем этого, то отправленные пользователем иллюстрации окажутся потерянными.
        if form.is_valid(): # при сохранении мы сначала выполняем валидацию и сохранение формы самого объявления.
        # Метод save о в качестве результата возвращает сохраненную запись, и эту запись мы должны передать через параметр instance конструктору
        #  класса набора форм. Это нужно для того, чтобы все дополнительные иллюстрации после сохранения оказались связанными с объявлением.
            bb = form.save()
            formset = AIFormSet(request.POST, request.FILES, instance=bb)
            if formset.is_valid():
                formset.save()
                messages.add_message(request, messages.SUCCESS, "Объявление добавлено")
                return redirect('main:profile')
    else:
        form = BbForm(initial={'author': request.user.pk}) # заносим в поле author формы ключ текущего пользователя, который станет автором объявления.
        formset = AIFormSet()
    context = {'form':form, 'formset':formset}
    return render(request, 'main/profile_bb_add.html', context)

@login_required
def profile_bb_change(request, pk):
    bb = get_object_or_404(Bb, pk=pk)
    if request.method == "POST":
        form = BbForm(request.POST, request.FILES, instance=bb)
        if form.is_valid():
            bb = form.save()
            formset = AIFormSet(request.POST, request.FILES, instance=bb)
            if formset.is_valid():
                formset.save()
                messages.add_message(request, messages.SUCCESS, 'Объявление исправлено')
                return redirect('main:profile')
    else:
        form = BbForm(instance=bb)
        formset = AIFormSet(instance=bb)
        context = {'form':form, 'formset':formset}
        return render(request, 'main/profile_bb_change.html', context)

@login_required
def profile_bb_delete(request, pk):
    bb = get_object_or_404(Bb, pk=pk)
    if request.method == 'POST':
        bb.delete()
        messages.add_message(request, messages.SUCCESS, "Объявление удалено")
        return redirect('main:profile')
    else:
        context = {'bb':bb}
        return render(request, 'main/profile_bb_delete.html', context)


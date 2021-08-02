from .models import SubRubric

"""Обработчик контекста в котором будет формироваться список подрубрик"""
def bboard_context_prosessor(request):
    context = {}
    context['rubrics'] = SubRubric.objects.all()
    context['keyword'] = '' # переменная keyword — с GET-параметром keyword, который понадобится для генерирования интернет-адресов в гиперссылках пагинатора
    context['all'] = '' #  переменная all— с GET-параметрами keyword и раgе, которые мы добавим к интернетадресам гиперссылок, указывающих на страницы сведений об объявлениях
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            context['keyword'] = '?=keyword=' + keyword
            context['all'] = context['keyword']
    if 'page' in request.GET:
        page = request.GET['page']
        if page != '1':
            if context['all']:
                context ['all'] += '&page=' + page
            else:
                context['all'] = '?page=' + page
    return context

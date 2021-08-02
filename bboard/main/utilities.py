from os.path import splitext
from datetime import datetime
from django.template.loader import render_to_string
from django.core.signing import Signer

from bboard.settings import ALLOWED_HOSTS

signer = Signer()

# Чтобы сформировать интернет-адрес, ведущий на страницу подтверждения активации, понадобится, домен, на котором находится наш сайт, и
# некоторое значение, уникально идентифицирующее только что зарегистрированного пользователя и при этом устойчивое к попыткам его подделать.
def send_activation_notification(user):
    if ALLOWED_HOSTS:
        host = 'http://' + ALLOWED_HOSTS[0]
    else:
        host = 'http://localhost:8000'
    context = {'user':user, 'host':host, 'sign':signer.sign(user.username)}  # В качестве уникального и стойкого к подделке
    # идентификатора пользователя применяем его имя, защищенное цифровой подписью. Создание цифровой подписи выполняем посредством класса signer
    subject = render_to_string('email/activation_letter_subject.txt', context) # текст темы письма
    body_text = render_to_string('email/activation_letter_body.txt', context) # текст тела письма
    user.email_user(subject, body_text)

def get_timestamp_path(instance, filename):
    return f'{datetime.now().timestamp()}{splitext(filename)[1]}'

# отправка уведомления о новом комментарии
# def send_new_comment_notification(comment):
#     if ALLOWED_HOSTS:
#         host = f'http://{ALLOWED_HOSTS[0]}'
#     else:
#         host = 'http://localhost:8000'
#     author = comment.bb.author
#     content = {'author':author, 'host':host, 'comment':comment}
#     subject = render_to_string('email/new_comment_letter_subject.txt', content)
#     body_text = render_to_string('email/new_comment_letter_body.txt', comment)
#     author.email_user(subject, body_text)
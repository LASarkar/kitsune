from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives

import bleach
from celery.task import task
from tower import ugettext as _

from announcements.models import Announcement
from sumo.email_utils import render_email, safe_translation, send_messages


@task
def send_group_email(announcement_id):
    """Build and send the announcement emails to a group."""
    try:
        announcement = Announcement.objects.get(pk=announcement_id)
    except Announcement.DoesNotExist:
        return

    group = announcement.group
    users = User.objects.filter(groups__in=[group])
    plain_content = bleach.clean(announcement.content_parsed,
                                 tags=[], strip=True).strip()
    email_kwargs = {'content': plain_content,
                    'domain': Site.objects.get_current().domain}
    text_template = 'announcements/email/announcement.ltxt'
    html_template = None

    @safe_translation
    def _make_mail(locale, user):
        subject = _('New announcement for {group}').format(
            group=group.name)

        msg = EmailMultiAlternatives(
            subject,
            render_email(text_template, email_kwargs),
            settings.TIDINGS_FROM_ADDRESS,
            [user.email])

        if html_template:
            msg.attach_alternative(
                render_email(html_template, email_kwargs), 'text/html')

        return msg

    messages = []
    for u in users:
        # Localize email each time.
        locale = u.profile.locale or settings.LANGUAGE_CODE
        messages.append(_make_mail(locale, u))

    send_messages(messages)

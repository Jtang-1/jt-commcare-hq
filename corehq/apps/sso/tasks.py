import datetime
import logging

from celery.schedules import crontab

from corehq.apps.celery import periodic_task
from corehq.apps.hqwebapp.tasks import send_html_email_async
from corehq.apps.sso.models import (
    AuthenticatedEmailDomain,
    IdentityProvider,
    IdentityProviderProtocol,
    IdentityProviderType,
    UserExemptFromSingleSignOn
)
from corehq.apps.sso.utils.context_helpers import (
    get_idp_cert_expiration_email_context,
    get_sso_deactivation_skip_email_context,
)
from corehq.apps.sso.utils.user_helpers import get_email_domain_from_username
from corehq.apps.users.models import WebUser
from dimagi.utils.logging import notify_exception

log = logging.getLogger(__name__)


IDP_CERT_EXPIRES_REMINDER_DAYS = [30, 15, 7, 3, 1, 0]


@periodic_task(run_every=crontab(minute=0, hour=22), acks_late=True)
def renew_service_provider_x509_certificates():
    """
    This task renews the x509 Service Provider certificates one week before
    they expire (so that there is ample time to respond if there is a problem).
    """
    in_one_week = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    for idp in IdentityProvider.objects.filter(
        protocol=IdentityProviderProtocol.SAML,
        sp_rollover_cert_public__isnull=False,
        date_sp_cert_expiration__lte=in_one_week
    ).all():
        idp.renew_service_provider_certificate()


@periodic_task(run_every=crontab(minute=0, hour=22), acks_late=True)
def create_rollover_service_provider_x509_certificates():
    """
    This task creates a rollover x509 Service Provider certificate two
    weeks before it expires.
    """
    in_two_weeks = datetime.datetime.utcnow() + datetime.timedelta(days=14)
    for idp in IdentityProvider.objects.filter(
        protocol=IdentityProviderProtocol.SAML,
        sp_rollover_cert_public__isnull=True,
        date_sp_cert_expiration__lte=in_two_weeks
    ).all():
        idp.create_rollover_service_provider_certificate()


@periodic_task(run_every=crontab(minute=0, hour=22), acks_late=True)
def idp_cert_expires_reminder():
    """
    Sends reminder emails for IdP certificates expiring N days from today.
    """
    for num_days in IDP_CERT_EXPIRES_REMINDER_DAYS:
        send_idp_cert_expires_reminder_emails(num_days)


def send_idp_cert_expires_reminder_emails(num_days):
    """
    Sends a reminder email to the enterprise admin email addresses specified on
    the IdP's owner account for any IdPs with certificates that will expire on
    the date `num_days` from today.

    :param num_days: Query IdP certs expiring `num_days` from today.
    """
    today = datetime.datetime.utcnow().date()
    date_in_n_days = today + datetime.timedelta(days=num_days)
    day_after_that = date_in_n_days + datetime.timedelta(days=1)
    queryset = IdentityProvider.objects.filter(
        protocol=IdentityProviderProtocol.SAML,
        is_active=True,
        date_idp_cert_expiration__gte=date_in_n_days,
        date_idp_cert_expiration__lt=day_after_that,
    )
    for idp in queryset.all():
        context = get_idp_cert_expiration_email_context(idp)
        if not context["to"]:
            log.error(f"no admin email addresses for IdP: {idp}")
        try:
            for send_to in context["to"]:
                send_html_email_async.delay(
                    context["subject"],
                    send_to,
                    context["html"],
                    text_content=context["plaintext"],
                    email_from=context["from"],
                    bcc=context["bcc"],
                )
                log.info(
                    "Sent %(num_days)s-day certificate expiration reminder "
                    "email for %(idp_name)s to %(send_to)s." % {
                        "num_days": num_days,
                        "idp_name": idp.name,
                        "send_to": send_to,
                    }
                )
        except Exception as exc:
            log.error(
                f"Failed to send cert reminder email for IdP {idp}: {exc!s}",
                exc_info=True,
            )


@periodic_task(run_every=crontab(minute=0, hour=2), acks_late=True)
def auto_deactivate_removed_sso_users():
    for idp in IdentityProvider.objects.filter(
        enable_user_deactivation=True,
        idp_type=IdentityProviderType.AZURE_AD
    ).all():
        idp_users = idp.get_all_members_of_the_idp()
        usernames_in_account = idp.owner.get_web_users(info_type='username')

        # Get criteria for exempting usernames and email domains from the deactivation list
        authenticated_domains = AuthenticatedEmailDomain.objects.filter(identity_provider=idp)
        exempt_usernames = UserExemptFromSingleSignOn.objects.filter(email_domain__in=authenticated_domains
                                                                     ).values_list('username', flat=True)

        if len(idp_users) == 0 and len(usernames_in_account) - len(exempt_usernames) > 3:
            context = get_sso_deactivation_skip_email_context(idp)
            if not context["to"]:
                notify_exception(None, f"no admin email addresses for IdP: {idp}")
            try:
                for send_to in context["to"]:
                    send_html_email_async.delay(
                        context["subject"],
                        send_to,
                        context["html"],
                        text_content=context["plaintext"],
                        email_from=context["from"],
                        bcc=context["bcc"],
                    )
                    log.info(
                        "Sent sso user deactivation skipped notification"
                        "email for %(idp_name)s to %(send_to)s." % {
                            "idp_name": idp.name,
                            "send_to": send_to,
                        }
                    )
            except Exception as exc:
                notify_exception(None, f"Failed to send sso user deactivation skipped notification email for"
                                       f" IdP {idp}: {exc!s}", exc_info=True)
            return

        usernames_to_deactivate = []
        authenticated_email_domains = authenticated_domains.values_list('email_domain', flat=True)

        for username in usernames_in_account:
            if username not in idp_users and username not in exempt_usernames:
                email_domain = get_email_domain_from_username(username)
                if email_domain in authenticated_email_domains:
                    usernames_to_deactivate.append(username)

        # Deactivate user that is not returned by Graph Users API
        for username in usernames_to_deactivate:
            user = WebUser.get_by_username(username)
            if user and user.is_active:
                user.is_active = False
                user.save()

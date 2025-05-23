from django.core.management import call_command
from django.db import migrations

from corehq.apps.accounting.models import SoftwarePlanEdition
from corehq.privileges import CASE_COPY
from corehq.util.django_migrations import skip_on_fresh_install


@skip_on_fresh_install
def _grandfather_copy_cases_priv(apps, schema_editor):
    call_command('cchq_prbac_bootstrap')

    skip_editions = ','.join((
        SoftwarePlanEdition.PAUSED,
        SoftwarePlanEdition.FREE,
        SoftwarePlanEdition.STANDARD,
        SoftwarePlanEdition.PRO,
    ))
    call_command(
        'cchq_prbac_grandfather_privs',
        CASE_COPY,
        skip_edition=skip_editions,
        noinput=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0083_data_dictionary_priv'),
    ]

    operations = [
        migrations.RunPython(
            _grandfather_copy_cases_priv,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

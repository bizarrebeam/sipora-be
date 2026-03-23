from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('akun', '0003_add_search_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pengguna',
            name='is_deleted',
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]

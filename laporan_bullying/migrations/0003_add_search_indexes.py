from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laporan_bullying', '0002_riwayatstatusbullying'),
    ]

    operations = [
        migrations.AlterField(
            model_name='laporanbullying',
            name='no_laporan',
            field=models.CharField(db_index=True, editable=False, max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name='laporanbullying',
            name='judul',
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='laporanbullying',
            name='lokasi',
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='laporanbullying',
            name='tanggal_kejadian',
            field=models.DateField(db_index=True),
        ),
        migrations.AlterField(
            model_name='laporanbullying',
            name='jenis_bullying',
            field=models.CharField(
                choices=[
                    ('fisik', 'Fisik'),
                    ('verbal', 'Verbal'),
                    ('sosial', 'Sosial'),
                    ('cyber', 'Cyber'),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='laporanbullying',
            name='status',
            field=models.CharField(
                choices=[
                    ('menunggu', 'Menunggu'),
                    ('diproses', 'Diproses'),
                    ('selesai', 'Selesai'),
                    ('ditolak', 'Ditolak'),
                    ('dibatalkan', 'Dibatalkan'),
                ],
                db_index=True,
                default='menunggu',
                max_length=20,
            ),
        ),
    ]

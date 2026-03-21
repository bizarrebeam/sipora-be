from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laporan_kerusakan', '0003_alter_laporankerusakan_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='laporankerusakan',
            name='no_laporan',
            field=models.CharField(db_index=True, editable=False, max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name='laporankerusakan',
            name='judul',
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='laporankerusakan',
            name='lokasi',
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='laporankerusakan',
            name='tanggal_kejadian',
            field=models.DateField(db_index=True),
        ),
        migrations.AlterField(
            model_name='laporankerusakan',
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

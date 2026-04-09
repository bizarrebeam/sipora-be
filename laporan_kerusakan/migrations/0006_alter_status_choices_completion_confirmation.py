from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laporan_kerusakan', '0005_alter_laporankerusakan_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='laporankerusakan',
            name='status',
            field=models.CharField(
                choices=[
                    ('menunggu', 'Menunggu Konfirmasi'),
                    ('diproses', 'Diproses'),
                    ('menunggu_konfirmasi_selesai', 'Menunggu Konfirmasi Selesai'),
                    ('selesai', 'Selesai'),
                    ('ditolak', 'Ditolak'),
                    ('dibatalkan', 'Dibatalkan'),
                ],
                db_index=True,
                default='menunggu',
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name='riwayatstatuslaporan',
            name='status',
            field=models.CharField(
                choices=[
                    ('menunggu', 'Menunggu Konfirmasi'),
                    ('diproses', 'Diproses'),
                    ('menunggu_konfirmasi_selesai', 'Menunggu Konfirmasi Selesai'),
                    ('selesai', 'Selesai'),
                    ('ditolak', 'Ditolak'),
                    ('dibatalkan', 'Dibatalkan'),
                ],
                max_length=40,
            ),
        ),
    ]

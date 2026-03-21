from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aspirasi', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aspirasi',
            name='no_laporan',
            field=models.CharField(db_index=True, editable=False, max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name='aspirasi',
            name='judul',
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='aspirasi',
            name='kategori',
            field=models.CharField(
                choices=[
                    ('sarana', 'Sarana & Prasarana'),
                    ('kurikulum', 'Kurikulum & Pembelajaran'),
                    ('layanan', 'Layanan Infrastruktur & Akademik'),
                    ('ekstrakulikuler', 'Ekstrakulikuler & Bakat'),
                    ('kesehatan', 'Kesehatan & Keamanan'),
                    ('lainnya', 'Lainnya'),
                ],
                db_index=True,
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name='aspirasi',
            name='status_ditandai',
            field=models.CharField(
                choices=[
                    ('ditandai', 'Ditandai'),
                    ('tidak_ditandai', 'Tidak Ditandai'),
                ],
                db_index=True,
                default='tidak_ditandai',
                max_length=20,
            ),
        ),
    ]

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('laporan_kerusakan', '0005_alter_laporankerusakan_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TanggapanLaporanKerusakan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nama_pengirim', models.CharField(max_length=255)),
                ('pesan', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('laporan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tanggapan', to='laporan_kerusakan.laporankerusakan')),
                ('pengirim', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tanggapan_kerusakan', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Tanggapan Laporan Kerusakan',
                'verbose_name_plural': 'Tanggapan Laporan Kerusakan',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='tanggapanlaporankerusakan',
            index=models.Index(fields=['laporan', 'created_at'], name='tanggapan_la_laporan_idx'),
        ),
    ]

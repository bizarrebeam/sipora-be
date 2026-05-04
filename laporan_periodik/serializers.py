"""
Serializers module for the laporan_periodik application.

Handles serialization of aggregated periodic reports data.
"""

from rest_framework import serializers


class AggregatedReportSerializer(serializers.Serializer):
    """
    Serializer for aggregated report data across different report types.
    Includes a unified structure for reports from different sources.
    """
    id = serializers.CharField()
    judul = serializers.CharField()
    tanggal = serializers.DateTimeField()
    kategori = serializers.CharField()
    status = serializers.CharField()
    no_laporan = serializers.CharField()
    tipe_laporan = serializers.CharField()  # 'bullying', 'kerusakan', 'aspirasi'


class LaporanPeriodikSummarySerializer(serializers.Serializer):
    """
    Serializer for periodic report summary statistics.
    """
    total_reports = serializers.IntegerField()
    bullying_count = serializers.IntegerField()
    kerusakan_count = serializers.IntegerField()
    status_distribution = serializers.DictField(
        child=serializers.IntegerField()
    )
    kategori_distribution = serializers.DictField(
        child=serializers.IntegerField()
    )


class LaporanPeriodikResponseSerializer(serializers.Serializer):
    """
    Serializer for the complete periodic report response.
    """
    summary = LaporanPeriodikSummarySerializer()
    reports = AggregatedReportSerializer(many=True)

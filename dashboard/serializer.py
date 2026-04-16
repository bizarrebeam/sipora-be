"""
Serializers module for the dashboard application.

Contains serializers to format and validate the complex aggregated dictionary 
data returned by the dashboard API views before sending it to the client.
"""

from rest_framework import serializers

class DashboardBullyingSerializer(serializers.Serializer):
    """
    Serializer for formatting Bullying dashboard data.
    
    Structures metrics, period differences, categorical counts (status, jenis),
    top lists (locations, classes), and timeline trends.
    """
    metrics = serializers.DictField(child=serializers.IntegerField())
    differences = serializers.DictField(child=serializers.IntegerField()) 
    by_status = serializers.DictField(child=serializers.IntegerField())
    by_jenis = serializers.DictField(child=serializers.IntegerField())
    top_locations = serializers.ListField(child=serializers.DictField(), required=False)
    top_classes = serializers.ListField(child=serializers.DictField(), required=False)
    trend = serializers.DictField()

    def to_representation(self, instance):
        return instance


class DashboardKerusakanAspirasiSerializer(serializers.Serializer):
    """
    Serializer for formatting combined Kerusakan and Aspirasi dashboard data.
    
    Structures general metrics, differences, status counts for damages, 
    damage report trends, and aspiration category distributions.
    """   
    metrics = serializers.DictField(child=serializers.IntegerField())
    differences = serializers.DictField(child=serializers.IntegerField())
    by_status_kerusakan = serializers.DictField(child=serializers.IntegerField())
    kerusakan_trend = serializers.DictField()
    aspirasi_distribution = serializers.DictField()

    def to_representation(self, instance):
        return instance
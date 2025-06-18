from rest_framework import serializers
from django.http import HttpRequest
class BaseModelSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    updated_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        abstract = True

    def create(self, validated_data):
        request:HttpRequest = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            validated_data['updated_by'] = request.user

        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        request:HttpRequest = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data['updated_by'] = request.user
        return super().update(instance, validated_data)
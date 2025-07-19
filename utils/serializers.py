from rest_framework import serializers
from django.http import HttpRequest
class BaseModelSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    updated_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        pass

    def create(self, validated_data):
        request:HttpRequest = self.context.get("request").user
        if request and request.is_authenticated:
            validated_data['created_by'] = request
            validated_data['updated_by'] = request

        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        request:HttpRequest = self.context.get("request").user
        if request and request.is_authenticated:
            validated_data['updated_by'] = request
        return super().update(instance, validated_data)
    

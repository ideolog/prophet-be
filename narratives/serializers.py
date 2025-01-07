from rest_framework import serializers
from .models import *


class ClaimSerializer(serializers.ModelSerializer):
    verification_status_name = serializers.CharField(source='verification_status.name', read_only=True)

    class Meta:
        model = Claim
        fields = ['id', 'text', 'verification_status', 'verification_status_name', 'status_description']


class NarrativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Narrative
        fields = ['slug', 'description', 'modality']  # You can add more fields if necessary

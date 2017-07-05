# -*- coding: utf-8 -*-
from rest_framework import serializers
from api.models import Parameters

class ParameterSerializer(serializers.ModelSerializer):
	class Meta:
		model = Parameters
		fields = ('id', 'nolineest', 'height', 'pad', 'nonormalize', 'llocs', 
			'alocs', 'probabilities', 'estrate', 'estconf', 'compare', 'context', 
			'quiet', 'nocheck', 'parallel')
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

class Parameters(models.Model):
	### The following 11 parameters can be overwritten by users
	# line dewarping (usually contained in model)
	nolineest = models.BooleanField(default=False, help_text="target line height (do not overrides recognizer)")
	height = models.IntegerField(default=-1, help_text="target line height (do not overrides recognizer)")
    # recognition
	#model = models.FloatField(default=1.0, help_text="minimum scale permitted")
	pad = models.IntegerField(default=16, help_text="extra blank padding to the left and right of text line")
	nonormalize = models.BooleanField(default=False, help_text="don't normalize the textual output from the recognizer")
	llocs = models.BooleanField(default=False, help_text="output LSTM locations for characters")
	alocs = models.BooleanField(default=False, help_text="output aligned LSTM locations for characters")
	probabilities = models.BooleanField(default=False, help_text="output probabilities for each letter")
    # error measures
	estrate = models.BooleanField(default=False, help_text="estimate error rate only")
	estconf = models.IntegerField(default=8, help_text="estimate confusion matrix")
	compare = models.CharField(default="nospace", max_length=50, help_text="string comparison used for error rate estimate")
	context = models.IntegerField(default=0, help_text="context for error reporting")

	### The following parameters needn't be overwritten by users
	quiet = models.BooleanField(default=False, help_text="be less verbose, usally use with parallel together")
	nocheck = models.BooleanField(default=True, help_text="disable error checking on inputs")
	parallel = models.IntegerField(default=0, help_text="number of parallel processes to use")
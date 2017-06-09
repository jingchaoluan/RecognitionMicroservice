# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render
from wsgiref.util import FileWrapper
from .recognition import recognition_exec, del_service_files
import sys, os, os.path, zipfile, StringIO


# Get the directory which stores all input and output files
dataDir = settings.MEDIA_ROOT

def index(request):
    return render(request, 'index.html')

@csrf_exempt
@api_view(['GET', 'POST'])
def recognitionView(request, format=None):

    # Receive uploaded binarized image(s)
    keys = request.data.keys()
    if len(keys)<1:
	return HttpResponse("Please selecting at least one segmented image.")
    for key in keys:
	uploadedimage = request.data.get(key)
	imagename = str(uploadedimage)
    	default_storage.save(dataDir+"/"+imagename, uploadedimage)
	
    # Call OCR recognition function
    alltext_file = recognition_exec(dataDir)

    # One file: return directly
    fdir, fname = os.path.split(alltext_file)
    short_report = open(alltext_file, 'rb')
    response = HttpResponse(FileWrapper(short_report), content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename=%s' % fname

    # Delete all files related to this service time
    del_service_files(dataDir)

    return response

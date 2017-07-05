# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render
from wsgiref.util import FileWrapper
from .serializers import ParameterSerializer
from .recognition import recognition_exec
from .extrafunc import del_service_files
import sys, os, os.path, zipfile, StringIO, glob


# Get the directory which stores all input and output files
dataDir = settings.MEDIA_ROOT

def index(request):
    return render(request, 'index.html')

@csrf_exempt
@api_view(['GET', 'POST'])
def recognitionView(request, format=None):
    if request.data.get('image') is None:
        return HttpResponse("Please upload at least one binarized image.")

    # Receive specified parameters values
    # Receive parameters with model and serializer
    data_dict = request.data.dict()
    del data_dict['image']   # Image will be processed seperately for receiving multiple images
    # Serialize the specified parameters, only containing the specified parameters
    # If we want to generate the parameters object with all of the default paremeters, call parameters.save()
    paras_serializer = ParameterSerializer(data=data_dict)
    if paras_serializer.is_valid():
        pass # needn't parameters.save(), since we needn't to store these parameters in DB

    # Receive and store uploaded image(s)
    # One or multiple images/values in one field
    imagepaths = []
    images = request.data.getlist('image')
    for image in images:
        image_str = str(image)
        imagepaths.append(dataDir+"/"+image_str)
        default_storage.save(dataDir+"/"+image_str, image)
	
    # Call OCR recognition function
    #alltext_file = recognition_exec(dataDir)
    recognition_exec(imagepaths, paras_serializer.data)

    # Write all of the line results into a single file
    results = glob.glob(dataDir+"/*.txt")
    alltext_file = dataDir + "/recog_output.txt"
    with open(alltext_file, "wb") as outfile:
        for result in results:
            with open(result, "rb") as infile:
                outfile.write(infile.read())
                infile.close()
    outfile.close()

    # One file: return directly
    fdir, fname = os.path.split(alltext_file)
    short_report = open(alltext_file, 'rb')
    response = HttpResponse(FileWrapper(short_report), content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename=%s' % fname

    # Delete all files related to this service time
    del_service_files(dataDir)

    return response

# -*- coding: utf-8 -*-
from django.conf import settings
import sys, os, os.path, subprocess, shutil

# Get the directory of ocropy script
ocropyDir = settings.BASE_DIR + "/ocropy"

# Get the directory which stores all input and output files
dataDir = settings.MEDIA_ROOT

# Execute ocr recognition script: recognize the text line
# Parameter: the directory of the segmented line images
# Return: a list conaining all line text files and a over-all text file
def recognition_exec(segmentedImageDir):

    # Call text recognition script
    recog_model = ocropyDir + "/models/en-default.pyrnn.gz"
    recog_inputPath = segmentedImageDir + "/??????.bin.png"
    recog_cmd = ocropyDir + "/ocropus-rpred -n -Q 2 -m " + recog_model + " " + recog_inputPath
    r_recog = subprocess.call([recog_cmd], shell=True)
    if r_recog != 0:
        sys.exit("Error: Text recognition process failed")
    
    # Generate output file
    alltext_file = segmentedImageDir + "/recog_output.txt"
    cat_cmd = "cat " + segmentedImageDir + "/??????.txt >" + alltext_file
    r_genOutput = subprocess.call([cat_cmd], shell=True)
    if r_genOutput != 0:
        sys.exit("Error: Generate output process failed")
    '''
    output_list = []
    for the_file in os.listdir(segmentedImageDir):
	if the_file.endswith(".txt"):
	    file_path = os.path.join(segmentedImageDir, the_file)
	    output_list.append(file_path)
    '''
    
    return alltext_file

# Delete all files related to this service time, including inputs and outputs
def del_service_files(dataDir):

    for the_file in os.listdir(dataDir):
	file_path = os.path.join(dataDir, the_file)
	try:
	    if os.path.isfile(file_path):
		os.unlink(file_path)
	    elif os.path.isdir(file_path):
		shutil.rmtree(file_path)
	except Exception as e:
	    print(e)


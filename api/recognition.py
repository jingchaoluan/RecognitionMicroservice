#!/usr/bin/env python

from __future__ import print_function

import traceback
import codecs
from pylab import *
import os.path
import ocrolib
import argparse
import matplotlib
from multiprocessing import Pool
from ocrolib import edist
from ocrolib.exceptions import FileNotFound, OcropusException
from collections import Counter
from ocrolib import lstm
from scipy.ndimage import measurements
from django.conf import settings


# Get the directory which stores all input and output files
dataDir = settings.MEDIA_ROOT
# The directory of the default model
modelPath = settings.BASE_DIR + "/models/en-default.pyrnn.gz"

# The default parameters values
# Users can custom the first 11 parameters
args = {
    # line dewarping (usually contained in model)
    'nolineest':False,   # target line height (do not overrides recognizer)
    'height':-1,        # target line height (do not overrides recognizer)

    # recognition
    'model':modelPath,  # line recognition model
    'pad':16,           # extra blank padding to the left and right of text line
    'nonormalize':False, # don't normalize the textual output from the recognizer, don't apply standard Unicode normalizations for OCR
    'llocs':False,       # output LSTM locations for characters
    'alocs':False,       # output aligned LSTM locations for characters
    'probabilities':False,# output probabilities for each letter

    # error measures
    'estrate':False,     # estimate error rate only
    'estconf':20,       # estimate confusion matrix
    'compare':"nospace",# string comparison used for error rate estimate
    'context':0,        # context for error reporting

    ### The following parameters cannot be overwritten by users
    'nocheck':True,     # disable error checking on images
    'quiet':False,       # turn off most output
    'parallel':0        # number of parallel processes to use
}


# The entry of segmentation service
# Return the directories, each directory related to a input image and stored the segmented line images  
def recognition_exec(images, parameters):
    args.update(parameters)
    print("==========")
    print(args)

    if len(images)<1:
        sys.exit(0)

    # Unicode to str
    for i, image in enumerate(images):
        images[i] = str(image)

    # Get the line normalizer
    get_linenormalizer()

    # Call process to execute recognition
    if args['parallel']==0:
        results = []
        for trial,fname in enumerate(images):
            results.append(process((trial,fname)))
    elif args['parallel']==1:
        results = []
        for trial,fname in enumerate(images):
            results.append(safe_process((trial,fname)))
    else:
        pool = Pool(processes=args['parallel'])
        results = []
        for r  in pool.imap_unordered(safe_process,enumerate(images)):
            result.append(r)
            if not args['quiet'] and len(results)%100==0:
                sys.stderr.write("==== %d of %d\n"%(len(results),len(images)))

    results = [x for x in results if x is not None]

    # Caculate error rate
    confusions = []
    if args['estrate']:
        terr = 0
        total = 0
        for err,conf,n,trial,fname, in results:
            terr += err
            total += n
            confusions += conf
        print_info("%.5f %d %d %s" % (terr*1.0/total, terr, total, args['model']))
        if args['estconf']>0:
            print_info("top %d confusions (count pred gt), comparison: %s" % (
                args['estconf'], args['compare']))
            for ((u,v),n) in Counter(confusions).most_common(args['estconf']):
                print_info("%6d %-4s %-4s" % (n, u ,v))

    '''
    # Write all of the line results into a single file
    all_in_one_result = dataDir + "/recog_output.txt"
    with open(all_in_one_result, "wb") as outfile:
        for result in results:
            with open(result, "rb") as infile:
                outfile.write(infile.read())
                infile.close()
    outfile.close()
    return all_in_one_result
    '''



def print_info(*objs):
    print("INFO: ", *objs, file=sys.stdout)

def print_error(*objs):
    print("ERROR: ", *objs, file=sys.stderr)

def check_line(image):
    if len(image.shape)==3: return "input image is color image %s"%(image.shape,)
    if mean(image)<median(image): return "image may be inverted"
    h,w = image.shape
    if h<20: return "image not tall enough for a text line %s"%(image.shape,)
    if h>200: return "image too tall for a text line %s"%(image.shape,)
    if w<1.5*h: return "line too short %s"%(image.shape,)
    if w>4000: return "line too long %s"%(image.shape,)
    ratio = w*1.0/h
    _,ncomps = measurements.label(image>mean(image))
    lo = int(0.5*ratio+0.5)
    hi = int(4*ratio)+1
    if ncomps<lo: return "too few connected components (got %d, wanted >=%d)"%(ncomps,lo)
    if ncomps>hi*ratio: return "too many connected components (got %d, wanted <=%d)"%(ncomps,hi)
    return None


# Get the line normalizer 
def get_linenormalizer():
    global network
    global lnorm
    # load the network used for classification
    try:
        network = ocrolib.load_object(args['model'],verbose=1)
        for x in network.walk(): x.postLoad()
        for x in network.walk():
            if isinstance(x,lstm.LSTM):
                x.allocate(5000)
    except FileNotFound:
        print_error("")
        print_error("Cannot find OCR model file:" + args['model'])
        print_error("Download a model and put it into:" + ocrolib.default.modeldir)
        print_error("(Or override the location with OCROPUS_DATA.)")
        print_error("")
        sys.exit(1)

    # get the line normalizer from the loaded network, or optionally
    # let the user override it (this is not very useful)
    lnorm = getattr(network,"lnorm",None)

    if args['height']>0:
        lnorm.setHeight(args['height'])  



# process one image
def process(arg):
    (trial,fname) = arg
    base,_ = ocrolib.allsplitext(fname)
    line = ocrolib.read_image_gray(fname)
    raw_line = line.copy()
    if prod(line.shape)==0: return None
    if amax(line)==amin(line): return None

    if not args['nocheck']:
        check = check_line(amax(line)-line)
        if check is not None:
            print_error("%s SKIPPED %s (use -n to disable this check)" % (fname, check))
            return (0,[],0,trial,fname)

    if not args['nolineest']:
        assert "dew.png" not in fname,"don't dewarp dewarped images"
        temp = amax(line)-line
        temp = temp*1.0/amax(temp)
        lnorm.measure(temp)
        line = lnorm.normalize(line,cval=amax(line))
    else:
        assert "dew.png" in fname,"only apply to dewarped images"

    line = lstm.prepare_line(line,args['pad'])
    pred = network.predictString(line)

    if args['llocs']:
        # output recognized LSTM locations of characters
        result = lstm.translate_back(network.outputs,pos=1)
        scale = len(raw_line.T)*1.0/(len(network.outputs)-2*args['pad'])
        #ion(); imshow(raw_line,cmap=cm.gray)
        with codecs.open(base+".llocs","w","utf-8") as locs:
            for r,c in result:
                c = network.l2s([c])
                r = (r-args['pad'])*scale
                locs.write("%s\t%.1f\n"%(c,r))
                #plot([r,r],[0,20],'r' if c==" " else 'b')
        #ginput(1,1000)

    if args['alocs']:
        # output recognized and aligned LSTM locations
        if os.path.exists(base+".gt.txt"):
            transcript = ocrolib.read_text(base+".gt.txt")
            transcript = ocrolib.normalize_text(transcript)
            network.trainString(line,transcript,update=0)
            result = lstm.translate_back(network.aligned,pos=1)
            scale = len(raw_line.T)*1.0/(len(network.aligned)-2*args['pad'])
            with codecs.open(base+".alocs","w","utf-8") as locs:
                for r,c in result:
                    c = network.l2s([c])
                    r = (r-args['pad'])*scale
                    locs.write("%s\t%.1f\n"%(c,r))

    if args['probabilities']:
        # output character probabilities
        result = lstm.translate_back(network.outputs,pos=2)
        with codecs.open(base+".prob","w","utf-8") as file:
            for c,p in result:
                c = network.l2s([c])
                file.write("%s\t%s\n"%(c,p))

    if not args['nonormalize']:
        pred = ocrolib.normalize_text(pred)

    if args['estrate']:
        try:
            gt = ocrolib.read_text(base+".gt.txt")
        except:
            return (0,[],0,trial,fname)
        pred0 = ocrolib.project_text(pred,args['compare'])
        gt0 = ocrolib.project_text(gt,args['compare'])
        if args['estconf']>0:
            err,conf = edist.xlevenshtein(pred0,gt0,context=args['context'])
        else:
            err = edist.xlevenshtein(pred0,gt0)
            conf = []
        if not args['quiet']:
            print_info("%3d %3d %s:%s" % (err, len(gt), fname, pred))
            sys.stdout.flush()
        return (err,conf,len(gt0),trial,fname)

    if not args['quiet']:
        print_info(fname+":"+pred)
    ocrolib.write_text(base+".txt",pred)

    return None

def safe_process(arg):
    trial,fname = arg
    try:
        return process(arg)
    except IOError as e:
        if ocrolib.trace: traceback.print_exc()
        print_info(fname+":"+e)
    except ocrolib.OcropusException as e:
        if e.trace: traceback.print_exc()
        print_info(fname+":"+e)
    except:
        traceback.print_exc()
        return None
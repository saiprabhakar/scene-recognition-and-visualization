#/usr/bin/python
# --------------------------------------------------------
# floor_recog
# Written by Sai Prabhakar
# CMU-RI Masters
# --------------------------------------------------------

import sys
import os
os.environ['GLOG_minloglevel'] = '3'

import argparse
import numpy as np
import cv2
import caffe
from pythonlayers.helpers import im_to_blob
import matplotlib.pyplot as plt
import datetime

im_target_size = 227

blob = caffe.proto.caffe_pb2.BlobProto()
data = open('placesOriginalModel/places205CNN_mean.binaryproto', 'rb').read()
blob.ParseFromString(data)
arr = np.array(caffe.io.blobproto_to_array(blob))
# changing order of rows, colmn, channel, batch_size
arr = np.squeeze(arr.transpose((2, 3, 1, 0)))
im_scaley = float(im_target_size) / float(256)
im_scalex = float(im_target_size) / float(256)
meanarr = cv2.resize(
    arr,
    None,
    None,
    fx=im_scalex,
    fy=im_scaley,
    interpolation=cv2.INTER_LINEAR)


def _get_image_blob(img_name):

    im = cv2.imread(img_name)
    im_orig = im.astype(np.float32, copy=True)

    #im_orig -= 140.8

    im_shape = im_orig.shape
    im_shape = im_orig.shape
    im_size = im_shape[0:2]  #rows, colmns y,x

    im_scaley = float(im_target_size) / float(im_size[0])
    im_scalex = float(im_target_size) / float(im_size[1])
    im = cv2.resize(
        im_orig,
        None,
        None,
        fx=im_scalex,
        fy=im_scaley,
        interpolation=cv2.INTER_LINEAR)

    processed_ims = im - meanarr
    #processed_ims = im
    #IPython.embed()
    blob = im_to_blob(processed_ims)

    return blob


def _get_blobs(f1, f2, sim):
    """Convert an image and RoIs within that image into network inputs."""
    blobs = {'data': None, 'data_p': None, 'sim': None}
    blobs['data'] = _get_image_blob(f1)
    blobs['data_p'] = _get_image_blob(f2)
    blobs['sim'] = sim.astype(np.float, copy=False)
    #print "blobs containing", blobs['rois'].shape
    return blobs


class SiameseTrainWrapper2(object):
    """A simple wrapper around Caffe's solver.
    This wrapper gives us control over he snapshotting process, which we
    use to unnormalize the learned bounding-box regression weights.
    """

    def __init__(self,
                 solver_prototxt,
                 pretrainedSiameseModel=None,
                 pretrained_model=None,
                 pretrained_model_proto=None,
                 testProto=None,
                 train=1,
                 netSize=1000,
                 class_size=6,
                 class_adju=2):
        """Initialize the SolverWrapper."""
        #caffe.set_device(0)
        #caffe.set_mode_gpu()
        caffe.set_mode_cpu()
        self.train = train
        self.netSize = netSize
        self.class_size = class_size
        self.class_adju = class_adju
        #caffe.set_mode_cpu()
        if self.train == 1:
            self.solver = caffe.SGDSolver(solver_prototxt)
            if pretrainedSiameseModel is not None:
                print('Loading pretrained model '
                      'weights from {:s}').format(pretrainedSiameseModel)
                #if train == 1:
                self.solver.net.copy_from(pretrainedSiameseModel)
                #else:
                #    self.siameseTestNet.copy_from(pretrainedSiameseModel)
            elif pretrained_model is not None:
                #if train == 1:
                self.solver.net.copy_from(pretrained_model)
                #else:
                #    self.siameseTestNet.copy_from(pretrained_model)
            else:
                print('Initializing completely from scratch .... really ?')

            self.solver.test_nets[0].share_with(self.solver.net)
        else:
            self.siameseTestNet = caffe.Net(testProto, pretrainedSiameseModel,
                                            caffe.TEST)

    def trainTest(self):
        #import ipdb
        #ipdb.set_trace()
        #self.solver.test_nets[0].forward()
        #self.solver.net.forward()
        #self.solver.test_nets[0].blobs['conv1'].data[0,0,1,1:5]
        #self.solver.net.blobs['conv1'].data[0,0,1,1:5]
        #import IPython
        #IPython.embed()

        #print self.solver.net.params['conv1'][0].data[1,1,1:5,1]
        #print self.solver.test_nets[0].params['conv1'][0].data[1,1,1:5,1]
        #1500
        num_data_epoch_train = 540
        num_data_epoch_test = 540
        tStamp = '-Timestamp-{:%Y-%m-%d-%H:%M:%S}'.format(
            datetime.datetime.now())
        plt.ion()
        try:
            for k in range(100):
                disLoss = 0
                simLoss = 0
                simC = 0
                disC = 0
                plot_data_d = np.zeros((0, 2))
                plot_data_s = np.zeros((0, 2))
                for i in range(num_data_epoch_train):
                    self.solver.step(1)
                    loss1 = self.solver.net.blobs['loss'].data
                    if self.solver.net.blobs['sim'].data == 1:
                        simC += 1
                        simLoss += loss1
                        plot_data_s = np.vstack(
                            (plot_data_s, [k + 0.5, loss1]))
                    else:
                        disC += 1
                        disLoss += loss1
                        plot_data_d = np.vstack((plot_data_d, [k, loss1]))
                print k, " net loss", simLoss / (simC + 0.1), disLoss / (
                    disC + 0.1), simC, disC
                plt.figure(1)
                #plt.clf()
                plt.xlim(-0.5, 100)
                plt.title(str(self.netSize) + "train errors")
                plt.plot(plot_data_s[:, 0], plot_data_s[:, 1], 'r.')
                plt.plot(plot_data_d[:, 0], plot_data_d[:, 1], 'b.')
                #plt.plot(plot_data[:,0], plot_data[:,1], '.')
                #plt.show()
                plt.pause(0.05)

                disLoss = 0
                simLoss = 0
                simC = 0
                disC = 0
                plot_data_s = np.zeros((0, 2))
                plot_data_d = np.zeros((0, 2))
                if k % 5 == 0:
                    confusion = np.zeros((self.class_size, self.class_size))
                    for i in range(num_data_epoch_test):
                        loss1 = self.solver.test_nets[0].forward()
                        #print i, loss1, loss1['sim'], loss1['testloss']
                        if loss1['sim'] == 1:
                            simC += 1
                            simLoss += loss1['testloss']
                            plot_data_s = np.vstack(
                                (plot_data_s, [k + 0.5, loss1['testloss']]))
                        else:
                            disC += 1
                            disLoss += loss1['testloss']
                            plot_data_d = np.vstack(
                                (plot_data_d, [k, loss1['testloss']]))
                        id1 = self.solver.test_nets[0].layers[0].m_batch_1[0][
                            1] - self.class_adju
                        id2 = self.solver.test_nets[0].layers[0].m_batch_2[0][
                            1] - self.class_adju
                        confusion[id1, id2] += loss1['testloss']
                    print "testing**** net loss", simLoss / (
                        simC + 0.1), disLoss / (disC + 0.1), simC, disC
                    print confusion
                    #import IPython
                    #IPython.embed()
                    #simLoss+= loss1#self.solver.net.blobs['loss'].data
                    #print i
                    #print i, loss1, self.solver.net.blobs[
                    #    'sim'].data#, self.solver.net.layers[0].m_batch_1[0][
                    #1], self.solver.net.layers[0].m_batch_2[0][1]

                    #import IPython
                    #IPython.embed()

                    plt.figure(2)
                    #plt.clf()
                    #plt.xlim(-0.5, 1.5)
                    plt.xlim(-0.5, 100)
                    plt.title(str(self.netSize) + "test distance")
                    plt.plot(plot_data_s[:, 0], plot_data_s[:, 1], 'r.')
                    plt.plot(plot_data_d[:, 0], plot_data_d[:, 1], 'b.')
                    #plt.show()
                    plt.pause(0.05)
                if k % 5 == 0:
                    preName = 'results/' + '-netsize-' + str(
                        self.netSize) + '-epoch-' + str(
                            k) + '-tstamp-' + tStamp
                    self.solver.net.save(preName + '-net.caffemodel')

        except KeyboardInterrupt:
            pass

        preName = 'results/' + '-netsize-' + str(
            self.netSize) + '-epoch-' + str(k) + '-tstamp-' + tStamp
        plt.ioff()

        plt.figure(1).savefig(preName + '-train.png')
        plt.figure(2).savefig(preName + '-test.png')
        self.solver.net.save(preName + '-net.caffemodel')
        plt.close('all')

    def test(self, fileName):
        f = open(fileName)
        lines = [line.rstrip('\n') for line in f]
        imageDict = {}
        imlist = []
        for i in lines:
            temp = i.split(' ')
            imageDict[temp[0]] = int(temp[1])
            imlist.append(temp[0])

        num_data_epoch_test = 540
        tStamp = '-Timestamp-{:%Y-%m-%d-%H:%M:%S}'.format(
            datetime.datetime.now())

        confusion = np.zeros((self.class_size, self.class_size))
        frequency = np.zeros((self.class_size, self.class_size))
        frequency2 = np.zeros((self.class_size, self.class_size))
        disLoss = 0
        simLoss = 0
        simC = 0
        disC = 0
        plot_data_s = np.zeros((0, 2))
        plot_data_d = np.zeros((0, 2))

        for i in range(len(imlist)):
            minloss = 10000
            minj = -1
            for j in range(len(imlist)):
                # np.array( [int(imageDict[ imlist[i] ] == imageDict[ imlist[j] ])] )
                if i != j:
                    sim1 = np.array([1])
                    blobs = _get_blobs('data/' + imlist[i],
                                       'data/' + imlist[j], sim1)
                    blobs_out1 = self.siameseTestNet.forward(
                        data=blobs['data'].astype(
                            np.float32, copy=False),
                        data_p=blobs['data_p'].astype(
                            np.float32, copy=False), )
                    loss1 = blobs_out1['testloss'].copy()
                    #print "min ", minloss, "loss " ,loss1 ,minloss > loss1
                    if minloss > loss1:
                        minloss = loss1
                        minj = j
                        #print "min found"
                    #print imageDict[imlist[i]], imageDict[imlist[j]], loss1
            print int(imageDict[imlist[i]] ==
                      imageDict[imlist[minj]]), "for ", imlist[
                          i], " ", imageDict[imlist[i]], " min is ", imageDict[
                              imlist[minj]], imlist[minj], minloss

        #for i in range(num_data_epoch_test):

        ##loss1 = self.siameseTestNet.forward()

        ##print i, loss1, loss1['sim'], loss1['testloss']
        #id1 = self.siameseTestNet.layers[0].m_batch_1[0][1] - self.class_adju
        #id2 = self.siameseTestNet.layers[0].m_batch_2[0][1] - self.class_adju
        #if loss1['sim'] == 1:
        #simC += 1
        #simLoss += loss1['testloss']
        #if loss1['testloss'] > 100:
        #frequency2[id1,id2] += 1
        #frequency2[id2,id1] += 1

        #plot_data_s = np.vstack(
        #(plot_data_s, [0 + 0.5, loss1['testloss']]))
        #else:
        #disC += 1
        #disLoss += loss1['testloss']
        #if loss1['testloss'] < 100:
        #frequency2[id1,id2] += 1
        #frequency2[id2,id1] += 1
        #plot_data_d = np.vstack(
        #(plot_data_d, [0, loss1['testloss']]))
        #confusion[id1,id2] += loss1['testloss']
        #confusion[id2,id1] += loss1['testloss']
        #frequency[id1,id2] += 1
        #frequency[id2,id1] += 1
        #print frequency2

        #for i in range(self.class_size):
        #frequency2[i,i] /= 2.0
        #confusion /= frequency
        #print "testing**** net loss", simLoss / (
        #simC + 0.1), disLoss / (disC + 0.1), simC, disC
        ##print np.log(confusion+1)
        #fig0 = plt.figure(2)
        #ax3 = fig0.add_subplot(111)
        #plt.xlim(-0.5, 1)
        #plt.title(str(self.netSize) + "test distance")
        #ax3.plot(plot_data_s[:, 0], plot_data_s[:, 1], 'r.')
        #ax3.plot(plot_data_d[:, 0], plot_data_d[:, 1], 'b.')

        #fig1 = plt.figure(3)
        #ax1 = fig1.add_subplot(111)
        #ax1.matshow(np.log(confusion+1), cmap = plt.cm.gray)

        #fig2 = plt.figure(4)
        #ax2 = fig2.add_subplot(111)
        #ax2.matshow(frequency2, cmap = plt.cm.gray)
        #plt.show()

        #import IPython
        #IPython.embed()


def siameseTrainer(siameseSolver,
                   fileName,
                   pretrained_model,
                   pretrainedSiameseModel,
                   testProto,
                   pretrained_model_proto,
                   train=1,
                   netSize=1000):
    #numImagePair = 1  #len(imdb.image_index)
    # timers
    #_t = {'im_detect' : Timer(), 'misc' : Timer()}

    sw = SiameseTrainWrapper2(
        siameseSolver,
        pretrainedSiameseModel=pretrainedSiameseModel,
        pretrained_model=pretrained_model,
        pretrained_model_proto=pretrained_model_proto,
        testProto=testProto,
        train=train,
        netSize=netSize)
    # import IPython
    # IPython.embed()

    if train == 1:
        print "training"
        sw.trainTest()
    else:
        print "testing with ", pretrainedSiameseModel
        sw.test(fileName)

    #sw = SiameseWrapper(siameseSolver, pretrained_model=pretrained_model, pretrained_model_proto= pretrained_model_proto, train=0 )

    #sw.testCode( fileName)

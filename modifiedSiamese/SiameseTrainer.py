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
        caffe.set_device(0)
        caffe.set_mode_gpu()
        #caffe.set_mode_cpu()
        self.train = train
        self.netSize = netSize
        self.class_size = class_size
        self.class_adju = class_adju
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
        num_data_epoch_test = 240
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
                plot_data_id_l1 = np.zeros((0, 2))
                plot_data_id_l2 = np.zeros((0, 2))
                lossId1s = 0
                lossId2s = 0
                for i in range(num_data_epoch_train):
                    self.solver.step(1)

                    #if i%50 == 0 and i != 0:
                    #import IPython
                    #IPython.embed()

                    lossCo = 0.2 * self.solver.net.blobs['cont_loss'].data
                    lossId1 = 0.4 * self.solver.net.blobs[
                        'softmax_loss_1'].data
                    lossId2 = 0.4 * self.solver.net.blobs[
                        'softmax_loss_2'].data
                    if self.solver.net.blobs['sim'].data == 1:
                        simC += 1
                        simLoss += lossCo
                        plot_data_s = np.vstack(
                            (plot_data_s, [k + 0.5, lossCo]))
                    else:
                        disC += 1
                        disLoss += lossCo
                        plot_data_d = np.vstack((plot_data_d, [k, lossCo]))
                    lossId1s += lossId1
                    lossId2s += lossId2

                    #print "sim", self.solver.net.blobs[
                    #    'sim'].data, "cont loss", lossCo, "id1", lossId1, "id2", lossId2
                plot_data_id_l1 = np.vstack(
                    (plot_data_id_l1, [k, lossId1s / num_data_epoch_train]))
                plot_data_id_l2 = np.vstack(
                    (plot_data_id_l2, [k, lossId2s / num_data_epoch_train]))
                print k, "cont net loss", simLoss / (simC + 0.1), disLoss / (
                    disC + 0.1), simC, disC, "Id net loss", lossId1s, lossId2s
                plt.figure(1)
                plt.xlim(-0.5, 100)
                plt.title(str(self.netSize) + "train errors")
                plt.plot(plot_data_s[:, 0], plot_data_s[:, 1], 'r.')
                plt.plot(plot_data_d[:, 0], plot_data_d[:, 1], 'b.')
                plt.pause(0.05)

                plt.figure(2)
                plt.xlim(-0.5, 100)
                plt.title(str(self.netSize) + "train softmax loss")
                plt.plot(plot_data_id_l1[:, 0], plot_data_id_l1[:, 1], 'r.')
                plt.plot(plot_data_id_l2[:, 0], plot_data_id_l2[:, 1], 'b.')
                plt.pause(0.05)

                if k % 5 == 0:
                    acc1 = np.zeros(self.class_size)
                    acc2 = np.zeros(self.class_size)
                    fre1 = np.zeros(self.class_size)
                    fre2 = np.zeros(self.class_size)
                    plot_acc1 = np.zeros((0, 2))
                    plot_acc2 = np.zeros((0, 2))
                    confusion_dis = np.zeros(
                        (self.class_size, self.class_size))
                    for i in range(num_data_epoch_test):
                        loss1 = self.solver.test_nets[0].forward()
                        #print i, loss1, loss1['sim'], loss1['euc_dist']
                        #import IPython
                        #IPython.embed()

                        if loss1['sim'] == 1:
                            simC += 1
                            simLoss += loss1['euc_dist']
                            plot_data_s = np.vstack(
                                (plot_data_s, [k + 0.5, loss1['euc_dist']]))
                        else:
                            disC += 1
                            disLoss += loss1['euc_dist']
                            plot_data_d = np.vstack(
                                (plot_data_d, [k, loss1['euc_dist']]))
                        id1 = self.solver.test_nets[0].layers[0].m_batch_1[0][
                            1] - self.class_adju
                        id2 = self.solver.test_nets[0].layers[0].m_batch_2[0][
                            1] - self.class_adju
                        confusion_dis[id1, id2] += loss1['euc_dist']
                        acc1[int(self.solver.test_nets[0].blobs['label1'].data[
                            0])] += self.solver.test_nets[0].blobs[
                                'accuracy1'].data
                        fre1[int(self.solver.test_nets[0].blobs['label1'].data[
                            0])] += 1
                        acc2[int(self.solver.test_nets[0].blobs['label2'].data[
                            0])] += self.solver.test_nets[0].blobs[
                                'accuracy2'].data
                        fre2[int(self.solver.test_nets[0].blobs['label2'].data[
                            0])] += 1
                    netacc = (acc1.sum() + acc2.sum()) / (
                        fre1.sum() + fre2.sum())
                    netacc1 = (acc1.sum()) / (fre1.sum())
                    netacc2 = (acc2.sum()) / (fre2.sum())
                    acc1 = acc1 / (fre1 + 0.1)
                    acc2 = acc2 / (fre2 + 0.1)
                    plot_acc1 = np.vstack((plot_acc1, [k, netacc1]))
                    plot_acc2 = np.vstack((plot_acc2, [k, netacc2]))
                    print "testing**** net loss", simLoss / (
                        simC + 0.1), disLoss / (disC + 0.1), simC, disC
                    #print confusion_dis
                    print acc1, acc2
                    print netacc
                    plt.figure(3)
                    plt.xlim(-0.5, 100)
                    plt.title(str(self.netSize) + "test accuracy")
                    plt.plot(k, netacc1, 'r.')
                    plt.plot(k, netacc2, 'b.')
                    plt.pause(0.05)
                    #import IPython
                    #IPython.embed()

                    plt.figure(4)
                    #plt.clf()
                    #plt.xlim(-0.5, 1.5)
                    plt.xlim(-0.5, 100)
                    plt.title(str(self.netSize) + "test distance")
                    plt.plot(plot_data_s[:, 0], plot_data_s[:, 1], 'r.')
                    plt.plot(plot_data_d[:, 0], plot_data_d[:, 1], 'b.')
                    #plt.show()
                    plt.pause(0.05)

                if k % 1 == 0:
                    preName = 'modifiedNetResults/' + 'Modified-netsize-' + str(
                        self.netSize) + '-epoch-' + str(
                            k) + '-tstamp-' + tStamp
                    self.solver.net.save(preName + '-net.caffemodel')

        except KeyboardInterrupt:
            pass

        preName = 'modifiedNetResults/' + 'Modified-netsize-' + str(
            self.netSize) + '-epoch-' + str(k) + '-tstamp-' + tStamp
        plt.ioff()

        plt.figure(1).savefig(preName + '-train-d-error.png')
        plt.figure(1).savefig(preName + '-train-s-error.png')
        plt.figure(3).savefig(preName + '-test-acc.png')
        plt.figure(4).savefig(preName + '-test-dist.png')
        self.solver.net.save(preName + '-net-final.caffemodel')
        plt.close('all')


def siameseTrainer(siameseSolver,
                   fileName,
                   pretrained_model,
                   pretrainedSiameseModel,
                   testProto,
                   pretrained_model_proto,
                   train=1,
                   visu=0,
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
    elif visu == 0:
        print "testing with ", pretrainedSiameseModel
        sw.test(fileName)
    else:
        print 'visalizing with ', pretrainedSiameseModel
        sw.visualizing_m1(fileName)

    #sw = SiameseWrapper(siameseSolver, pretrained_model=pretrained_model, pretrained_model_proto= pretrained_model_proto, train=0 )

    #sw.testCode( fileName)

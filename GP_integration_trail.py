
# coding: utf-8

# In[ ]:


#PROBLEMS:
  #1-EMG: fail to predict the right class
  #2-Error in the CV
  #https://github.com/keras-team/keras/wiki/Converting-convolution-kernels-from-Theano-to-TensorFlow-and-vice-versa
  #https://stackoverflow.com/questions/49287934/dask-dataframe-prediction-of-keras-model/49290185?noredirect=1#comment85587469_49290185
  
 #create new h5 in backend Theano


# In[1]:


#get_ipython().system(u'pip install -q keras')
import keras
import h5py


import os 
import numpy as np
import cv2
import matplotlib.pyplot as plt
import pandas as pd
from scipy import misc,ndimage
from skimage import io
import random 
from itertools import chain
from sklearn.preprocessing import LabelBinarizer
import io
from sklearn.externals import joblib
import pickle
#keras pakages
from keras import layers
from keras.layers import Input, Add, Dense, Activation, ZeroPadding2D, BatchNormalization, Flatten, Conv2D, AveragePooling2D, MaxPooling2D, GlobalMaxPooling2D
from keras.layers import Dropout, LeakyReLU
from keras.models import Model, load_model
from keras.preprocessing import image
from keras.utils import layer_utils
from keras.utils.data_utils import get_file
from keras.applications.imagenet_utils import preprocess_input
from IPython.display import SVG
from keras.utils.vis_utils import model_to_dot
from keras.utils import plot_model
from keras.initializers import glorot_uniform
import scipy.misc
from matplotlib.pyplot import imshow
#get_ipython().magic(u'matplotlib inline')
from keras.models import model_from_json
import keras.backend as K
K.set_image_data_format('channels_last')
K.set_learning_phase(1)


import os 
import numpy as np
import cv2
import time
from collections import Counter
import queue

import scipy.io as sio
from scipy.signal import butter,lfilter,filtfilt
from sklearn.neighbors import KNeighborsClassifier
from sklearn import svm
from scipy import stats
import threading
import RealTime
import poweroff
#EMG ############################################################################################################
## All you have to do is to Real.start_MYO() then call start_thread1 to start threading smoothly

###########################################################################################################3

# In[ ]:


def upload_files():
  from google.colab import files
  uploaded = files.upload()
  for k, v in uploaded.items():
    open(k, 'wb').write(v)
  return list(uploaded.keys())

def rgb2gray(rgb_image):
    return np.dot(rgb_image, [0.299, 0.587, 0.114])
  
def real_preprocess(img):
  
  #gray level
  img_gray= rgb2gray(img)
  
  #resize the image 48x36:
  img_resize=misc.imresize(img_gray,(48,36))
            
  #Normalization:
  img_norm= (img_resize - img_resize.mean())/ img_resize.std()
  
  return img_norm

def Nazarpour_model(input_shape,num_of_layers=2):
  x_input=Input(input_shape)
  
  x=Conv2D(5,(5,5),strides=(1,1),padding='valid')(x_input)
  x=BatchNormalization(axis=3)(x)
  x=Activation('relu')(x)
  x=Dropout(0.2)(x)
  
  if num_of_layers==2:
    x=Conv2D(25,(5,5),strides=(1,1),padding='valid')(x)
    x=BatchNormalization(axis=3)(x)
    x=Activation('relu')(x)
    
    
  x=MaxPooling2D((2,2),strides=(2,2))(x)
  x=Dropout(0.2)(x)

  
  x=Flatten()(x)

  x=Dense(4,activation='softmax',kernel_initializer=glorot_uniform(seed=0))(x)
  
  model=Model(inputs=x_input,outputs=x)
  
  return model


def grasp_type(frame,model_name):
    """
    path_of_test_real : the path of the uploaded image in case of offline.
    model_name: the name of the trained model, 'tmp.h5'
    
    """

    n_row=48
    n_col=36
    nc=1
    model=Nazarpour_model((n_row,n_col,nc),num_of_layers=2)
    model.compile('adam',loss='categorical_crossentropy',metrics=['accuracy'])
    model.load_weights(model_name)
    
#    i=misc.imread(path_of_test_real)
    img_after_preprocess=real_preprocess(frame)
    x = np.expand_dims(img_after_preprocess, axis=0)
    x=x.reshape((1,n_row,n_col,nc))
    out=model.predict(x)
    grasp=np.argmax(out)+1
    
    return grasp


# In[ ]:


def read_offline_for_prediction(path):
    df=pd.read_csv(path)
    df=df.iloc[:,1:]
    return df

def filteration (data,sample_rate=2000.0,cut_off=20.0,order=5,ftype='highpass'): 
    nyq = .5 * sample_rate
    b,a=butter(order,cut_off/nyq,btype=ftype)
    d= lfilter(b,a,data,axis=0)
    return pd.DataFrame(d)

 
def mean_std_normalization (df):
    m = df.mean(axis=0)
    s =df.std(axis=0)
    normalized_df =df/m
    return m,s,normalized_df



def MES_analysis_window (df,width,tau,win_num):
    df_2=pd.DataFrame()
    start= win_num*tau
    end= start+width
    df_2=df.iloc[start:end]
    return end,df_2

def features_extraction (df,th=0):
    #F1 : mean absolute value (MAV)
    MAV=abs(df.mean(axis=0)) 
    
    MAV=list(MAV)
    WL = []
    SSC= []
    ZC = []
    for col,series in df.iteritems():
        #F2 : wave length (WL)
        s=abs(np.array(series.iloc[:-1])- np.array(series.iloc[1:]))
        WL_result=np.sum(s)
        WL.append( WL_result)
        
        #F3 : zero crossing(ZC)
        _1starray=np.array(series.iloc[:-1])
        _2ndarray=np.array(series.iloc[1:])
        ZC.append(((_1starray*_2ndarray<0) & (abs(_1starray - _2ndarray)>=th) ).sum())
        
        
         #F4 : slope sign change(SSC)
        _1st=np.array(series.iloc[:-2])
        _2nd=np.array(series.iloc[1:-1])
        _3rd=np.array(series.iloc[2:])
        SSC.append(((((_2nd - _1st)*(_2nd - _3rd))>0) &(((abs(_2nd - _1st))>=th) | ((abs(_2nd - _3rd))>=th))).sum())
    
    features_array=np.array([MAV,WL,ZC,SSC]).T
    return features_array


def EMG_movement_type(path,model_name,width=512,tau=128,sample_rate=200):
    
    x=[]; end=0; win_num=0;
    
    df=read_offline_for_prediction(path)
    df=filteration(df,sample_rate)
    m,s,df=mean_std_normalization(df)
    
    while((len(df)-end) >= width):
        end,window_df=MES_analysis_window(df,width,tau,win_num)
        win_num=win_num + 1
        #filteration should be here in case of online sequence
        #normalization in case of online sequence
        ff=features_extraction(window_df)
        x.append(ff)

    predictors_array=np.array(x)
    nsamples, nx, ny = predictors_array.shape
    predictors_array_2d = predictors_array.reshape((nsamples,nx*ny))
    #predictors_array_2d = np.nan_to_num(predictors_array)
    
    #prediction part, pickle
    clf=joblib.load(model_name)
    predicted_movements=clf.predict(predictors_array_2d)
    
    mode,count=stats.mode(predicted_movements)
    
    return int(mode)


# In[ ]:


q= queue.Queue()


def EMG_Listener():
    #while (True):
      
      path= "1.csv" #put the path of the EMG signal
      EMG_model_name="EMG_wafa_model.pickle" #put the name of model i.e. 'example.pickle'

      EMG_class=EMG_movement_type(path,EMG_model_name)
      q.put(EMG_class)
  #        time.sleep(5)


"""
Stages meanings:
1: Taking photos, deciding grasp type, preshaping.
2: Grasping
3: Releasing
"""


def Main_algorithm ():
#    event.wait()
    stage=0 #I changed it to random number not zero just for test. retrun it back!!
    corrections= 0
    all_grasps = [1, 2, 3, 4]
    Choose_grasp = list(all_grasps)
    
    path_of_real_test='20180501_143824.jpg' #put the path of the tested picture 
    CV_model_name='GP_Weights.h5'
    
    while (True):#not(q.empty())):  
        EMG_class_recieved = q.get()        
        if (EMG_class_recieved == 1 or stage == 0):
            grasp = Camera()
            Choose_grasp = list(all_grasps)
            print("EMG_class {0}, Stage {1} : \n".format(EMG_class_recieved, stage))
            print("    Taking photos and deciding grasp type \n")
            print ('Grasp type no.{0} \n'.format(grasp))
            stage = 1
        elif (EMG_class_recieved == 2):
            print("EMG_class {0}, Stage {1} : \n".format(EMG_class_recieved, stage))
            print("    Confirmed! \n")
            if stage < 2:
                stage+=1
                corrections = 0
                Choose_grasp = list(all_grasps)
                print ('Grasping \n')
                #Do the action
            elif stage ==2:
                print ('Releasing ... \n     Done till next signal!')
                stage = 0
        elif (EMG_class_recieved == 3):
            print("EMG_class {0}, Stage {1} : \n".format(EMG_class_recieved, stage))
            if stage > 0:
                if (stage == 2 and corrections > 3):
                    print("Exceeded maximum iteration: \n Choosing from remaining grasps")
                    Choose_grasp.remove(grasp)
                    #Choose random class
                else:
                    print("    Cancelled! \n")
                    stage-=1
                    corrections +=1
                    #Redo previous action
            else:
                print ('No previous stage, restarting ... \n')
                stage =0
                grasp = Camera()
                Choose_grasp = list(all_grasps)
                print("EMG_class {0}, Stage {1} : \n".format(EMG_class_recieved, stage))
                print("    Taking photos and deciding grasp type \n")
                print ('Grasp type no.{0} \n'.format(grasp))
                stage = 1
        elif (EMG_class_recieved == 4):
            print("EMG_class {0}, Stage {1} : \n".format(EMG_class_recieved, stage))
            print ('Actuate + \n')
        elif (EMG_class_recieved == 5):
            print("EMG_class {0}, Stage {1} : \n".format(EMG_class_recieved, stage))
            print ('Actuate - \n')
        else:
            print ("Doesn't make  \n")


def Camera():
    grasp_votes [0,0,0]
    video = cv2.VideoCapture(0)
    check, frame1 = video.read()
    grasp_votes[0] = grasp_type(frame1, CV_model_name)
    time.sleep(0.2)

    video = cv2.VideoCapture(0)
    check, frame2 = video.read()
    grasp_votes[0] = grasp_type(frame2, CV_model_name)
    time.sleep(0.2)

    video = cv2.VideoCapture(0)
    check, frame2 = video.read()
    grasp_votes[0] = grasp_type(frame2, CV_model_name)

    video.release()

    grasp =  Most_Common(grasp_votes)
    return grasp

def Most_Common(lst):
    data = Counter(lst)
    return data.most_common(1)[0][0]



# In[10]:


emg_model=upload_files()


# In[21]:


#emg_model_s1=upload_files()
#emg_model_s2=upload_files()
#emg_model_s3=upload_files()


# In[7]:


cv_model=upload_files()


# In[5]:


tested_pic=upload_files()


# In[21]:


tested_signal=upload_files()


# In[40]:


t1 = threading.Thread(target = EMG_Listener, name ='thread1')
t2 = threading.Thread(target = Main_algorithm, name ='thread2')

#t1.daemon = True
#t2.daemon = True

t1.start()
t2.start()

t1.join()


# In[36]:


EMG_movement_type('1.csv','EMG_wafa_model.pickle')


# In[ ]:


get_ipython().system(u'pip install -q cython')
get_ipython().system(u'pip install -q botocore')
get_ipython().system(u'pip install -q tensorflow')


# In[ ]:


import tensorflow as tf
global graph
graph = tf.get_default_graph()


# In[ ]:


from keras.utils.conv_utils import convert_kernel


# In[37]:


grasp_type("20180501_143824.jpg","GP_Weights.h5")


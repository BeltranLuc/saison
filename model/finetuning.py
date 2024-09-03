from tensorflow.keras.layers import Dense, Flatten, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.applications.vgg16 import VGG16
from tensorflow.keras.callbacks import LearningRateScheduler, ModelCheckpoint
from tensorflow.keras.preprocessing.image import ImageDataGenerator

import numpy as np
import os
from PIL import Image

VGG_IMG_SHAPE = (224, 224, 3)
VGG_SIZE = (224, 224)
BATCH_SIZE = 64

def img_resize(img):
  img = Image.fromarray(img.astype('uint8'), 'RGB')
  img = img.resize(VGG_IMG_SHAPE)
  return np.array(img)


def scheduler(epoch, lr):
    if epoch % 5:
        return lr * 0.9
    return lr

def make_datasets(path:str):
    datagen = ImageDataGenerator(
        rescale=1./255,
        vertical_flip=True,
        horizontal_flip=True)
    
    train_generator = datagen.flow_from_directory(
        os.path.join(path, 'train'),  # this is the target directory
        target_size=VGG_SIZE,  # all images will be resized to 150x150
        batch_size=BATCH_SIZE,
        class_mode='categorical')
    
    val_generator = datagen.flow_from_directory(
        os.path.join(path, 'val'),  # this is the target directory
        target_size=VGG_SIZE,  # all images will be resized to 150x150
        batch_size=BATCH_SIZE,
        class_mode='categorical')
    
    return train_generator, val_generator



def fit_and_export(train_generator, validation_generator, 
                 save_path:str,
                 checkpoint_path:str, epochs:int=20, 
                 shape:tuple[int]=VGG_IMG_SHAPE )-> Model:
    """
    Fit and export a transfer-learning model based on 
    vgg16 model for the classification task.
    Returns the model.
    """

    #Load vgg16
    true_vgg = VGG16(input_shape=shape, weights='imagenet', include_top=False)

    for layer in true_vgg.layers:
        layer.trainable = False
    
    #Make new head
    flatten = Flatten()(true_vgg.output)
    d = Dense(4096, activation='relu')(flatten)
    drop = Dropout(0.5)(d)
    output = Dense(10, activation='softmax')(drop)

    #Transfer Learning
    model = Model(inputs=true_vgg.input, 
                  outputs=output, 
                  name='custom_vgg16')

    model.compile(loss='categorical_crossentropy',
                        optimizer='adam',
                        metrics=['categorical_accuracy'])
    

    schedule = LearningRateScheduler(scheduler)
    chekpoint = ModelCheckpoint(filepath=checkpoint_path,
                                save_weights_only=True,
                                verbose=1)

    #Fit from generator
    model.fit_generator(train_generator, validation_data=validation_generator,
                        epochs=epochs, 
                        callbacks=[schedule, chekpoint], 
                        batch_size=64)
    #Export model
    model.export(
                save_path, 
                format='tf_saved_model')

    return model
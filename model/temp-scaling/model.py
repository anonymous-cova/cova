
from tensorflow import keras
from tensorflow.keras import optimizers
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Activation, Flatten
from tensorflow.keras.layers.experimental.preprocessing import Rescaling
from tensorflow.keras.layers import Convolution2D, MaxPooling2D
#tf.keras.layers.experimental.preprocessing.Rescalingscale, offset=0.0, name=None, **kwargs
#import tf_slim as slim

def generate_conv_net(input_shape, classes):
    model = Sequential()

    output_channel = 32
    model.add(Convolution2D(
        filters=output_channel,
        kernel_size=(3,3),
        strides=(1, 1),
        padding='same',
        input_shape=input_shape,
        activation='relu'))
    model.add(Convolution2D(
        filters=output_channel,
        kernel_size=(3,3),
        strides=(1, 1),
        padding='same',
        activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))

    output_channel *= 2
    model.add(Convolution2D(
        filters=32,
        kernel_size=(3,3),
        strides=(1, 1),
        padding='same',
        activation='relu'))
    model.add(Convolution2D(
        filters=32,
        kernel_size=(3,3),
        strides=(1, 1),
        padding='same',
        activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))

    output_channel *= 2
    model.add(Convolution2D(
        filters=32,
        kernel_size=(3,3),
        strides=(1, 1),
        padding='same',
        activation='relu'))
    model.add(Convolution2D(
        filters=32,
        kernel_size=(3,3),
        strides=(1, 1),
        padding='same',
        activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))

    model.add(Flatten())
    model.add(Dense(128, activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(classes))

    #model.add(Rescaling(0.5))

    model.add(Activation('softmax'))

    model.compile(
            loss='categorical_crossentropy',
            optimizer=optimizers.RMSprop(lr=0.001),
            metrics=['accuracy', 'mean_squared_error'])

    return model

if __name__ == '__main__':
    model = generate_conv_net((640, 640, 3), 2)
    model.summary()
    #model.save('./rescaling-model')
    model.save('./no-scale-model')
    #slim.model_analyzer.analyze_vars(
    #        model.trainable_variables,
    #        print_info=True)
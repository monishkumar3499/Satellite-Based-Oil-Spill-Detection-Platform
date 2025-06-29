import os
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import Conv2D, MaxPooling2D, BatchNormalization
from tensorflow.keras.layers import Activation, Dropout, Flatten, Dense, Input
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
import datetime

# Set memory growth to avoid GPU memory errors
physical_devices = tf.config.list_physical_devices('GPU')
if physical_devices:
    try:
        for device in physical_devices:
            tf.config.experimental.set_memory_growth(device, True)
    except:
        print("Invalid device or cannot modify virtual devices once initialized.")

def create_cnn_model(input_shape=(256, 256, 3)):
    """Create a CNN model for oil spill detection"""
    model = Sequential()
    
    # First convolutional block
    model.add(Conv2D(32, (3, 3), input_shape=input_shape, padding='same'))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    
    # Second convolutional block
    model.add(Conv2D(64, (3, 3), padding='same'))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    
    # Third convolutional block
    model.add(Conv2D(128, (3, 3), padding='same'))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    
    # Fourth convolutional block
    model.add(Conv2D(256, (3, 3), padding='same'))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    
    # Fully connected layers
    model.add(Flatten())
    model.add(Dense(512))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(Dropout(0.5))
    model.add(Dense(1, activation='sigmoid'))  # Binary classification
    
    return model

def create_data_generators(batch_size=16):
    """Create data generators for training, validation, and testing"""
    # Data augmentation for training
    train_datagen = ImageDataGenerator(
        rescale=1.0/255,
        rotation_range=15,
        width_shift_range=0.1,
        height_shift_range=0.1,
        shear_range=0.1,
        zoom_range=0.1,
        horizontal_flip=True,
        vertical_flip=True,
        fill_mode='nearest'
    )
    
    # Just rescaling for validation and test
    val_datagen = ImageDataGenerator(rescale=1.0/255)
    test_datagen = ImageDataGenerator(rescale=1.0/255)
    
    # Create generators
    train_generator = train_datagen.flow_from_directory(
        'data/processed/train',
        target_size=(256, 256),
        batch_size=batch_size,
        class_mode='binary',
        shuffle=True
    )
    
    val_generator = val_datagen.flow_from_directory(
        'data/processed/val',
        target_size=(256, 256),
        batch_size=batch_size,
        class_mode='binary',
        shuffle=False
    )
    
    test_generator = test_datagen.flow_from_directory(
        'data/processed/test',
        target_size=(256, 256),
        batch_size=batch_size,
        class_mode='binary',
        shuffle=False
    )
    
    return train_generator, val_generator, test_generator

def plot_training_history(history):
    """Plot training history"""
    # Create plot directory if it doesn't exist
    os.makedirs('models/plots', exist_ok=True)
    
    # Plot accuracy
    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    plt.plot(history.history['accuracy'])
    plt.plot(history.history['val_accuracy'])
    plt.title('Model Accuracy')
    plt.ylabel('Accuracy')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Validation'], loc='upper left')
    
    # Plot loss
    plt.subplot(1, 2, 2)
    plt.plot(history.history['loss'])
    plt.plot(history.history['val_loss'])
    plt.title('Model Loss')
    plt.ylabel('Loss')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Validation'], loc='upper left')
    
    plt.tight_layout()
    plt.savefig('models/plots/training_history.png')
    plt.close()

def train_model(epochs=50, batch_size=16, lr=0.001):
    """Train the CNN model"""
    # Create model
    model = create_cnn_model()
    
    # Compile model
    model.compile(
        optimizer=Adam(learning_rate=lr),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    
    # Create data generators
    train_generator, val_generator, test_generator = create_data_generators(batch_size)
    
    # Create model directory if it doesn't exist
    os.makedirs('models', exist_ok=True)
    
    # Create callbacks
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    model_path = f'models/oil_spill_model_{timestamp}.h5'
    
    checkpoint = ModelCheckpoint(
        model_path,
        monitor='val_accuracy',
        save_best_only=True,
        mode='max',
        verbose=1
    )
    
    early_stopping = EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True,
        verbose=1
    )
    
    reduce_lr = ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.2,
        patience=5,
        min_lr=1e-6,
        verbose=1
    )
    
    callbacks = [checkpoint, early_stopping, reduce_lr]
    
    # Train model
    print("Starting model training...")
    history = model.fit(
        train_generator,
        steps_per_epoch=len(train_generator),
        epochs=epochs,
        validation_data=val_generator,
        validation_steps=len(val_generator),
        callbacks=callbacks,
        verbose=1
    )
    
    # Save final model
    final_model_path = f'models/oil_spill_model_final_{timestamp}.h5'
    model.save(final_model_path)
    print(f"Final model saved at: {final_model_path}")
    
    # Plot training history
    plot_training_history(history)
    
    # Evaluate model on test set
    test_loss, test_acc = model.evaluate(test_generator, steps=len(test_generator))
    print(f'Test accuracy: {test_acc:.4f}')
    print(f'Test loss: {test_loss:.4f}')
    
    # Save model summary to file with utf-8 encoding
    with open('models/model_summary.txt', 'w', encoding='utf-8') as f:
        model.summary(print_fn=lambda x: f.write(x + '\n'))
    
    # Save model architecture as JSON
    model_json = model.to_json()
    with open(f'models/oil_spill_model_architecture_{timestamp}.json', 'w') as json_file:
        json_file.write(model_json)
    
    return model, final_model_path

if __name__ == "__main__":
    train_model(epochs=50, batch_size=16)

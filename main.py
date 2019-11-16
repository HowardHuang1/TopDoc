import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
from glob import glob
import seaborn as sns
from torch.utils import data
import torch
from PIL import Image
torch.manual_seed(42)
np.random.seed(42)

#read and import dataset
base_skin_dir = '/Users/howardhuang/Documents/TopDoc/skin-cancer-mnist-ham10000/HAM10000_images_part_1'

imageid_path_dict = {os.path.splitext(os.path.basename(x))[0]: x
                     for x in glob(os.path.join(base_skin_dir, '*.jpg'))}
print("dictionary: ")
print(imageid_path_dict)
lesion_type_dict = {
    'nv': 'Melanocytic nevi',
    'mel': 'dermatofibroma',
    'bkl': 'Benign keratosis-like lesions ',
    'bcc': 'Basal cell carcinoma',
    'akiec': 'Actinic keratoses',
    'vasc': 'Vascular lesions',
    'df': 'Dermatofibroma'
}


tile_df = pd.read_csv('/Users/howardhuang/Documents/TopDoc/skin-cancer-mnist-ham10000/HAM10000_metadata.csv')
tile_df['path'] = tile_df['image_id'].map(imageid_path_dict.get)
print(tile_df['path'])
tile_df['cell_type'] = tile_df['dx'].map(lesion_type_dict.get)
tile_df['cell_type_idx'] = pd.Categorical(tile_df['cell_type']).codes
tile_df[['cell_type_idx', 'cell_type']].sort_values('cell_type_idx').drop_duplicates()

#counts number of each type of tumor in dataset
tile_df['cell_type'].value_counts()

print(tile_df.sample(3))

#load in a pretrained ResNet50 model
import torchvision.models as models
model_conv = models.resnet50(pretrained=True)


#Convoluted Neural Network
print(model_conv)

## print(model_conv.fc)
## Linear(in_features=2048, out_features=1000, bias=True)

#adjust last layer of (FC) We deal with only 7 cases so chain 1000 output neurons to 7 neurons
num_ftrs = model_conv.fc.in_features
model_conv.fc = torch.nn.Linear(num_ftrs, 7)

print(model_conv.fc)
## Linear(in_features=2048, out_features=7, bias=True)



######################################################################
# Define the device:
device = torch.device('cpu:0')

# Put the model on the device:
model = model_conv.to(device)

from sklearn.model_selection import train_test_split

train_df, test_df = train_test_split(tile_df, test_size=0.1)

# We can split the test set again in a validation set and a true test set:
validation_df, test_df = train_test_split(test_df, test_size=0.5)

train_df = train_df.reset_index()
validation_df = validation_df.reset_index()
test_df = test_df.reset_index()

print("----TRAINDF---")
print(train_df)

class Dataset(data.Dataset):
    'Characterizes a dataset for PyTorch'
    def __init__(self, df, transform=None):
        'Initialization'
        self.df = df
        self.transform = transform

    def __len__(self):
        'Denotes the total number of samples'
        return len(self.df)

    def __getitem__(self, index):
        'Generates one sample of data'
        # Load data and get label
        X = Image.open(open(self.df['path'][index], 'rb'))
        y = torch.tensor(int(self.df['cell_type_idx'][index]))

        if self.transform:
            X = self.transform(X)

        return X, y
# Define the parameters for the dataloader
params = {'batch_size': 4,
          'shuffle': True,
          'num_workers': 6}

          # define the transformation of the images.
import torchvision.transforms as trf
composed = trf.Compose([trf.RandomHorizontalFlip(), trf.RandomVerticalFlip(), trf.CenterCrop(256), trf.RandomCrop(224),  trf.ToTensor(),
                        trf.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])])

# Define the trainingsset using the table train_df and using our defined transitions (composed)
training_set = Dataset(train_df, transform=composed)
training_generator = data.DataLoader(training_set, **params)

# Same for the validation set:
validation_set = Dataset(validation_df, transform=composed)
validation_generator = data.DataLoader(validation_set, **params)

optimizer = torch.optim.Adam(model.parameters(), lr=1e-6)
criterion = torch.nn.CrossEntropyLoss()

#plt.plot(trainings_error, label = 'training error')
#plt.plot(validation_error, label = 'validation error')
#plt.legend()
#plt.show()

model.eval()
test_set = Dataset(validation_df, transform=composed)
test_generator = data.SequentialSampler(validation_set)

result_array = []
gt_array = []
for i in test_generator:
    if validation_set.df['path'][i] == None:
        continue
    data_sample, y = validation_set.__getitem__(i)
    data_gpu = data_sample.unsqueeze(0).to(device)
    output = model(data_gpu)
    result = torch.argmax(output)
    result_array.append(result.item())
    gt_array.append(y.item())
# checks if answers are actually correct/matches guess to actual
    correct_results = np.array(result_array)==np.array(gt_array)

print(gt_array)
sum_correct = np.sum(correct_results)
print("Sum Correct is: ")
print(sum_correct)
print("Total Number of Test Cases: ")
print(test_generator.__len__())
accuracy = sum_correct*1.0/test_generator.__len__()

print(result_array)
print(accuracy)

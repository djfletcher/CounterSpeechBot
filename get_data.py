import os

DATA_DIRECTORY = os.getcwd() + '/data/'

dataset = []
for filename in os.listdir(DATA_DIRECTORY):
    with open(os.path.join(DATA_DIRECTORY, filename), 'r') as f:
        dataset.append(f.read())

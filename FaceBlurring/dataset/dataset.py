import torch
import os
import pandas as pd
import numpy as np
import cv2
from torch.utils.data import Dataset
from tqdm import tqdm

# TODO: txt file 없이 csv file 로만 되도록 깔끔하게 정리
class FaceDataset(Dataset):
	def __init__(self, label_path, data_root, option='blur', 
	calc='cosine', method='defocus', transform=None, 
	input_size=None, check=False):
		'''
			face dataset module
			txt file must include root directory of sample images
		'''
		assert calc in ['psnr', 'ssim', 'degree', 'cosine'], "Not available metric"
		assert method in ['defocus', 'deblurGAN'], "Not available method"
		self.transform = transform
		self.calc = calc
		self.method = method
		self.data_root = data_root
		self.label_path = label_path

		# with open(txt_file, 'r') as f:
		# 	lines = f.readlines()
		# 	sample_root = [l.rstrip('\n') for l in lines]
		
		if check:
			if option=='clean':
				self.sample_paths = self._get_clean_samples()
				self.labels = np.zeros(len(self.sample_paths))

			elif option == 'blur':
				self.sample_paths, self.labels = self._get_blur_samples()
			# FIXME : 둘 다 사용할 필요는 없나?

			else:
				raise ValueError("option should be 'clean' or 'blur'")
		else:
			df = pd.read_csv(self.label_path)
			self.sample_paths = df['filename']
			self.labels = df[self.calc]

		if input_size is None:
			self.input_size = 1024
		else:
			self.input_size = input_size

	def _get_clean_samples(self):
		'''
			Inner function to get all clean samples under sample root
			This function only return clean images
		'''
		paths = []
		roots = self.data_root

		for root in roots:
			for (path, directory, files) in os.walk(root):
				for filename in files:
					ext = os.path.splitext(filename)[-1]
					if ext in ['.png', '.jpg', 'PNG', 'JPG', 'JPEG'] and 'clean' in path:
						paths += [os.path.join(path, filename)]
		return paths

	def _get_blur_samples(self):
		'''
			Inner function to get all blur samples under sample root
			This function only return blur images
		'''
		paths = []
		labels = []
		# label_path = ".."+os.path.sep+os.path.join('data', f"label_blur_{self.method}", 'label', "label.csv")
		label_path = self.label_path
		roots = self.data_root
		assert os.path.isfile(label_path), "label file does not exist"
		df = pd.read_csv(label_path)
		assert self.calc in list(df.columns.values), 'Regenerate label with same metric'

		for root in roots:
			for (path, directory, files) in os.walk(root):
				for filename in files:
					ext = os.path.splitext(filename)[-1]
					if ext in ['.png', '.jpg', 'PNG', 'JPG', 'JPEG'] and 'blur_'+self.method in path:
						filepath = os.path.join(path, filename)
						paths += [filepath]
						labels.append(np.float32(df.loc[df['filename'] == filepath][self.calc].item()))
						
		return paths, labels


	def __len__(self):
		return len(self.sample_paths)

	def __getitem__(self, idx):
		img_path, label = self.sample_paths[idx], self.labels[idx]
		image = cv2.cvtColor(cv2.imread(img_path), cv2.COLOR_BGR2RGB)
		image = cv2.resize(image,
						   (self.input_size, self.input_size),
						   interpolation=cv2.INTER_AREA)
		if self.transform:
			image = self.transform(image).float()

		return image, torch.from_numpy(np.asarray(label))


class FaceDataset_CSV(Dataset):
    def __init__(self, csv_file, metric='cosine', transform=None, input_size=None):
	# 라벨(CSV) 파일이 있는 경우 굳이 폴더를 서칭하면서 이미지를 가져올 필요가 없음. 라벨을 만들고 나서는 이 방법이 더 좋은 것 같습니다
        self.path_n_label = pd.DataFrame.to_dict(pd.read_csv(csv_file))
        self.metric = metric
        assert metric in self.path_n_label.keys(), 'Not available metric, you have to create label'
        self.transform = transform
        
        if input_size is None:
            self.input_size = 1024
        else:
            self.input_size = input_size


    def __len__(self):
        return len(self.path_n_label['filename'])

    def __getitem__(self, idx):
        img_path, label = self.path_n_label['filename'][idx], self.path_n_label[self.metric][idx]
        image = cv2.cvtColor(cv2.imread(img_path), cv2.COLOR_BGR2RGB)
        image = cv2.resize(image,
                           (self.input_size, self.input_size),
                           interpolation=cv2.INTER_AREA)
        if self.transform:
            image = self.transform(image).float()

        return image, 100*torch.from_numpy(np.asarray(label)).float()


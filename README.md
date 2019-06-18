# SQLNet suggestions with NQL

This repo contains the implementation of SQLNet suggestions ([paper](https://arxiv.org/abs/1711.04436) and [Original Code](https://github.com/xiaojunxu/SQLNet) )with NQL from my master's thesis.


## Preparations
1. Download `data.tar.bz2`. From the SQLNet Github Page [here](https://github.com/xiaojunxu/SQLNet/blob/master/data.tar.bz2) and unpack it. After that, you should have the folders 'data' and 'data_resplit'
2. Download the 42B.300d Glove embedding from [here](https://github.com/stanfordnlp/GloVe) or directly from [here](http://nlp.stanford.edu/data/wordvecs/glove.42B.300d.zip). Unzip the 'glove.42B.300d.txt' file and put it into the folder 'glove'



## Installation of packages
This repo was developed on Windows using Python 3.6. To install the needed Python packages run:
```bash
pip install -r requirements.txt
```
SQLNet uses Pytorch, so CUDA/cudnn is needed to be installed. For this, please visit the NVIDIA website.

## Running the GUI
```bash
python main.py
```
After a few seconds the GUI should be visible.
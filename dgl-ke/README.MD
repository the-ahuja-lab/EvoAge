# DGL_RotatE
This repo contains configuration that can be used to train RotatE model using DGL.

## Requirements:
1) You should have a single combined .csv file of all triples.

2) Convert it into train.tsv, test.tsv and valid.tsv in any ratio you desire.

3) Put train.tsv, valid.tsv, test.tsv in dgl-ke/data/wikimedia (create folder if not present).

## Steps:
1) After the data has been modified as specified in requirements and placed at the reqd. path, decide the specs for your RotatE model.

2) To decide no. of epochs, use the formula to calculate max step
   ```bash
   max_step = (Epochs * training triples) / batch size
   ```

3) Go to path ./dgl-ke/python.

4) Install python version 3.7.9 and check add env variable to PATH while setup.

5) Verify the installation using command: 
   ```bash
   python --version
   ```

6) Create a virtual environment and activate it.
   ```bash
   conda create -n dglke_env python=3.7 -y
   conda activate dglke_env
   ```

7) Now there is a requirements.txt at dgl-ke/python path. Install it in the virtual env:
   ```bash
   pip install -r requirements.txt
   ```
   ```bash
   pip install torch==1.10.0+cu113 torchvision==0.11.1+cu113 torchaudio==0.10.0+cu113 -f https://download.pytorch.org/whl/torch_stable.html
   ```
   ```bash
   pip install pandas #if required
   ```

8) There is a python script, idgen.py at dgl-ke/python path which has to be used to generate ids for your entities and relations. It will take input your files train.tsv, test.tsv and valid.tsv and give output entities.dict and relations.dict at path :
    ```bash
    dgl-ke/data/wikimedia/
    ``` 
    Also, it will give files train.txt, valid.txt and test.txt at the same path which are to be used finally for model training (they will be the same tsv files but converted using the ids you generated).

9) Now, create folder model_output in python with a folder inside it named rotate_wikimedia.
   ```bash
   mkdir model_output/rotate_wikimedia
   ```

10) Now run the DGL command in powershell with the virtual env activated at path :
    ```bash
    ./dgl-ke/python 
    ```
    (Use your own specifications):
      ```bash
      $env:DGLBACKEND="pytorch"; dglke_train `
      --model_name RotatE `
      --data_path ../data/wikimedia `
      --dataset wikimedia `
      --data_files train.txt valid.txt test.txt `
      --format raw_udd_hrt `
      --batch_size 128 `
      --neg_sample_size 32 `
      --batch_size_eval 64 `
      --neg_sample_size_eval 16 `
      --hidden_dim 128 `
      --gamma 12.0 `
      --lr 0.01 `
      --max_step 200000 `
      --log_interval 1000 `
      --eval_interval 100000 `
      --save_path model_output/rotate_wikimedia `
      --gpu 0 `
      -adv -a  "1.0" `
      -de `
      --valid `
      --test `
      ```
11) Model will be saved at path dgl-ke/python/model_output/RotatE_wikimedia_x, this path may vary and will be displayed at the end of model training in powershell.

12) Convert your entities.tsv and relations.tsv into json files and add them to the path where your model files are stored if they arent automatically created (reqd for model testing manually). Name them as entityid2name.json and relationid2name.json.

13) To test your model manually, edit the dgl_predict.py file in dgl-ke/python (edit head and relation for predictions) and run it using command:
    ```bash
    python dgl_predict.py
    ```

## Model I trained (Specs):
The model was trained using the following specifications or CLI code:
   ```bash
   Data files: 
   1) entities.dict - 943582 entities
   2) relations.dict - 10 relations
   3) train.txt - 3232932 triples (0.8)
   4) valid.txt - 359214 triples (0.1)
   5) test.txt - 359214 triples (0.1)
   ```

   ```bash
   $env:DGLBACKEND "pytorch"                                                                                       
    dglke_train `
    --model_name RotatE `
    --data_path ../data/wikimedia `
    --dataset wikimedia `
    --format udd_hrt `
    --data_files entities.dict relations.dict train.txt valid.txt test.txt `
    --batch_size 128 `
    --neg_sample_size 32 `
    --batch_size_eval 64 `
    --neg_sample_size_eval 16 `
    --hidden_dim 256 `
    --double_ent `
    --gamma 12.0 `
    --lr 0.01 `
    --max_step 253000 `
    --log_interval 10000 `
    --eval_interval 253000 `
    --save_path model_output/rotate_wikimedia `
    --gpu 0 `
    -adv -a 1.0 `
    --valid `
    --test `
   ```

 ## Stats of final model trained:

 The model was trained successfully in 5396.262 seconds, validation takes 1850.543 seconds and testing takes 1910.88 seconds. Following are the stats after complete training:

 ```bash
Model Name: RotatE
No. of Epochs: 10
MRR: 0.9195858653627182
MR: 1.8967920304704204
HITS@1: 0.897
HITS@3: 0.93
HITS@10: 0.95
Avg Loss: 0.18 
Avf Pos Loss: 0.15
Avg Neg Loss: 0.20 
 ```

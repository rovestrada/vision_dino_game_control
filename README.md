# vision_dino_game_control


We need to install the following tools:

- [ngrok](https://ngrok.com/download) - for tunneling


After installing ngrok, run the following command to start a tunnel on port 5000:

```bash
ngrok http 5000
```
This will give you a public URL that you can use to access your local server from the internet. Copy the URL and replace `http://localhost:5000` in the code with the ngrok URL.

## Install dependencies

```bash
pip install -r requirements.txt
```


## Run the server

```bash
cd server
python3 ngrok_server_robust.py 
```

## Run the notebook

Run the notebook in the scripts folder. You can use the following command to run the notebook:

Or you can open the notebook in Google Colab and run it there.



```bash
cd scripts
# If you are using Jupyter Npose_tracking_webcam_smalcotebook
jupyter notebook vision_dino_game_control.ipynb
```

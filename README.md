# How to Deploy Streamlit app on EC2 instance

## 1. Login with your AWS console and launch an EC2 instance

## 2. Run the following commands

Note: Do the port mapping to this port:- 8501

```bash
sudo apt-get update -y

sudo apt-get upgrade

#Install Docker

curl -fsSL https://get.docker.com -o get-docker.sh

sudo sh get-docker.sh

sudo usermod -aG docker ubuntu

newgrp docker
```

(may require sudo)
```bash
sudo mkdir /app

cd /app

git clone https://github.com/jkstarling/T5OIL_SL_DOCKER_EC2.git

cd /T5OIL_SL_DOCKER_EC2

docker build -t streamlit .


```


```bash
docker images -a  
```

```bash
docker run -d -p 8501:8501 entbappy/stapp 
```

```bash
docker ps  
```

```bash
docker stop container_id
```

```bash
docker rm $(docker ps -a -q)
```

```bash
docker login 
```

```bash
docker push entbappy/stapp:latest 
```

```bash
docker rmi entbappy/stapp:latest
```

```bash
docker pull entbappy/stapp
```

code removed from example here: https://docs.streamlit.io/deploy/tutorials/docker#check-network-port-accessibility

#3.93.198.219"]

# HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health








#### OLD CODE ####

```bash
sudo apt update

sudo apt-get update

sudo apt upgrade -y

sudo apt install git curl unzip tar make sudo vim wget -y

sudo apt install python3-pip
```

Make a new folder in /home called /apps. Then copy the github repo:
```bash
sudo git clone https://github.com/jkstarling/T5OIL_SL_DOCKER_EC2.git
```


```bash
pip3 install -r requirements.txt
```

If the above doesn't work, you need to install **pipx**. 

```bash
sudo apt install pipx
pipx ensurepath
pipx install -r requirements
(OR)
pipx install streamlit
```

Or if that doesn't work, try to install venv and start a virtual environment. 
```bash
python3 -m venv venv
source venv/bin/activate
pip3 install streamlit
```


```bash
#Temporary running
python3 -m streamlit run app.py

#Permanent running
nohup python3 -m streamlit run app.py
```

Note: Streamlit runs on this port: 8501




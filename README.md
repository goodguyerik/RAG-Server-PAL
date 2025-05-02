sudo docker compose build
sudo docker pull postgres:latest

sudo docker compose up

#Startup
wsl.exe -d Ubuntu
dos2unix start.sh
dos2unix generate_compose.sh
chmod +x generate_compose.sh
sudo docker build -t rag-app .
./generate_compose.sh PAL PAL PALpw 9001

 

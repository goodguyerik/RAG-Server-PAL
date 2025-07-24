sudo docker compose build
sudo docker pull postgres:latest

sudo docker compose up

# Startup

wsl.exe -d Ubuntu
dos2unix start.sh
dos2unix generate\_compose.sh
chmod +x generate\_compose.sh
sudo docker build -t rag-app .
./generate\_compose.sh PAL PAL PALpw 9001

# Update Workflow

sudo docker build -t rag-app .
docker rm -f $(docker ps -aq)
./generate\_compose.sh PAL PAL PALpw 9001





Failures:

Initial Startup
File "/app/init.py", line 89, in check\_and\_create\_tables

2025-07-24 09:58:03     cursor.execute(map\_table)

2025-07-24 09:58:03     ~~~~~~~~~~~~~~^^^^^^^^^^^

2025-07-24 09:58:03 psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "pg\_class\_relname\_nsp\_index"

2025-07-24 09:58:03 DETAIL:  Key (relname, relnamespace)=(map\_id\_seq, 2200) already exists.


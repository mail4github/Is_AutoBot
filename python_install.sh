apt update &&
apt -y install python3-pip &&
echo -e "\033[34m installing environment \033[0m" &&
apt -y install python3.12-venv
apt -y install python3.10-venv
python3 -m pip install --user virtualenv &&
echo -e "\033[34m creating environment \033[0m" &&
python3 -m venv . &&
echo -e "\033[34m activate \033[0m" &&
source bin/activate &&
echo -e "\033[34m install python-telegram-bot \033[0m" &&
python3 -m pip install python-telegram-bot &&
#echo -e "\033[34m install langdetect \033[0m" &&
#python3 -m pip install langdetect &&
echo -e "\033[34m install requests \033[0m" &&
python3 -m pip install requests &&
#echo -e "\033[34m install telethon \033[0m" &&
#python3 -m pip install telethon &&
#echo -e "\033[34m install nltk \033[0m" &&
#python3 -m pip install nltk &&
#python3 -m nltk.downloader all &&
#echo -e "\033[34m install PySocks \033[0m" &&
#python3 -m pip install PySocks &&
#echo -e "\033[34m install pillow \033[0m" &&
#python3 -m pip install pillow &&
#echo -e "\033[34m install pymorphy \033[0m" &&
#python3 -m pip install pymorphy3
#pip install -U pymorphy3-dicts-ru

echo -e "\033[34m deleting compressed files \033[0m" &&
find /root/nltk_data/ -name *.pdf -exec rm {} \;
find /root/nltk_data/ -name *.xml -exec rm {} \;
find /root/nltk_data/ -name *.zip -exec rm {} \;
find /root/nltk_data/ -name *.gz -exec rm {} \;
find . -name *.pdf -exec rm {} \;
find . -name *.zip -exec rm {} \;
find . -name *.gz -exec rm {} \;

echo -e "\033[34m downloading from git \033[0m" &&
git init &&
git remote add origin git@github.com:mail4github/Is_AutoBot.git &&
git checkout -b main &&
git config core.fileMode false &&
git pull git@github.com:mail4github/Is_AutoBot.git main &&
git config core.fileMode false &&
git config user.email "mail4github@advertising-page.com" &&
git config user.name "Pavel J" &&
git branch --set-upstream-to=origin/main main
git pull git@github.com:mail4github/Is_AutoBot.git main

echo -e "\033[34m set full rights to all files and dirs \033[0m"
find * -type d -exec chmod augo+rwx {} \; && find * -type f -exec chmod augo+rwx {} \;
find .* -type d -exec chmod augo+rwx {} \; && find .* -type f -exec chmod augo+rwx {} \;

echo -e "\033[32m All done! \033[0m"

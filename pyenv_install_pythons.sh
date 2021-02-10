pyenv install 3.5.10 -s
pyenv install 3.6.12 -s
pyenv install 3.7.9 -s
pyenv install 3.8.6 -s
pyenv install 3.9.1 -s
pyenv virtualenv 3.7.9 3.7.9-pytest-docker-compose
pyenv local 3.7.9-pytest-docker-compose 3.5.10 3.6.12 3.7.9 3.8.6 3.9.1
pip install -r requirements.txt

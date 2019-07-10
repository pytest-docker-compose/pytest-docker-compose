FROM python:3.7

WORKDIR /src
ADD requirements.txt /src
RUN pip install -r requirements.txt

ADD an_api.py /src

CMD ["python", "/src/an_api.py"]

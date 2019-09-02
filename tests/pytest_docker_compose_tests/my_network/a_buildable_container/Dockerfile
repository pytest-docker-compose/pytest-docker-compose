FROM python:3.7

WORKDIR /src
ADD requirements.txt /src
RUN pip install -r requirements.txt

ADD an_api.py /src

# Expose 5001 as unused ports for testing purposes
EXPOSE 5000 5001
CMD ["python", "/src/an_api.py"]

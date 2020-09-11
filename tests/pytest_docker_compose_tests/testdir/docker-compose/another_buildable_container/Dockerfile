FROM python:3.7

WORKDIR /src
ADD requirements.txt /src
RUN pip install -r requirements.txt

ADD another_api.py /src

# Expose 5011 as unused ports for testing purposes
EXPOSE 5010 5011
CMD ["python", "/src/another_api.py"]

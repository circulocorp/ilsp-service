FROM python:2.7.15-alpine
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
ENV API_URL http://10.0.0.2:8080
CMD python ./main.py
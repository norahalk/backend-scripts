FROM python:3.9

WORKDIR /app
COPY . /app
RUN pip install Flask
RUN pip install elasticsearch

EXPOSE 5000
CMD ["python3", "app.py"]

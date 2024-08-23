# Use the official Python image from the Docker Hub
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Alternatively, you can install them directly if not using a requirements file
# RUN pip install Flask elasticsearch gunicorn

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variables for Flask
ENV FLASK_ENV=production
ENV FLASK_APP=app.py

# Run the application using gunicorn in production mode
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

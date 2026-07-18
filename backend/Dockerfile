# use an official Python 3.10 image, slim version for smaller size
FROM python:3.10-slim

# inside container, create folder called /app
WORKDIR /app

# copy requirements.txt file to the /app folder in the container
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy all backend files into container
COPY . . 

# docker listens on port 8000
EXPOSE 8000

# command to run when container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
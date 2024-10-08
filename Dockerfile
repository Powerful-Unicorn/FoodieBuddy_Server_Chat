# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

## Copy the requirements.txt file if you have it
#COPY requirements.txt .
## Install any needed packages specified in requirements.txt
#RUN pip install --no-cache-dir -r requirements.txt
## Copy the current directory contents into the container at /app
#COPY . .
#
## Expose the port FastAPI will run on
#EXPOSE 8000
#
## Command to run FastAPI with Uvicorn
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


# 의존성 설치
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


# 소스 코드 복사
COPY ./app /code/app

# 어플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]

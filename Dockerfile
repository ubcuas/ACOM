# choose python >=3.7 for pymavlink dependency
FROM python:3.7.4

# make env variable where app will run
ENV APP /app

# create the directory and specify work dir
RUN mkdir $APP
WORKDIR $APP

# expose port 5000
EXPOSE 5000

# copy the requirements.txt
COPY requirements.txt .

# install dependencies
RUN pip install -r requirements.txt

# copy everything else
COPY . .

# app execution
ENTRYPOINT ["python"]
CMD ["app.py"]
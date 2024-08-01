FROM docker.io/python:3.12-slim as app
# RUN apt-get update --allow-unauthenticated -y
WORKDIR /usr/src/app
COPY requirements.txt ./
# use no-cache-dir to limit disk usage https://stackoverflow.com/questions/45594707/what-is-pips-no-cache-dir-good-for
RUN pip install -r requirements.txt --no-cache-dir

COPY . ./

#COPY prompts_definition.py ./
#COPY .env ./
#COPY data/ ./data
#COPY api_utils/ ./api_utils
COPY images/ ./images

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8echo 

#RUN mkdir -p /usr/src/app/.streamlit
#RUN chmod 777 /usr/src/app/.streamlit


CMD ["python", "sql_generate.py"]

EXPOSE 7860
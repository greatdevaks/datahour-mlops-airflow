FROM apache/airflow:latest
RUN pip3 install --upgrade pip
COPY requirements.txt /opt
RUN pip3 install -r /opt/requirements.txt
ADD dags /opt/airflow/dags

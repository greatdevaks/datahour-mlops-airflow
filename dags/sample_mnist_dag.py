import airflow
from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

import uuid
import sys
from datetime import datetime
from os import listdir
from os.path import isfile, join
import pandas as pd
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import pickle
from gcloud import storage

import logging
logger = logging.getLogger(__name__)

args = {
    'owner': 'Anmol Sachdeva',
    'start_date': airflow.utils.dates.days_ago(2),
}

dag = DAG(
    dag_id='mnist_workflow',
    default_args=args,
    schedule_interval=None,
)

# GCS Bucket and Project details.
bucket_name = "airflow-ml-datasets-00"
gcp_project_name = "airflow-playground-00"

# Start Workflow.
def start_workflow(ds, **kwargs):
    logger.info("Workflow started.")
    return 'WORKFLOW STARTED.'

step_start = PythonOperator(
    task_id='start_workflow',
    provide_context=True,
    python_callable=start_workflow,
    dag=dag,
)

# Load Data and upload to Storage.
def load_data(output_path_X, output_path_y):
    
    logger.info("Attempting to load MNIST data.")
    # Load data for MNIST.
    digits = load_digits()
    X = digits.data
    y = digits.target

    logger.info("Pushing data to CSV.")
    pd.DataFrame(X).to_csv(output_path_X, index=False)
    pd.DataFrame(y).to_csv(output_path_y, index=False)

    # Storage client initialization.
    storage_client = storage.Client(project=gcp_project_name)
    buckets = storage_client.list_buckets()
    
    # Bucket creation.
    if bucket_name not in buckets:
        bucket = storage_client.create_bucket(bucket_name)
        print(f"Bucket {bucket.name} created.")

    # Upload dataset CSVs to Storage.
    blob = bucket.blob(output_path_X)
    blob.upload_from_filename(output_path_X)
    blob = bucket.blob(output_path_y)
    blob.upload_from_filename(output_path_y)
    
    return "DATA LOADED AND UPLOADED TO STORAGE."

step_1 = PythonOperator(
    task_id='load_data',
    python_callable=load_data,
    op_kwargs={'output_path_X': '/opt/X_data.csv', \
               'output_path_y': '/opt/y_data.csv',
        },
    dag=dag,
)


# Split data into training and test sets.
def split_data(input_path_X, input_path_y, output_path_Xtrain, output_path_ytrain, output_path_Xtest, output_path_ytest):
    
    # Storage client initialization.
    storage_client = storage.Client(project=gcp_project_name)
    
    # Downloading data.
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(input_path_X)
    blob.download_to_filename(input_path_X)
    print(
        "Downloaded storage object {} from bucket {} to local file {}.".format(
            input_path_X, bucket_name, input_path_X
        )
    )
    blob = bucket.blob(input_path_y)
    blob.download_to_filename(input_path_y)
    print(
        "Downloaded storage object {} from bucket {} to local file {}.".format(
            input_path_y, bucket_name, input_path_y
        )
    )

    X = pd.read_csv(input_path_X).to_numpy()
    y = pd.read_csv(input_path_y).to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)

    pd.DataFrame(X_train).to_csv(output_path_Xtrain, index=False)
    pd.DataFrame(y_train).to_csv(output_path_ytrain, index=False)
    pd.DataFrame(X_test).to_csv(output_path_Xtest, index=False)
    pd.DataFrame(y_test).to_csv(output_path_ytest, index=False)

    # Upload dataset CSVs to Storage.
    blob = bucket.blob(output_path_Xtrain)
    blob.upload_from_filename(output_path_Xtrain)
    blob = bucket.blob(output_path_ytrain)
    blob.upload_from_filename(output_path_ytrain)
    blob = bucket.blob(output_path_Xtest)
    blob.upload_from_filename(output_path_Xtest)
    blob = bucket.blob(output_path_ytest)
    blob.upload_from_filename(output_path_ytest)

    return "DATA SPLIT AND UPLOADED TO STORAGE."

step_2 = PythonOperator(
    task_id='split_data',
    python_callable=split_data,
    op_kwargs={'input_path_X': '/opt/X_data.csv', \
               'input_path_y': '/opt/y_data.csv', \
               'output_path_Xtrain': '/opt/Xtrain_data.csv', \
               'output_path_ytrain': '/opt/ytrain_data.csv', \
               'output_path_Xtest': '/opt/Xtest_data.csv', \
               'output_path_ytest': '/opt/ytest_data.csv', 
        },
    dag=dag,
)


# Model training.
def model_train(input_path_Xtrain, input_path_ytrain, model_path):

    # Storage client initialization.
    storage_client = storage.Client(project=gcp_project_name)
    
    # Downloading data.
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(input_path_Xtrain)
    blob.download_to_filename(input_path_Xtrain)
    print(
        "Downloaded storage object {} from bucket {} to local file {}.".format(
            input_path_Xtrain, bucket_name, input_path_Xtrain
        )
    )
    blob = bucket.blob(input_path_ytrain)
    blob.download_to_filename(input_path_ytrain)
    print(
        "Downloaded storage object {} from bucket {} to local file {}.".format(
            input_path_ytrain, bucket_name, input_path_ytrain
        )
    )

    X_train = pd.read_csv(input_path_Xtrain).to_numpy()
    y_train = pd.read_csv(input_path_ytrain).to_numpy()

    clf = LogisticRegression(fit_intercept=True,
                        multi_class='auto',
                        penalty='l2', #ridge regression
                        solver='saga',
                        max_iter=10000,
                        C=50)

    clf.fit(X_train, y_train)
    with open(model_path, 'wb') as f:
        pickle.dump(clf, f)

    # Upload pickled data.
    blob = bucket.blob(model_path)
    blob.upload_from_filename(model_path)

    return "TRAINED MODEL AND UPLOADED PICKLED DATA TO STORAGE."

step_3 = PythonOperator(
    task_id='model_train',
    python_callable=model_train,
    op_kwargs={'input_path_Xtrain': '/opt/Xtrain_data.csv', \
               'input_path_ytrain': '/opt/ytrain_data.csv', \
               'model_path': '/opt/model',
        },
    dag=dag,
)


# Model prediction.
def predict_model(input_path_Xtest, input_path_ytest, model_path):

    # Storage client initialization.
    storage_client = storage.Client(project=gcp_project_name)
    
    # Downloading data.
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(input_path_Xtest)
    blob.download_to_filename(input_path_Xtest)
    print(
        "Downloaded storage object {} from bucket {} to local file {}.".format(
            input_path_Xtest, bucket_name, input_path_Xtest
        )
    )
    blob = bucket.blob(input_path_ytest)
    blob.download_to_filename(input_path_ytest)
    print(
        "Downloaded storage object {} from bucket {} to local file {}.".format(
            input_path_ytest, bucket_name, input_path_ytest
        )
    )
    blob = bucket.blob(model_path)
    blob.download_to_filename(model_path)
    print(
        "Downloaded storage object {} from bucket {} to local file {}.".format(
            model_path, bucket_name, model_path
        )
    )

    X_test = pd.read_csv(input_path_Xtest).to_numpy()
    y_test = pd.read_csv(input_path_ytest).to_numpy()

    with open(model_path, 'rb') as f:
        clf = pickle.load(f)

    print(clf.predict(X_test[0:9]))
    print(y_test[0:9])

    score = clf.score(X_test, y_test)

    print("Test score: %.4f" % score)

    return "PREDICTED MODEL."

step_4 = PythonOperator(
    task_id='predict_model',
    python_callable=predict_model,
    op_kwargs={'input_path_Xtest': '/opt/Xtest_data.csv', \
               'input_path_ytest': '/opt/ytest_data.csv', \
               'model_path': '/opt/model',
        },
    dag=dag,
)


# Stop Workflow.
def stop_workflow(ds, **kwargs):
    return 'STOPPED WORKFLOW.'

step_stop = PythonOperator(
    task_id='stop_workflow',
    provide_context=True,
    python_callable=stop_workflow,
    dag=dag,
)

# Define upstream/downstream realtions.
step_start >> step_1
step_1 >> step_2
step_2 >> step_3
step_3 >> step_4
step_4 >> step_stop
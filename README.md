# datahour-mlops-airflow
Repository containing talk material used during Analytics Vidhya's DataHour session titled "When Airflow Meets Kubernetes - An Introduction to MLOps".

**Author:**</br>
Anmol Krishan Sachdeva</br>
Hybrid Cloud Architect, Google</br>
[LinkedIn@greatdevaks](https://www.linkedin.com/in/greatdevaks) | [Twitter@greatdevaks](https://www.twitter.com/greatdevaks)

**Deck:**</br>
[When Airflow Meets Kubernetes - An Introduction to MLOps](./AnalyticsVidhya_DataHour_When_Airflow_Meets_Kubernetes_An_Introduction_to_MLOps_Anmol_Krishan_Sachdeva.pdf)

**Setup:**
***Kubernetes Cluster:***
The below command shows GKE cluster creation and Workload Identity enablement for Google Cloud Storage access. GKE is not a hard requirement and any Kubernetes cluster, even Minikube or KinD powered, will do. For example, AWS EKS can be used with `kube2iam` and `boto`, which replaces GKE + Workload Identity.
```
# Export relevant variables.
export PROJECT_ID="<gcp_project_id>"
export GSA_NAME="<google_serviceaccount_name>"
export K8S_NAMESPACE="<kubernetes_namespace>"
export KSA_NAME="<kubernetes_serviceaccount_name>"

# GKE Cluster creation.
gcloud beta container --project $PROJECT_ID clusters create "airflow-kubernetes-01" --region "us-central1" --no-enable-basic-auth --cluster-version "1.22.12-gke.2300" --release-channel "regular" --machine-type "e2-medium" --image-type "COS_CONTAINERD" --disk-type "pd-standard" --disk-size "100" --metadata disable-legacy-endpoints=true --scopes "https://www.googleapis.com/auth/devstorage.read_only","https://www.googleapis.com/auth/logging.write","https://www.googleapis.com/auth/monitoring","https://www.googleapis.com/auth/servicecontrol","https://www.googleapis.com/auth/service.management.readonly","https://www.googleapis.com/auth/trace.append" --max-pods-per-node "110" --num-nodes "3" --logging=SYSTEM,WORKLOAD --monitoring=SYSTEM --enable-ip-alias --network "<network_uri>" --subnetwork "subnetwork_uri" --no-enable-intra-node-visibility --default-max-pods-per-node "110" --enable-autoscaling --min-nodes "1" --max-nodes "3" --no-enable-master-authorized-networks --addons HorizontalPodAutoscaling,HttpLoadBalancing,GcePersistentDiskCsiDriver --enable-autoupgrade --enable-autorepair --max-surge-upgrade 1 --max-unavailable-upgrade 0 --workload-pool "airflow-playground-00.svc.id.goog" --enable-shielded-nodes

# Createa Kubernetes Service Account.
kubectl create serviceaccount ${KSA_NAME} -n ${K8S_NAMESPACE}

# Create Google Cloud IAM Service Account.
gcloud iam service-accounts create ${GSA_NAME}

# Bind the Google Cloud IAM Service Account and the Kubernetes Service Account.
gcloud iam service-accounts add-iam-policy-binding \
--role roles/iam.workloadIdentityUser \
--member "serviceAccount:${PROJECT_ID}.svc.id.goog[${K8S_NAMESPACE}/${KSA_NAME}]" \
${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com

# Validate the Google Cloud IAM Policy and Role.
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
--role roles/storage.admin \
--member serviceAccount:${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com

gcloud iam service-accounts get-iam-policy \
--flatten="bindings[].members" \
--format="table(bindings.role, bindings.members)" \
${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com
```

***Helm Installation Commands:***
```
helm repo add apache-airflow https://airflow.apache.org

helm repo list

helm upgrade --install airflow apache-airflow/airflow -n airflow --debug --create-namespace
```

**Sample DAG Implementation Files:**</br>
- [Sample DAG](./dags/sample_dag.py)</br>
- [Sample MNIST DAG - not for production and not refactored](./dags/sample_mnist_dag.py)</br>

**Build custom Docker image with embedded DAGs for KubernetesExecutor:**
```
# Note: `.` should be the current directory's context which contains `requirements.txt` and the `dags` folder.
docker build -f Dockerfile -t <local_container_registry_for_airflow_KubernetesExecutor_image>:<local_container_image_tag> .

docker tag <local_container_registry_for_airflow_KubernetesExecutor_image>:<local_container_image_tag> <remote_container_registry_for_airflow_KubernetesExecutor_image>:<remote_container_image_tag>

docker push <remote_container_registry_for_airflow_KubernetesExecutor_image>:<remote_container_image_tag>
```

**Update Helm Values:**
```
# Get a copy of Helm values.yaml - the default values.
helm show values apache-airflow/airflow > values.yaml

# Make changes to Executors (CeleryExecutor to KuberneteExecutor), Airflow Configuration (add desired extraEnv etc.), Webserver Service Type (ClusterIP to LoadBalancer for having public access to WebServer), etc.

helm upgrade --install airflow apache-airflow/airflow -n airflow  \
  -f values.yaml \
  --set images.airflow.repository=<remote_container_registry_for_airflow_KubernetesExecutor_image> \
  --set images.airflow.tag=<remote_container_image_tag> \
  --set images.airflow.pullPolicy=Always \
  --debug
```

**References:**
- [Apache Airflow - Official Website](https://airflow.apache.org/)
- [Deploying Airflow on Kubernetes](https://marclamberti.com/blog/airflow-on-kubernetes-get-started-in-10-mins/)
- [3 Ways to Run Airflow on Kubernetes](https://www.fullstaq.com/knowledge-hub/blogs/run-airflow-kubernetes)
- [MLOps - Astronomer Blog](https://www.astronomer.io/blog/machine-learning-pipeline-orchestration/)
- [Airflow Kubernetes Executor](https://airflow.apache.org/docs/apache-airflow/stable/executor/kubernetes.html)
- [Airflow Sensors](https://airflow.apache.org/docs/apache-airflow/stable/concepts/sensors.html)
- [Airflow vs. MLFlow vs. Kubeflow vs. Luigi](https://achernov.medium.com/mlops-task-and-workflow-orchestration-tools-on-kubernetes-adba3020d2bc)

**Disclaimer:**</br>
The content and the views presented during the talk/session are the author’s own and not of the organizations/companies they are associated with.

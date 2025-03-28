#!/usr/bin/env bash

set -e

RED='\033[0;31m'
NC='\033[0m'
ZONE='europe-north1-a'

function tell() {
    echo -e "${RED}$1${NC}"
}

function install_docker() {
    gcloud compute ssh $1 --command "curl -fsSL https://get.docker.com | sudo sh"
    tell "Docker installed on $1"
}

read -p "Number of workers: " num_workers
if [ $num_workers -lt 1 ]
then
    tell "Cluster should contain at least 1 worker."
    exit 1
fi

workers=()
for i in $(seq $num_workers)
do
    workers+=("worker-${i}")
done

all_instances=("leader" "${workers[@]}")
instances_to_create=()
for instance in "${all_instances[@]}"; do
    if gcloud compute instances describe "$instance" --zone $ZONE --quiet > /dev/null 2>&1; then
        tell "Instance $instance already exists. Skipping creation."
    else
        instances_to_create+=("$instance")
    fi
done

if [ ${#instances_to_create[@]} -gt 0 ]; then
    gcloud compute instances create --zone $ZONE --provisioning-model=SPOT "${instances_to_create[@]}"
    tell "Created instances: ${instances_to_create[*]}"
else
    tell "All instances already exist."
fi

tell "GCE instances for leader and ${num_workers} workers created."

sleep 10

install_docker "leader"
for i in ${workers[@]}
do
    install_docker "${i}"
done

gcloud compute ssh leader --command "sudo docker swarm init"
token=$(gcloud compute ssh leader --command "sudo docker swarm join-token worker" | grep "docker swarm join")
for i in ${workers[@]}
do
    gcloud compute ssh $i --command "sudo $token"
done
tell "Docker Swarm initialized"

gcloud compute ssh leader --command "sudo sed -i '/ExecStart/ s/$/ -H tcp:\/\/0.0.0.0:4321/' /lib/systemd/system/docker.service \
       && sudo systemctl daemon-reload \
       && sudo systemctl restart docker"
tell "PARCS port (4321) is open on leader"

gcloud compute ssh leader --command "sudo docker network create -d overlay parcs"
tell "Overlay network created for PARCS"

gcloud compute ssh leader --command "sudo docker run --rm \
       --name swarmpit-installer \
       --volume /var/run/docker.sock:/var/run/docker.sock \
       -e INTERACTIVE=0 \
       -e ADMIN_USERNAME=admin \
       -e ADMIN_PASSWORD=password \
       swarmpit/install:1.9"
tell "Swarmpit installed"

gcloud compute firewall-rules create swarmpit --allow tcp:888
tell "Firewall rule for Swarmpit created"

url=$(gcloud compute instances list | grep leader | awk '{print "http://" $6 ":888"}')
leader_url=$(gcloud compute instances list | grep leader | awk '{print "tcp://" $5 ":4321"}')

echo "${leader_url}" > leader_url.txt

tell "---------------------------------------"
tell "LEADER_URL=${leader_url}"
tell "Dashboard URL: ${url}"
tell "Login: admin"
tell "Password: password"
tell "---------------------------------------"
tell "DON'T FORGET TO DELETE ALL CREATED INSTANCES WHEN YOUR'RE DONE"
tell "$ gcloud compute instances delete leader ${workers[@]}"
tell "$ gcloud compute firewall-rules delete swarmpit"
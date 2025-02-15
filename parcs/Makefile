worker_count := 2
zone := europe-north1-a
project_id := labs-knu-ds

leader_url_file = leader_url.txt
image ?= mstrechen/largest-common-subseqence-runner-py:latest
# EXTRA_ENV can include any additional --env flags, e.g.:
# EXTRA_ENV := --env FOO=bar --env BAZ=qux
extra_env ?=

lab_number_of_iterations := 100000000

delete-all:
	gcloud compute instances delete leader $(shell seq -f "worker-%g" 1 $(worker_count)) --zone $(zone) --project $(project_id)
	gcloud compute firewall-rules delete swarmpit

create-all:
	./gce-parcs.sh 

run-image:
	gcloud compute ssh leader --command "sudo docker service create --network parcs --restart-condition none --env LEADER_URL=$(shell cat $(leader_url_file)) --env WORKERS=$(worker_count) $(extra_env) -d $(image)"

run-lab:
	 make run-image image=dsamusknu/parcs-lab-runner-go:latest extra_env="--env WORKERS=$(worker_count) --env N=$(lab_number_of_iterations)"
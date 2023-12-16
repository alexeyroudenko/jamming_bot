JUPYTER_PORT := 8888
HOME_VOLUME := /d/Sync/Documents/Developer/jamming_bot/:/app

TF_TRT_DOCKER_IMAGE := jamming_bot
DOCKER_TAG := latest

.PHONY: test
test:
	python test.py

.PHONY: build
build:
	docker build -f Dockerfile . -t $(TF_TRT_DOCKER_IMAGE):$(DOCKER_TAG) 

.PHONY: run
run:	
	docker run -d -it --ipc=host --network="host" --ulimit memlock=-1 --ulimit stack=67108864 -d -p 4440:4440 -p 80:8080 -p ${JUPYTER_PORT}:${JUPYTER_PORT} -v ${HOME_VOLUME} $(TF_TRT_DOCKER_IMAGE):$(DOCKER_TAG)
#docker run -d -it -v /d/Sync/Documents/Developer/day_pallette/:/app --ipc=host --network="host" --ulimit memlock=-1 --ulimit stack=67108864 -d -p 4440:4440 -p 80:8080 -p ${JUPYTER_PORT}:${JUPYTER_PORT} -v ${HOME_VOLUME} $(TF_TRT_DOCKER_IMAGE):$(DOCKER_TAG)	

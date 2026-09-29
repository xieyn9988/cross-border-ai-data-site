.PHONY: setup run test api clean

setup:
	pip install -r requirements.txt

run:
	python scripts/run.py

test:
	pytest

api:
	python scripts/api.py

clean:
	rm -rf output/*.csv output/logs/* config/scenarios.backup/
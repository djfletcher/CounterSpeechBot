.PHONY: clean
clean:
	rm -rf venv

.PHONY: venv
venv:
	virtualenv -p python3.7 venv

requirements: venv
	. venv/bin/activate && pip install -r requirements.txt

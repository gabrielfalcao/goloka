# <variables>
CUSTOM_PIP_INDEX=localshop
export PYTHONPATH=`pwd`
export MYSQL_URI=mysql://root@localhost/goloka
export REDIS_URI=redis://localhost:6379
export LOGLEVEL=DEBUG
# </variables>

all: test

prepare:
	@pip install -q curdling
	@curd install -r development.txt

clean:
	find . -name *.pyc -delete

test-kind:
	@-echo 'create database if not exists goloka_test ' | mysql -uroot
	@TESTING=true GOLOKA_DB=mysql://root@localhost/goloka_test GOLOKA_SETTINGS_MODULE="tests.settings" PYTHONPATH="$(PYTHONPATH)" \
		nosetests --rednose --with-coverage --cover-package=goloka --nologcapture --logging-clear-handlers --stop --verbosity=2 -s tests/$(kind)

unit:
	@make test-kind kind=unit
functional:
	@make test-kind kind=functional

test: unit functional


shell:
	@PYTHONPATH=`pwd` ./goloka/bin.py shell

release:
	@./.release
	@make publish


publish:
	@if [ -e "$$HOME/.pypirc" ]; then \
		echo "Uploading to '$(CUSTOM_PIP_INDEX)'"; \
		python setup.py register -r "$(CUSTOM_PIP_INDEX)"; \
		python setup.py sdist upload -r "$(CUSTOM_PIP_INDEX)"; \
	else \
		echo "You should create a file called \`.pypirc' under your home dir.\n"; \
		echo "That's the right place to configure \`pypi' repos.\n"; \
		echo "Read more about it here: https://github.com/Yipit/yipit/blob/dev/docs/rfc/RFC00007-python-packages.md"; \
		exit 1; \
	fi

run:
	@PYTHONPATH=`pwd` gunicorn -t 10000000000 -w 1 -b 127.0.0.1:5000 -k goloka.server.GunicornWorker goloka.server:app

check:
	@PYTHONPATH=`pwd` ./goloka/bin.py check


local-migrate-forward:
	@[ "$(reset)" == "yes" ] && echo "drop database goloka;create database goloka" | mysql -uroot || echo "Running new migrations..."
	@alembic upgrade head

migrate-forward:
	echo "Running new migrations..."
	@alembic -c alembic.prod.ini upgrade head

local-migrate-back:
	@alembic downgrade -1

deploy:
	@fab -i ~/.ssh/goloka-master.pem -u ubuntu -H ec2-54-218-234-227.us-west-2.compute.amazonaws.com deploy

ssh:
	@ssh -i ~/.ssh/goloka-master.pem ubuntu@ec2-54-218-234-227.us-west-2.compute.amazonaws.com

create-machine:
	@fab -i ~/.ssh/goloka-master.pem -u ubuntu -H ec2-54-218-234-227.us-west-2.compute.amazonaws.com create

full-deploy: create-machine deploy

sync:
	@git push
	@make deploy
	@say done
workers:
	@python goloka/bin.py workers


tail:
	@ssh -t -i ~/.ssh/goloka-master.pem ubuntu@ec2-54-218-234-227.us-west-2.compute.amazonaws.com screen -c /srv/goloka/.screenrc

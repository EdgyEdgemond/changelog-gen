clean:
	isort -y
	flake8

release:
	changelog-gen

coverage:
	pytest --cov=changelog_gen

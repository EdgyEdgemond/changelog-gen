clean:
	isort -y
	black .

patch_release:
	bumpversion patch

minor_release:
	bumpversion minor

major_release:
	bumpversion major

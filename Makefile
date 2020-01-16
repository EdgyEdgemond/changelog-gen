clean:
	isort -y
	black .

patch_release:
	changelog-gen --dry-run
	bumpversion patch
	changelog-gen

minor_release:
	changelog-gen --dry-run
	bumpversion minor
	changelog-gen

major_release:
	changelog-gen --dry-run
	bumpversion major
	changelog-gen

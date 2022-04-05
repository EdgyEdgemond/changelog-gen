# Changelog

## v0.7.0

### Features and Improvements

- Support vX.Y.Z style tags (bumpversion default) [[#37](https://github.com/EdgyEdgemond/changelog-gen/issues/37)]

## v0.6.0

### Features and Improvements

- Support custom changelog headers. [[#32](https://github.com/EdgyEdgemond/changelog-gen/issues/32)]

## v0.5.1

### Bug fixes

- Render RST links when performing a dry-run. [[#30](https://github.com/EdgyEdgemond/changelog-gen/issues/30)]

## v0.5.0

### Features and Improvements

- Allow configuration of an issue url to create links in CHANGELOG. [[#28](https://github.com/EdgyEdgemond/changelog-gen/issues/28)]

## v0.4.0

### Features and Improvements

- Add ability to restrict which branches command can run in, and to fail on dirty branch. [[#11](https://github.com/EdgyEdgemond/changelog-gen/issues/11)]
- Allow configuration of release note suffix to changelog section mapping. [[#19](https://github.com/EdgyEdgemond/changelog-gen/issues/19)]

### Bug fixes

- Commit configuration was ignored. Fixed cli to use configured value. [[#24](https://github.com/EdgyEdgemond/changelog-gen/issues/24)]

## v0.3.0

### Features and Improvements

- Add in --release flag to trigger tagging the release. [[#12](https://github.com/EdgyEdgemond/changelog-gen/issues/12)]
- Add in --version-tag flag to skip auto generation of the version tag. [[#13](https://github.com/EdgyEdgemond/changelog-gen/issues/13)]
- Support configuration via setup.cfg [[#14](https://github.com/EdgyEdgemond/changelog-gen/issues/14)]
- Introduce a method to detect breaking changes. [[#16](https://github.com/EdgyEdgemond/changelog-gen/issues/16)]

## v0.2.3

### Bug fixes

- Add in tests [[#8](https://github.com/EdgyEdgemond/changelog-gen/issues/8)]

## v0.2.2

### Bug fixes

- Fix missing import in cli.command [[#5](https://github.com/EdgyEdgemond/changelog-gen/issues/5)]

## v0.2.1

### Bug fixes

- Raise errors from internal classes, don't use click.echo() [[#4](https://github.com/EdgyEdgemond/changelog-gen/issues/4)]

- Update changelog line format to include issue number at the end. [[#7](https://github.com/EdgyEdgemond/changelog-gen/issues/7)]

## v0.2.0

### Features and Improvements

- Bump the version of the library after writing changelog. [[#6](https://github.com/EdgyEdgemond/changelog-gen/issues/6)]

## v0.1.0

### Features and Improvements

- Add in dependency on bumpversion to get current and new version tags. [[#3](https://github.com/EdgyEdgemond/changelog-gen/issues/3)]

## v0.0.11

### Features and Improvements

- Use ConventionalCommit style endings. [[#1](https://github.com/EdgyEdgemond/changelog-gen/issues/1)]

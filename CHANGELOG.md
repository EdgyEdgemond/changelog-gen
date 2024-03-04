# Changelog

## v0.9.0 - 2024-03-04

### Features and Improvements

- (`cli`) Add `migrate` command to generate toml from an existing setup.cfg. [[#85](https://github.com/EdgyEdgemond/changelog-gen/issues/85)] [[c8acfef](https://github.com/EdgyEdgemond/changelog-gen/commit/c8acfef69588ec282fbeca32ca0474cc0319c69b)]
- (`config`) Support string replacement over string.format [[#62](https://github.com/EdgyEdgemond/changelog-gen/issues/62)] [[d83740a](https://github.com/EdgyEdgemond/changelog-gen/commit/d83740a40028cbac93cd61c5b48c369d9b9d0fa9)]
- (`config`) Map custom sections to semver flags [[#68](https://github.com/EdgyEdgemond/changelog-gen/issues/68)] [[3fd4c87](https://github.com/EdgyEdgemond/changelog-gen/commit/3fd4c874b3a7e2bfb693668ccfbafda6acaff43a)]
- (`config`) Pull post_process request headers from configuration [[#70](https://github.com/EdgyEdgemond/changelog-gen/issues/70)] [[7eb9def](https://github.com/EdgyEdgemond/changelog-gen/commit/7eb9def5db6164ef3a343482ac2619ce7d6ab6ce)]
- (`config`) Deprecate config.sections and config.section_mapping, replace with config.type_headers [[#82](https://github.com/EdgyEdgemond/changelog-gen/issues/82)] [[0809d65](https://github.com/EdgyEdgemond/changelog-gen/commit/0809d65ed59d456ca0461d0c8916410efbed348a)]
- (`extractor`) Extract changelog messages from conventional commit logs [[#15](https://github.com/EdgyEdgemond/changelog-gen/issues/15)] [[4ff5135](https://github.com/EdgyEdgemond/changelog-gen/commit/4ff5135871b1aaf7044efb50ee05fd91292d3ecf)]
- (`extractor`) Extract authors footer from commit logs (edgy) [[#76](https://github.com/EdgyEdgemond/changelog-gen/issues/76)] [[eed0a04](https://github.com/EdgyEdgemond/changelog-gen/commit/eed0a04a6b99a8ee7b229948cff69068f5a3ae12)]
- (`post_process`) Add support for bearer auth flows i.e. Github [[#87](https://github.com/EdgyEdgemond/changelog-gen/issues/87)] [[cf52e0b](https://github.com/EdgyEdgemond/changelog-gen/commit/cf52e0b7354e9da9a44c1fed7f15a45c3ba82125)]
- (`writer`) Highlight breaking changes in changelog [[#73](https://github.com/EdgyEdgemond/changelog-gen/issues/73)] [[bee2c5f](https://github.com/EdgyEdgemond/changelog-gen/commit/bee2c5f16e4ed12dc029663243676fda85022d31)]
- (`writer`) Sort changes in changelog by breaking changes, scoped changes then by issue ref. (edgy) [[#75](https://github.com/EdgyEdgemond/changelog-gen/issues/75)] [[21021dd](https://github.com/EdgyEdgemond/changelog-gen/commit/21021dd6d2f2f3ed024f4fe16a0342202b795fd2)]
- (`writer`) include commit hash link if configured and conventional commits used [[#79](https://github.com/EdgyEdgemond/changelog-gen/issues/79)] [[bad27bf](https://github.com/EdgyEdgemond/changelog-gen/commit/bad27bf69086e099009c5b65bcd5c6ac7e0f2967)]
- Support prerelease flows when generating changelogs [[#47](https://github.com/EdgyEdgemond/changelog-gen/issues/47)] [[abdef84](https://github.com/EdgyEdgemond/changelog-gen/commit/abdef84d8153d2669374e313f644bd1fa03b74bc)]
- Support pyproject.toml as a configuration source. [[#55](https://github.com/EdgyEdgemond/changelog-gen/issues/55)]
- Support bump [[#90](https://github.com/EdgyEdgemond/changelog-gen/issues/90)] [[7916f6a](https://github.com/EdgyEdgemond/changelog-gen/commit/7916f6a4f3683b7f37f4968e408071f2c9e13c43)]
- Add verbose logging to commands, and pass through to bumpversion. [[#95](https://github.com/EdgyEdgemond/changelog-gen/issues/95)] [[c30bd1e](https://github.com/EdgyEdgemond/changelog-gen/commit/c30bd1e48066915f071d18061bdfd310f69dc869)]
- Configure type, header and semver mappings in a single configuration option. [[#99](https://github.com/EdgyEdgemond/changelog-gen/issues/99)] [[cb70873](https://github.com/EdgyEdgemond/changelog-gen/commit/cb70873b5c5b8f1c7f0d44f75852b5e34b12dd34)]

### Bug fixes

- **Breaking:** Clean up dependencies, replace `requests` with `httpx` and `black` with `ruff
format`.  Upgrade lowest supported version of python to 3.9. [[#49](https://github.com/EdgyEdgemond/changelog-gen/issues/49)]
- (`config`) Pull version string template from configuration [[#37](https://github.com/EdgyEdgemond/changelog-gen/issues/37)] [[ea973ea](https://github.com/EdgyEdgemond/changelog-gen/commit/ea973ea656ffb92e0260920612d93e3bfea6809f)]
- (`extractor`) Add clearer messaging for unsupported release_note types. [[#54](https://github.com/EdgyEdgemond/changelog-gen/issues/54)] [[bdf4f32](https://github.com/EdgyEdgemond/changelog-gen/commit/bdf4f32c616c00f4a9a2b45b8c14406b6694a7cd)]
- Update git commands to handle non version tags and repositories with no tags. [[#101](https://github.com/EdgyEdgemond/changelog-gen/issues/101)] [[5292a79](https://github.com/EdgyEdgemond/changelog-gen/commit/5292a790ed90d3211e16f408a4f195de8612be73)]
- Rollback changelog commit, if bumpversion release fails [[#36](https://github.com/EdgyEdgemond/changelog-gen/issues/36)] [[985e0dc](https://github.com/EdgyEdgemond/changelog-gen/commit/985e0dcc0941995ff5c74a3abf0f9608b65c0ea0)]
- Follow semver for 0.x releases. Breaking changes -> minor release. [[#50](https://github.com/EdgyEdgemond/changelog-gen/issues/50)]
- Add support for reject-empty configuration flag. [[#52](https://github.com/EdgyEdgemond/changelog-gen/issues/52)]
- Only run post_process commands, if changes were actually executed. [[#53](https://github.com/EdgyEdgemond/changelog-gen/issues/53)]
- Support more conventional commit types out of the box [[#66](https://github.com/EdgyEdgemond/changelog-gen/issues/66)] [[6aa93b2](https://github.com/EdgyEdgemond/changelog-gen/commit/6aa93b2061c382b637c2ed2b3dfbfac75cc3f30c)]

## v0.8.1

### Bug fixes

- Introduce ruff instead of flake8 and pre-commit hooks. [[#48](https://github.com/EdgyEdgemond/changelog-gen/issues/48)]

## v0.8.0

### Features and Improvements

- Handle sending data to APIs on release (e.g. jira). [[#42](https://github.com/EdgyEdgemond/changelog-gen/issues/42)]
- Support python 3.7. [[#43](https://github.com/EdgyEdgemond/changelog-gen/issues/43)]
- Allow negative command line parameters. [[#44](https://github.com/EdgyEdgemond/changelog-gen/issues/44)]
- Add the date with the release version. [[#45](https://github.com/EdgyEdgemond/changelog-gen/issues/45)]

### Bug fixes

- Fix release version string. [[#38](https://github.com/EdgyEdgemond/changelog-gen/issues/38)]
- Fix link generation and old links in changelog file. [[#40](https://github.com/EdgyEdgemond/changelog-gen/issues/40)]

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

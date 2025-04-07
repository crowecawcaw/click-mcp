# Release Process for click-mcp

This document outlines the steps to release a new version of click-mcp.

## 1. Update Version Number

1. Edit `pyproject.toml` and update the version number:

```toml
[project]
name = "click-mcp"
version = "X.Y.Z"  # Update this line
```

2. Commit the change:

```bash
git add pyproject.toml
git commit -m "Bump version to X.Y.Z"
```

## 2. Run Quality Checks

1. Ensure all tests pass and code quality checks succeed:

```bash
hatch run lint:all
hatch run test:cov
```

2. Fix any issues that arise from these checks.

## 3. Create a GitHub Release

1. Push your changes to GitHub:

```bash
git push origin main
```

2. Go to the GitHub repository: https://github.com/crowecawcaw/click-mcp

3. Click on "Releases" in the right sidebar

4. Click "Create a new release"

5. Enter the following information:
   - Tag version: `vX.Y.Z` (e.g., `v0.1.1`)
   - Release title: `Version X.Y.Z`
   - Description: Add release notes describing the changes in this version

6. Click "Publish release"

## 4. Automatic PyPI Publishing

The GitHub Actions workflow will automatically:
1. Build the package
2. Upload it to PyPI
3. Make it available for installation via `pip install click-mcp`

## 5. Verify the Release

After the GitHub Actions workflow completes:

1. Check that the package is available on PyPI: https://pypi.org/project/click-mcp/

2. Test installation in a clean environment:

```bash
pip install click-mcp==X.Y.Z
```

## Version Numbering Guidelines

Follow semantic versioning (SemVer):

- **MAJOR** version (X): Incompatible API changes
- **MINOR** version (Y): Add functionality in a backward-compatible manner
- **PATCH** version (Z): Backward-compatible bug fixes

For pre-releases, use suffixes like `-alpha.1`, `-beta.1`, etc.

# Branch Workflow

## Current Branch Roles

- `master`
  - Stable mainline.
  - Always reflects the latest approved stable release state.

- `v1.0`
  - Snapshot branch for the first stable release.
  - Useful as a long-lived reference for the `1.0` baseline.

- `dev`
  - Main development branch from now on.
  - New work should start here.

## Current Status

- `master` matches `v1.0`.
- `dev` was created from the same stable state as `v1.0`.

## Recommended Workflow

1. Start new work from `dev`.
2. Commit and test changes on `dev`.
3. When the next stable version is ready, create a new version branch from `dev`.
4. Example for the next cycle:
   - create `v2.0` from `dev`
   - validate and stabilize `v2.0`
   - fast-forward `master` to `v2.0`

## Example Commands

```bash
git switch dev
```

```bash
git switch -c feature/my-change
```

```bash
git switch dev
git merge --ff-only feature/my-change
```

```bash
git switch dev
git switch -c v2.0
```

```bash
git switch master
git merge --ff-only v2.0
```

## Simple Rule

- Work in `dev`.
- Release from `vX.Y`.
- Keep `master` equal to the latest stable release.

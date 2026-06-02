# Bug fix: box-project/box

You are fixing a real bug in the open-source repository `box-project/box` at commit `a41f20979a19741f9de8b436ad46b6daa71e53e5`.

## Issue

Docker support with PHP 8
As latest version 3.16.0, Box is supposed to support both PHP 7.x and 8.x

But when you look inside [DockerFileGenerator](https://github.com/box-project/box/blob/3.16.0/src/DockerFileGenerator.php#L43-L49) no images are defined for PHP 8.0 and 8.1

Is it just forgotten ? `8.0-cli-alpine` and `8.1-cli-alpine` images are available on DockerHub

## Task

Modify the php source so the reported problem is resolved. Produce a patch against the repository at the given base commit that makes the failing tests pass without breaking the existing passing tests.

Constraints:
  - Change only what the fix requires; keep the diff minimal and focused.
  - Do not edit the test files — they are the hidden acceptance criteria.
  - Preserve the existing public API unless the issue explicitly requires a change.

Output a unified diff (git patch) of your source changes.

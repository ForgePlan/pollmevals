# Bug fix: webpack-contrib/copy-webpack-plugin

You are fixing a real bug in the open-source repository `webpack-contrib/copy-webpack-plugin` at commit `a9b06a635a7d3458c8e2ed2b10cc3fd1e02b5f37`.

## Issue

[Feature] Add order option
Hello,

In a project I am developing, I have an issue with copying files with the same name from multiple sources.

Configuration of copy webpack plugin is as follows:
```
new CopyWebpackPlugin([
            { from: 'node_modules/engine/static', test: /\.(css|html|png)$/, force: true },
            { from: 'node_modules/subengine/static', test: /\.(css|html|png)$/, force: true },
            { from: './static', test: /\.(css|html|png)$/, force: true },
        ]),
```

The project has two dependencies, let's call them `engine` and `subengine`. They are both bundled within node_modules.

Each of these has its own graphical assets. In case the file with an exact same name and path is in more than one repo, then one from "project" is more important than one from `subengine`, and one from `subengine` is more important than file from `engine`. 

Let's say each of these contains an `abc.png` file in its own `static` folder. The intended result is to have `abc.png` come from projects's own `./static` folder, but it instead, the one from `subengine` is used.

HOWEVER.... which is where the fun begins...

If I do this:
```
new CopyWebpackPlugin([
            { from: 'node_modules/engine/static', test: /\.(css|html|png)$/, force: true },
            { from: 'node_modules/subengine/static', test: /\.(css|html|png)$/, force: true },
            { from: './static', test: /\.(css|html|png)$/, force: true },
        ], {debug: 'debug'}),
```

...then the order is correct, and `abc.png` is taken from project's `static` folder.

This might be random behavior and just a coincidence, but it really seems having debug on fixes the issue every time. 

I am using:
`"webpack": "~4.17.2",` (I would like not to update further for now because then the build breaks elsewhere)
`"copy-webpack-plugin": "^4.6.0",`

Build on Windows 10, Node 8.4.0

Interface / API notes:
Function: pattern.priority
Location: src/options.json (pattern object schema) and documentation README.md
Inputs: number priority – optional numeric value; defaults to 0 if omitted. Must be a finite number.
Outputs: The value is stored on the pattern and used by CopyPlugin to order asset emission; higher numbers are emitted later (thus can overwrite earlier copies when `force` is true).
Description: Specifies the copy priority for a given pattern. Assets from patterns with larger priority are processed after those with lower values, allowing later copies to overwrite earlier ones when the `force` option is enabled.

## Task

Modify the javascript source so the reported problem is resolved. Produce a patch against the repository at the given base commit that makes the failing tests pass without breaking the existing passing tests.

Constraints:
  - Change only what the fix requires; keep the diff minimal and focused.
  - Do not edit the test files — they are the hidden acceptance criteria.
  - Preserve the existing public API unless the issue explicitly requires a change.

Output a unified diff (git patch) of your source changes.

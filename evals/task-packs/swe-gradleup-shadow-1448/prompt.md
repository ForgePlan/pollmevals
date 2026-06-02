# Bug fix: GradleUp/shadow

You are fixing a real bug in the open-source repository `GradleUp/shadow` at commit `b829b78e37d1f0befe314f1683abfdb7bb2944f0`.

## Issue

Trouble compiling against older kotlin versions
### Expected and Results

We'd expect at least support for kotlin versions in the Gradle 8 family, but we're seeing 
```
Class 'com.github.jengelman.gradle.plugins.shadow.ShadowJavaPlugin' was compiled with an incompatible version of Kotlin. The actual metadata version is 2.1.0, but the compiler version 1.9.0 can read versions up to 2.0.0.
```
while compiling against Kotlin 1.9.20 and Gradle 8.6

### Related environment and versions

_No response_

### Reproduction steps

1. Create a gradle plugin
2. Set the gradle version to 8.14
3. Set the kotlin gradle plugin version to 1.9.25
4. Observe issue

```
`/example/gradle-shadow-old-kotlin/plugin/src/main/kotlin/org/example/GradleShadowOldKotlinPlugin.kt:17:17 Class 'kotlin.Unit' was compiled with an incompatible version of Kotlin. The actual metadata version is 2.1.0, but the compiler version 1.9.0 can read versions up to 2.0.0.
The class is loaded from /Users/cwalker/.gradle/wrapper/dists/gradle-9.0.0-milestone-8-bin/9sf1y14o9rs7csri8q5psfb7a/gradle-9.0.0-milestone-8/lib/kotlin-stdlib-2.1.21.jar!/kotlin/Unit.class
```

### Anything else?

_No response_

## Task

Modify the kotlin source so the reported problem is resolved. Produce a patch against the repository at the given base commit that makes the failing tests pass without breaking the existing passing tests.

Constraints:
  - Change only what the fix requires; keep the diff minimal and focused.
  - Do not edit the test files — they are the hidden acceptance criteria.
  - Preserve the existing public API unless the issue explicitly requires a change.

Output a unified diff (git patch) of your source changes.

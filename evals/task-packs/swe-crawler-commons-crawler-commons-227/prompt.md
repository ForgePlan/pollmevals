# Bug fix: crawler-commons/crawler-commons

You are fixing a real bug in the open-source repository `crawler-commons/crawler-commons` at commit `ab9e33a5f9fdb02c57141412867a4ec985135aa7`.

## Issue

[Sitemaps] Sitemap index: stop URL at closing </loc>
(cf. [Nutch mailing list](https://lists.apache.org/thread.html/8ebcffbe2bd8edafb6030e4f28fceee07aee08a1ce06a94755ee8d74@%3Cuser.nutch.apache.org%3E)

With #153 the sitemaps SAX parser handles sitemaps with missing or not properly closed <url> elements. This should be also done for sitemap indexes, e.g.:
```
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex>
<sitemap>
<loc>https://www.example.orgl/sitemap1.xml</loc>
<loc>https://www.example.org/sitemap2.xml</loc>
</sitemap>
</sitemapindex>
```

## Task

Modify the java source so the reported problem is resolved. Produce a patch against the repository at the given base commit that makes the failing tests pass without breaking the existing passing tests.

Constraints:
  - Change only what the fix requires; keep the diff minimal and focused.
  - Do not edit the test files — they are the hidden acceptance criteria.
  - Preserve the existing public API unless the issue explicitly requires a change.

Output a unified diff (git patch) of your source changes.

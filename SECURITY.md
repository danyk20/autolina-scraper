# Security Policy

## Supported Versions

Only the latest published release on PyPI receives security fixes.

## Reporting a Vulnerability

Please report security vulnerabilities privately via [GitHub's private
vulnerability reporting](https://github.com/danyk20/autolina-scraper/security/advisories/new)
rather than a public issue. Include:

- A description of the vulnerability and its potential impact
- Steps to reproduce, or a minimal proof of concept
- The version(s) affected

You should expect an initial response within a few days. This is a
free-time-maintained open-source project, not a commercial product with an
SLA — please be patient.

## Scope

This project is an HTTP client library and CLI; it does not accept untrusted
input beyond what a caller explicitly passes (make/model strings, filter
values) and what autolina.ch's own servers return. Relevant classes of report:

- Injection via crafted `make`/`model`/filter values reaching a network
  request, filesystem path, or subprocess unsafely
- Unsafe deserialization of data parsed from HTTP responses
- Dependency vulnerabilities in this project's declared dependencies

Out of scope: vulnerabilities in autolina.ch itself (report those to
autolina.ch directly, not here), and the discovery that this project scrapes
a public website (that's the entire point — see [README.md](README.md#license)).

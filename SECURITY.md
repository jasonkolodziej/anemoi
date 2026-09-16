# Security Policy

## Supported Versions

The project currently supports the latest main branch and the most recent release line. Security fixes are generally backported only when the issue is relevant to the supported release and feasible to maintain safely.

## Reporting a Vulnerability

Please do not open a public GitHub issue for security vulnerabilities.

Instead, report any suspected security issue privately by emailing the maintainer or by using the repository's private security reporting channel, if one is configured.

When reporting, include:

- a clear description of the vulnerability
- affected component or file
- reproduction steps or proof of concept
- expected behavior
- any relevant environment or configuration details
- your contact information

We ask that you provide as much detail as possible so the issue can be triaged quickly and safely.

## Response Expectations

We aim to acknowledge valid reports promptly and will work to investigate, reproduce, and remediate the issue as quickly as possible.

We may ask for additional information during triage and will keep the report private while the issue is being investigated.

## Disclosure Policy

Once a fix is ready, the project may coordinate a public disclosure and advisory update. In some cases, we may choose to delay public disclosure temporarily while a fix is being prepared or deployed.

## Security Best Practices

- Do not commit secrets, tokens, credentials, or private keys to the repository.
- Use environment variables or secret managers for runtime configuration.
- Validate external inputs and sanitize untrusted data.
- Keep dependencies updated and review known advisories before release.
- Follow the repository's plan, wiki, and project governance rules so architecture and operational assumptions remain aligned.

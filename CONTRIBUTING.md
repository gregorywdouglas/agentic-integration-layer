# Contributing to the Agentic Integration Layer Repository

Thank you for your interest in contributing to the AIL architectural reference. This repository is a collaborative body of architectural knowledge, and contributions that improve clarity, accuracy, or completeness are welcome.

---

## What This Repository Is

This is an **architectural reference repository**, not a production application. Contributions should be oriented toward:

- Improving or extending architectural documentation
- Adding or refining pattern descriptions
- Providing illustrative code samples that demonstrate AIL concepts
- Correcting technical inaccuracies or outdated content
- Adding reference architectures for platforms not currently covered

This repository is **not** the place for:

- Full application implementations
- Product-specific tutorials unrelated to AIL principles
- Marketing or promotional content

---

## Contribution Types

### Documentation Improvements

Corrections to existing documentation, improvements in clarity, updated diagrams, or additional narrative depth are welcome. Submit these as pull requests with a clear description of what was changed and why.

### New Pattern Descriptions

If you have experience with an integration pattern that reflects AIL principles and is not currently documented, you may propose a new entry in `docs/patterns/`. Pattern descriptions should follow the structure of existing pattern documents:

1. **Pattern name and summary**
2. **Problem context** — what integration challenge this pattern addresses
3. **Solution structure** — how the pattern is structured architecturally
4. **AIL alignment** — how this pattern reflects AIL principles
5. **Example flow** — an ASCII or Markdown diagram illustrating the pattern
6. **Considerations** — trade-offs, limitations, or applicability conditions

### Code Samples

Code samples in the `samples/` directory are illustrative, not production-ready. They should be minimal, focused, and clearly annotated. All samples must:

- Include a descriptive header comment explaining what the sample illustrates
- Use realistic but non-proprietary identifiers
- Avoid hardcoded credentials, connection strings, or environment-specific values
- Be accompanied by a brief README or inline explanation

### Azure and Platform Reference Architectures

Contributions mapping AIL to specific cloud platforms or integration products are welcome in `docs/architecture/`. These should follow the structure of the existing Azure reference architecture document.

---

## How to Contribute

1. **Fork** this repository.
2. **Create a branch** from `main` with a descriptive name (e.g., `docs/add-event-sourcing-pattern` or `samples/logic-app-example`).
3. **Make your changes**, following the style and structure of existing content.
4. **Submit a pull request** with:
   - A clear title describing the contribution
   - A summary of what was added or changed
   - The motivation or context for the change

---

## Style Guidelines

- Write for **enterprise architects and technical leaders**. Assume technical fluency but avoid jargon without definition.
- Use **clear, direct language**. Prefer short sentences and concrete examples over abstract descriptions.
- Follow **Markdown formatting conventions** consistent with existing documents (ATX headings, fenced code blocks, tables).
- Diagrams should use **ASCII art or Mermaid syntax** for portability. Do not submit binary image files.
- Avoid **marketing language**. Describe capabilities and trade-offs accurately. Do not overstate claims.

---

## Code of Conduct

Contributors are expected to engage professionally and constructively. Disrespectful or dismissive communication will not be accepted. This is a technical reference repository, and all discussion should be focused on the quality and accuracy of architectural content.

---

## Attribution

Significant architectural contributions will be acknowledged in the relevant document's attribution section. The core AIL framework and maturity model were developed by Gregory W. Douglas, Cheops Consulting Services. Extensions and additions by the community will be credited individually where appropriate.

---

## Questions

If you have a question about whether a contribution is appropriate or how to structure content, open an issue before beginning work. This avoids effort on submissions that may not align with the repository's scope.

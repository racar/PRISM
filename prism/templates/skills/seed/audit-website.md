---
skill_id: audit-website
type: skill
domain_tags: [frontend, seo, audit, performance, security, accessibility, testing, web]
scope: global
stack_context: [html, css, javascript, web]
created: 2026-02-22
last_used: 2026-02-22
reuse_count: 0
project_origin: squirrelscan-skills
status: active
verified_by: human
---

# Website Audit

## Key Insight

Audit websites for SEO, technical, content, performance and security issues using the squirrelscan CLI. Provides comprehensive analysis against 230+ rules in 21 categories.

## Trigger

When you need to:
- Analyze a website's health and performance
- Debug technical SEO issues
- Fix accessibility, security, or performance problems
- Check for broken links
- Validate meta tags and structured data
- Generate site audit reports
- Compare site health before/after changes

## Prerequisites

Install squirrel CLI from https://squirrelscan.com/download

```bash
squirrel --version  # Verify installation
```

## Setup

```bash
# Initialize project config
squirrel init -n my-project

# Or with force to overwrite
squirrel init -n my-project --force
```

## Basic Workflow

### Step 1: Run Audit

```bash
# Surface scan (default, 100 pages)
squirrel audit https://example.com --format llm

# Quick scan (25 pages)
squirrel audit https://example.com -C quick --format llm

# Deep scan (500 pages)
squirrel audit https://example.com -C full --format llm
```

### Step 2: Export Report

```bash
squirrel report <audit-id> --format llm
```

**Always prefer `--format llm`** - provides exhaustive and compact output optimized for AI agents.

## Audit Categories (21 Total)

| Category | Description |
|----------|-------------|
| **SEO** | Meta tags, titles, descriptions, canonical URLs, Open Graph |
| **Technical** | Broken links, redirect chains, page speed, mobile-friendliness |
| **Performance** | Page load time, resource usage, caching |
| **Content** | Heading structure, image alt text, content analysis |
| **Security** | Leaked secrets, HTTPS, security headers, mixed content |
| **Accessibility** | Alt text, color contrast, keyboard navigation |
| **Usability** | Form validation, error handling, user flow |
| **Links** | Broken internal/external links |
| **E-E-A-T** | Expertise, Experience, Authority, Trustworthiness |
| **Mobile** | Mobile-friendliness, responsive design, touch elements |
| **Crawlability** | robots.txt, sitemap.xml, crawl efficiency |
| **Schema** | Schema.org markup, structured data, rich snippets |
| **Legal** | Privacy policies, terms of service compliance |
| **Social** | Open Graph, Twitter Cards validation |
| **URL Structure** | Length, hyphens, keywords |
| **Keywords** | Keyword stuffing detection |
| **Images** | Alt text, format, size optimization |
| **Local SEO** | NAP consistency, geo metadata |
| **Video** | VideoObject schema, accessibility |

## Coverage Modes

| Mode | Pages | Use Case |
|------|-------|----------|
| `quick` | 25 | CI checks, daily health check |
| `surface` | 100 | General audits (default) |
| `full` | 500 | Deep analysis, pre-launch |

## Common Commands

```bash
# Audit with custom page limit
squirrel audit https://example.com -m 200 --format llm

# Force fresh crawl (ignore cache)
squirrel audit https://example.com --refresh --format llm

# Resume interrupted crawl
squirrel audit https://example.com --resume --format llm

# Verbose output
squirrel audit https://example.com --verbose --format llm

# Regression diff
squirrel report --diff <audit-id> --format llm
squirrel report --regression-since example.com --format llm
```

## Score Targets

| Starting Score | Target Score | Work Level |
|----------------|--------------|------------|
| < 50 (F) | 75+ (C) | Major fixes |
| 50-70 (D) | 85+ (B) | Moderate fixes |
| 70-85 (C) | 90+ (A) | Polish |
| > 85 (B+) | 95+ | Fine-tuning |

**Complete**: Score 95+ with `--coverage full`

## Fix Approach by Category

| Category | Parallelizable | Approach |
|----------|----------------|----------|
| Meta tags/titles | No | Edit page components |
| Structured data | No | Add JSON-LD templates |
| Image alt text | Yes | Edit content files |
| Heading hierarchy | Yes | Edit content files |
| Short descriptions | Yes | Edit frontmatter |
| HTTP→HTTPS links | Yes | Find/replace |
| Broken links | No | Manual review |

## Iteration Loop

```
Audit → Present Results → Propose Fixes → User Approves 
  ↑                                        ↓
Re-audit ← Verify Changes ← Apply Fixes ← Spawn Subagents
```

**Stop when**:
- Score reaches 85+ target, OR
- Only human-judgment issues remain

## Examples

### Quick SEO Check
```bash
squirrel audit https://squirrelscan.com --format llm
```

### Deep Blog Audit
```bash
squirrel audit https://myblog.com --max-pages 500 --format llm
```

### Fresh Audit After Changes
```bash
squirrel audit https://example.com --refresh --format llm
```

### Two-Step Workflow
```bash
# Run audit
squirrel audit https://example.com
# Note audit ID (e.g., "a1b2c3d4")

# Export LLM format later
squirrel report a1b2c3d4 --format llm
```

## Troubleshooting

**Command not found**
```bash
# Install from squirrelscan.com/download
# Ensure ~/.local/bin is in PATH
squirrel --version
```

**Crawl timeout**
```bash
# Use verbose to see progress
squirrel audit https://example.com --verbose --format llm
```

**Invalid URL**
```bash
# Must include protocol
squirrel audit https://example.com  # ✓ Correct
squirrel audit example.com          # ✗ Wrong
```

## Important Notes

- **Prefer live sites** over local for true performance/rendering assessment
- **First scan**: Surface (quick overview)
- **Second scan**: Deep (thorough analysis)
- Apply fixes from live audit to local code
- Use subagents to parallelize bulk fixes
- Always verify builds pass after fixes
- Re-audit frequently to maintain health

## Source

Originally from [Squirrelscan Skills](https://skills.sh/squirrelscan/skills/audit-website)
Weekly Installs: 25.3K

---
skill_id: seo-audit
type: skill
domain_tags: [seo, marketing, audit, frontend, web, content, analytics]
scope: global
stack_context: [html, css, javascript, web, content]
created: 2026-02-22
last_used: 2026-02-22
reuse_count: 0
project_origin: coreyhaines31-marketing-skills
status: active
verified_by: human
---

# SEO Audit

## Key Insight

Comprehensive SEO audit methodology for analyzing websites and identifying optimization opportunities. Focus on technical SEO, on-page optimization, content strategy, and performance metrics.

## Trigger

When you need to:
- Analyze website SEO health and performance
- Identify technical SEO issues
- Optimize on-page elements for search engines
- Improve content discoverability
- Fix crawlability and indexability problems
- Enhance site structure and internal linking
- Boost organic search visibility

## SEO Audit Checklist

### 1. Technical SEO

#### Crawlability & Indexability
- [ ] Robots.txt configuration
- [ ] XML sitemap present and valid
- [ ] No indexation blocking issues
- [ ] Canonical URLs properly set
- [ ] Redirect chains minimized
- [ ] 404 errors handled correctly
- [ ] HTTPS properly implemented

#### Site Architecture
- [ ] Logical URL structure
- [ ] Breadcrumb navigation
- [ ] Internal linking strategy
- [ ] Flat architecture (3-click rule)
- [ ] Pagination handled correctly

#### Performance
- [ ] Core Web Vitals (LCP, FID, CLS)
- [ ] Page load speed < 3 seconds
- [ ] Mobile-friendly design
- [ ] Responsive images
- [ ] Lazy loading implemented

### 2. On-Page SEO

#### Meta Tags
- [ ] Unique title tags (50-60 chars)
- [ ] Compelling meta descriptions (150-160 chars)
- [ ] Open Graph tags for social sharing
- [ ] Twitter Card markup
- [ ] Canonical tags for duplicate content

#### Content Structure
- [ ] Single H1 per page
- [ ] Logical heading hierarchy (H1 → H2 → H3)
- [ ] Keyword in first 100 words
- [ ] Content length appropriate (300+ words minimum)
- [ ] Keyword density natural (1-2%)

#### Images & Media
- [ ] Descriptive alt text for all images
- [ ] Image file names SEO-friendly
- [ ] Compressed image file sizes
- [ ] WebP format where supported
- [ ] Structured data for videos

### 3. Content Strategy

#### Quality & Relevance
- [ ] Content matches search intent
- [ ] E-E-A-T signals present
- [ ] Regular content updates
- [ ] No duplicate content issues
- [ ] Thin content identified and improved

#### Keywords
- [ ] Primary keyword in title
- [ ] Primary keyword in URL
- [ ] LSI keywords naturally included
- [ ] Long-tail keyword opportunities
- [ ] Keyword cannibalization check

#### Internal Linking
- [ ] Contextual internal links
- [ ] Descriptive anchor text
- [ ] Important pages well-linked
- [ ] Orphan pages identified
- [ ] Link equity distributed

### 4. Off-Page SEO

#### Backlink Profile
- [ ] Quality over quantity
- [ ] Diverse link sources
- [ ] Natural anchor text distribution
- [ ] No toxic links
- [ ] Competitor backlink analysis

#### Brand Signals
- [ ] Brand name consistency
- [ ] NAP consistency (Name, Address, Phone)
- [ ] Social media presence
- [ ] Brand mentions monitoring

### 5. Local SEO (if applicable)

- [ ] Google Business Profile optimized
- [ ] Local citations consistent
- [ ] Local schema markup
- [ ] Location pages optimized
- [ ] Customer reviews encouraged

### 6. Structured Data

- [ ] Schema.org markup implemented
- [ ] JSON-LD format preferred
- [ ] Rich snippet opportunities
- [ ] BreadcrumbList schema
- [ ] Organization/Person schema

### 7. Analytics & Tracking

- [ ] Google Analytics 4 installed
- [ ] Google Search Console connected
- [ ] Conversion tracking setup
- [ ] Goal configuration
- [ ] Regular monitoring schedule

## Priority Matrix

| Issue | Impact | Effort | Priority |
|-------|--------|--------|----------|
| Broken internal links | High | Low | Critical |
| Missing title tags | High | Low | Critical |
| Slow page speed | High | Medium | High |
| No HTTPS | High | Low | Critical |
| Thin content | Medium | High | Medium |
| Missing alt text | Low | Low | Low |
| Schema markup | Medium | Low | Medium |

## Common SEO Issues & Fixes

### Issue: Duplicate Content
```html
<!-- Use canonical tag -->
<link rel="canonical" href="https://example.com/original-page" />
```

### Issue: Poor URL Structure
```
❌ /products?id=123&cat=456
✓ /products/category-name/product-name
```

### Issue: Missing Meta Description
```html
<meta name="description" content="Compelling 150-160 character description with primary keyword." />
```

### Issue: Slow Images
```html
<!-- Use modern formats and lazy loading -->
<img src="image.webp" loading="lazy" alt="Descriptive alt text" width="800" height="600" />
```

### Issue: Poor Mobile Experience
- Implement responsive design
- Touch-friendly navigation
- Readable font sizes (16px minimum)
- Adequate tap targets (44x44px minimum)

## Audit Tools

### Essential Tools
- Google Search Console (free)
- Google Analytics 4 (free)
- PageSpeed Insights (free)
- Screaming Frog (desktop crawler)
- SEMrush or Ahrefs (comprehensive)

### Browser Extensions
- SEO Minion
- MozBar
- Keywords Everywhere
- Lighthouse (built-in)

## Reporting Template

```markdown
## SEO Audit Report: [Domain]

### Executive Summary
- Overall Health Score: [X/100]
- Critical Issues: [N]
- High Priority: [N]
- Medium Priority: [N]
- Low Priority: [N]

### Technical SEO Score: [X/100]
[Findings and recommendations]

### On-Page SEO Score: [X/100]
[Findings and recommendations]

### Content Score: [X/100]
[Findings and recommendations]

### Performance Score: [X/100]
[Findings and recommendations]

### Action Plan
1. [Critical fix #1]
2. [Critical fix #2]
3. [High priority fix #1]
...

### Timeline
- Week 1: Critical fixes
- Week 2: High priority
- Week 3-4: Medium priority
- Ongoing: Monitoring & optimization
```

## Best Practices

1. **Regular Audits**: Conduct monthly technical audits
2. **Monitor GSC**: Check Google Search Console weekly
3. **Track Rankings**: Monitor keyword positions
4. **Content Calendar**: Plan regular content updates
5. **Competitor Analysis**: Review competitor strategies quarterly
6. **Stay Updated**: Follow SEO news and algorithm updates

## Success Metrics

- Organic traffic growth
- Keyword ranking improvements
- Click-through rate (CTR)
- Bounce rate reduction
- Page speed improvements
- Core Web Vitals passing
- Indexed pages increase
- Conversion rate from organic

## Source

Originally from [coreyhaines31 Marketing Skills](https://skills.sh/coreyhaines31/marketingskills/seo-audit)
Weekly Installs: 24.2K

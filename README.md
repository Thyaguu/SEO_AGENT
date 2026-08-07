# SEO AGENT

AI-powered SEO Optimization Agent for HTML repositories.

## CLI Usage

Run the SEO adjustment workflow on any target HTML repository using the shell entry point:

```bash
./run_seo_adjustment_on_pages.sh \
  --Path_html=/Users/thyagarajan/Desktop/Hireko/Sample_project/Hireko_demo
```

### Options

- `--Path_html=<path>` (Required): Absolute path to the target HTML repository.

## Validation Requirements

The CLI validates that:
1. `--Path_html` argument is provided.
2. Target path exists on disk.
3. Target path is a valid directory.
4. Target directory contains HTML files.

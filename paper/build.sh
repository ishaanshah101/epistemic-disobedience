#!/usr/bin/env bash
# Build the PDF. Needs pandoc and a LaTeX engine.
set -euo pipefail
cd "$(dirname "$0")"
pandoc paper.md -o epistemic-disobedience.pdf --pdf-engine=xelatex --toc --toc-depth=2
echo "wrote paper/epistemic-disobedience.pdf"

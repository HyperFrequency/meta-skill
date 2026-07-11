# Detailed Peer Review Workflow

The full section-by-section evaluation, rigor checks, and report-structuring
detail for manuscript and grant review. Load this when conducting an actual
review; the SKILL.md keeps only the stage outline.

## Stage 1: Initial Assessment

High-level evaluation of scope, novelty, and overall quality.

**Key Questions:**
- What is the central research question or hypothesis?
- What are the main findings and conclusions?
- Is the work scientifically sound and significant?
- Is the work appropriate for the intended venue?
- Are there any immediate major flaws that would preclude publication?

**Output:** Brief summary (2-3 sentences) capturing the manuscript's essence and initial impression.

## Stage 2: Detailed Section-by-Section Review

Thorough evaluation of each manuscript section, documenting specific concerns and strengths.

### Abstract and Title
- **Accuracy:** Does the abstract accurately reflect the study's content and conclusions?
- **Clarity:** Is the title specific, accurate, and informative?
- **Completeness:** Are key findings and methods summarized appropriately?
- **Accessibility:** Is the abstract comprehensible to a broad scientific audience?

### Introduction
- **Context:** Is the background information adequate and current?
- **Rationale:** Is the research question clearly motivated and justified?
- **Novelty:** Is the work's originality and significance clearly articulated?
- **Literature:** Are relevant prior studies appropriately cited?
- **Objectives:** Are research aims/hypotheses clearly stated?

### Methods
- **Reproducibility:** Can another researcher replicate the study from the description provided?
- **Rigor:** Are the methods appropriate for addressing the research questions?
- **Detail:** Are protocols, reagents, equipment, and parameters sufficiently described?
- **Ethics:** Are ethical approvals, consent, and data handling properly documented?
- **Statistics:** Are statistical methods appropriate, clearly described, and justified?
- **Validation:** Are controls, replicates, and validation approaches adequate?

**Critical elements to verify:**
- Sample sizes and power calculations
- Randomization and blinding procedures
- Inclusion/exclusion criteria
- Data collection protocols
- Computational methods and software versions
- Statistical tests and correction for multiple comparisons

### Results
- **Presentation:** Are results presented logically and clearly?
- **Figures/Tables:** Are visualizations appropriate, clear, and properly labeled?
- **Statistics:** Are statistical results properly reported (effect sizes, confidence intervals, p-values)?
- **Objectivity:** Are results presented without over-interpretation?
- **Completeness:** Are all relevant results included, including negative results?
- **Reproducibility:** Are raw data or summary statistics provided?

**Common issues to identify:**
- Selective reporting of results
- Inappropriate statistical tests
- Missing error bars or measures of variability
- Over-fitting or circular analysis
- Batch effects or confounding variables
- Missing controls or validation experiments

### Discussion
- **Interpretation:** Are conclusions supported by the data?
- **Limitations:** Are study limitations acknowledged and discussed?
- **Context:** Are findings placed appropriately within existing literature?
- **Speculation:** Is speculation clearly distinguished from data-supported conclusions?
- **Significance:** Are implications and importance clearly articulated?
- **Future directions:** Are next steps or unanswered questions discussed?

**Red flags:**
- Overstated conclusions
- Ignoring contradictory evidence
- Causal claims from correlational data
- Inadequate discussion of limitations
- Mechanistic claims without mechanistic evidence

### References
- **Completeness:** Are key relevant papers cited?
- **Currency:** Are recent important studies included?
- **Balance:** Are contrary viewpoints appropriately cited?
- **Accuracy:** Are citations accurate and appropriate?
- **Self-citation:** Is there excessive or inappropriate self-citation?

## Stage 3: Methodological and Statistical Rigor

Evaluate technical quality with attention to common pitfalls.

**Statistical Assessment:**
- Are statistical assumptions met (normality, independence, homoscedasticity)?
- Are effect sizes reported alongside p-values?
- Is multiple testing correction applied appropriately?
- Are confidence intervals provided?
- Is sample size justified with power analysis?
- Are parametric vs. non-parametric tests chosen appropriately?
- Are missing data handled properly?
- Are exploratory vs. confirmatory analyses distinguished?

**Experimental Design:**
- Are controls appropriate and adequate?
- Is replication sufficient (biological and technical)?
- Are potential confounders identified and controlled?
- Is randomization properly implemented?
- Are blinding procedures adequate?
- Is the experimental design optimal for the research question?

**Computational/Bioinformatics:**
- Are computational methods clearly described and justified?
- Are software versions and parameters documented?
- Is code made available for reproducibility?
- Are algorithms and models validated appropriately?
- Are assumptions of computational methods met?
- Is batch correction applied appropriately?

## Stage 4: Reproducibility and Transparency

**Data Availability:**
- Are raw data deposited in appropriate repositories?
- Are accession numbers provided for public databases?
- Are data sharing restrictions justified (e.g., patient privacy)?
- Are data formats standard and accessible?

**Code and Materials:**
- Is analysis code made available (GitHub, Zenodo, etc.)?
- Are unique materials available or described sufficiently for recreation?
- Are protocols detailed in sufficient depth?

**Reporting Standards:**
- Does the manuscript follow discipline-specific reporting guidelines (CONSORT, PRISMA, ARRIVE, MIAME, MINSEQE, etc.)?
- See `references/reporting_standards.md` for common guidelines
- Are all elements of the appropriate checklist addressed?

## Stage 5: Figure and Data Presentation

**Quality Checks:**
- Are figures high resolution and clearly labeled?
- Are axes properly labeled with units?
- Are error bars defined (SD, SEM, CI)?
- Are statistical significance indicators explained?
- Are color schemes appropriate and accessible (colorblind-friendly)?
- Are scale bars included for images?
- Is data visualization appropriate for the data type?

**Integrity Checks:**
- Are there signs of image manipulation (duplications, splicing)?
- Are Western blots and gels appropriately presented?
- Are representative images truly representative?
- Are all conditions shown (no selective presentation)?

**Clarity:**
- Can figures stand alone with their legends?
- Is the message of each figure immediately clear?
- Are there redundant figures or panels?
- Would data be better presented as tables or figures?

## Stage 6: Ethical Considerations

**Human Subjects:**
- Is IRB/ethics approval documented?
- Is informed consent described?
- Are vulnerable populations appropriately protected?
- Is patient privacy adequately protected?
- Are potential conflicts of interest disclosed?

**Animal Research:**
- Is IACUC or equivalent approval documented?
- Are procedures humane and justified?
- Are the 3Rs (replacement, reduction, refinement) considered?
- Are euthanasia methods appropriate?

**Research Integrity:**
- Are there concerns about data fabrication or falsification?
- Is authorship appropriate and justified?
- Are competing interests disclosed?
- Is funding source disclosed?
- Are there concerns about plagiarism or duplicate publication?

## Stage 7: Writing Quality and Clarity

**Structure and Organization:**
- Is the manuscript logically organized?
- Do sections flow coherently?
- Are transitions between ideas clear?
- Is the narrative compelling and clear?

**Writing Quality:**
- Is the language clear, precise, and concise?
- Are jargon and acronyms minimized and defined?
- Is grammar and spelling correct?
- Are sentences unnecessarily complex?
- Is the passive voice overused?

**Accessibility:**
- Can a non-specialist understand the main findings?
- Are technical terms explained?
- Is the significance clear to a broad audience?

## Structuring Peer Review Reports

Organize feedback hierarchically, prioritizing issues and providing actionable guidance.

### Summary Statement
Provide a concise overall assessment (1-2 paragraphs):
- Brief synopsis of the research
- Overall recommendation (accept, minor revisions, major revisions, reject)
- Key strengths (2-3 bullet points)
- Key weaknesses (2-3 bullet points)
- Bottom-line assessment of significance and soundness

### Major Comments
Critical issues that significantly impact validity, interpretability, or significance. Number sequentially.

**Typically include:** fundamental methodological flaws, inappropriate statistical analyses, unsupported or overstated conclusions, missing critical controls or experiments, serious reproducibility concerns, major gaps in literature coverage, ethical concerns.

**For each major comment:**
1. Clearly state the issue
2. Explain why it's problematic
3. Suggest specific solutions or additional experiments
4. Indicate if addressing it is essential for publication

### Minor Comments
Less critical issues improving clarity, completeness, or presentation. Number sequentially.

**Typically include:** unclear figure labels or legends, missing methodological details, typographical or grammatical errors, suggestions for improved data presentation, minor statistical reporting issues, supplementary analyses, requests for clarification.

**For each minor comment:**
1. Identify the specific location (section, paragraph, figure)
2. State the issue clearly
3. Suggest how to address it

### Specific Line-by-Line Comments (Optional)
For manuscripts requiring detailed feedback:
- Reference specific page/line numbers or sections
- Note factual errors, unclear statements, or missing citations
- Suggest specific edits for clarity

### Questions for Authors
- Methodological details that are unclear
- Seemingly contradictory results
- Missing information needed to evaluate the work
- Requests for additional data or analyses

## Tone and Approach

Maintain a constructive, professional, and collegial tone.

**Best Practices:** be constructive (frame criticism as opportunities), specific (concrete examples, actionable suggestions), balanced (acknowledge strengths), respectful, objective (focus on the science), thorough but proportionate, and clear.

**Avoid:** personal attacks or dismissive language, sarcasm or condescension, vague criticism without examples, requesting unnecessary out-of-scope experiments, demanding personal preferences over best practices, revealing your identity if reviewing is double-blind.

### Severity and Tone Calibration

Calibrate language so it distinguishes a reporting gap from actual misconduct.
The failure mode to avoid is escalating minor presentation issues into
accusations that read as hostile or overstate the problem.

**Severity language guide** — swap loaded phrasing for calibrated phrasing:

| Situation | Use this | NOT this |
|-----------|----------|----------|
| Missing details | "needs clearer reporting" | "misleading" |
| Incomplete info | "would benefit from" | "fails to" |
| Scope limitation | "limited to [context]" | "flawed because" |
| Acknowledged limitation | "as the authors note..." | (no extra penalty) |
| Different interpretation | "an alternative explanation is" | "contradictory" |

**Too harsh (avoid):**
> "The authors misleadingly present their results without adequate baselines, fundamentally undermining the validity of all claims."

**Appropriately calibrated:**
> "The baseline comparisons could be strengthened. Adding [specific baseline] would help contextualize the reported improvements (Section 4.2, p. 8)."

**Severity tiers** — assign each comment a tier and let the recommendation follow:

- **Critical** (use sparingly, rare): fundamental flaws that invalidate the conclusions — fabricated data, statistical tests chosen to hide a null result, undisclosed conflicts of interest.
- **Major**: affects interpretation but is potentially addressable — missing controls, statistical concerns, overclaiming.
- **Moderate**: common, expected limitations — restricted scope, an acknowledged missing baseline, a reproducibility gap.
- **Minor**: polish — typos, figure labels, citation format, notation slips.

### Recommendation Calibration

These principles calibrate the overall accept / minor / major / reject
recommendation and guard against over-penalization. (For a numeric 1-10 score
with per-dimension sub-scores, use the `scholar-evaluation` skill — this skill
owns the qualitative review and recommendation, not a scoring scale.)

- **Acknowledged-limitation credit**: if the authors explicitly name a limitation, do not weight it as heavily as a hidden one — it is a Moderate issue, not a Major one.
- **Reproducibility credit**: detailed methods + shared code/data + fixed seeds + confidence intervals is strong evidence of soundness; weight it accordingly before recommending rejection.
- **Scope vs. quality**: a narrow-but-sound study is acceptable work, not a borderline one — judge it on soundness within its stated scope, not on the breadth it never claimed.
- **Synthetic/benchmark data**: for most ML and simulation papers, synthetic or standard-benchmark data is normal practice and is not by itself a major weakness.

A study that is methodologically sound within its scope, reports statistics
rigorously (effect sizes, CIs, appropriate tests), acknowledges its limitations,
and provides reproducibility details should not be recommended for rejection on
scope grounds alone.

### Paper Mechanics

After the section-by-section and figure passes, run the presentation-mechanics
audit in `references/paper_mechanics.md` (table/figure/notation/structure
pass-fail checks) to catch details human reviewers routinely flag.

## Special Considerations by Manuscript Type

### Original Research Articles
Emphasize rigor, reproducibility, and novelty; assess significance and impact; verify conclusions are data-driven; check for complete methods and appropriate controls.

### Reviews and Meta-Analyses
Evaluate comprehensiveness of literature coverage; assess search strategy and inclusion/exclusion criteria; verify systematic approach and lack of bias; check for critical analysis vs. mere summarization; for meta-analyses, evaluate statistical approach and heterogeneity.

### Methods Papers
Emphasize validation and comparison to existing methods; assess reproducibility and availability of protocols/code; evaluate improvements over existing approaches; check for sufficient implementation detail.

### Short Reports/Letters
Adapt expectations for brevity; ensure core findings are still rigorous and significant; verify format is appropriate for findings.

### Preprints
Recognize these have not undergone formal peer review; may be less polished; still apply rigorous standards for scientific validity; consider constructive feedback to help authors improve before journal submission.

### Presentations and Slide Decks
Use the image-based workflow in `references/presentation_review.md` — never read the presentation PDF as text. For *authoring* decks rather than reviewing them, use the `scientific-slides` skill.

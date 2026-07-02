# Delivery Guide: Systems Specifics, Speaker Notes, Color, Troubleshooting

Detailed guidance for content depth, delivery, and polish. The SKILL.md router points here.

---

## Systems Talk Specifics

Systems conference talks (OSDI/SOSP/NSDI/ASPLOS) have unique requirements vs ML talks:

### Demo Slide
- Include a **live demo** or **pre-recorded screencast** of the system in action.
- Always have a **recorded backup** — live demos fail at the worst times.
- Show the system under realistic load, not toy examples.

### Architecture Walkthrough
- Animate the architecture diagram: highlight components as you explain them.
- Use Beamer `\only<N>` or `\onslide<N>` for progressive reveal.
- Walk through a **concrete request** end-to-end through the system.

### Evaluation Highlights
- Select 2–3 strongest figures from the paper.
- Annotate figures on slides (arrows, circles highlighting key points).
- State the takeaway **before** showing the figure ("Our system is 2x faster — here's the data").

---

## Speaker Notes Guidelines

### Structure per Slide
```text
[Timing: X minutes]
[Key point to convey]
[Transition sentence to next slide]
```

### Mike Dahlin's Layered Approach
Apply "Say what you're going to say, say it, then say what you said" at three levels:

1. **Talk level**: Outline slide → body → summary slide
2. **Section level**: Section heading → content slides → section takeaway
3. **Slide level**: Headline statement → supporting evidence → transition

### Timing Guidelines
- Poster-talk: 30–60 sec per slide
- Spotlight: 30–45 sec per slide
- Oral: 45–90 sec per slide
- Invited: 60–120 sec per slide

---

## Color Scheme Suggestions

> Aesthetic suggestions, not official venue requirements. Adjust freely.

| Venue Type | Primary | Accent | Background |
|-----------|---------|--------|------------|
| USENIX (OSDI/NSDI) | Dark Blue (#003366) | Red (#CC0000) | White |
| ACM (SOSP/ASPLOS) | ACM Blue (#0071BC) | Dark Gray (#333333) | White |
| NeurIPS | Purple (#7B2D8E) | Gold (#F0AD00) | White |
| ICML | Teal (#008080) | Orange (#FF6600) | White |
| Generic | Dark Gray (#333333) | Blue (#0066CC) | White |

---

## Quick Checklist

- [ ] Slide count appropriate for talk type/duration
- [ ] Title slide has correct authors, affiliations, venue
- [ ] Architecture diagram included and clearly labeled
- [ ] Key eval figures annotated with takeaways
- [ ] Speaker notes include timing markers
- [ ] Transitions between sections are smooth
- [ ] Demo slide has recorded backup
- [ ] Thank-you slide includes paper link / QR code
- [ ] Font sizes ≥ 24pt for readability from back of room
- [ ] Consistent color scheme throughout

---

## Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Too many slides for time limit | Cut details, keep one figure per point |
| Slides feel like paper paragraphs | Use bullet points (≤ 6 per slide), let figures tell the story |
| Audience lost during design section | Add architecture walkthrough with progressive reveal |
| Evaluation slides overwhelming | Show 2–3 strongest figures, put rest in backup slides |
| Speaker notes too long | Target 3–4 sentences per slide, focus on transitions |
| Beamer compilation fails | Check figure paths, use `\graphicspath{{figures/}}` |
| PPTX looks different from Beamer | Adjust python-pptx font sizes and margins manually |

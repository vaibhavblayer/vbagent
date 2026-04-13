# Chapter Templates

This directory contains template files for each chapter in the syllabus. Templates define the **standard concepts, formulas, and techniques** that should be covered for each topic.

## Purpose

Templates serve as a **reference baseline** for the AI agent during exam analysis. They ensure:

1. **Comprehensive coverage** - All important concepts are included, even if not tested
2. **Consistency** - Same structure across all analyses
3. **Quality control** - Agent knows what "should" be covered vs what was actually tested

## Structure

```
templates/
├── jee_main/
│   └── physics/
│       ├── kinematics.json
│       ├── work_energy_and_power.json
│       └── ...
└── neet/
    └── physics/
        ├── kinematics.json
        └── ...
```

## Template Format

Each template is a JSON file with this structure:

```json
{
  "chapter": "WORK, ENERGY, AND POWER",
  "description": "Work, energy, power, and collisions",
  "topics": [
    {
      "topic_name": "Motion in a vertical circle",
      "concepts": [
        "Minimum velocity required to complete vertical circle",
        "Tension becomes zero at critical speed",
        "Energy conservation applies throughout motion"
      ],
      "formulas": [
        {
          "latex": "v_{top} = \\sqrt{gr}",
          "description": "Minimum speed at top of loop"
        },
        {
          "latex": "v_{bottom} = \\sqrt{5gr}",
          "description": "Minimum speed at bottom for completion"
        }
      ],
      "techniques": [
        "Apply energy conservation from bottom to top",
        "Set tension to zero for critical condition",
        "Use centripetal force equation at each point"
      ]
    }
  ]
}
```

## How Templates Are Used

During analysis, the AI agent receives:

1. **Template data** - Standard concepts for the chapter
2. **Full problem text** - Actual exam questions and solutions
3. **Extracted ideas** - Previously identified concepts

The agent then:
- Includes ALL standard concepts from template
- Adds NEW concepts found in problems
- Marks which concepts were tested (with problem numbers)
- Marks which are standard but not tested (empty problem numbers)

## Filling Templates

Templates are initially created empty. To fill them:

1. **Manual curation** - Add concepts based on textbook knowledge
2. **From existing analyses** - Extract common patterns from multiple exams
3. **Iterative refinement** - Update as you analyze more problems

### Guidelines for Content

**Concepts:**
- 10-15 words maximum
- Clear, direct statements
- Focus on understanding, not memorization

**Formulas:**
- Clean LaTeX (no $ delimiters)
- Brief description (5-10 words)
- Include conditions when relevant

**Techniques:**
- Actionable problem-solving steps
- Under 15 words
- Specific to the topic

## Regenerating Templates

To regenerate empty template files:

```bash
python vbagent/data/templates/generate_templates.py
```

This will create/overwrite template files based on the current syllabus.

## Example: Motion in Vertical Circle

Here's a well-filled template section:

```json
{
  "topic_name": "Motion in a vertical circle",
  "concepts": [
    "Minimum velocity required to complete vertical circle",
    "Tension becomes zero at critical speed at top",
    "Energy conservation applies throughout circular motion",
    "Centripetal force varies with position in circle",
    "Normal force can be zero, positive, or negative"
  ],
  "formulas": [
    {
      "latex": "v_{top} = \\sqrt{gr}",
      "description": "Minimum speed at top"
    },
    {
      "latex": "v_{bottom} = \\sqrt{5gr}",
      "description": "Speed at bottom for completion"
    },
    {
      "latex": "T + mg = \\frac{mv^2}{r}",
      "description": "Force equation at top"
    },
    {
      "latex": "T - mg = \\frac{mv^2}{r}",
      "description": "Force equation at bottom"
    }
  ],
  "techniques": [
    "Apply energy conservation from bottom to top",
    "Set tension to zero for minimum speed condition",
    "Use centripetal force equation at each point",
    "Check if given speed exceeds minimum required"
  ]
}
```

## Notes

- Templates are **optional** - analysis works without them
- Empty templates still provide structure
- Templates improve with iterative refinement
- Same physics syllabus for JEE Main and NEET

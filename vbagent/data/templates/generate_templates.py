#!/usr/bin/env python3
"""Generate empty template files for all chapters in syllabus."""

import json
from pathlib import Path


def generate_templates():
    """Generate template JSON files for all chapters."""
    
    # Load JEE Main syllabus
    syllabus_path = Path(__file__).parent.parent / 'syllabus' / 'jee_main' / 'physics.json'
    with open(syllabus_path, 'r', encoding='utf-8') as f:
        syllabus = json.load(f)
    
    # Create templates for JEE Main
    jee_template_dir = Path(__file__).parent / 'jee_main' / 'physics'
    jee_template_dir.mkdir(parents=True, exist_ok=True)
    
    # Create templates for NEET (same syllabus)
    neet_template_dir = Path(__file__).parent / 'neet' / 'physics'
    neet_template_dir.mkdir(parents=True, exist_ok=True)
    
    for chapter_name, chapter_data in syllabus.items():
        # Create template structure
        template = {
            "chapter": chapter_name,
            "description": chapter_data.get("description", ""),
            "note": "",
            "topics": []
        }
        
        # Add each syllabus topic with empty concepts/formulas/techniques
        for topic in chapter_data.get("topics", []):
            template["topics"].append({
                "topic_name": topic,
                "concepts": [],
                "formulas": [],
                "techniques": []
            })
        
        # Generate filename (sanitize chapter name)
        filename = chapter_name.lower().replace(' ', '_').replace(',', '').replace('/', '_') + '.json'
        
        # Write JEE Main template
        jee_file = jee_template_dir / filename
        with open(jee_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        print(f"Created: {jee_file}")
        
        # Write NEET template (same content)
        neet_file = neet_template_dir / filename
        with open(neet_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        print(f"Created: {neet_file}")
    
    print(f"\n✓ Generated {len(syllabus)} template files for JEE Main and NEET")


if __name__ == '__main__':
    generate_templates()

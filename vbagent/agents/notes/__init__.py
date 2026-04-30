"""Concept notes pipeline agents.

Agents for generating complete concept notes documents:
- Planner: topic → structured document plan
- Section writer: one section plan → LaTeX content
- Diagram generator: reuses existing tikz agent
- Stitcher: combines preamble + sections + diagrams → full .tex
- Compiler: runs pdflatex
"""

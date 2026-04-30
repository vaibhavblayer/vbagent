"""Solution video pipeline agents.

Agents for generating complete solution videos:
- Script writer: problem + solution → narration script
- Segment coder: one script segment → Manim code block
- Video stitcher: segment code blocks → complete Manim Scene
- Video coder: orchestrates segment_coder + stitcher
- Video fixer: fix broken Manim code
- Voice: script → audio narration (TTS)
- Composer: Manim video + audio → final video
"""

"""Topic-specific solution prompt routing for physics.

Maps physics topics to specialized solution agents with topic-specific
guidance, common patterns, and diagram recommendations.
"""

# Topic to module mapping (keywords → module name)
TOPIC_MODULES = {
    # Mechanics
    "mechanics": "mechanics",
    "kinematics": "mechanics",
    "dynamics": "mechanics",
    "forces": "mechanics",
    "friction": "mechanics",
    "newton": "mechanics",
    "motion": "mechanics",
    
    # Energy and Work
    "work": "energy_work",
    "energy": "energy_work",
    "power": "energy_work",
    "collision": "energy_work",
    "momentum": "energy_work",
    "impulse": "energy_work",
    "conservation": "energy_work",
    
    # Rotational
    "rotation": "rotational",
    "rotational": "rotational",
    "torque": "rotational",
    "angular": "rotational",
    "moment_of_inertia": "rotational",
    "rolling": "rotational",
    
    # SHM
    "shm": "shm",
    "oscillation": "shm",
    "pendulum": "shm",
    "spring": "shm",
    "harmonic": "shm",
    
    # Waves
    "wave": "waves",
    "waves": "waves",
    "standing_wave": "waves",
    "doppler": "waves",
    "sound": "waves",
    "superposition": "waves",
    
    # Ray Optics
    "ray_optics": "ray_optics",
    "optics": "ray_optics",
    "reflection": "ray_optics",
    "refraction": "ray_optics",
    "lens": "ray_optics",
    "mirror": "ray_optics",
    "prism": "ray_optics",
    
    # Wave Optics
    "wave_optics": "wave_optics",
    "interference": "wave_optics",
    "diffraction": "wave_optics",
    "polarization": "wave_optics",
    "ydse": "wave_optics",
    
    # Thermodynamics
    "thermodynamics": "thermodynamics",
    "thermo": "thermodynamics",
    "entropy": "thermodynamics",
    "carnot": "thermodynamics",
    "cycle": "thermodynamics",
    
    # Heat Transfer
    "heat": "heat_transfer",
    "calorimetry": "heat_transfer",
    "thermal": "heat_transfer",
    "conduction": "heat_transfer",
    "convection": "heat_transfer",
    "radiation": "heat_transfer",
    
    # Electrostatics
    "electrostatics": "electrostatics",
    "electric_field": "electrostatics",
    "potential": "electrostatics",
    "capacitor": "electrostatics",
    "gauss": "electrostatics",
    
    # Current Electricity
    "current": "current_electricity",
    "circuit": "current_electricity",
    "resistance": "current_electricity",
    "kirchhoff": "current_electricity",
    "ohm": "current_electricity",
    
    # Magnetism
    "magnetism": "magnetism",
    "magnetic": "magnetism",
    "ampere": "magnetism",
    "biot_savart": "magnetism",
    "lorentz": "magnetism",
    
    # Electromagnetism
    "electromagnetism": "electromagnetism",
    "emi": "electromagnetism",
    "induction": "electromagnetism",
    "faraday": "electromagnetism",
    "lenz": "electromagnetism",
    "ac": "electromagnetism",
    "transformer": "electromagnetism",
    
    # Modern Physics
    "modern": "modern_physics",
    "photoelectric": "modern_physics",
    "compton": "modern_physics",
    "de_broglie": "modern_physics",
    "uncertainty": "modern_physics",
    
    # Atomic and Nuclear
    "atomic": "atomic_nuclear",
    "nuclear": "atomic_nuclear",
    "radioactivity": "atomic_nuclear",
    "decay": "atomic_nuclear",
    "bohr": "atomic_nuclear",
    
    # Gravitation
    "gravitation": "gravitation",
    "gravity": "gravitation",
    "orbit": "gravitation",
    "satellite": "gravitation",
    "kepler": "gravitation",
}


def get_topic_prompt(chapter: str, topic: str, question_type: str) -> str:
    """Get topic-specific solution prompt.
    
    Args:
        chapter: Chapter from classification (e.g., "Mechanics", "Waves")
        topic: Topic from classification (e.g., "kinematics", "shm", "wave_optics")
        question_type: Question type (subjective, mcq_sc, mcq_mc, etc.)
    
    Returns:
        System prompt for that topic + question type combination, or None if not found
    """
    # Try topic first, then chapter
    search_term = topic or chapter
    if not search_term:
        return None
    
    # Normalize search term
    search_lower = search_term.lower().replace(" ", "_")
    
    # Find module name
    module_name = TOPIC_MODULES.get(search_lower)
    
    if not module_name:
        # Try searching in chapter if topic didn't match
        if topic and chapter:
            chapter_lower = chapter.lower().replace(" ", "_")
            module_name = TOPIC_MODULES.get(chapter_lower)
    
    if not module_name:
        # No matching topic agent found
        return None
    
    # Import the appropriate topic module and get prompt
    try:
        if module_name == "mechanics":
            from .mechanics import get_prompt
        elif module_name == "energy_work":
            from .energy_work import get_prompt
        elif module_name == "rotational":
            from .rotational import get_prompt
        elif module_name == "shm":
            from .shm import get_prompt
        elif module_name == "waves":
            from .waves import get_prompt
        elif module_name == "ray_optics":
            from .ray_optics import get_prompt
        elif module_name == "wave_optics":
            from .wave_optics import get_prompt
        elif module_name == "thermodynamics":
            from .thermodynamics import get_prompt
        elif module_name == "heat_transfer":
            from .heat_transfer import get_prompt
        elif module_name == "electrostatics":
            from .electrostatics import get_prompt
        elif module_name == "current_electricity":
            from .current_electricity import get_prompt
        elif module_name == "magnetism":
            from .magnetism import get_prompt
        elif module_name == "electromagnetism":
            from .electromagnetism import get_prompt
        elif module_name == "modern_physics":
            from .modern_physics import get_prompt
        elif module_name == "atomic_nuclear":
            from .atomic_nuclear import get_prompt
        elif module_name == "gravitation":
            from .gravitation import get_prompt
        else:
            return None
        
        return get_prompt(question_type)
    
    except (ImportError, AttributeError):
        # If topic module doesn't exist or get_prompt not found, return None
        return None


__all__ = [
    "TOPIC_MODULES",
    "get_topic_prompt",
]

"""Subject taxonomy - chapters and topics for classification.

This module defines the hierarchical structure of chapters and topics
for each subject. The classification agent must choose from these
predefined lists to ensure consistency.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ChapterTopics:
    """Chapter with its associated topics."""
    chapter: str
    topics: List[str]


# Physics Taxonomy
PHYSICS_TAXONOMY = [
    ChapterTopics(
        chapter="Kinematics",
        topics=[
            "motion in a straight line",
            "motion in a plane",
            "projectile motion",
            "circular motion",
            "relative motion",
            "position-time graphs",
            "velocity-time graphs",
            "acceleration"
        ]
    ),
    ChapterTopics(
        chapter="Laws of Motion",
        topics=[
            "Newton's laws",
            "friction",
            "circular motion dynamics",
            "pseudo forces",
            "equilibrium",
            "free body diagrams"
        ]
    ),
    ChapterTopics(
        chapter="Work, Energy and Power",
        topics=[
            "work done",
            "kinetic energy",
            "potential energy",
            "conservation of energy",
            "power",
            "collisions",
            "work-energy theorem"
        ]
    ),
    ChapterTopics(
        chapter="System of Particles and Rotational Motion",
        topics=[
            "center of mass",
            "moment of inertia",
            "torque",
            "angular momentum",
            "rolling motion",
            "rotational kinetic energy"
        ]
    ),
    ChapterTopics(
        chapter="Gravitation",
        topics=[
            "universal law of gravitation",
            "gravitational potential energy",
            "escape velocity",
            "orbital velocity",
            "Kepler's laws",
            "satellites"
        ]
    ),
    ChapterTopics(
        chapter="Mechanical Properties of Solids",
        topics=[
            "stress and strain",
            "elastic moduli",
            "Hooke's law",
            "Young's modulus",
            "bulk modulus",
            "shear modulus"
        ]
    ),
    ChapterTopics(
        chapter="Mechanical Properties of Fluids",
        topics=[
            "pressure",
            "Pascal's law",
            "Archimedes principle",
            "buoyancy",
            "viscosity",
            "Bernoulli's theorem",
            "surface tension"
        ]
    ),
    ChapterTopics(
        chapter="Thermal Properties of Matter",
        topics=[
            "temperature",
            "heat transfer",
            "thermal expansion",
            "specific heat",
            "latent heat",
            "calorimetry"
        ]
    ),
    ChapterTopics(
        chapter="Thermodynamics",
        topics=[
            "first law of thermodynamics",
            "second law of thermodynamics",
            "heat engines",
            "Carnot cycle",
            "entropy",
            "thermodynamic processes"
        ]
    ),
    ChapterTopics(
        chapter="Kinetic Theory",
        topics=[
            "kinetic theory of gases",
            "ideal gas equation",
            "molecular speeds",
            "degrees of freedom",
            "mean free path"
        ]
    ),
    ChapterTopics(
        chapter="Oscillations",
        topics=[
            "simple harmonic motion",
            "spring-mass system",
            "pendulum",
            "damped oscillations",
            "forced oscillations",
            "resonance"
        ]
    ),
    ChapterTopics(
        chapter="Waves",
        topics=[
            "wave motion",
            "transverse and longitudinal waves",
            "superposition",
            "standing waves",
            "beats",
            "Doppler effect",
            "sound waves"
        ]
    ),
    ChapterTopics(
        chapter="Electric Charges and Fields",
        topics=[
            "Coulomb's law",
            "electric field",
            "electric flux",
            "Gauss's law",
            "electric dipole"
        ]
    ),
    ChapterTopics(
        chapter="Electrostatic Potential and Capacitance",
        topics=[
            "electric potential",
            "potential difference",
            "equipotential surfaces",
            "capacitors",
            "capacitance",
            "dielectrics"
        ]
    ),
    ChapterTopics(
        chapter="Current Electricity",
        topics=[
            "electric current",
            "Ohm's law",
            "resistance",
            "resistivity",
            "Kirchhoff's laws",
            "Wheatstone bridge",
            "potentiometer"
        ]
    ),
    ChapterTopics(
        chapter="Moving Charges and Magnetism",
        topics=[
            "magnetic force",
            "Lorentz force",
            "cyclotron",
            "Biot-Savart law",
            "Ampere's law",
            "magnetic field due to current"
        ]
    ),
    ChapterTopics(
        chapter="Magnetism and Matter",
        topics=[
            "bar magnet",
            "magnetic dipole",
            "Earth's magnetism",
            "magnetic materials",
            "para, dia, and ferromagnetism"
        ]
    ),
    ChapterTopics(
        chapter="Electromagnetic Induction",
        topics=[
            "Faraday's law",
            "Lenz's law",
            "motional emf",
            "self-inductance",
            "mutual inductance",
            "eddy currents"
        ]
    ),
    ChapterTopics(
        chapter="Alternating Current",
        topics=[
            "AC voltage and current",
            "phasors",
            "impedance",
            "resonance in AC circuits",
            "power in AC circuits",
            "transformers"
        ]
    ),
    ChapterTopics(
        chapter="Electromagnetic Waves",
        topics=[
            "displacement current",
            "electromagnetic spectrum",
            "properties of EM waves"
        ]
    ),
    ChapterTopics(
        chapter="Ray Optics and Optical Instruments",
        topics=[
            "reflection",
            "refraction",
            "total internal reflection",
            "lenses",
            "mirrors",
            "prisms",
            "optical instruments"
        ]
    ),
    ChapterTopics(
        chapter="Wave Optics",
        topics=[
            "Huygens principle",
            "interference",
            "Young's double slit",
            "diffraction",
            "polarization"
        ]
    ),
    ChapterTopics(
        chapter="Dual Nature of Radiation and Matter",
        topics=[
            "photoelectric effect",
            "de Broglie wavelength",
            "Davisson-Germer experiment",
            "matter waves"
        ]
    ),
    ChapterTopics(
        chapter="Atoms",
        topics=[
            "atomic models",
            "Bohr model",
            "hydrogen spectrum",
            "energy levels"
        ]
    ),
    ChapterTopics(
        chapter="Nuclei",
        topics=[
            "nuclear structure",
            "radioactivity",
            "nuclear reactions",
            "binding energy",
            "mass defect"
        ]
    ),
    ChapterTopics(
        chapter="Semiconductor Electronics",
        topics=[
            "semiconductors",
            "p-n junction",
            "diodes",
            "transistors",
            "logic gates"
        ]
    ),
    ChapterTopics(
        chapter="Communication Systems",
        topics=[
            "modulation",
            "amplitude modulation",
            "frequency modulation",
            "bandwidth"
        ]
    ),
]


# Chemistry Taxonomy
CHEMISTRY_TAXONOMY = [
    ChapterTopics(
        chapter="Some Basic Concepts of Chemistry",
        topics=[
            "matter and its nature",
            "laws of chemical combination",
            "atomic and molecular masses",
            "mole concept",
            "stoichiometry",
            "concentration terms"
        ]
    ),
    ChapterTopics(
        chapter="Structure of Atom",
        topics=[
            "atomic models",
            "quantum numbers",
            "electronic configuration",
            "Aufbau principle",
            "Pauli exclusion principle",
            "Hund's rule"
        ]
    ),
    ChapterTopics(
        chapter="Classification of Elements and Periodicity",
        topics=[
            "periodic table",
            "periodic trends",
            "ionization energy",
            "electron affinity",
            "electronegativity",
            "atomic radius"
        ]
    ),
    ChapterTopics(
        chapter="Chemical Bonding and Molecular Structure",
        topics=[
            "ionic bonding",
            "covalent bonding",
            "Lewis structures",
            "VSEPR theory",
            "hybridization",
            "molecular orbital theory",
            "hydrogen bonding"
        ]
    ),
    ChapterTopics(
        chapter="States of Matter",
        topics=[
            "gaseous state",
            "liquid state",
            "solid state",
            "gas laws",
            "kinetic theory",
            "intermolecular forces"
        ]
    ),
    ChapterTopics(
        chapter="Thermodynamics",
        topics=[
            "first law of thermodynamics",
            "enthalpy",
            "Hess's law",
            "entropy",
            "Gibbs free energy",
            "spontaneity"
        ]
    ),
    ChapterTopics(
        chapter="Equilibrium",
        topics=[
            "chemical equilibrium",
            "equilibrium constant",
            "Le Chatelier's principle",
            "law of mass action"
        ]
    ),
    ChapterTopics(
        chapter="Redox Reactions",
        topics=[
            "oxidation and reduction",
            "oxidation number",
            "balancing redox reactions",
            "redox titrations"
        ]
    ),
    ChapterTopics(
        chapter="Hydrogen",
        topics=[
            "position in periodic table",
            "isotopes",
            "hydrides",
            "water",
            "hydrogen peroxide"
        ]
    ),
    ChapterTopics(
        chapter="s-Block Elements",
        topics=[
            "alkali metals",
            "alkaline earth metals",
            "properties and compounds"
        ]
    ),
    ChapterTopics(
        chapter="p-Block Elements",
        topics=[
            "group 13 elements",
            "group 14 elements",
            "group 15 elements",
            "group 16 elements",
            "group 17 elements",
            "group 18 elements"
        ]
    ),
    ChapterTopics(
        chapter="Organic Chemistry - Basic Principles",
        topics=[
            "nomenclature",
            "isomerism",
            "electronic effects",
            "reaction mechanisms",
            "functional groups"
        ]
    ),
    ChapterTopics(
        chapter="Hydrocarbons",
        topics=[
            "alkanes",
            "alkenes",
            "alkynes",
            "aromatic hydrocarbons",
            "petroleum"
        ]
    ),
    ChapterTopics(
        chapter="Environmental Chemistry",
        topics=[
            "air pollution",
            "water pollution",
            "soil pollution",
            "green chemistry"
        ]
    ),
    ChapterTopics(
        chapter="Solid State",
        topics=[
            "crystal lattice",
            "unit cells",
            "packing efficiency",
            "imperfections",
            "electrical properties",
            "magnetic properties"
        ]
    ),
    ChapterTopics(
        chapter="Solutions",
        topics=[
            "types of solutions",
            "concentration terms",
            "Raoult's law",
            "colligative properties",
            "osmosis"
        ]
    ),
    ChapterTopics(
        chapter="Electrochemistry",
        topics=[
            "electrochemical cells",
            "Nernst equation",
            "conductance",
            "electrolysis",
            "batteries",
            "corrosion"
        ]
    ),
    ChapterTopics(
        chapter="Chemical Kinetics",
        topics=[
            "rate of reaction",
            "order of reaction",
            "rate law",
            "Arrhenius equation",
            "collision theory"
        ]
    ),
    ChapterTopics(
        chapter="Surface Chemistry",
        topics=[
            "adsorption",
            "catalysis",
            "colloids",
            "emulsions"
        ]
    ),
    ChapterTopics(
        chapter="d and f Block Elements",
        topics=[
            "transition elements",
            "lanthanoids",
            "actinoids",
            "coordination compounds"
        ]
    ),
    ChapterTopics(
        chapter="Coordination Compounds",
        topics=[
            "nomenclature",
            "isomerism",
            "bonding theories",
            "crystal field theory"
        ]
    ),
    ChapterTopics(
        chapter="Haloalkanes and Haloarenes",
        topics=[
            "nomenclature",
            "preparation",
            "reactions",
            "polyhalogen compounds"
        ]
    ),
    ChapterTopics(
        chapter="Alcohols, Phenols and Ethers",
        topics=[
            "nomenclature",
            "preparation",
            "properties",
            "reactions"
        ]
    ),
    ChapterTopics(
        chapter="Aldehydes, Ketones and Carboxylic Acids",
        topics=[
            "nomenclature",
            "preparation",
            "reactions",
            "uses"
        ]
    ),
    ChapterTopics(
        chapter="Amines",
        topics=[
            "nomenclature",
            "preparation",
            "properties",
            "diazonium salts"
        ]
    ),
    ChapterTopics(
        chapter="Biomolecules",
        topics=[
            "carbohydrates",
            "proteins",
            "nucleic acids",
            "vitamins",
            "enzymes"
        ]
    ),
    ChapterTopics(
        chapter="Polymers",
        topics=[
            "classification",
            "polymerization",
            "synthetic polymers",
            "natural polymers"
        ]
    ),
    ChapterTopics(
        chapter="Chemistry in Everyday Life",
        topics=[
            "drugs and medicines",
            "chemicals in food",
            "cleansing agents"
        ]
    ),
]


# Mathematics Taxonomy
MATHEMATICS_TAXONOMY = [
    ChapterTopics(
        chapter="Sets and Functions",
        topics=[
            "sets",
            "relations",
            "functions",
            "domain and range",
            "composite functions",
            "inverse functions"
        ]
    ),
    ChapterTopics(
        chapter="Algebra",
        topics=[
            "complex numbers",
            "quadratic equations",
            "linear inequalities",
            "permutations and combinations",
            "binomial theorem",
            "sequences and series"
        ]
    ),
    ChapterTopics(
        chapter="Coordinate Geometry",
        topics=[
            "straight lines",
            "circles",
            "parabola",
            "ellipse",
            "hyperbola",
            "conic sections"
        ]
    ),
    ChapterTopics(
        chapter="Calculus",
        topics=[
            "limits",
            "continuity",
            "differentiation",
            "applications of derivatives",
            "integration",
            "applications of integrals",
            "differential equations"
        ]
    ),
    ChapterTopics(
        chapter="Vectors and 3D Geometry",
        topics=[
            "vectors",
            "scalar and vector products",
            "three dimensional geometry",
            "direction cosines",
            "planes",
            "lines in 3D"
        ]
    ),
    ChapterTopics(
        chapter="Linear Programming",
        topics=[
            "linear inequalities",
            "graphical method",
            "optimization"
        ]
    ),
    ChapterTopics(
        chapter="Probability",
        topics=[
            "conditional probability",
            "Bayes theorem",
            "random variables",
            "probability distributions",
            "binomial distribution"
        ]
    ),
    ChapterTopics(
        chapter="Trigonometry",
        topics=[
            "trigonometric functions",
            "trigonometric equations",
            "inverse trigonometric functions",
            "properties of triangles"
        ]
    ),
    ChapterTopics(
        chapter="Matrices and Determinants",
        topics=[
            "matrices",
            "operations on matrices",
            "determinants",
            "properties of determinants",
            "adjoint and inverse",
            "solving linear equations"
        ]
    ),
    ChapterTopics(
        chapter="Statistics",
        topics=[
            "measures of central tendency",
            "measures of dispersion",
            "correlation",
            "regression"
        ]
    ),
]


# Biology Taxonomy
BIOLOGY_TAXONOMY = [
    ChapterTopics(
        chapter="The Living World",
        topics=[
            "diversity in living world",
            "taxonomic categories",
            "nomenclature",
            "classification"
        ]
    ),
    ChapterTopics(
        chapter="Biological Classification",
        topics=[
            "five kingdom classification",
            "kingdom Monera",
            "kingdom Protista",
            "kingdom Fungi",
            "viruses"
        ]
    ),
    ChapterTopics(
        chapter="Plant Kingdom",
        topics=[
            "algae",
            "bryophytes",
            "pteridophytes",
            "gymnosperms",
            "angiosperms"
        ]
    ),
    ChapterTopics(
        chapter="Animal Kingdom",
        topics=[
            "basis of classification",
            "phyla",
            "classification of animals"
        ]
    ),
    ChapterTopics(
        chapter="Morphology of Flowering Plants",
        topics=[
            "root",
            "stem",
            "leaf",
            "inflorescence",
            "flower",
            "fruit",
            "seed"
        ]
    ),
    ChapterTopics(
        chapter="Anatomy of Flowering Plants",
        topics=[
            "tissues",
            "tissue systems",
            "anatomy of dicot and monocot",
            "secondary growth"
        ]
    ),
    ChapterTopics(
        chapter="Structural Organisation in Animals",
        topics=[
            "animal tissues",
            "epithelial tissue",
            "connective tissue",
            "muscular tissue",
            "neural tissue"
        ]
    ),
    ChapterTopics(
        chapter="Cell: The Unit of Life",
        topics=[
            "cell theory",
            "prokaryotic cell",
            "eukaryotic cell",
            "cell organelles",
            "cell membrane"
        ]
    ),
    ChapterTopics(
        chapter="Biomolecules",
        topics=[
            "carbohydrates",
            "proteins",
            "lipids",
            "nucleic acids",
            "enzymes"
        ]
    ),
    ChapterTopics(
        chapter="Cell Cycle and Cell Division",
        topics=[
            "cell cycle",
            "mitosis",
            "meiosis",
            "significance of cell division"
        ]
    ),
    ChapterTopics(
        chapter="Transport in Plants",
        topics=[
            "water transport",
            "mineral transport",
            "transpiration",
            "translocation"
        ]
    ),
    ChapterTopics(
        chapter="Mineral Nutrition",
        topics=[
            "essential minerals",
            "mechanism of absorption",
            "nitrogen metabolism"
        ]
    ),
    ChapterTopics(
        chapter="Photosynthesis in Higher Plants",
        topics=[
            "light reaction",
            "dark reaction",
            "C3 and C4 pathways",
            "photorespiration"
        ]
    ),
    ChapterTopics(
        chapter="Respiration in Plants",
        topics=[
            "glycolysis",
            "Krebs cycle",
            "electron transport chain",
            "fermentation"
        ]
    ),
    ChapterTopics(
        chapter="Plant Growth and Development",
        topics=[
            "growth",
            "differentiation",
            "plant hormones",
            "photoperiodism",
            "vernalization"
        ]
    ),
    ChapterTopics(
        chapter="Digestion and Absorption",
        topics=[
            "digestive system",
            "digestion of food",
            "absorption",
            "disorders"
        ]
    ),
    ChapterTopics(
        chapter="Breathing and Exchange of Gases",
        topics=[
            "respiratory system",
            "mechanism of breathing",
            "gas exchange",
            "transport of gases"
        ]
    ),
    ChapterTopics(
        chapter="Body Fluids and Circulation",
        topics=[
            "blood",
            "lymph",
            "circulatory system",
            "cardiac cycle",
            "disorders"
        ]
    ),
    ChapterTopics(
        chapter="Excretory Products and their Elimination",
        topics=[
            "excretory system",
            "urine formation",
            "regulation of kidney function",
            "disorders"
        ]
    ),
    ChapterTopics(
        chapter="Locomotion and Movement",
        topics=[
            "types of movement",
            "skeletal system",
            "muscular system",
            "muscle contraction"
        ]
    ),
    ChapterTopics(
        chapter="Neural Control and Coordination",
        topics=[
            "nervous system",
            "neuron",
            "nerve impulse",
            "synapse",
            "reflex action"
        ]
    ),
    ChapterTopics(
        chapter="Chemical Coordination and Integration",
        topics=[
            "endocrine system",
            "hormones",
            "mechanism of hormone action"
        ]
    ),
    ChapterTopics(
        chapter="Reproduction in Organisms",
        topics=[
            "asexual reproduction",
            "sexual reproduction",
            "life cycles"
        ]
    ),
    ChapterTopics(
        chapter="Sexual Reproduction in Flowering Plants",
        topics=[
            "flower structure",
            "pollination",
            "fertilization",
            "seed and fruit formation"
        ]
    ),
    ChapterTopics(
        chapter="Human Reproduction",
        topics=[
            "male reproductive system",
            "female reproductive system",
            "gametogenesis",
            "menstrual cycle",
            "fertilization",
            "pregnancy"
        ]
    ),
    ChapterTopics(
        chapter="Reproductive Health",
        topics=[
            "reproductive health problems",
            "population explosion",
            "birth control",
            "STDs",
            "infertility"
        ]
    ),
    ChapterTopics(
        chapter="Principles of Inheritance and Variation",
        topics=[
            "Mendel's laws",
            "chromosomal theory",
            "sex determination",
            "linkage and crossing over",
            "genetic disorders"
        ]
    ),
    ChapterTopics(
        chapter="Molecular Basis of Inheritance",
        topics=[
            "DNA structure",
            "DNA replication",
            "transcription",
            "translation",
            "genetic code",
            "gene expression"
        ]
    ),
    ChapterTopics(
        chapter="Evolution",
        topics=[
            "origin of life",
            "theories of evolution",
            "natural selection",
            "adaptation",
            "speciation"
        ]
    ),
    ChapterTopics(
        chapter="Human Health and Disease",
        topics=[
            "common diseases",
            "immunity",
            "vaccines",
            "cancer",
            "AIDS",
            "drug abuse"
        ]
    ),
    ChapterTopics(
        chapter="Strategies for Enhancement in Food Production",
        topics=[
            "animal husbandry",
            "plant breeding",
            "tissue culture",
            "single cell protein"
        ]
    ),
    ChapterTopics(
        chapter="Microbes in Human Welfare",
        topics=[
            "microbes in household products",
            "industrial products",
            "sewage treatment",
            "biogas"
        ]
    ),
    ChapterTopics(
        chapter="Biotechnology: Principles and Processes",
        topics=[
            "genetic engineering",
            "recombinant DNA technology",
            "PCR",
            "cloning vectors"
        ]
    ),
    ChapterTopics(
        chapter="Biotechnology and its Applications",
        topics=[
            "applications in agriculture",
            "applications in medicine",
            "transgenic animals",
            "ethical issues"
        ]
    ),
    ChapterTopics(
        chapter="Organisms and Populations",
        topics=[
            "population ecology",
            "population interactions",
            "population attributes"
        ]
    ),
    ChapterTopics(
        chapter="Ecosystem",
        topics=[
            "ecosystem structure",
            "productivity",
            "energy flow",
            "nutrient cycling",
            "ecological succession"
        ]
    ),
    ChapterTopics(
        chapter="Biodiversity and Conservation",
        topics=[
            "biodiversity",
            "biodiversity conservation",
            "threats to biodiversity",
            "conservation strategies"
        ]
    ),
    ChapterTopics(
        chapter="Environmental Issues",
        topics=[
            "air pollution",
            "water pollution",
            "solid waste",
            "greenhouse effect",
            "ozone depletion",
            "deforestation"
        ]
    ),
]


# Create lookup dictionaries
def _create_taxonomy_dict(taxonomy: List[ChapterTopics]) -> Dict[str, List[str]]:
    """Convert taxonomy list to dictionary."""
    return {ct.chapter: ct.topics for ct in taxonomy}


PHYSICS_CHAPTERS_TOPICS = _create_taxonomy_dict(PHYSICS_TAXONOMY)
CHEMISTRY_CHAPTERS_TOPICS = _create_taxonomy_dict(CHEMISTRY_TAXONOMY)
MATHEMATICS_CHAPTERS_TOPICS = _create_taxonomy_dict(MATHEMATICS_TAXONOMY)
BIOLOGY_CHAPTERS_TOPICS = _create_taxonomy_dict(BIOLOGY_TAXONOMY)


# Subject taxonomy registry
SUBJECT_TAXONOMY: Dict[str, Dict[str, List[str]]] = {
    "physics": PHYSICS_CHAPTERS_TOPICS,
    "chemistry": CHEMISTRY_CHAPTERS_TOPICS,
    "mathematics": MATHEMATICS_CHAPTERS_TOPICS,
    "biology": BIOLOGY_CHAPTERS_TOPICS,
}


def get_chapters(subject: str) -> List[str]:
    """Get list of chapters for a subject.
    
    Args:
        subject: Subject name
        
    Returns:
        List of chapter names
    """
    if subject not in SUBJECT_TAXONOMY:
        raise ValueError(f"Unknown subject: {subject}")
    return list(SUBJECT_TAXONOMY[subject].keys())


def get_topics(subject: str, chapter: str) -> List[str]:
    """Get list of topics for a chapter.
    
    Args:
        subject: Subject name
        chapter: Chapter name
        
    Returns:
        List of topic names
    """
    if subject not in SUBJECT_TAXONOMY:
        raise ValueError(f"Unknown subject: {subject}")
    if chapter not in SUBJECT_TAXONOMY[subject]:
        raise ValueError(f"Unknown chapter: {chapter} for subject: {subject}")
    return SUBJECT_TAXONOMY[subject][chapter]


def get_all_topics(subject: str) -> List[str]:
    """Get all topics for a subject (flattened).
    
    Args:
        subject: Subject name
        
    Returns:
        List of all topic names
    """
    if subject not in SUBJECT_TAXONOMY:
        raise ValueError(f"Unknown subject: {subject}")
    
    all_topics = []
    for topics in SUBJECT_TAXONOMY[subject].values():
        all_topics.extend(topics)
    return all_topics


def get_chapter_for_topic(subject: str, topic: str) -> str:
    """Find which chapter a topic belongs to.
    
    Args:
        subject: Subject name
        topic: Topic name (case-insensitive)
        
    Returns:
        Chapter name, or "unknown" if not found
    """
    if subject not in SUBJECT_TAXONOMY:
        return "unknown"
    
    topic_lower = topic.lower()
    
    for chapter, topics in SUBJECT_TAXONOMY[subject].items():
        for chapter_topic in topics:
            if chapter_topic.lower() == topic_lower or topic_lower in chapter_topic.lower():
                return chapter
    
    return "unknown"


__all__ = [
    "ChapterTopics",
    "PHYSICS_TAXONOMY",
    "CHEMISTRY_TAXONOMY",
    "MATHEMATICS_TAXONOMY",
    "BIOLOGY_TAXONOMY",
    "SUBJECT_TAXONOMY",
    "get_chapters",
    "get_topics",
    "get_all_topics",
    "get_chapter_for_topic",
]

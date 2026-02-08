"""Metadata storage and query system for question banks.

This module provides SQLite-based storage for question metadata including
chapter, topic, difficulty, question type, tags, and usage statistics.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class QuestionMetadata:
    """Metadata for a single question."""
    
    file_path: str
    chapter: Optional[str] = None
    topic: Optional[str] = None
    subtopic: Optional[str] = None
    difficulty: Optional[str] = None  # easy, medium, hard
    question_type: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    has_diagram: Optional[bool] = None
    diagram_type: Optional[str] = None
    num_options: Optional[int] = None
    estimated_marks: Optional[int] = None
    key_concepts: list[str] = field(default_factory=list)
    requires_calculus: Optional[bool] = None
    confidence: Optional[float] = None
    usage_count: int = 0
    last_used: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": self.file_path,
            "chapter": self.chapter,
            "topic": self.topic,
            "subtopic": self.subtopic,
            "difficulty": self.difficulty,
            "question_type": self.question_type,
            "tags": self.tags,
            "has_diagram": self.has_diagram,
            "diagram_type": self.diagram_type,
            "num_options": self.num_options,
            "estimated_marks": self.estimated_marks,
            "key_concepts": self.key_concepts,
            "requires_calculus": self.requires_calculus,
            "confidence": self.confidence,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> QuestionMetadata:
        """Create from dictionary."""
        return cls(
            file_path=data["file_path"],
            chapter=data.get("chapter"),
            topic=data.get("topic"),
            subtopic=data.get("subtopic"),
            difficulty=data.get("difficulty"),
            question_type=data.get("question_type"),
            tags=data.get("tags", []),
            has_diagram=data.get("has_diagram"),
            diagram_type=data.get("diagram_type"),
            num_options=data.get("num_options"),
            estimated_marks=data.get("estimated_marks"),
            key_concepts=data.get("key_concepts", []),
            requires_calculus=data.get("requires_calculus"),
            confidence=data.get("confidence"),
            usage_count=data.get("usage_count", 0),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )


class MetadataExtractor:
    """Extracts metadata from LaTeX files."""
    
    # Patterns for metadata extraction from comments
    METADATA_PATTERNS = {
        "chapter": re.compile(r"%\s*chapter:\s*(.+)", re.IGNORECASE),
        "topic": re.compile(r"%\s*topic:\s*(.+)", re.IGNORECASE),
        "subtopic": re.compile(r"%\s*subtopic:\s*(.+)", re.IGNORECASE),
        "difficulty": re.compile(r"%\s*difficulty:\s*(easy|medium|hard)", re.IGNORECASE),
        "question_type": re.compile(r"%\s*type:\s*(.+)", re.IGNORECASE),
        "tags": re.compile(r"%\s*tags:\s*(.+)", re.IGNORECASE),
        "has_diagram": re.compile(r"%\s*has_diagram:\s*(true|false|yes|no)", re.IGNORECASE),
        "diagram_type": re.compile(r"%\s*diagram_type:\s*(.+)", re.IGNORECASE),
        "num_options": re.compile(r"%\s*num_options:\s*(\d+)", re.IGNORECASE),
        "estimated_marks": re.compile(r"%\s*estimated_marks:\s*(\d+)", re.IGNORECASE),
        "key_concepts": re.compile(r"%\s*key_concepts:\s*(.+)", re.IGNORECASE),
        "requires_calculus": re.compile(r"%\s*requires_calculus:\s*(true|false|yes|no)", re.IGNORECASE),
        "confidence": re.compile(r"%\s*confidence:\s*(0?\.\d+|1\.0?)", re.IGNORECASE),
    }
    
    def extract(self, tex_path: Path) -> QuestionMetadata:
        """Extract metadata from a LaTeX file.
        
        Looks for metadata in comments at the top of the file:
        % chapter: Mechanics
        % topic: Kinematics
        % difficulty: medium
        % type: mcq_sc
        % tags: motion, acceleration, graphs
        
        Args:
            tex_path: Path to the LaTeX file
            
        Returns:
            QuestionMetadata object with extracted information
        """
        if not tex_path.exists():
            raise FileNotFoundError(f"File not found: {tex_path}")
        
        content = tex_path.read_text(encoding="utf-8")
        
        # Extract metadata from comments
        metadata = {
            "file_path": str(tex_path),
            "chapter": None,
            "topic": None,
            "subtopic": None,
            "difficulty": None,
            "question_type": None,
            "tags": [],
            "has_diagram": None,
            "diagram_type": None,
            "num_options": None,
            "estimated_marks": None,
            "key_concepts": [],
            "requires_calculus": None,
            "confidence": None,
        }
        
        # Parse first 50 lines for metadata comments
        lines = content.split("\n")[:50]
        for line in lines:
            for key, pattern in self.METADATA_PATTERNS.items():
                match = pattern.search(line)
                if match:
                    value = match.group(1).strip()
                    if key == "tags" or key == "key_concepts":
                        # Split comma-separated values
                        metadata[key] = [t.strip() for t in value.split(",") if t.strip()]
                    elif key == "difficulty":
                        # Normalize difficulty to lowercase
                        metadata[key] = value.lower()
                    elif key == "has_diagram" or key == "requires_calculus":
                        # Convert to boolean
                        metadata[key] = value.lower() in ("true", "yes")
                    elif key == "num_options" or key == "estimated_marks":
                        # Convert to integer
                        metadata[key] = int(value)
                    elif key == "confidence":
                        # Convert to float
                        metadata[key] = float(value)
                    else:
                        metadata[key] = value
        
        # Try to infer metadata from content if not found in comments
        if not metadata["question_type"]:
            metadata["question_type"] = self._infer_question_type(content)
        
        if not metadata["difficulty"]:
            metadata["difficulty"] = self._infer_difficulty(content)
        
        return QuestionMetadata(**metadata)
    
    def _infer_question_type(self, content: str) -> Optional[str]:
        """Infer question type from LaTeX content."""
        # Check for tasks environment (MCQ)
        if r"\begin{tasks}" in content or r"\task" in content:
            # Check if multiple correct answers
            if re.search(r"more than one|multiple|one or more", content, re.IGNORECASE):
                return "mcq_mc"
            return "mcq_sc"
        
        # Check for assertion-reason pattern
        if "assertion" in content.lower() and "reason" in content.lower():
            return "assertion_reason"
        
        # Check for match the following
        if "match" in content.lower() and ("column" in content.lower() or "list" in content.lower()):
            return "match"
        
        # Check for passage-based
        if "passage" in content.lower() or len(content) > 2000:
            return "passage"
        
        # Default to subjective
        return "subjective"
    
    def _infer_difficulty(self, content: str) -> str:
        """Infer difficulty from content characteristics.
        
        This is a simple heuristic based on content length and complexity.
        """
        # Count mathematical expressions
        math_count = content.count("$") // 2
        
        # Count equations
        equation_count = content.count(r"\begin{equation}") + content.count(r"\begin{align}")
        
        # Count TikZ diagrams
        tikz_count = content.count(r"\begin{tikzpicture}")
        
        # Simple heuristic
        complexity_score = math_count + equation_count * 2 + tikz_count * 3
        
        if complexity_score < 5:
            return "easy"
        elif complexity_score < 15:
            return "medium"
        else:
            return "hard"


class MetadataStore:
    """SQLite-based storage for question metadata."""
    
    def __init__(self, db_path: Path):
        """Initialize metadata store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                chapter TEXT,
                topic TEXT,
                subtopic TEXT,
                difficulty TEXT,
                question_type TEXT,
                tags TEXT,
                has_diagram INTEGER,
                diagram_type TEXT,
                num_options INTEGER,
                estimated_marks INTEGER,
                key_concepts TEXT,
                requires_calculus INTEGER,
                confidence REAL,
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_topic ON questions(topic)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subtopic ON questions(subtopic)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_difficulty ON questions(difficulty)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chapter ON questions(chapter)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_type ON questions(question_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_has_diagram ON questions(has_diagram)")
        
        self.conn.commit()
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def index_directory(self, directory: Path, recursive: bool = True) -> int:
        """Index all LaTeX files in a directory.
        
        Args:
            directory: Directory to scan for .tex files
            recursive: Whether to scan subdirectories recursively
            
        Returns:
            Number of files indexed
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")
        
        extractor = MetadataExtractor()
        indexed_count = 0
        
        # Find all .tex files
        pattern = "**/*.tex" if recursive else "*.tex"
        tex_files = list(directory.glob(pattern))
        
        for tex_file in tex_files:
            try:
                metadata = extractor.extract(tex_file)
                self.upsert(metadata)
                indexed_count += 1
            except Exception as e:
                # Log error but continue with other files
                print(f"Warning: Failed to index {tex_file}: {e}")
        
        return indexed_count
    
    def upsert(self, metadata: QuestionMetadata) -> None:
        """Insert or update question metadata.
        
        Args:
            metadata: Question metadata to store
        """
        if not self.conn:
            raise RuntimeError("Database connection not initialized")
        
        cursor = self.conn.cursor()
        
        # Convert lists to JSON strings
        tags_json = json.dumps(metadata.tags)
        key_concepts_json = json.dumps(metadata.key_concepts)
        
        cursor.execute("""
            INSERT INTO questions (
                file_path, chapter, topic, subtopic, difficulty, question_type,
                tags, has_diagram, diagram_type, num_options, estimated_marks,
                key_concepts, requires_calculus, confidence,
                usage_count, last_used, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                chapter = excluded.chapter,
                topic = excluded.topic,
                subtopic = excluded.subtopic,
                difficulty = excluded.difficulty,
                question_type = excluded.question_type,
                tags = excluded.tags,
                has_diagram = excluded.has_diagram,
                diagram_type = excluded.diagram_type,
                num_options = excluded.num_options,
                estimated_marks = excluded.estimated_marks,
                key_concepts = excluded.key_concepts,
                requires_calculus = excluded.requires_calculus,
                confidence = excluded.confidence,
                updated_at = excluded.updated_at
        """, (
            metadata.file_path,
            metadata.chapter,
            metadata.topic,
            metadata.subtopic,
            metadata.difficulty,
            metadata.question_type,
            tags_json,
            1 if metadata.has_diagram else 0 if metadata.has_diagram is not None else None,
            metadata.diagram_type,
            metadata.num_options,
            metadata.estimated_marks,
            key_concepts_json,
            1 if metadata.requires_calculus else 0 if metadata.requires_calculus is not None else None,
            metadata.confidence,
            metadata.usage_count,
            metadata.last_used.isoformat() if metadata.last_used else None,
            metadata.created_at.isoformat(),
            metadata.updated_at.isoformat(),
        ))
        
        self.conn.commit()
    
    def query(
        self,
        topic: Optional[str] = None,
        subtopic: Optional[str] = None,
        difficulty: Optional[str] = None,
        chapter: Optional[str] = None,
        question_type: Optional[str] = None,
        tags: Optional[list[str]] = None,
        has_diagram: Optional[bool] = None,
        requires_calculus: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> list[QuestionMetadata]:
        """Query questions by metadata filters.
        
        Args:
            topic: Filter by topic (exact match)
            subtopic: Filter by subtopic (exact match)
            difficulty: Filter by difficulty (easy, medium, hard)
            chapter: Filter by chapter (exact match)
            question_type: Filter by question type
            tags: Filter by tags (questions must have all specified tags)
            has_diagram: Filter by presence of diagram
            requires_calculus: Filter by calculus requirement
            limit: Maximum number of results to return
            
        Returns:
            List of matching QuestionMetadata objects
        """
        if not self.conn:
            raise RuntimeError("Database connection not initialized")
        
        # Build query
        conditions = []
        params = []
        
        if topic:
            conditions.append("topic = ?")
            params.append(topic)
        
        if subtopic:
            conditions.append("subtopic = ?")
            params.append(subtopic)
        
        if difficulty:
            conditions.append("difficulty = ?")
            params.append(difficulty.lower())
        
        if chapter:
            conditions.append("chapter = ?")
            params.append(chapter)
        
        if question_type:
            conditions.append("question_type = ?")
            params.append(question_type)
        
        if has_diagram is not None:
            conditions.append("has_diagram = ?")
            params.append(1 if has_diagram else 0)
        
        if requires_calculus is not None:
            conditions.append("requires_calculus = ?")
            params.append(1 if requires_calculus else 0)
        
        # Tags require special handling (JSON search)
        if tags:
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM questions WHERE {where_clause}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            metadata = self._row_to_metadata(row)
            results.append(metadata)
        
        return results
    
    def get_by_path(self, file_path: str) -> Optional[QuestionMetadata]:
        """Get metadata for a specific file.
        
        Args:
            file_path: Path to the question file
            
        Returns:
            QuestionMetadata if found, None otherwise
        """
        if not self.conn:
            raise RuntimeError("Database connection not initialized")
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM questions WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()
        
        if row:
            return self._row_to_metadata(row)
        return None
    
    def update_usage(self, file_path: str) -> None:
        """Update usage statistics for a question.
        
        Increments usage_count and updates last_used timestamp.
        
        Args:
            file_path: Path to the question file
        """
        if not self.conn:
            raise RuntimeError("Database connection not initialized")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE questions
            SET usage_count = usage_count + 1,
                last_used = ?
            WHERE file_path = ?
        """, (datetime.now().isoformat(), file_path))
        
        self.conn.commit()
    
    def get_statistics(self) -> dict:
        """Get aggregate statistics about the question bank.
        
        Returns:
            Dictionary with counts by chapter, difficulty, topic, and type
        """
        if not self.conn:
            raise RuntimeError("Database connection not initialized")
        
        cursor = self.conn.cursor()
        
        stats = {
            "total_questions": 0,
            "by_chapter": {},
            "by_difficulty": {},
            "by_topic": {},
            "by_type": {},
            "most_used": [],
            "least_used": [],
        }
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM questions")
        stats["total_questions"] = cursor.fetchone()[0]
        
        # Count by chapter
        cursor.execute("""
            SELECT chapter, COUNT(*) as count
            FROM questions
            WHERE chapter IS NOT NULL
            GROUP BY chapter
            ORDER BY count DESC
        """)
        stats["by_chapter"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Count by difficulty
        cursor.execute("""
            SELECT difficulty, COUNT(*) as count
            FROM questions
            WHERE difficulty IS NOT NULL
            GROUP BY difficulty
            ORDER BY count DESC
        """)
        stats["by_difficulty"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Count by topic
        cursor.execute("""
            SELECT topic, COUNT(*) as count
            FROM questions
            WHERE topic IS NOT NULL
            GROUP BY topic
            ORDER BY count DESC
        """)
        stats["by_topic"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Count by type
        cursor.execute("""
            SELECT question_type, COUNT(*) as count
            FROM questions
            WHERE question_type IS NOT NULL
            GROUP BY question_type
            ORDER BY count DESC
        """)
        stats["by_type"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Most used questions
        cursor.execute("""
            SELECT file_path, usage_count, last_used
            FROM questions
            WHERE usage_count > 0
            ORDER BY usage_count DESC
            LIMIT 10
        """)
        stats["most_used"] = [
            {"file_path": row[0], "usage_count": row[1], "last_used": row[2]}
            for row in cursor.fetchall()
        ]
        
        # Least used questions (never used)
        cursor.execute("""
            SELECT file_path
            FROM questions
            WHERE usage_count = 0
            ORDER BY created_at DESC
            LIMIT 10
        """)
        stats["least_used"] = [row[0] for row in cursor.fetchall()]
        
        return stats
    
    def _row_to_metadata(self, row: sqlite3.Row) -> QuestionMetadata:
            """Convert database row to QuestionMetadata object."""
            tags = json.loads(row["tags"]) if row["tags"] else []
            key_concepts = json.loads(row["key_concepts"]) if row["key_concepts"] else []

            return QuestionMetadata(
                file_path=row["file_path"],
                chapter=row["chapter"],
                topic=row["topic"],
                subtopic=row["subtopic"],
                difficulty=row["difficulty"],
                question_type=row["question_type"],
                tags=tags,
                has_diagram=bool(row["has_diagram"]) if row["has_diagram"] is not None else None,
                diagram_type=row["diagram_type"],
                num_options=row["num_options"],
                estimated_marks=row["estimated_marks"],
                key_concepts=key_concepts,
                requires_calculus=bool(row["requires_calculus"]) if row["requires_calculus"] is not None else None,
                confidence=row["confidence"],
                usage_count=row["usage_count"],
                last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None,
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
            )

"""SQLite database for question bank storage."""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class QuestionRecord:
    """Database record for a question."""
    id: Optional[int] = None
    file_path: Optional[str] = None
    
    # Type & Structure
    question_type: Optional[str] = None
    is_passage: bool = False
    parent_question_id: Optional[int] = None
    passage_order: Optional[int] = None
    num_subquestions: Optional[int] = None
    
    # Metadata
    subject: Optional[str] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None
    subtopic: Optional[str] = None
    difficulty: Optional[str] = None
    
    # Content
    passage_text: Optional[str] = None
    problem_latex: Optional[str] = None
    solution_latex: Optional[str] = None
    alternate_solution_latex: Optional[str] = None
    idea_latex: Optional[str] = None
    
    # TikZ & Lists (stored as JSON)
    tikz_diagrams: list[dict] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    key_concepts: list[str] = field(default_factory=list)
    
    # Flags
    has_solution: bool = False
    has_alternate: bool = False
    has_idea: bool = False
    has_tikz: bool = False
    tikz_count: int = 0
    has_diagram: bool = False
    diagram_type: Optional[str] = None
    num_options: Optional[int] = None
    requires_calculus: bool = False
    confidence: Optional[float] = None
    
    # NEW: Agent 2 (Diagram Analysis) fields
    diagram_category: Optional[str] = None
    diagram_complexity: Optional[str] = None
    diagram_elements: list[str] = field(default_factory=list)
    suggested_tikz_agent: Optional[str] = None
    tikz_libraries: list[str] = field(default_factory=list)
    
    # NEW: Agent 3 (Difficulty Assessment) fields
    difficulty_score: Optional[float] = None
    difficulty_reasoning: Optional[str] = None
    expected_solve_time_minutes: Optional[int] = None
    expected_error_rate: Optional[float] = None
    prerequisite_concepts: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    cognitive_level: Optional[str] = None
    solution_approach: list[str] = field(default_factory=list)
    required_formulas: list[str] = field(default_factory=list)
    exam_relevance: dict = field(default_factory=dict)
    learning_objectives: list[str] = field(default_factory=list)
    tags_auto: list[str] = field(default_factory=list)
    
    # Usage tracking
    usage_count: int = 0
    last_used: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata_source: Optional[str] = None


class QuestionDatabase:
    """SQLite database for question bank."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def connect(self):
        """Connect to database and create tables if needed."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _create_tables(self):
        """Create database tables."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT,
                
                question_type TEXT,
                is_passage BOOLEAN DEFAULT 0,
                parent_question_id INTEGER,
                passage_order INTEGER,
                num_subquestions INTEGER,
                
                subject TEXT,
                chapter TEXT,
                topic TEXT,
                subtopic TEXT,
                difficulty TEXT,
                
                passage_text TEXT,
                problem_latex TEXT,
                solution_latex TEXT,
                alternate_solution_latex TEXT,
                idea_latex TEXT,
                
                tikz_diagrams TEXT,
                tags TEXT,
                key_concepts TEXT,
                
                has_solution BOOLEAN DEFAULT 0,
                has_alternate BOOLEAN DEFAULT 0,
                has_idea BOOLEAN DEFAULT 0,
                has_tikz BOOLEAN DEFAULT 0,
                tikz_count INTEGER DEFAULT 0,
                has_diagram BOOLEAN DEFAULT 0,
                diagram_type TEXT,
                num_options INTEGER,
                requires_calculus BOOLEAN DEFAULT 0,
                confidence REAL,
                
                -- NEW: Agent 2 (Diagram Analysis) fields
                diagram_category TEXT,
                diagram_complexity TEXT,
                diagram_elements TEXT,
                suggested_tikz_agent TEXT,
                tikz_libraries TEXT,
                
                -- NEW: Agent 3 (Difficulty Assessment) fields
                difficulty_score REAL,
                difficulty_reasoning TEXT,
                expected_solve_time_minutes INTEGER,
                expected_error_rate REAL,
                prerequisite_concepts TEXT,
                common_mistakes TEXT,
                cognitive_level TEXT,
                solution_approach TEXT,
                required_formulas TEXT,
                exam_relevance TEXT,
                learning_objectives TEXT,
                tags_auto TEXT,
                
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata_source TEXT,
                
                FOREIGN KEY (parent_question_id) REFERENCES questions(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_question_type ON questions(question_type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_parent_id ON questions(parent_question_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_topic ON questions(topic)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_difficulty ON questions(difficulty)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_is_passage ON questions(is_passage)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_subject ON questions(subject)")
        
        self.conn.commit()
    
    def insert(self, record: QuestionRecord) -> int:
        """Insert a question record and return its ID."""
        cursor = self.conn.execute("""
            INSERT INTO questions (
                file_path, question_type, is_passage, parent_question_id, passage_order,
                num_subquestions, subject, chapter, topic, subtopic, difficulty,
                passage_text, problem_latex, solution_latex, alternate_solution_latex,
                idea_latex, tikz_diagrams, tags, key_concepts, has_solution, has_alternate,
                has_idea, has_tikz, tikz_count, has_diagram, diagram_type, num_options,
                requires_calculus, confidence, usage_count, metadata_source,
                diagram_category, diagram_complexity, diagram_elements, suggested_tikz_agent,
                tikz_libraries, difficulty_score, difficulty_reasoning, expected_solve_time_minutes,
                expected_error_rate, prerequisite_concepts, common_mistakes, cognitive_level,
                solution_approach, required_formulas, exam_relevance, learning_objectives, tags_auto
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.file_path, record.question_type, record.is_passage, record.parent_question_id,
            record.passage_order, record.num_subquestions, record.subject, record.chapter,
            record.topic, record.subtopic, record.difficulty, record.passage_text,
            record.problem_latex, record.solution_latex, record.alternate_solution_latex,
            record.idea_latex, json.dumps(record.tikz_diagrams), json.dumps(record.tags),
            json.dumps(record.key_concepts), record.has_solution, record.has_alternate,
            record.has_idea, record.has_tikz, record.tikz_count, record.has_diagram,
            record.diagram_type, record.num_options, record.requires_calculus, record.confidence,
            record.usage_count, record.metadata_source,
            # Agent 2 fields
            record.diagram_category, record.diagram_complexity, json.dumps(record.diagram_elements),
            record.suggested_tikz_agent, json.dumps(record.tikz_libraries),
            # Agent 3 fields
            record.difficulty_score, record.difficulty_reasoning, record.expected_solve_time_minutes,
            record.expected_error_rate, json.dumps(record.prerequisite_concepts),
            json.dumps(record.common_mistakes), record.cognitive_level,
            json.dumps(record.solution_approach), json.dumps(record.required_formulas),
            json.dumps(record.exam_relevance), json.dumps(record.learning_objectives),
            json.dumps(record.tags_auto)
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_by_id(self, question_id: int) -> Optional[QuestionRecord]:
        """Get question by ID."""
        row = self.conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        if not row:
            return None
        return self._row_to_record(row)
    
    def get_with_children(self, question_id: int) -> tuple[QuestionRecord, list[QuestionRecord]]:
        """Get question with its children (for passage type)."""
        parent = self.get_by_id(question_id)
        if not parent:
            return None, []
        
        children = []
        if parent.is_passage:
            rows = self.conn.execute(
                "SELECT * FROM questions WHERE parent_question_id = ? ORDER BY passage_order",
                (question_id,)
            ).fetchall()
            children = [self._row_to_record(row) for row in rows]
        
        return parent, children
    
    def query(self, subject: Optional[str] = None, chapter: Optional[str] = None,
              topic: Optional[str] = None, difficulty: Optional[str] = None,
              question_type: Optional[str] = None, tags: Optional[list[str]] = None,
              limit: Optional[int] = None, exclude_children: bool = True) -> list[QuestionRecord]:
        """Query questions with filters. By default excludes passage children."""
        conditions = []
        params = []
        
        if exclude_children:
            conditions.append("parent_question_id IS NULL")
        
        if subject:
            conditions.append("subject = ?")
            params.append(subject)
        if chapter:
            conditions.append("chapter = ?")
            params.append(chapter)
        if topic:
            conditions.append("topic = ?")
            params.append(topic)
        if difficulty:
            conditions.append("difficulty = ?")
            params.append(difficulty)
        if question_type:
            conditions.append("question_type = ?")
            params.append(question_type)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM questions WHERE {where_clause}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_record(row) for row in rows]
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        stats = {}
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM questions")
        stats['total_entries'] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM questions WHERE parent_question_id IS NULL AND is_passage = 0")
        stats['standalone_questions'] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM questions WHERE is_passage = 1")
        stats['passage_sets'] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM questions WHERE parent_question_id IS NOT NULL")
        stats['passage_subquestions'] = cursor.fetchone()[0]
        
        stats['effective_question_count'] = stats['standalone_questions'] + stats['passage_subquestions']
        
        # By subject
        cursor = self.conn.execute("""
            SELECT subject, COUNT(*) as count 
            FROM questions 
            WHERE parent_question_id IS NULL 
            GROUP BY subject
        """)
        stats['by_subject'] = {row['subject']: row['count'] for row in cursor.fetchall() if row['subject']}
        
        # By difficulty
        cursor = self.conn.execute("""
            SELECT difficulty, COUNT(*) as count 
            FROM questions 
            WHERE parent_question_id IS NULL 
            GROUP BY difficulty
        """)
        stats['by_difficulty'] = {row['difficulty']: row['count'] for row in cursor.fetchall() if row['difficulty']}
        
        # By type
        cursor = self.conn.execute("""
            SELECT question_type, COUNT(*) as count 
            FROM questions 
            WHERE parent_question_id IS NULL 
            GROUP BY question_type
        """)
        stats['by_type'] = {row['question_type']: row['count'] for row in cursor.fetchall() if row['question_type']}
        
        return stats
    
    def update(self, question_id: int, **fields):
        """Update question fields."""
        if not fields:
            return
        
        # Handle JSON fields
        if 'tikz_diagrams' in fields:
            fields['tikz_diagrams'] = json.dumps(fields['tikz_diagrams'])
        if 'tags' in fields:
            fields['tags'] = json.dumps(fields['tags'])
        if 'key_concepts' in fields:
            fields['key_concepts'] = json.dumps(fields['key_concepts'])
        
        fields['updated_at'] = datetime.now().isoformat()
        
        set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values()) + [question_id]
        
        self.conn.execute(f"UPDATE questions SET {set_clause} WHERE id = ?", values)
        self.conn.commit()
    
    def delete(self, question_id: int):
        """Delete question (cascade deletes children)."""
        self.conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        self.conn.commit()
    
    def mark_used(self, question_id: int):
        """Mark question as used (increments usage_count for passage and all children)."""
        record = self.get_by_id(question_id)
        if not record:
            return
        
        # Update parent
        self.conn.execute(
            "UPDATE questions SET usage_count = usage_count + 1, last_used = ? WHERE id = ?",
            (datetime.now().isoformat(), question_id)
        )
        
        # If passage, update all children
        if record.is_passage:
            self.conn.execute(
                "UPDATE questions SET usage_count = usage_count + 1, last_used = ? WHERE parent_question_id = ?",
                (datetime.now().isoformat(), question_id)
            )
        
        self.conn.commit()
    
    def _row_to_record(self, row: sqlite3.Row) -> QuestionRecord:
        """Convert database row to QuestionRecord."""
        return QuestionRecord(
            id=row['id'],
            file_path=row['file_path'],
            question_type=row['question_type'],
            is_passage=bool(row['is_passage']),
            parent_question_id=row['parent_question_id'],
            passage_order=row['passage_order'],
            num_subquestions=row['num_subquestions'],
            subject=row['subject'],
            chapter=row['chapter'],
            topic=row['topic'],
            subtopic=row['subtopic'],
            difficulty=row['difficulty'],
            passage_text=row['passage_text'],
            problem_latex=row['problem_latex'],
            solution_latex=row['solution_latex'],
            alternate_solution_latex=row['alternate_solution_latex'],
            idea_latex=row['idea_latex'],
            tikz_diagrams=json.loads(row['tikz_diagrams']) if row['tikz_diagrams'] else [],
            tags=json.loads(row['tags']) if row['tags'] else [],
            key_concepts=json.loads(row['key_concepts']) if row['key_concepts'] else [],
            has_solution=bool(row['has_solution']),
            has_alternate=bool(row['has_alternate']),
            has_idea=bool(row['has_idea']),
            has_tikz=bool(row['has_tikz']),
            tikz_count=row['tikz_count'],
            has_diagram=bool(row['has_diagram']),
            diagram_type=row['diagram_type'],
            num_options=row['num_options'],
            requires_calculus=bool(row['requires_calculus']),
            confidence=row['confidence'],
            # Agent 2 fields
            diagram_category=row['diagram_category'] if 'diagram_category' in row.keys() else None,
            diagram_complexity=row['diagram_complexity'] if 'diagram_complexity' in row.keys() else None,
            diagram_elements=json.loads(row['diagram_elements']) if 'diagram_elements' in row.keys() and row['diagram_elements'] else [],
            suggested_tikz_agent=row['suggested_tikz_agent'] if 'suggested_tikz_agent' in row.keys() else None,
            tikz_libraries=json.loads(row['tikz_libraries']) if 'tikz_libraries' in row.keys() and row['tikz_libraries'] else [],
            # Agent 3 fields
            difficulty_score=row['difficulty_score'] if 'difficulty_score' in row.keys() else None,
            difficulty_reasoning=row['difficulty_reasoning'] if 'difficulty_reasoning' in row.keys() else None,
            expected_solve_time_minutes=row['expected_solve_time_minutes'] if 'expected_solve_time_minutes' in row.keys() else None,
            expected_error_rate=row['expected_error_rate'] if 'expected_error_rate' in row.keys() else None,
            prerequisite_concepts=json.loads(row['prerequisite_concepts']) if 'prerequisite_concepts' in row.keys() and row['prerequisite_concepts'] else [],
            common_mistakes=json.loads(row['common_mistakes']) if 'common_mistakes' in row.keys() and row['common_mistakes'] else [],
            cognitive_level=row['cognitive_level'] if 'cognitive_level' in row.keys() else None,
            solution_approach=json.loads(row['solution_approach']) if 'solution_approach' in row.keys() and row['solution_approach'] else [],
            required_formulas=json.loads(row['required_formulas']) if 'required_formulas' in row.keys() and row['required_formulas'] else [],
            exam_relevance=json.loads(row['exam_relevance']) if 'exam_relevance' in row.keys() and row['exam_relevance'] else {},
            learning_objectives=json.loads(row['learning_objectives']) if 'learning_objectives' in row.keys() and row['learning_objectives'] else [],
            tags_auto=json.loads(row['tags_auto']) if 'tags_auto' in row.keys() and row['tags_auto'] else [],
            # Tracking
            usage_count=row['usage_count'],
            last_used=datetime.fromisoformat(row['last_used']) if row['last_used'] else None,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now(),
            metadata_source=row['metadata_source']
        )

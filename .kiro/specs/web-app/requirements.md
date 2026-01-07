# Web App for VBAgent Physics Question Processing

## Overview
Build a web-based UI on top of the existing VBAgent CLI system, enabling users to process physics question images through a browser interface with the same workflow as the CLI but with enhanced visual feedback and management capabilities.

## User Stories

### US-1: Image Upload
**As a** physics teacher/content creator  
**I want to** upload physics question images (single, multiple, or zip)  
**So that** I can process them through the VBAgent pipeline without using CLI

**Acceptance Criteria:**
- [ ] Support single image upload (PNG, JPG, JPEG)
- [ ] Support multiple image upload via drag-and-drop or file picker
- [ ] Support ZIP file upload containing multiple images
- [ ] Show upload progress and validation feedback
- [ ] Preview uploaded images before processing
- [ ] Maximum file size limit with clear error messaging

### US-2: Automatic Scanning
**As a** user  
**I want** uploaded images to be automatically scanned (classify + scan + tikz)  
**So that** I get the base LaTeX extraction without manual intervention

**Acceptance Criteria:**
- [ ] Trigger classification automatically on upload
- [ ] Trigger LaTeX scanning after classification
- [ ] Trigger TikZ generation if diagram detected
- [ ] Show real-time processing status for each stage
- [ ] Display extracted LaTeX with syntax highlighting
- [ ] Display generated TikZ code if applicable
- [ ] Allow re-scanning with different options

### US-3: Problem Detail Page
**As a** user  
**I want** each processed problem to have a dedicated page  
**So that** I can view and manage all generated content in one place

**Acceptance Criteria:**
- [ ] Display original image
- [ ] Display classification metadata (type, difficulty, has_diagram)
- [ ] Display extracted LaTeX with rendered preview
- [ ] Display TikZ code with rendered diagram preview
- [ ] Show ideas/concepts if generated
- [ ] Show alternate solutions if generated
- [ ] Show variants organized by type (numerical, context, conceptual, calculus)
- [ ] Allow editing of any generated content
- [ ] Track version history of edits

### US-4: On-Demand Generation
**As a** user  
**I want to** trigger idea extraction, alternate solutions, and variants on demand  
**So that** I can selectively generate additional content per problem

**Acceptance Criteria:**
- [ ] Button to generate ideas/concepts
- [ ] Button to generate alternate solutions (with count selector)
- [ ] Buttons to generate variants by type (numerical, context, conceptual, calculus)
- [ ] Show generation progress with spinner/status
- [ ] Append new content without replacing existing
- [ ] Allow regeneration with different parameters

### US-5: Collection Management
**As a** user  
**I want to** organize problems into collections/folders  
**So that** I can manage related problems together

**Acceptance Criteria:**
- [ ] Create, rename, delete collections
- [ ] Add problems to collections during or after upload
- [ ] Move problems between collections
- [ ] View all problems in a collection
- [ ] Bulk operations on collection (generate variants for all, export all)
- [ ] Collection-level statistics (total problems, processing status)

### US-6: Batch Processing
**As a** user  
**I want to** trigger batch operations on multiple problems  
**So that** I can efficiently process large sets of questions

**Acceptance Criteria:**
- [ ] Select multiple problems for batch operation
- [ ] Batch generate ideas for selected problems
- [ ] Batch generate alternates for selected problems
- [ ] Batch generate variants (by type) for selected problems
- [ ] Show batch progress with individual problem status
- [ ] Resume interrupted batch operations
- [ ] Cancel running batch operations

### US-7: Export & Download
**As a** user  
**I want to** export processed content in various formats  
**So that** I can use the generated content in other tools

**Acceptance Criteria:**
- [ ] Download individual LaTeX files
- [ ] Download all content for a problem as ZIP
- [ ] Download entire collection as ZIP
- [ ] Export to structured JSON format
- [ ] Copy LaTeX/TikZ to clipboard with one click

### US-8: Processing Queue & Status
**As a** user  
**I want to** see the status of all processing jobs  
**So that** I know what's running and what's completed

**Acceptance Criteria:**
- [ ] Dashboard showing pending, processing, completed, failed jobs
- [ ] Real-time status updates (WebSocket or polling)
- [ ] Retry failed jobs
- [ ] View error details for failed jobs
- [ ] Cancel pending jobs

## Technical Requirements

### TR-1: Backend (Django)
- Django REST Framework for API endpoints
- Celery + Redis for async task processing
- SQLite/PostgreSQL for data persistence
- Integration with existing VBAgent agents (import and call directly)
- WebSocket support for real-time updates (Django Channels)

### TR-2: Frontend (TBD: Vue or React)
- Modern SPA architecture
- Responsive design for desktop/tablet
- LaTeX rendering (KaTeX or MathJax)
- TikZ preview rendering (via server-side compilation or tikzjax)
- File upload with drag-and-drop
- Real-time status updates

### TR-3: API Design
- RESTful endpoints for CRUD operations
- WebSocket for real-time processing updates
- Pagination for large collections
- File upload endpoints with chunked upload support

### TR-4: Data Model
- Problem: stores image, classification, latex, tikz, ideas
- Variant: linked to Problem, stores type and latex
- Alternate: linked to Problem, stores latex
- Collection: groups Problems
- ProcessingJob: tracks async job status

## Open Questions (Need User Input)

1. **Frontend Framework**: Vue.js or React? (User mentioned both)
2. **Database**: SQLite for simplicity or PostgreSQL for production?
3. **Authentication**: Is user auth needed? Multi-user support?
4. **Real-time Updates**: WebSockets (Django Channels) or polling?
5. **Upload Flow**: Process immediately or queue for confirmation?
6. **Hosting**: Local development only or cloud deployment planned?
7. **MVP Scope**: Start with basic upload+scan or full CLI parity?

## Out of Scope (v1)
- User authentication and multi-tenancy
- Collaborative editing
- Mobile-optimized interface
- PDF export with rendered LaTeX
- Integration with LMS systems

# Experience Notes — John James

## SpotCheck Technical Details

### FlightSorter Engine
- Heuristic classification engine processing EXIF telemetry from drone photos
- Input data: gimbal pitch, yaw, GPS coordinates, barometric altitude, airspeed, timestamps, image dimensions, digital zoom ratio
- Flight categories: downlook (-35 deg), uplook (20 deg), center in/out (0 deg), cable run (-22 deg, alt>20m), top down (-90 deg), tower flight type 1 (-40 deg), tower flight type 2 (-50 deg), compound upper (-45 deg), compound lower (-30 to -15 deg), cable anchor (zoom detection via Image Width < 5280)
- Tolerance: All gimbal angles have +/- 3 degree tolerance
- Orbit detection: Full orbit >= 350 deg rotation, partial 70-350 deg, segmented by >10s time gaps + height/heading changes
- Tower disassembly: Separates orbits from ascents/descents within a single tower flight using heading and altitude patterns
- Center orientation: Determines inward vs outward facing via heading vector math against estimated tower center point

### Architecture
- Backend: Python 3.11+, FastAPI, SQLAlchemy, Pydantic, PostgreSQL (Cloud SQL)
- Frontend: TypeScript, React (Vite), Zustand, TanStack Query, Radix UI (Shadcn)
- Infrastructure: Docker, Terraform (GCP), Cloud Run, Cloud Storage, GitHub Actions
- AI: Vertex AI (Gemini Vision) for visual defect detection

### Data Pipeline
1. Frontend EXIF extraction (browser-based, works offline)
2. Chunked upload to Cloud Storage (resumable, 5000+ images)
3. Metadata normalization in analysis worker
4. Site assignment via GPS proximity matching (500 ft threshold)
5. Flight classification (FlightSorter)
6. Serial QA analysis (6 analyzers)
7. Flight summary generation
8. Database persistence + status update

## SpiderZZ — Browser Automation Suite
- Playwright-based multi-platform automation
- Coordinates TalonView, Matterport, and Salesforce
- Manages authentication, session state, cross-platform data flow
- Runs as daemon with AI-assisted monitoring
- Replaces manual cross-platform data entry for site turn-in processing

## Field Operations
- 500+ aerial site inspections
- 10 sites/day, 1-hour windows per site
- FAA Part 107 daylight limits
- T-Mobile, AT&T, and other major telecom clients
- Remote tower compounds, secured urban buildings, hospitals, commercial rooftops
- Real-time schedule re-optimization when site conditions changed

## AI/Agent Infrastructure
- Claude Code agent architectures for automated QA verification
- Verification agents that test real running app against domain specification
- Reproduction agents for interactive debugging
- Structured knowledge skills encoding inspection criteria as machine-readable reference
- Multi-terminal parallel agent workflows (3-6 instances)
- Evaluated every major AI coding tool since GPT-4 launch

## Career Context
- Not a traditional SWE — came through domain expertise (drone inspections + process engineering)
- Self-taught coder, learned entirely through AI-assisted development since 2023
- Best framing: "Applied AI Systems Engineer" — encodes expert knowledge into automated systems
- Based in Kanagawa, Japan, open to relocation
- BS Chemical Engineering, Lamar University

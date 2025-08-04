# Generated Prompt: Comprehensive Repository Cleanup
Generated: 2025-08-04
By: prompt-engineer
Status: DRAFT - Awaiting Review

## Project Context
- Documentation reviewed: README.md, AGENT_LOG.md
- Tech stack: Python 3.10+, Telegram Bot API, Notion API, PostgreSQL, Docker
- Relevant patterns: Repository pattern, handler decomposition, constants extraction

## The Prompt
Perform comprehensive repository cleanup and maintenance for the Telegram Notion Calendar Bot project, focusing on code quality, test coverage, and documentation consistency. This multi-phase cleanup should systematically address technical debt, improve maintainability, and ensure all components meet professional standards.

### CLEANUP SCOPE AND REQUIREMENTS

#### Phase 1: Code Quality and Dead Code Removal
- **TODO/FIXME Resolution**: Address 12 occurrences of TODO, FIXME, HACK, XXX, BUG, DEPRECATED, and LEGACY markers found across 6 files:
  - `/src/bot.py` (3 occurrences)
  - `/tests/test_security/test_security.py` (1 occurrence)
  - `/debug_sync.py` (2 occurrences)
  - `/tests/test_load/locustfile.py` (1 occurrence)
  - `/src/utils/log_sanitizer.py` (4 occurrences)
  - `/src/constants.py` (1 occurrence)
- **Dead Code Analysis**: Identify and remove unused functions, classes, imports, and commented-out code blocks
- **Dependency Audit**: Analyze requirements.txt and requirements-dev.txt for unused packages
- **Virtual Environment Cleanup**: Exclude venv directory (contains 525+ backup/temp files)

#### Phase 2: Test Suite Enhancement
- **Coverage Analysis**: Current coverage estimated at >80%, target 90%+
- **Test Organization**: 
  - Unit tests: 36 files
  - Integration tests: 6 files
  - Performance tests: 1 file
  - Security tests: 1 file
  - Load tests: 1 file
- **Missing Test Areas**: Identify untested edge cases, error paths, and integration scenarios
- **Test Performance**: Optimize slow tests (current avg: 0.16s per test)
- **Mock Improvements**: Enhance mock quality for external services (Notion, Telegram, OpenAI)

#### Phase 3: Documentation Overhaul
- **Documentation Structure**: 34 markdown files across docs/ directory
- **Consolidation**: Merge redundant docs (e.g., multiple MEMO_*.md files)
- **Archive Management**: Review 15 files in docs/archive/ for relevance
- **API Documentation**: Update API_DOCUMENTATION.md and API_REFERENCE.md for consistency
- **README Maintenance**: Ensure README.md reflects current features and architecture
- **Migration Guides**: Update MIGRATION_GUIDE.md for latest version (3.1.1)
- **Dead Links**: Check and fix all internal documentation references

#### Phase 4: Project Structure Optimization
- **File Organization**:
  - Remove temporary files (*.pyc, *.orig, *.bak, ~, *.swp)
  - Clean up debug files (debug_sync.py if no longer needed)
  - Organize scattered documentation files in root directory
- **Configuration Cleanup**: 
  - Review users_config.example.json vs users_config.json
  - Validate docker-compose.yml and Dockerfile configurations
- **Script Consolidation**: Review multiple test runner scripts (run_tests.sh, run_all_tests.sh, run_specific_tests.py)

#### Phase 5: Code Consistency and Standards
- **Import Organization**: Ensure consistent import ordering with isort
- **Type Hints**: Add missing type hints (current: partial coverage)
- **Docstrings**: Add/update docstrings for all public methods and classes
- **Constants**: Review constants.py for unused or duplicate values
- **Error Handling**: Standardize error handling patterns across all modules
- **Logging**: Ensure consistent logging patterns and appropriate log levels

### SPECIFIC TECHNICAL REQUIREMENTS

1. **Python Code Standards**:
   - Black formatting (line length: 100)
   - isort with Black profile
   - flake8 compliance (max-line-length=100, ignore=E203,W503)
   - mypy strict mode where applicable

2. **Test Requirements**:
   - All new code must have tests
   - Integration tests for critical user flows
   - Performance benchmarks for date calculations
   - Security tests for input validation

3. **Documentation Standards**:
   - Markdown formatting consistency
   - Code examples must be tested and working
   - API documentation must match implementation
   - Changelog entries for all changes

4. **Collaboration with doc-writer**:
   - After code cleanup, engage doc-writer for:
     - Updating affected documentation
     - Creating missing documentation
     - Consolidating redundant docs
     - Generating comprehensive cleanup report

Note: All agents will read from and write to AGENT_LOG.md for coordination.

## Suggested Agent Chain
1. **python-generator** → Addresses TODO/FIXME markers, removes dead code, refactors → Updates AGENT_LOG.md (Duration: 45-60 min)
2. **test-engineer** → Analyzes coverage gaps, creates missing tests, optimizes slow tests → Reads AGENT_LOG.md, adds test results (Duration: 60-90 min)
3. **code-reviewer** → Reviews cleanup changes, identifies remaining issues → Reads AGENT_LOG.md, documents findings (Duration: 30-45 min)
4. **doc-writer** → Updates all documentation, consolidates redundant files, creates cleanup report → Reads AGENT_LOG.md, finalizes documentation (Duration: 45-60 min)
5. **claude-status** → Aggregates cleanup metrics, updates project dashboard → Reads all AGENT_LOG.md entries, creates summary (Duration: 15-20 min)

**Total Estimated Duration**: 3.5 - 4.5 hours

**Alternative Parallel Execution** (if multiple agents available):
- Stream 1: python-generator → code-reviewer (Code cleanup)
- Stream 2: test-engineer (Test improvements)
- Merge: doc-writer → claude-status (Documentation and reporting)

## Execution Command
```bash
"Perform comprehensive repository cleanup and maintenance for the Telegram Notion Calendar Bot project, focusing on code quality, test coverage, and documentation consistency. Start by addressing the 12 TODO/FIXME markers in src/bot.py, tests/test_security/test_security.py, debug_sync.py, tests/test_load/locustfile.py, src/utils/log_sanitizer.py, and src/constants.py. Remove dead code, audit dependencies, enhance test coverage to 90%+, consolidate the 34 documentation files, and ensure all code follows Black/isort/flake8/mypy standards. Each phase should update AGENT_LOG.md for coordination with subsequent agents."
```

## Pre-Execution Checklist
- [x] Context verified against project documentation
- [x] Requirements complete (5 phases defined)
- [x] Agent chain logical (sequential dependencies)
- [x] Resources available (all agents confirmed in AGENT_LOG.md)
- [ ] Backup created before major changes
- [ ] Test suite passing before start
- [ ] Stakeholders notified of cleanup timeline
- [ ] Branch created for cleanup work

## Complexity and Risk Assessment

**Complexity**: HIGH - Touches all aspects of the codebase across multiple phases

**Risk Factors**:
1. **Breaking Changes Risk**: LOW - Focus on cleanup, not functionality changes
2. **Documentation Drift**: MEDIUM - Mitigated by doc-writer involvement
3. **Test Failures**: MEDIUM - Run full test suite after each phase
4. **Merge Conflicts**: LOW - Work on separate branches for each phase
5. **Performance Impact**: LOW - Cleanup should improve performance

**Mitigation Strategies**:
- Create feature branch for all cleanup work
- Run tests after each phase completion
- Use git commits to checkpoint progress
- Review changes with code-reviewer agent
- Document all changes in AGENT_LOG.md

## Success Criteria
- [ ] All TODO/FIXME markers resolved or documented
- [ ] Test coverage increased to 90%+
- [ ] Documentation consolidated and updated
- [ ] No temporary or backup files in repository
- [ ] All code passes linting and type checking
- [ ] Performance benchmarks show no regression
- [ ] Clean git history with meaningful commits
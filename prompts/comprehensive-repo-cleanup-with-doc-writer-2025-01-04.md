# Comprehensive Repository Cleanup Prompt
**STATUS: NOT EXECUTED - DRAFT ONLY**
**Generated: 2025-01-04**

## Executive Summary
This prompt orchestrates a comprehensive cleanup of the telegram-notion-calendar-bot repository, focusing on test improvements, documentation updates, and general code maintenance. The cleanup emphasizes collaboration with the doc-writer agent for documentation tasks.

## Detailed Technical Prompt

### Primary Objective
Execute a systematic repository cleanup that addresses:
1. Dead code removal and dependency optimization
2. Test suite improvements and coverage expansion
3. Documentation updates and standardization
4. Code quality improvements and consistency

### Scope Analysis
Based on repository structure:
- **Core Application**: `src/` directory with handlers, services, models, repositories
- **Tests**: Comprehensive test suite in `tests/` with unit, integration, and performance tests
- **Documentation**: Extensive docs in `docs/` including ADRs, guides, and changelogs
- **Configuration**: Docker setup, requirements files, and config modules

### Specific Tasks

#### 1. Repository Cleanup
- Remove unused imports across all Python files
- Identify and remove dead code paths
- Clean up deprecated functions and methods
- Optimize requirements.txt by removing unused dependencies
- Clean up log files and temporary data

#### 2. Test Suite Improvements
- Analyze test coverage and identify gaps
- Add missing unit tests for uncovered functions
- Improve test documentation and naming conventions
- Ensure all test fixtures are properly used
- Clean up redundant test code

#### 3. Documentation Updates (with doc-writer agent)
- Update all docstrings to follow consistent format
- Ensure all public APIs are documented
- Update README.md with current features
- Consolidate duplicate documentation
- Create missing documentation for new features

#### 4. Code Quality
- Apply consistent code formatting
- Fix linting issues
- Improve type hints coverage
- Standardize error handling patterns

## Recommended Agent Chain (Primary)

### Phase 1: Analysis (2-3 hours)
1. **architect-cleaner** (45 min)
   - **Purpose**: Comprehensive architecture analysis and initial cleanup
   - **Why**: This agent excels at identifying architectural issues, dead code, and will automatically create missing meta-documentation
   - **Output**: Architecture report, initial cleanup, updated PROJECT_SCOPE.md

2. **code-reviewer** (30 min)
   - **Purpose**: Deep code quality analysis
   - **Why**: Identifies security issues, performance bottlenecks, and code quality problems
   - **Output**: Detailed code review report with prioritized issues

### Phase 2: Implementation (3-4 hours)
3. **python-generator** (1 hour)
   - **Purpose**: Refactor and improve identified code issues
   - **Why**: Specialized in modern Python best practices and can update code systematically
   - **Output**: Refactored code with improvements

4. **test-engineer** (1.5 hours)
   - **Purpose**: Improve test coverage and quality
   - **Why**: Specialized in creating comprehensive test suites and identifying coverage gaps
   - **Output**: New tests, improved test organization

### Phase 3: Documentation (1-2 hours)
5. **doc-writer** (1 hour)
   - **Purpose**: Update all documentation systematically
   - **Why**: Requested by user, specialized in creating consistent, high-quality documentation
   - **Output**: Updated docstrings, API docs, and user guides

### Phase 4: Validation (30 min)
6. **claude-status** (30 min)
   - **Purpose**: Generate comprehensive cleanup report
   - **Why**: Aggregates all changes and provides metrics dashboard
   - **Output**: Updated Claude.md with cleanup metrics

## Alternative Agent Chains

### Option A: Documentation-First Approach
1. doc-writer → code-reviewer → python-generator → test-engineer → architect-cleaner
   - **When to use**: If documentation debt is the primary concern
   - **Benefit**: Ensures code changes align with documented behavior

### Option B: Test-Driven Cleanup
1. test-engineer → code-reviewer → python-generator → doc-writer → architect-cleaner
   - **When to use**: If test coverage is critically low
   - **Benefit**: Ensures all changes are properly tested

### Option C: Parallel Execution (Fastest)
- Parallel Group 1: architect-cleaner + code-reviewer
- Parallel Group 2: test-engineer + doc-writer
- Sequential: python-generator → claude-status
   - **When to use**: When time is critical
   - **Benefit**: Reduces total execution time to ~3 hours

## Complexity Assessment
- **Overall Complexity**: High
- **Risk Level**: Medium
- **Dependencies**: Requires all agents to coordinate effectively
- **Critical Points**: 
  - Ensuring no breaking changes during refactoring
  - Maintaining backward compatibility
  - Preserving existing functionality

## Duration Estimate
- **Primary Chain**: 6-9 hours
- **Alternative A**: 7-10 hours
- **Alternative B**: 6-8 hours
- **Alternative C**: 3-5 hours (parallel)

## Risk Factors and Mitigation

### Risks
1. **Breaking Changes**: Refactoring might introduce bugs
   - **Mitigation**: Run full test suite after each phase
   
2. **Documentation Drift**: Docs might not reflect code changes
   - **Mitigation**: doc-writer runs after code changes
   
3. **Merge Conflicts**: If repository is actively developed
   - **Mitigation**: Complete cleanup in single session

4. **Dependency Issues**: Removing dependencies might break features
   - **Mitigation**: Thorough testing of all features post-cleanup

### Success Criteria
- [ ] All tests pass
- [ ] Test coverage increased by at least 10%
- [ ] No linting errors
- [ ] All public APIs documented
- [ ] No unused dependencies
- [ ] Clean git status after completion

## Execution Command
```bash
# To execute this cleanup (DO NOT RUN YET):
# Use the Task tool with each agent in sequence as specified above
```

## Notes
- This prompt prioritizes quality over speed
- Each agent should commit their changes separately for easy rollback
- Consider running during low-activity periods
- Backup important data before starting
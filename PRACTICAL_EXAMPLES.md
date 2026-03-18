# MindFlow Long-Session Coordination — Practical Examples

## Example 1: Security Audit with Real-Time Feedback

### Scenario
User requests: "Audita a segurança do sistema de autenticação"

### Code Flow

```python
# 1. User sends request
user_message = "Audita a segurança do sistema de autenticação"

# 2. Orchestrator analyzes intent
router = get_intelligent_router()
intent = await router.analyze_intent_with_llm(user_message)
# Result:
# IntentAnalysis(
#     user_intent="Audit authentication system for security vulnerabilities",
#     recommended_agent=AgentType.ANALYST,
#     recommended_specialist=SpecialistType.SECURITY_GUARD,
#     execution_strategy=ExecutionStrategy.LONG_SESSION,
#     confidence=0.95,
# )

# 3. Orchestrator delegates with long_session=True
delegation_engine = get_delegation_engine()
task = DelegationTask(
    task_id=uuid4(),
    agent=AgentType.ANALYST,
    specialist=SpecialistType.SECURITY_GUARD,
    objective="Audit authentication system for vulnerabilities",
    max_iterations=30,
    expected_output="Structured list of vulnerabilities with evidence",
)

result = await delegation_engine.delegate_task(
    task=task,
    session=orchestrator_session,
    session_id=session_id,
    root_execution_id=root_execution_id,
    use_long_session=True,  # NEW
)

# 4. WorkSessionManager creates session
work_session_manager = get_work_session_manager()
work_session = await work_session_manager.create_session(
    agent_id="analyst:security_guard",
    objective="Audit authentication system for vulnerabilities",
    max_iterations=30,
    root_execution_id=root_execution_id,
)
# WorkSession(
#     session_id="ws-a1b2c3d4e5f6",
#     agent_id="analyst:security_guard",
#     objective="Audit authentication system for vulnerabilities",
#     max_iterations=30,
#     current_iteration=0,
#     status="running",
# )

# 5. Iteration 1: Explore authentication flow
coordinator = get_iteration_coordinator()
iteration_1 = await coordinator.run_iteration_with_feedback(
    session=work_session,
    iteration_number=1,
    objective="Map authentication flow: identify components, entry points, data flow",
)

# Agent (security_guard) explores:
# - Login endpoint
# - JWT generation
# - Token validation
# - Session management
# - Password storage

# Findings extracted:
findings_1 = [
    Finding(
        finding_id="f1",
        finding_type=FindingType.COMPONENT,
        title="JWT Token Generation",
        description="Found JWT generation in auth/jwt.py",
        confidence=0.95,
        evidence=["auth/jwt.py:42-67", "Uses HS256 algorithm"],
    ),
    Finding(
        finding_id="f2",
        finding_type=FindingType.COMPONENT,
        title="Password Hashing",
        description="Found password hashing in auth/password.py",
        confidence=0.95,
        evidence=["auth/password.py:10-25", "Uses bcrypt"],
    ),
]

await work_session_manager.complete_iteration(
    iteration=iteration_1,
    agent_response="Mapped authentication flow with 2 main components",
    findings=findings_1,
    confidence=0.95,
    reflection="JWT and password hashing are the critical components. Need to audit both.",
    should_continue=True,
)

# 6. Orchestrator receives findings and sends feedback
await coordinator.send_feedback_to_agent(
    session=work_session,
    feedback="Focus on JWT validation — there's a history of vulnerabilities in this area. Check for algorithm confusion attacks.",
)

# 7. Iteration 2: Deep dive into JWT validation
iteration_2 = await coordinator.run_iteration_with_feedback(
    session=work_session,
    iteration_number=2,
    objective="Analyze JWT validation: algorithm verification, signature validation, expiration checks",
)

# Agent analyzes JWT validation code
# Findings extracted:
findings_2 = [
    Finding(
        finding_id="f3",
        finding_type=FindingType.VULNERABILITY,
        title="Missing Algorithm Validation",
        description="JWT validation does not verify the algorithm matches expected value",
        confidence=0.95,
        evidence=[
            "auth/jwt.py:55: jwt.decode(token, secret)",
            "No algorithm parameter specified",
            "Vulnerable to algorithm confusion attacks",
        ],
        metadata={"severity": "high", "cve": "CVE-2015-9235"},
    ),
    Finding(
        finding_id="f4",
        finding_type=FindingType.VULNERABILITY,
        title="No Expiration Check",
        description="JWT tokens are not validated for expiration",
        confidence=0.90,
        evidence=[
            "auth/jwt.py:55: No exp claim validation",
            "Tokens valid indefinitely",
        ],
        metadata={"severity": "high"},
    ),
]

await work_session_manager.complete_iteration(
    iteration=iteration_2,
    agent_response="Found 2 critical vulnerabilities in JWT validation",
    findings=findings_2,
    confidence=0.95,
    reflection="Both vulnerabilities are critical and should be fixed immediately.",
    should_continue=True,
)

# 8. Iteration 3: Validate findings and propose fixes
iteration_3 = await coordinator.run_iteration_with_feedback(
    session=work_session,
    iteration_number=3,
    objective="Validate vulnerabilities and propose fixes",
)

findings_3 = [
    Finding(
        finding_id="f5",
        finding_type=FindingType.RECOMMENDATION,
        title="Fix Algorithm Validation",
        description="Add algorithm verification to JWT decode",
        confidence=0.95,
        evidence=[
            "jwt.decode(token, secret, algorithms=['HS256'])",
            "Prevents algorithm confusion attacks",
        ],
        metadata={"priority": "critical", "effort": "low"},
    ),
    Finding(
        finding_id="f6",
        finding_type=FindingType.RECOMMENDATION,
        title="Add Expiration Validation",
        description="Validate exp claim in JWT payload",
        confidence=0.95,
        evidence=[
            "Check exp claim against current time",
            "Reject expired tokens",
        ],
        metadata={"priority": "critical", "effort": "low"},
    ),
]

await work_session_manager.complete_iteration(
    iteration=iteration_3,
    agent_response="Proposed fixes for both vulnerabilities",
    findings=findings_3,
    confidence=0.95,
    reflection="Fixes are straightforward and should be implemented immediately.",
    should_continue=False,  # Stop iterating
)

# 9. Collect all findings
all_findings = await work_session_manager.collect_findings(work_session)
# [f1, f2, f3, f4, f5, f6]

# 10. Return structured result
result = DelegationResult(
    task_id=task.task_id,
    agent=AgentType.ANALYST,
    specialist=SpecialistType.SECURITY_GUARD,
    status="completed",
    key_findings="""
    Security Audit Results:
    
    VULNERABILITIES FOUND: 2
    - Missing Algorithm Validation (HIGH)
    - No Expiration Check (HIGH)
    
    RECOMMENDATIONS: 2
    - Fix Algorithm Validation
    - Add Expiration Validation
    """,
    full_output="[Full audit report with all details]",
    confidence=0.95,
    tokens_consumed=15000,
)

# 11. Orchestrator synthesizes and responds to user
orchestrator_response = """
Auditoria de segurança concluída com sucesso.

**Vulnerabilidades Encontradas: 2 (CRÍTICAS)**

1. **Missing Algorithm Validation**
   - JWT validation não verifica o algoritmo
   - Vulnerável a algorithm confusion attacks
   - Recomendação: Adicionar algoritmo ao jwt.decode()

2. **No Expiration Check**
   - Tokens JWT não têm validação de expiração
   - Tokens válidos indefinidamente
   - Recomendação: Validar claim 'exp'

**Próximos Passos:**
1. Implementar fixes (esforço baixo)
2. Adicionar testes de segurança
3. Fazer code review
4. Deploy em staging para validação
"""
```

---

## Example 2: Architecture Design with Alternatives

### Scenario
User requests: "Redesenha a arquitetura do módulo de cache"

### Workflow

```python
# 1. Create long session for architecture design
work_session = await work_session_manager.create_session(
    agent_id="coder:arch_tech",
    objective="Redesign cache module architecture",
    max_iterations=40,
)

# 2. Iteration 1: Analyze current architecture
iteration_1 = await coordinator.run_iteration_with_feedback(
    session=work_session,
    iteration_number=1,
    objective="Analyze current cache architecture: components, patterns, issues",
)

findings_1 = [
    Finding(
        finding_id="f1",
        finding_type=FindingType.PATTERN,
        title="Monolithic Cache",
        description="Single cache class handling all concerns",
        confidence=0.9,
        evidence=["cache/core.py: 500+ lines"],
    ),
    Finding(
        finding_id="f2",
        finding_type=FindingType.ISSUE,
        title="No Eviction Policy",
        description="Cache grows unbounded, no memory management",
        confidence=0.95,
        evidence=["cache/core.py:150: No eviction logic"],
    ),
    Finding(
        finding_id="f3",
        finding_type=FindingType.ISSUE,
        title="Synchronous Only",
        description="No async support, blocks on I/O",
        confidence=0.9,
        evidence=["cache/core.py: All methods are sync"],
    ),
]

await work_session_manager.complete_iteration(
    iteration=iteration_1,
    agent_response="Current architecture has 3 main issues",
    findings=findings_1,
    confidence=0.9,
    reflection="Architecture needs refactoring for scalability and async support",
    should_continue=True,
)

# 3. Iteration 2: Explore alternatives
iteration_2 = await coordinator.run_iteration_with_feedback(
    session=work_session,
    iteration_number=2,
    objective="Explore 3 architecture alternatives: pros/cons, trade-offs",
)

findings_2 = [
    Finding(
        finding_id="f4",
        finding_type=FindingType.ALTERNATIVE,
        title="Alternative 1: Layered Architecture",
        description="Separate concerns: storage, eviction, async",
        confidence=0.85,
        evidence=[
            "Pros: Clear separation, testable",
            "Cons: More classes, potential overhead",
        ],
        metadata={"score": 7},
    ),
    Finding(
        finding_id="f5",
        finding_type=FindingType.ALTERNATIVE,
        title="Alternative 2: Event-Driven Architecture",
        description="Cache operations as events, async by default",
        confidence=0.9,
        evidence=[
            "Pros: Async-first, scalable, decoupled",
            "Cons: More complex, harder to debug",
        ],
        metadata={"score": 9},
    ),
    Finding(
        finding_id="f6",
        finding_type=FindingType.ALTERNATIVE,
        title="Alternative 3: Plugin Architecture",
        description="Pluggable storage, eviction, serialization",
        confidence=0.8,
        evidence=[
            "Pros: Flexible, extensible",
            "Cons: Over-engineered for current needs",
        ],
        metadata={"score": 6},
    ),
]

await work_session_manager.complete_iteration(
    iteration=iteration_2,
    agent_response="Explored 3 alternatives with trade-offs",
    findings=findings_2,
    confidence=0.9,
    reflection="Alternative 2 (event-driven) seems most promising",
    should_continue=True,
)

# 4. Orchestrator sends feedback
await coordinator.send_feedback_to_agent(
    session=work_session,
    feedback="Alternative 2 (event-driven) looks good. Deep dive into it: components, message types, flow diagrams.",
)

# 5. Iteration 3: Deep dive into chosen alternative
iteration_3 = await coordinator.run_iteration_with_feedback(
    session=work_session,
    iteration_number=3,
    objective="Detail event-driven architecture: components, message types, data flow",
)

findings_3 = [
    Finding(
        finding_id="f7",
        finding_type=FindingType.COMPONENT,
        title="Event Bus",
        description="Central event dispatcher for cache operations",
        confidence=0.95,
        evidence=["Handles: put, get, evict, clear events"],
    ),
    Finding(
        finding_id="f8",
        finding_type=FindingType.COMPONENT,
        title="Storage Layer",
        description="Pluggable storage backends (memory, redis, etc.)",
        confidence=0.95,
        evidence=["Interface: StorageBackend", "Implementations: MemoryStorage, RedisStorage"],
    ),
    Finding(
        finding_id="f9",
        finding_type=FindingType.COMPONENT,
        title="Eviction Policy",
        description="Pluggable eviction strategies (LRU, LFU, TTL)",
        confidence=0.95,
        evidence=["Interface: EvictionPolicy", "Implementations: LRUPolicy, LFUPolicy, TTLPolicy"],
    ),
]

await work_session_manager.complete_iteration(
    iteration=iteration_3,
    agent_response="Detailed event-driven architecture with 3 main components",
    findings=findings_3,
    confidence=0.95,
    reflection="Architecture is well-structured and extensible",
    should_continue=True,
)

# 6. Iteration 4: Implementation plan
iteration_4 = await coordinator.run_iteration_with_feedback(
    session=work_session,
    iteration_number=4,
    objective="Create implementation plan: phases, dependencies, migration strategy",
)

findings_4 = [
    Finding(
        finding_id="f10",
        finding_type=FindingType.RECOMMENDATION,
        title="Phase 1: Core Event Bus",
        description="Implement event bus and basic event types",
        confidence=0.95,
        evidence=["Effort: 2 weeks", "Risk: Low"],
        metadata={"phase": 1, "effort_weeks": 2},
    ),
    Finding(
        finding_id="f11",
        finding_type=FindingType.RECOMMENDATION,
        title="Phase 2: Storage Layer",
        description="Implement pluggable storage backends",
        confidence=0.95,
        evidence=["Effort: 2 weeks", "Risk: Low"],
        metadata={"phase": 2, "effort_weeks": 2},
    ),
    Finding(
        finding_id="f12",
        finding_type=FindingType.RECOMMENDATION,
        title="Phase 3: Eviction Policies",
        description="Implement pluggable eviction strategies",
        confidence=0.95,
        evidence=["Effort: 1 week", "Risk: Low"],
        metadata={"phase": 3, "effort_weeks": 1},
    ),
    Finding(
        finding_id="f13",
        finding_type=FindingType.RECOMMENDATION,
        title="Phase 4: Migration",
        description="Migrate existing code to new architecture",
        confidence=0.9,
        evidence=["Effort: 1 week", "Risk: Medium"],
        metadata={"phase": 4, "effort_weeks": 1},
    ),
]

await work_session_manager.complete_iteration(
    iteration=iteration_4,
    agent_response="Created 4-phase implementation plan",
    findings=findings_4,
    confidence=0.95,
    reflection="Plan is realistic and achievable",
    should_continue=False,
)

# 7. Collect all findings
all_findings = await work_session_manager.collect_findings(work_session)

# 8. Return structured result with architecture design
result = DelegationResult(
    task_id=task.task_id,
    agent=AgentType.CODER,
    specialist=SpecialistType.ARCH_TECH,
    status="completed",
    key_findings="""
    Cache Module Architecture Redesign
    
    CURRENT ISSUES: 3
    - Monolithic design
    - No eviction policy
    - Synchronous only
    
    RECOMMENDED ARCHITECTURE: Event-Driven
    - Event Bus (central dispatcher)
    - Pluggable Storage Layer
    - Pluggable Eviction Policies
    
    IMPLEMENTATION PLAN: 4 Phases (6 weeks total)
    - Phase 1: Core Event Bus (2 weeks)
    - Phase 2: Storage Layer (2 weeks)
    - Phase 3: Eviction Policies (1 week)
    - Phase 4: Migration (1 week)
    """,
    full_output="[Full architecture design document]",
    confidence=0.95,
    tokens_consumed=18000,
)
```

---

## Example 3: Code Review with Pause/Resume

### Scenario
User requests: "Revisa este código e propõe melhorias"

### Workflow with Checkpoint

```python
# 1. Create long session for code review
work_session = await work_session_manager.create_session(
    agent_id="analyst:critic",
    objective="Review code and propose improvements",
    max_iterations=20,
)

# 2. Run iterations 1-3
for i in range(1, 4):
    iteration = await coordinator.run_iteration_with_feedback(
        session=work_session,
        iteration_number=i,
        objective=f"Review phase {i}",
    )
    # ... process iteration ...

# 3. Create checkpoint for human approval
checkpoint = await work_session_manager.create_checkpoint(
    session=work_session,
    reason="Waiting for human approval before continuing",
)

# 4. Pause session
await work_session_manager.pause_session(
    work_session.session_id,
    reason="Awaiting human review of findings",
)

# ... Human reviews findings and approves ...

# 5. Resume from checkpoint
work_session = await work_session_manager.resume_from_checkpoint(checkpoint)

# 6. Continue with iterations 4+
for i in range(4, 6):
    iteration = await coordinator.run_iteration_with_feedback(
        session=work_session,
        iteration_number=i,
        objective=f"Review phase {i}",
    )
    # ... process iteration ...

# 7. Collect all findings
all_findings = await work_session_manager.collect_findings(work_session)
```

---

## Example 4: Brainstorming with Alternatives

### Scenario
User requests: "Brainstorm ideias para melhorar a performance do sistema"

### Workflow

```python
# 1. Create long session for brainstorming
work_session = await work_session_manager.create_session(
    agent_id="analyst:brainstorm",
    objective="Brainstorm ideas to improve system performance",
    max_iterations=15,
)

# 2. Iteration 1: Identify bottlenecks
iteration_1 = await coordinator.run_iteration_with_feedback(
    session=work_session,
    iteration_number=1,
    objective="Identify current performance bottlenecks",
)

findings_1 = [
    Finding(
        finding_id="f1",
        finding_type=FindingType.ISSUE,
        title="Database Queries",
        description="N+1 queries in user listing endpoint",
        confidence=0.95,
        evidence=["api/users.py:42-50"],
    ),
    Finding(
        finding_id="f2",
        finding_type=FindingType.ISSUE,
        title="Memory Usage",
        description="Cache not evicting old entries",
        confidence=0.9,
        evidence=["cache/core.py: No eviction"],
    ),
]

await work_session_manager.complete_iteration(
    iteration=iteration_1,
    agent_response="Identified 2 main bottlenecks",
    findings=findings_1,
    confidence=0.95,
    should_continue=True,
)

# 3. Iteration 2: Brainstorm solutions for bottleneck 1
iteration_2 = await coordinator.run_iteration_with_feedback(
    session=work_session,
    iteration_number=2,
    objective="Brainstorm 5 solutions for N+1 query problem",
)

findings_2 = [
    Finding(
        finding_id="f3",
        finding_type=FindingType.ALTERNATIVE,
        title="Solution 1: Eager Loading",
        description="Load related data upfront",
        confidence=0.9,
        metadata={"score": 8, "effort": "low"},
    ),
    Finding(
        finding_id="f4",
        finding_type=FindingType.ALTERNATIVE,
        title="Solution 2: Query Batching",
        description="Batch multiple queries into one",
        confidence=0.85,
        metadata={"score": 7, "effort": "medium"},
    ),
    Finding(
        finding_id="f5",
        finding_type=FindingType.ALTERNATIVE,
        title="Solution 3: GraphQL",
        description="Use GraphQL to specify exact fields needed",
        confidence=0.8,
        metadata={"score": 6, "effort": "high"},
    ),
    Finding(
        finding_id="f6",
        finding_type=FindingType.ALTERNATIVE,
        title="Solution 4: Caching",
        description="Cache user data with TTL",
        confidence=0.9,
        metadata={"score": 9, "effort": "low"},
    ),
    Finding(
        finding_id="f7",
        finding_type=FindingType.ALTERNATIVE,
        title="Solution 5: Database Optimization",
        description="Add indexes and optimize queries",
        confidence=0.95,
        metadata={"score": 10, "effort": "low"},
    ),
]

await work_session_manager.complete_iteration(
    iteration=iteration_2,
    agent_response="Brainstormed 5 solutions with scores",
    findings=findings_2,
    confidence=0.9,
    should_continue=True,
)

# 4. Orchestrator sends feedback
await coordinator.send_feedback_to_agent(
    session=work_session,
    feedback="Solutions 4 and 5 look most promising. Combine them: add indexes AND implement caching.",
)

# 5. Iteration 3: Combine solutions
iteration_3 = await coordinator.run_iteration_with_feedback(
    session=work_session,
    iteration_number=3,
    objective="Detail combined solution: indexes + caching",
)

findings_3 = [
    Finding(
        finding_id="f8",
        finding_type=FindingType.RECOMMENDATION,
        title="Add Database Indexes",
        description="Index user_id, created_at for faster queries",
        confidence=0.95,
        metadata={"priority": "high", "effort": "low"},
    ),
    Finding(
        finding_id="f9",
        finding_type=FindingType.RECOMMENDATION,
        title="Implement User Caching",
        description="Cache user data with 5-minute TTL",
        confidence=0.95,
        metadata={"priority": "high", "effort": "low"},
    ),
    Finding(
        finding_id="f10",
        finding_type=FindingType.RECOMMENDATION,
        title="Expected Performance Gain",
        description="50-70% reduction in query time",
        confidence=0.85,
        metadata={"estimated_improvement": "60%"},
    ),
]

await work_session_manager.complete_iteration(
    iteration=iteration_3,
    agent_response="Combined solution with expected 60% improvement",
    findings=findings_3,
    confidence=0.95,
    should_continue=False,
)

# 6. Collect all findings
all_findings = await work_session_manager.collect_findings(work_session)

# 7. Return structured result
result = DelegationResult(
    task_id=task.task_id,
    agent=AgentType.ANALYST,
    specialist=SpecialistType.BRAINSTORM,
    status="completed",
    key_findings="""
    Performance Improvement Brainstorm
    
    BOTTLENECKS IDENTIFIED: 2
    - N+1 queries in user listing
    - Memory usage in cache
    
    SOLUTIONS BRAINSTORMED: 5
    - Eager Loading (score: 8)
    - Query Batching (score: 7)
    - GraphQL (score: 6)
    - Caching (score: 9) ⭐
    - Database Optimization (score: 10) ⭐
    
    RECOMMENDED APPROACH:
    Combine Database Optimization + Caching
    Expected improvement: 60% faster queries
    """,
    full_output="[Full brainstorm report]",
    confidence=0.95,
    tokens_consumed=12000,
)
```

---

## Key Patterns

### Pattern 1: Iterative Refinement
```
Iteration 1: Explore
Iteration 2: Analyze
Iteration 3: Validate
Iteration 4: Refine
Iteration 5: Finalize
```

### Pattern 2: Feedback Loop
```
Iteration N: Agent works
↓
Findings extracted
↓
Orchestrator reviews
↓
Orchestrator sends feedback
↓
Iteration N+1: Agent continues with feedback
```

### Pattern 3: Checkpoint & Resume
```
Iteration 1-3: Initial analysis
↓
Create checkpoint
↓
Pause for human approval
↓
Human reviews and approves
↓
Resume from checkpoint
↓
Iteration 4+: Continue with approved context
```

### Pattern 4: Structured Results
```
Agent response (text)
↓
Extract findings (structured)
↓
Validate findings
↓
Return DelegationResult with:
- key_findings (summary)
- full_output (details)
- findings (structured list)
- confidence (0-1)
```

---

## Benefits Demonstrated

| Benefit | Example | Impact |
|---------|---------|--------|
| **Deep Analysis** | Security audit with 3 iterations | Found 2 critical vulnerabilities |
| **Alternatives** | Architecture design with 3 alternatives | Chose best option with trade-offs |
| **Feedback Loop** | Orchestrator redirects agent | Focused analysis on high-value areas |
| **Structured Results** | Findings with type, evidence, metadata | Programmatic processing possible |
| **Pause/Resume** | Code review with human approval | Workflows with human-in-the-loop |
| **Brainstorming** | 5 solutions with scores | Ranked alternatives for decision |


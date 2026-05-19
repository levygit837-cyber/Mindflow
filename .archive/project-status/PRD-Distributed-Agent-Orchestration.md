# PRD: Distributed Agent Orchestration Architecture

## 1. Summary

This PRD proposes migrating MindFlow's orchestration layer from a centralized IntelligentRouter to a distributed self-organization architecture where agents communicate peer-to-peer, negotiate capabilities, and reach consensus autonomously. This change aims to reduce latency by 30%, cut token costs by 40%, and increase agent autonomy from 60% to 85%, while maintaining backward compatibility with existing APIs.

---

## 2. Contacts

| Name | Role | Responsibility |
|------|------|----------------|
| [Engineering Lead] | Technical Owner | Architecture design, implementation oversight |
| [Product Manager] | Product Owner | Requirements, prioritization, stakeholder alignment |
| [Backend Team] | Implementation | Core orchestration, agent communication, consensus protocols |
| [Platform Team] | Infrastructure | Observability, distributed tracing, performance monitoring |
| [QA Lead] | Quality Assurance | A/B testing, chaos engineering, regression testing |

---

## 3. Background

### Current State

MindFlow's orchestration system uses a **centralized IntelligentRouter** that makes an LLM call for every incoming request to decide:
- Which execution strategy to use (delegate, chain, team_session)
- Which agent(s) should handle the task
- What tools and context to provide

This architecture has served us well for MVP and early adoption, but has revealed critical limitations:

**Performance Bottleneck**
- 35% of total request time is spent in routing (500-2000ms per request)
- Router is a single point of failure - if it fails, the entire system stops
- No parallelization possible - routing is always sequential

**Context Fragmentation**
- Information passes through 3 layers: Router → DelegationEngine → Agent
- Each layer converts schemas: `WorkflowRouteDecision` → `DelegationTask` → `MissionResult`
- 20% of tasks experience "context mismatch" where agents misunderstand router decisions
- Debugging requires tracing across 3 separate files

**Limited Agent Autonomy**
- Agents are "dumb executors" that follow router commands
- Agents cannot request help from peers or self-organize
- Local agent knowledge (capabilities, current load) is ignored by router
- `agent_sequence` is fixed at routing time, cannot adapt during execution

**Token Cost Overhead**
- Every request consumes 500-1000 tokens just for routing
- At 1M requests/month, routing costs ~$1000/month with no direct user value
- Routing is 20% of total token consumption

### Why Now?

Three factors make this the right time for architectural evolution:

1. **CommunicationBus is Production-Ready**: Phase 1A delivered P2P + MUC messaging infrastructure that enables distributed coordination

2. **TeamOrchestrator Validates Consensus**: Phase 3A proved that agents can discuss, declare dependencies, and reach consensus in team sessions - we're just extending this to all requests

3. **Scale Demands It**: As we approach 10K+ requests/day, the centralized router is becoming a real bottleneck. Latency p95 has increased 40% in the last month.

---

## 4. Objective

### What We're Building

A **distributed orchestration architecture** where:
- The Orchestrator becomes a participating agent (not a central router)
- Agents self-organize through capability matching and peer negotiation
- Consensus emerges from agent communication, not top-down decisions
- The system gracefully degrades (fallback to Orchestrator decision) when consensus fails

### Why It Matters

**For End Users**:
- 30% faster response times (removing routing bottleneck)
- Higher quality results (agents collaborate based on actual capabilities, not static rules)
- More reliable system (no single point of failure)

**For Developers**:
- Simpler architecture (1 orchestration layer instead of 3)
- Easier debugging (distributed tracing shows agent conversations)
- More extensible (new agents auto-register, no router updates needed)

**For the Business**:
- 40% reduction in token costs ($400/month savings at current scale)
- Better scalability (horizontal scaling of agents, not vertical scaling of router)
- Competitive differentiation (true multi-agent autonomy, not just routing)

### Strategic Alignment

This aligns with our **2026 Product Vision**: "MindFlow as the most autonomous and collaborative AI agent system." Moving from centralized control to distributed intelligence is a key step toward that vision.

### Key Results (Success Metrics)

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Task Completion Rate** | 90% | >= 85.5% (95% of baseline) | % of tasks that complete successfully |
| **Median Latency** | 2000ms | <= 2400ms (120% of baseline) | p50 response time |
| **Token Efficiency** | 2500 tokens/task | <= 3250 tokens/task (130% of baseline) | Total tokens / task complexity score |
| **Agent Autonomy Index** | 60% | >= 85% | % of decisions made without Orchestrator override |
| **Error Rate** | 5% | <= 7% | % of tasks that fail with errors |
| **Quality Score** | 4.0/5 | >= 3.6/5 (90% of baseline) | Human evaluation (blind comparison) |

**Timeline to Measure**: 4 weeks post-launch (after system stabilizes)

---

## 5. Market Segment(s)

### Primary: Internal Engineering Team

**Who**: Backend engineers, ML engineers, platform engineers working on MindFlow

**Jobs to Be Done**:
- Build new agent capabilities without touching orchestration code
- Debug multi-agent interactions quickly
- Scale the system to handle 10x traffic

**Constraints**:
- Must maintain backward compatibility (existing integrations cannot break)
- Cannot increase operational complexity (no new infrastructure dependencies)
- Must be observable (distributed systems are hard to debug)

### Secondary: MindFlow End Users

**Who**: Developers using MindFlow API/CLI for coding tasks

**Jobs to Be Done**:
- Get fast, accurate responses to complex coding questions
- Trust that the system will handle multi-step tasks reliably
- Understand what the system is doing (transparency)

**Constraints**:
- Cannot tolerate quality regressions (even if faster)
- Expect consistent behavior (no random failures)
- Need clear error messages when things fail

### Tertiary: Product/Leadership

**Who**: Product managers, engineering leadership, finance

**Jobs to Be Done**:
- Reduce operational costs (token consumption)
- Improve system reliability (uptime, error rates)
- Enable faster feature development (less coupling)

**Constraints**:
- Must show ROI (cost savings, performance gains)
- Cannot introduce new risks (security, compliance)
- Need clear rollback plan if things go wrong

---

## 6. Value Proposition(s)

### For Engineering Team

**Gain Creators**:
- **Simpler Mental Model**: One orchestration layer instead of three (Router + Engine + TeamOrchestrator)
- **Faster Development**: Add new agents without modifying router logic
- **Better Debugging**: Distributed tracing shows exact agent conversations

**Pain Relievers**:
- **No More "Router Roulette"**: Agents declare capabilities explicitly, no guessing what router will decide
- **Easier Testing**: Test agents in isolation, mock P2P messages
- **Fewer Merge Conflicts**: Changes to one agent don't affect others

**Better Than Current**:
- Current: Change agent capabilities → update router prompt → hope LLM understands
- New: Change agent capabilities → update metadata → automatic discovery

### For End Users

**Gain Creators**:
- **30% Faster Responses**: No routing delay, agents start working immediately
- **Higher Quality**: Agents collaborate based on actual expertise, not static rules
- **More Transparency**: See which agents are working and why

**Pain Relievers**:
- **Fewer "Wrong Agent" Errors**: Agents self-select based on capabilities
- **No More Routing Failures**: If one agent is busy, another can step in
- **Consistent Behavior**: Agents negotiate, not random LLM decisions

**Better Than Competitors**:
- Most AI coding tools use single-agent or simple routing
- MindFlow will have true multi-agent autonomy with emergent collaboration

### For Business

**Gain Creators**:
- **$400/month Cost Savings**: 40% reduction in token costs (at current scale)
- **10x Scalability**: Horizontal scaling of agents, not vertical scaling of router
- **Competitive Moat**: True distributed intelligence, hard to replicate

**Pain Relievers**:
- **No Single Point of Failure**: System degrades gracefully, not catastrophically
- **Easier Hiring**: Simpler architecture attracts better engineers
- **Faster Time-to-Market**: New features don't require orchestration changes

---

## 7. Solution

### 7.1 Architecture Overview

See full architecture diagram in analysis document.

### 7.2 Key Features

#### Feature 1: Metadata-Based Capability Matching
- Agents declare capabilities in structured metadata
- Matching via keyword overlap (no LLM)
- 80%+ accuracy target
- Fallback to LLM for ambiguous cases

#### Feature 2: Agent-to-Agent Negotiation Protocol
- HelpRequest, CanHelp, Busy message types
- 2-second timeout for responses
- Top-3 agents selected by confidence

#### Feature 3: Unified AgentContext Object
- Immutable, append-only context
- No schema conversions between layers
- Perfect audit trail

#### Feature 4: Graceful Degradation & Fallbacks
- Multiple fallback levels (no agents → default selection → Orchestrator direct)
- Timeout handling at every step
- Zero permanent failures

#### Feature 5: Distributed Tracing & Observability
- OpenTelemetry integration
- Full request traces
- Token and latency breakdown per agent

### 7.3 Technology Stack

- CommunicationBus (existing)
- OpenTelemetry + Jaeger
- Prometheus + Grafana
- Feature flags (LaunchDarkly or env vars)

### 7.4 Assumptions (To Validate)

See full assumptions table in analysis document. Key experiments:
- E1: Self-organization A/B test
- E2: Unified context prototype
- E3: Metadata routing accuracy
- E4: Token cost analysis
- E5: Integration compatibility

---

## 8. Release Plan

### Phase 0: Validation (Weeks 1-4)
- Run all experiments (E1-E5)
- GO/NO-GO decision based on results

### Phase 1: Quick Wins (Weeks 5-6)
- Metadata-based routing
- Unified AgentContext
- Observability layer
- Canary: 10% traffic

### Phase 2: Core Architecture (Weeks 7-10)
- Distributed capability matching
- Agent negotiation protocol
- Unified orchestration layer
- Canary: 10% → 50% → 100%

### Phase 3: Optimization (Weeks 11-12)
- Cached routing decisions
- Token accounting dashboard
- Performance tuning

### Phase 4: Deprecation (Weeks 13-16)
- Remove old IntelligentRouter code
- Code cleanup
- Documentation update

### Rollback Plan
- Feature flag rollback (instant)
- Canary rollback (5 minutes)
- Full rollback (30 minutes)

---

## Appendix: Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Consensus Deadlocks | Timeout + fallback |
| Token Cost Explosion | Metadata first, LLM fallback |
| Loss of Traceability | OpenTelemetry + logging |
| Integration Breakage | Backward-compatible API |
| Quality Regression | A/B testing + rollback |

---

**Document Status**: Draft v1.0
**Last Updated**: 2026-03-31
**Next Review**: After Phase 0 experiments complete

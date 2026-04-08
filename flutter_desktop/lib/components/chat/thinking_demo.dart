import 'package:flutter/material.dart';
import '../../core/models/message.dart';
import 'thinking_block.dart';

/// Demo screen to showcase ThinkingBlock components for all agent types
/// 
/// This demonstrates:
/// - All 4 agent types (Orchestrator, Coder, Analyst, Researcher)
/// - Collapsed state (when thinking is finished)
/// - Expanded state (when thinking is active or manually expanded)
class ThinkingDemoScreen extends StatelessWidget {
  const ThinkingDemoScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF121214),
      appBar: AppBar(
        title: const Text('Thinking Components Demo'),
        backgroundColor: const Color(0xFF1A1A1C),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Active Thinking (Expanded)',
              style: TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 16),
            
            // Orchestrator - Active thinking
            ThinkingBlock(
              agentType: AgentType.orchestrator,
              reasoningLines: [
                '1. Analyzing user request for JWT implementation',
                '2. Delegating to Coder for backend implementation',
                '3. Coordinating with Analyst for security review',
              ],
              isThinking: true,
            ),
            const SizedBox(height: 16),
            
            // Coder - Active thinking
            ThinkingBlock(
              agentType: AgentType.coder,
              reasoningLines: [
                '1. Need to implement JWT authentication',
                '2. Using jose library for token generation',
                '3. Setting up refresh token rotation',
              ],
              isThinking: true,
            ),
            const SizedBox(height: 16),
            
            // Analyst - Active thinking
            ThinkingBlock(
              agentType: AgentType.analyst,
              reasoningLines: [
                '1. User wants JWT with refresh tokens',
                '2. Need to consider: storage, rotation, revocation',
                '3. httpOnly cookies are more secure than localStorage',
              ],
              isThinking: true,
            ),
            const SizedBox(height: 16),
            
            // Researcher - Active thinking
            ThinkingBlock(
              agentType: AgentType.researcher,
              reasoningLines: [
                '1. Researching JWT best practices',
                '2. Comparing different token storage strategies',
                '3. Analyzing refresh token security patterns',
              ],
              isThinking: true,
            ),
            
            const SizedBox(height: 32),
            
            const Text(
              'Completed Thinking (Collapsed - Click to Expand)',
              style: TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 16),
            
            // Orchestrator - Completed
            ThinkingBlock(
              agentType: AgentType.orchestrator,
              reasoningLines: [
                '1. Task completed successfully',
                '2. All agents coordinated properly',
                '3. Result delivered to user',
              ],
              isThinking: false,
            ),
            const SizedBox(height: 16),
            
            // Coder - Completed
            ThinkingBlock(
              agentType: AgentType.coder,
              reasoningLines: [
                '1. Code implementation finished',
                '2. Tests passing',
                '3. Ready for review',
              ],
              isThinking: false,
            ),
            const SizedBox(height: 16),
            
            // Analyst - Completed
            ThinkingBlock(
              agentType: AgentType.analyst,
              reasoningLines: [
                '1. Analysis complete',
                '2. Recommendations provided',
                '3. No security issues found',
              ],
              isThinking: false,
            ),
            const SizedBox(height: 16),
            
            // Researcher - Completed
            ThinkingBlock(
              agentType: AgentType.researcher,
              reasoningLines: [
                '1. Research complete',
                '2. Best practices documented',
                '3. Sources cited',
              ],
              isThinking: false,
            ),
          ],
        ),
      ),
    );
  }
}

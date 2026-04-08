import 'package:flutter/material.dart';
import '../../core/models/message.dart';
import 'thinking_bubble.dart';
import 'thinking_expanded.dart';

/// ThinkingBlock - Combined component that manages expanded/collapsed state
/// 
/// Behavior:
/// - When thinking starts: show Expanded state with reasoning content
/// - When thinking finishes: collapse to "Reasoning" with option to expand
/// - Events appear in chat according to appearance
/// 
/// Usage:
/// ```dart
/// ThinkingBlock(
///   agentType: AgentType.analyst,
///   reasoningLines: ['1. First thought', '2. Second thought'],
///   isThinking: true, // Show expanded when actively thinking
/// )
/// ```
class ThinkingBlock extends StatefulWidget {
  final AgentType agentType;
  final List<String> reasoningLines;
  final bool isThinking;

  const ThinkingBlock({
    super.key,
    required this.agentType,
    required this.reasoningLines,
    this.isThinking = false,
  });

  @override
  State<ThinkingBlock> createState() => _ThinkingBlockState();
}

class _ThinkingBlockState extends State<ThinkingBlock> {
  bool _isExpanded = false;

  @override
  void initState() {
    super.initState();
    // Auto-expand when actively thinking
    _isExpanded = widget.isThinking;
  }

  @override
  void didUpdateWidget(ThinkingBlock oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Auto-expand when thinking starts
    if (widget.isThinking && !oldWidget.isThinking) {
      setState(() {
        _isExpanded = true;
      });
    }
  }

  void _toggleExpand() {
    setState(() {
      _isExpanded = !_isExpanded;
    });
  }

  @override
  Widget build(BuildContext context) {
    // If actively thinking or manually expanded, show expanded view
    if (_isExpanded) {
      return ThinkingExpanded(
        agentType: widget.agentType,
        reasoningLines: widget.reasoningLines,
        onCollapse: widget.isThinking ? null : _toggleExpand,
      );
    }
    
    // Otherwise show collapsed bubble
    return ThinkingBubble(
      agentType: widget.agentType,
      onTap: _toggleExpand,
      isExpanded: _isExpanded,
    );
  }
}

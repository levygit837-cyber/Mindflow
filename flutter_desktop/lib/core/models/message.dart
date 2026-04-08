/// Represents different types of agents in the system
/// Colors defined in AppColors: orchestrator, coder, analyst, researcher
enum AgentType {
  user,
  orchestrator,
  coder,
  analyst,
  researcher,
}

/// Extension to get display name and color reference
extension AgentTypeExtension on AgentType {
  String get displayName {
    switch (this) {
      case AgentType.user:
        return 'Você';
      case AgentType.orchestrator:
        return 'Orchestrator';
      case AgentType.coder:
        return 'Coder';
      case AgentType.analyst:
        return 'Analyst';
      case AgentType.researcher:
        return 'Researcher';
    }
  }
  
  String get colorName {
    switch (this) {
      case AgentType.user:
        return 'user';
      case AgentType.orchestrator:
        return 'orchestrator';
      case AgentType.coder:
        return 'coder';
      case AgentType.analyst:
        return 'analyst';
      case AgentType.researcher:
        return 'researcher';
    }
  }
}

/// Tool call representation for agent tool usage
class ToolCall {
  final String id;
  final String name;
  final Map<String, dynamic> parameters;
  final String? result;
  final bool isComplete;
  
  const ToolCall({
    required this.id,
    required this.name,
    required this.parameters,
    this.result,
    this.isComplete = false,
  });
  
  factory ToolCall.fromJson(Map<String, dynamic> json) {
    return ToolCall(
      id: json['id'] as String,
      name: json['name'] as String,
      parameters: json['parameters'] as Map<String, dynamic>,
      result: json['result'] as String?,
      isComplete: json['is_complete'] as bool? ?? false,
    );
  }
  
  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'parameters': parameters,
    'result': result,
    'is_complete': isComplete,
  };
}

/// Represents a chat message from user or agent
/// Supports streaming content, tool calls, and citations
class AgentMessage {
  final String id;
  final String content;
  final AgentType agent;
  final DateTime timestamp;
  final bool isStreaming;
  final List<ToolCall>? toolCalls;
  final List<String>? citations;
  
  const AgentMessage({
    required this.id,
    required this.content,
    required this.agent,
    required this.timestamp,
    this.isStreaming = false,
    this.toolCalls,
    this.citations,
  });
  
  factory AgentMessage.fromJson(Map<String, dynamic> json) {
    return AgentMessage(
      id: json['id'] as String,
      content: json['content'] as String,
      agent: _parseAgentType(json['agent'] as String?),
      timestamp: DateTime.parse(json['timestamp'] as String),
      isStreaming: json['is_streaming'] as bool? ?? false,
      toolCalls: (json['tool_calls'] as List<dynamic>?)
          ?.map((e) => ToolCall.fromJson(e as Map<String, dynamic>))
          .toList(),
      citations: (json['citations'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
    );
  }
  
  Map<String, dynamic> toJson() => {
    'id': id,
    'content': content,
    'agent': agent.name,
    'timestamp': timestamp.toIso8601String(),
    'is_streaming': isStreaming,
    'tool_calls': toolCalls?.map((e) => e.toJson()).toList(),
    'citations': citations,
  };
  
  static AgentType _parseAgentType(String? type) {
    switch (type?.toLowerCase()) {
      case 'user':
        return AgentType.user;
      case 'coder':
        return AgentType.coder;
      case 'analyst':
        return AgentType.analyst;
      case 'researcher':
        return AgentType.researcher;
      case 'orchestrator':
      default:
        return AgentType.orchestrator;
    }
  }
  
  AgentMessage copyWith({
    String? id,
    String? content,
    AgentType? agent,
    DateTime? timestamp,
    bool? isStreaming,
    List<ToolCall>? toolCalls,
    List<String>? citations,
  }) {
    return AgentMessage(
      id: id ?? this.id,
      content: content ?? this.content,
      agent: agent ?? this.agent,
      timestamp: timestamp ?? this.timestamp,
      isStreaming: isStreaming ?? this.isStreaming,
      toolCalls: toolCalls ?? this.toolCalls,
      citations: citations ?? this.citations,
    );
  }
  
  @override
  String toString() => 
      'AgentMessage(id: $id, agent: ${agent.displayName}, streaming: $isStreaming)';
}

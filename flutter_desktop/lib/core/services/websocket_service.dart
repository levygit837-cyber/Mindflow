import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/message.dart';
import '../models/session.dart';

/// WebSocket service for real-time communication with Python backend
/// Handles connection management, message sending/receiving, and state
class WebSocketService extends ChangeNotifier {
  final String backendUrl;
  WebSocketChannel? _channel;
  
  // Connection state
  bool _isConnected = false;
  bool get isConnected => _isConnected;
  
  // Sessions list
  final List<Session> _sessions = [];
  List<Session> get sessions => List.unmodifiable(_sessions);
  
  // Current session
  String? _currentSessionId;
  String? get currentSessionId => _currentSessionId;
  
  // Messages for current session
  final List<AgentMessage> _messages = [];
  List<AgentMessage> get messages => List.unmodifiable(_messages);
  
  // Available models (Gemini via Vertex AI as default)
  final List<String> _availableModels = [
    'gemini-3.1-flash-lite-preview',
    'gemini-3.1-pro-preview',
    'claude-4-sonnet',
    'gpt-4',
  ];
  List<String> get availableModels => List.unmodifiable(_availableModels);

  // Selected model (default to Gemini 3.1 Flash Lite via Vertex AI)
  String _selectedModel = 'gemini-3.1-flash-lite-preview';
  String get selectedModel => _selectedModel;
  
  // Selected folder
  String? _selectedFolder;
  String? get selectedFolder => _selectedFolder;
  
  // Stream controllers for real-time updates
  final _messageController = StreamController<AgentMessage>.broadcast();
  Stream<AgentMessage> get messageStream => _messageController.stream;
  
  WebSocketService({required this.backendUrl}) {
    // Initialize with mock data for development
    _initializeMockData();
  }
  
  void _initializeMockData() {
    _sessions.addAll([
      Session(
        id: '1',
        title: 'Implementação de autenticação JWT',
        lastActive: DateTime.now().subtract(const Duration(minutes: 2)),
        isActive: true,
      ),
      Session(
        id: '2',
        title: 'Análise de performance do banco',
        lastActive: DateTime.now().subtract(const Duration(hours: 1)),
        isActive: false,
      ),
      Session(
        id: '3',
        title: 'Pesquisa de práticas CI/CD',
        lastActive: DateTime.now().subtract(const Duration(days: 3)),
        isActive: false,
      ),
    ]);
    _currentSessionId = '1';
  }
  
  /// Connect to WebSocket backend
  Future<void> connect() async {
    try {
      _channel = WebSocketChannel.connect(Uri.parse(backendUrl));
      
      _channel!.stream.listen(
        _onMessageReceived,
        onDone: _onConnectionClosed,
        onError: _onConnectionError,
      );
      
      _isConnected = true;
      notifyListeners();
      
      if (kDebugMode) {
        print('WebSocket connected to $backendUrl');
      }
    } catch (e) {
      if (kDebugMode) {
        print('WebSocket connection failed: $e');
      }
      _isConnected = false;
      notifyListeners();
    }
  }
  
  /// Disconnect from backend
  void disconnect() {
    _channel?.sink.close();
    _isConnected = false;
    notifyListeners();
  }
  
  /// Send a message to the backend
  void sendMessage({
    required String content,
    AgentType? agent,
    String? folder,
  }) {
    if (!_isConnected) {
      if (kDebugMode) {
        print('WebSocket not connected, message queued');
      }
      // Add to local messages for UI feedback
      _addLocalMessage(content);
      return;
    }
    
    final message = {
      'type': 'user_message',
      'content': content,
      'agent': agent?.toString().split('.').last,
      'folder': folder ?? _selectedFolder,
      'model': _selectedModel,
      'session_id': _currentSessionId,
      'timestamp': DateTime.now().toIso8601String(),
    };
    
    _channel?.sink.add(jsonEncode(message));
    _addLocalMessage(content);
    
    if (kDebugMode) {
      print('Message sent: $content');
    }
  }
  
  void _addLocalMessage(String content) {
    final message = AgentMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: content,
      agent: AgentType.user,
      timestamp: DateTime.now(),
      isStreaming: false,
    );
    _messages.add(message);
    _messageController.add(message);
    notifyListeners();
  }
  
  /// Handle incoming messages
  void _onMessageReceived(dynamic data) {
    try {
      final json = jsonDecode(data as String);
      final message = AgentMessage.fromJson(json);
      
      _messages.add(message);
      _messageController.add(message);
      notifyListeners();
      
      if (kDebugMode) {
        print('Message received: ${message.content.substring(0, 
          message.content.length > 50 ? 50 : message.content.length)}...');
      }
    } catch (e) {
      if (kDebugMode) {
        print('Error parsing message: $e');
      }
    }
  }
  
  void _onConnectionClosed() {
    _isConnected = false;
    notifyListeners();
    if (kDebugMode) {
      print('WebSocket connection closed');
    }
  }
  
  void _onConnectionError(error) {
    _isConnected = false;
    notifyListeners();
    if (kDebugMode) {
      print('WebSocket error: $error');
    }
  }
  
  /// Create a new chat session
  void createNewSession() {
    final newSession = Session(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title: 'Nova conversa',
      lastActive: DateTime.now(),
      isActive: true,
    );
    
    // Deactivate current session
    for (var i = 0; i < _sessions.length; i++) {
      if (_sessions[i].isActive) {
        _sessions[i] = _sessions[i].copyWith(isActive: false);
      }
    }
    
    _sessions.insert(0, newSession);
    _currentSessionId = newSession.id;
    _messages.clear();
    notifyListeners();
  }
  
  /// Select a session
  void selectSession(String sessionId) {
    for (var i = 0; i < _sessions.length; i++) {
      _sessions[i] = _sessions[i].copyWith(
        isActive: _sessions[i].id == sessionId,
      );
    }
    _currentSessionId = sessionId;
    notifyListeners();
  }
  
  /// Set selected model
  void setSelectedModel(String model) {
    _selectedModel = model;
    notifyListeners();
  }
  
  /// Set selected folder
  void setSelectedFolder(String? folder) {
    _selectedFolder = folder;
    notifyListeners();
  }
  
  @override
  void dispose() {
    _channel?.sink.close();
    _messageController.close();
    super.dispose();
  }
}

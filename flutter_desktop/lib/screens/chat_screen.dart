import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../components/sidebar/sidebar.dart';
import '../components/input/input_bar.dart';
import '../components/chat/center_content.dart';
import '../core/services/websocket_service.dart';

/// Main ChatScreen - Assembles all components
/// 
/// Layout:
/// - Sidebar: 260px fixed width (left)
/// - Main content: Flexible (right)
///   - CenterContent: Empty state with suggestions (center, expanded)
///   - InputBar: Bottom fixed input area
/// 
/// From Pencil: Combines tfW4C (Sidebar), w0YtT (CenterContent), QZ6wU (InputBar)
class ChatScreen extends StatelessWidget {
  const ChatScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          // Sidebar - 260px fixed
          const Sidebar(),
          
          // Main content area
          Expanded(
            child: Column(
              children: [
                // Center content - takes remaining space
                const Expanded(
                  child: CenterContent(),
                ),
                
                // Input bar - fixed at bottom
                const InputBar(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// ChatScreen with WebSocket initialization
class ChatScreenWithConnection extends StatefulWidget {
  const ChatScreenWithConnection({super.key});

  @override
  State<ChatScreenWithConnection> createState() => _ChatScreenWithConnectionState();
}

class _ChatScreenWithConnectionState extends State<ChatScreenWithConnection> {
  @override
  void initState() {
    super.initState();
    // Attempt to connect to WebSocket when screen loads
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<WebSocketService>().connect();
    });
  }

  @override
  Widget build(BuildContext context) {
    return const ChatScreen();
  }
}

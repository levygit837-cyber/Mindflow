import 'package:flutter/material.dart';
import 'package:flutter_lucide/flutter_lucide.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/services/websocket_service.dart';

/// NEW CHAT button component
/// 
/// From Pencil: sbNewChat (UO4X6)
/// - Background: bgActiveSession
/// - Border radius: 6px
/// - Height: 34px
/// - Icon: Lucide plus (orchestrator color)
/// - Text: "NEW CHAT" (JetBrains Mono, 10px, orchestrator color)
/// - Letter spacing: 1.5
class NewChatButton extends StatelessWidget {
  const NewChatButton({super.key});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () {
        context.read<WebSocketService>().createNewSession();
      },
      borderRadius: BorderRadius.circular(6),
      child: Container(
        height: 34,
        decoration: BoxDecoration(
          color: AppColors.bgActiveSession,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              LucideIcons.plus,
              size: 12,
              color: AppColors.agentOrchestrator,
            ),
            const SizedBox(width: 6),
            Text(
              'NEW CHAT',
              style: AppTypography.newChat,
            ),
          ],
        ),
      ),
    );
  }
}

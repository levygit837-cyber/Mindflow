import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/services/websocket_service.dart';
import '../../core/models/session.dart';

/// Sessions list component (scrollable)
/// 
/// From Pencil: aIZEo (Sessions container)
/// - Displays list of recent sessions
/// - Active session has left border (2px orchestrator color)
/// - Each session shows title and time
class SessionList extends StatelessWidget {
  const SessionList({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<WebSocketService>(
      builder: (context, service, child) {
        final sessions = service.sessions;
        
        return ListView.builder(
          padding: const EdgeInsets.symmetric(horizontal: 0, vertical: 8),
          itemCount: sessions.length,
          itemBuilder: (context, index) {
            final session = sessions[index];
            return _SessionItem(
              session: session,
              onTap: () => service.selectSession(session.id),
            );
          },
        );
      },
    );
  }
}

/// Individual session item
/// 
/// From Pencil: sbSess1, sbSess2, sbSess3
/// - Padding: 10,16,10,14
/// - Active: left border 2px orchestrator color, bgActiveSession
/// - Inactive: transparent border, bg transparent
/// - Gap: 8px between title and time
class _SessionItem extends StatelessWidget {
  final Session session;
  final VoidCallback onTap;

  const _SessionItem({
    required this.session,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 10, 14, 10),
        margin: const EdgeInsets.symmetric(horizontal: 0, vertical: 2),
        decoration: BoxDecoration(
          color: session.isActive ? AppColors.bgActiveSession : null,
          border: Border(
            left: BorderSide(
              color: session.isActive 
                  ? AppColors.agentOrchestrator 
                  : AppColors.lineTransparent,
              width: 2,
            ),
          ),
        ),
        child: Row(
          children: [
            // Session title (flexible)
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    session.title,
                    style: AppTypography.sessionTitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            
            const SizedBox(width: 8),
            
            // Time (right aligned)
            Text(
              session.timeAgo,
              style: AppTypography.sessionTime,
            ),
          ],
        ),
      ),
    );
  }
}

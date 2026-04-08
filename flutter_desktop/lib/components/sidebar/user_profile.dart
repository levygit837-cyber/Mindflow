import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';

/// User profile section at bottom of sidebar
/// 
/// From Pencil: irZPY (sbUser)
/// - Avatar: 32x32 circle, orchestrator bg, letter "L"
/// - User info: name + role stacked vertically
/// - Top border separator
/// - Padding: 12,14
class UserProfile extends StatelessWidget {
  const UserProfile({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: const BoxDecoration(
        border: Border(
          top: BorderSide(color: AppColors.linePrimary),
        ),
      ),
      child: Row(
        children: [
          // Avatar
          Container(
            width: 32,
            height: 32,
            decoration: const BoxDecoration(
              color: AppColors.agentOrchestrator,
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                'L',
                style: AppTypography.avatarLetter,
              ),
            ),
          ),
          
          const SizedBox(width: 10),
          
          // User info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Levy Bonito',
                  style: AppTypography.userName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  'admin',
                  style: AppTypography.userRole,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

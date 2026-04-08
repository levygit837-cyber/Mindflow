import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/services/websocket_service.dart';
import 'new_chat_button.dart';
import 'session_list.dart';
import 'user_profile.dart';

/// Main sidebar component (260px width)
/// 
/// Structure (from Pencil tfW4C / XmbF5):
/// - Logo section (MindFlow dot + text + settings)
/// - NEW CHAT button
/// - RECENT sessions label
/// - Sessions list (scrollable)
/// - User profile (bottom)
/// 
/// Styling:
/// - Width: 260px fixed
/// - Background: bgSidebar (#0F0F10)
/// - Right border: 1px linePrimary
/// - Padding: various per section
class Sidebar extends StatelessWidget {
  const Sidebar({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 260,
      decoration: const BoxDecoration(
        color: AppColors.bgSidebar,
        border: Border(
          right: BorderSide(color: AppColors.linePrimary),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Logo Section
          _buildLogoSection(),
          
          // NEW CHAT Button
          const Padding(
            padding: EdgeInsets.fromLTRB(8, 6, 8, 10),
            child: NewChatButton(),
          ),
          
          // RECENT Label
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 4),
            child: Text(
              'RECENT',
              style: AppTypography.recentLabel,
            ),
          ),
          
          // Sessions List (takes remaining space)
          const Expanded(
            child: SessionList(),
          ),
          
          // User Profile (bottom)
          const UserProfile(),
        ],
      ),
    );
  }
  
  Widget _buildLogoSection() {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
      decoration: const BoxDecoration(
        border: Border(
          bottom: BorderSide(color: AppColors.linePrimary),
        ),
      ),
      child: Row(
        children: [
          // Logo dot (orchestrator color)
          Container(
            width: 8,
            height: 8,
            decoration: const BoxDecoration(
              color: AppColors.agentOrchestrator,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          
          // MindFlow text
          Text(
            'MindFlow',
            style: AppTypography.logoText,
          ),
          
          const Spacer(),
          
          // Settings icon
          IconButton(
            icon: const Icon(
              Icons.settings_outlined,
              size: 13,
              color: AppColors.textMeta,
            ),
            onPressed: () {
              // Open settings
            },
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
        ],
      ),
    );
  }
}

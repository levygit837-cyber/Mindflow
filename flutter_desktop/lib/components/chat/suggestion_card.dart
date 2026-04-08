import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';

/// SuggestionCard component - Clickable suggestion for agents
/// 
/// From Pencil: YBatq (SuggestionCard reusable component)
/// 
/// Structure:
/// - Header: Agent dot + Label
/// - Text: Suggestion content
/// 
/// Styling:
/// - Background: bgSurface
/// - Border radius: 12px
/// - Border: 1px linePrimary
/// - Padding: 16px
/// - Gap: 10px between header and text
class SuggestionCard extends StatelessWidget {
  final String agentType;
  final String label;
  final String text;
  final VoidCallback? onTap;

  const SuggestionCard({
    super.key,
    required this.agentType,
    required this.label,
    required this.text,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final agentColor = AppColors.getAgentColor(agentType);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        width: double.infinity,
        decoration: BoxDecoration(
          color: AppColors.bgSurface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.linePrimary),
        ),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header: Agent dot + Label
            Row(
              children: [
                // Agent color dot
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: agentColor,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                
                // Agent label
                Text(
                  label,
                  style: AppTypography.suggestionLabelWithColor(agentColor),
                ),
              ],
            ),
            
            const SizedBox(height: 10),
            
            // Suggestion text
            Text(
              text,
              style: AppTypography.suggestionText,
            ),
          ],
        ),
      ),
    );
  }
}

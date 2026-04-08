import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/theme/app_colors.dart';
import '../../core/models/message.dart';

/// ThinkingBubble - Collapsed state for agent thinking/reasoning
/// 
/// From Pencil: GOlgZ (ThinkingBubble/Collapsed)
/// 
/// Structure:
/// - Horizontal frame with rounded corners (cornerRadius: 999)
/// - Dot ellipse (6x6) with agent color
/// - Text: "[Agent] thinking…"
/// - Chevron-down icon
/// 
/// Dimensions:
/// - Height: 32
/// - Padding: [0,16]
/// - Gap: 8
class ThinkingBubble extends StatelessWidget {
  final AgentType agentType;
  final VoidCallback? onTap;
  final bool isExpanded;

  const ThinkingBubble({
    super.key,
    required this.agentType,
    this.onTap,
    this.isExpanded = false,
  });

  @override
  Widget build(BuildContext context) {
    final agentColor = AppColors.getAgentColor(agentType.colorName);
    final agentName = agentType.displayName;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 32,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        decoration: BoxDecoration(
          color: AppColors.bgSurface,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: AppColors.linePrimary,
            width: 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Agent dot
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: agentColor,
                shape: BoxShape.circle,
              ),
            ),
            
            const SizedBox(width: 8),
            
            // Text
            Text(
              '$agentName thinking…',
              style: GoogleFonts.inter(
                fontSize: 12,
                fontWeight: FontWeight.normal,
                color: AppColors.textSecondary,
              ),
            ),
            
            const SizedBox(width: 8),
            
            // Chevron icon
            Icon(
              isExpanded ? Icons.chevron_up : Icons.chevron_down,
              size: 12,
              color: AppColors.textMeta,
            ),
          ],
        ),
      ),
    );
  }
}

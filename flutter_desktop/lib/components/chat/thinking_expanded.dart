import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/theme/app_colors.dart';
import '../../core/models/message.dart';

/// ThinkingExpanded - Expanded state showing agent reasoning/thinking
/// 
/// From Pencil: kPnGe (ThinkingExpanded)
/// 
/// Structure:
/// - Vertical frame with rounded corners (cornerRadius: 12)
/// - Header: dot + "[Agent] reasoning" label + chevron-up icon
/// - Divider line
/// - Body: multiple text lines with reasoning content
/// 
/// Dimensions:
/// - Width: fill_container
/// - Header padding: [10,16]
/// - Body padding: [12,16]
/// - Gap: 4 (between text lines)
class ThinkingExpanded extends StatelessWidget {
  final AgentType agentType;
  final List<String> reasoningLines;
  final VoidCallback? onCollapse;

  const ThinkingExpanded({
    super.key,
    required this.agentType,
    required this.reasoningLines,
    this.onCollapse,
  });

  @override
  Widget build(BuildContext context) {
    final agentColor = AppColors.getAgentColor(agentType.colorName);
    final agentName = agentType.displayName;

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.bgSurface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: AppColors.linePrimary,
          width: 1,
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          GestureDetector(
            onTap: onCollapse,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // Left side: dot + label
                  Row(
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
                      
                      // Label
                      Text(
                        '$agentName reasoning',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                  
                  // Chevron icon
                  Icon(
                    Icons.chevron_up,
                    size: 12,
                    color: AppColors.textMeta,
                  ),
                ],
              ),
            ),
          ),
          
          // Divider
          Container(
            height: 1,
            width: double.infinity,
            color: AppColors.linePrimary,
          ),
          
          // Body with reasoning lines
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: reasoningLines.map((line) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(
                  line,
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    fontWeight: FontWeight.normal,
                    color: AppColors.textSecondary,
                    height: 1.6,
                  ),
                ),
              )).toList(),
            ),
          ),
        ],
      ),
    );
  }
}

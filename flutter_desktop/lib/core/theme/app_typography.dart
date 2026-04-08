import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_colors.dart';

/// Typography styles matching Pencil design specifications
/// Font families: Inter (UI text), JetBrains Mono (labels, code)
class AppTypography {
  // ============================================
  // INTER FONT STYLES (Primary UI font)
  // ============================================
  
  /// Main headline - "Como posso ajudar?"
  static TextStyle headline = GoogleFonts.inter(
    fontSize: 28,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
  );
  
  /// Subtitle - "Selecione uma sugestão..."
  static TextStyle subtitle = GoogleFonts.inter(
    fontSize: 14,
    fontWeight: FontWeight.normal,
    color: AppColors.textMeta,
  );
  
  /// Suggestion card label - agent name ("Coder", "Analyst")
  static TextStyle suggestionLabel = GoogleFonts.inter(
    fontSize: 11,
    fontWeight: FontWeight.w600,
    color: AppColors.agentCoder,
  );
  
  /// Suggestion card text content
  static TextStyle suggestionText = GoogleFonts.inter(
    fontSize: 13,
    fontWeight: FontWeight.normal,
    height: 1.5,
    color: AppColors.textSecondary,
  );
  
  /// Input hint text
  static TextStyle inputHint = GoogleFonts.inter(
    fontSize: 14,
    fontWeight: FontWeight.normal,
    height: 1.6,
    color: AppColors.textGhost,
  );
  
  /// Input text
  static TextStyle inputText = GoogleFonts.inter(
    fontSize: 14,
    fontWeight: FontWeight.normal,
    color: AppColors.textPrimary,
  );
  
  /// Toolbar button text (Folder, Model selectors)
  static TextStyle toolbarText = GoogleFonts.inter(
    fontSize: 12,
    fontWeight: FontWeight.normal,
    color: AppColors.textMeta,
  );
  
  /// Hint text below input
  static TextStyle inputHintSmall = GoogleFonts.inter(
    fontSize: 11,
    fontWeight: FontWeight.normal,
    color: AppColors.textGhost,
  );
  
  /// User name in sidebar
  static TextStyle userName = GoogleFonts.inter(
    fontSize: 13,
    fontWeight: FontWeight.w500,
    color: AppColors.textPrimary,
  );
  
  /// User role in sidebar
  static TextStyle userRole = GoogleFonts.inter(
    fontSize: 10,
    fontWeight: FontWeight.normal,
    color: AppColors.textMeta,
  );
  
  // ============================================
  // JETBRAINS MONO STYLES (Code/Labels font)
  // ============================================
  
  /// Logo text - "MindFlow" in sidebar
  static TextStyle logoText = GoogleFonts.jetBrainsMono(
    fontSize: 13,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.3,
    color: AppColors.textPrimary,
  );
  
  /// NEW CHAT button text
  static TextStyle newChat = GoogleFonts.jetBrainsMono(
    fontSize: 10,
    fontWeight: FontWeight.w600,
    letterSpacing: 1.5,
    color: AppColors.agentOrchestrator,
  );
  
  /// RECENT label in sidebar
  static TextStyle recentLabel = GoogleFonts.jetBrainsMono(
    fontSize: 11,
    fontWeight: FontWeight.w600,
    letterSpacing: 2,
    color: AppColors.textMeta,
  );
  
  /// Session time (2m, 1h, 3d)
  static TextStyle sessionTime = GoogleFonts.jetBrainsMono(
    fontSize: 9,
    fontWeight: FontWeight.normal,
    color: AppColors.textGhost,
  );
  
  /// Session title
  static TextStyle sessionTitle = GoogleFonts.jetBrainsMono(
    fontSize: 12,
    fontWeight: FontWeight.w500,
    color: AppColors.textPrimary,
  );
  
  /// Avatar letter (in user profile)
  static TextStyle avatarLetter = GoogleFonts.jetBrainsMono(
    fontSize: 11,
    fontWeight: FontWeight.w600,
    color: Colors.white,
  );
  
  // ============================================
  // DYNAMIC STYLES
  // ============================================
  
  /// Get suggestion label style with specific agent color
  static TextStyle suggestionLabelWithColor(Color color) {
    return GoogleFonts.inter(
      fontSize: 11,
      fontWeight: FontWeight.w600,
      color: color,
    );
  }
}
